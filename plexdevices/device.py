import logging
import requests
import shutil
import xml.etree.ElementTree as ET
import plexdevices.compat
import plexdevices.exceptions
import plexdevices.hubs
import plexdevices.media
import plexdevices.utils
log = logging.getLogger(__name__)


def create_device(data):
    """Create a Device object and mixin the functionality it provides."""
    provides = data.get('provides').split(',')
    mixins = tuple([_provides_mixins(p) for p in provides
                    if _provides_mixins(p) is not None])
    return Device(data, mixins=mixins if mixins else None)


def _provides_mixins(provides):
    return {
        'server': Server,
        'player': Player,
    }.get(provides, None)


class DynamicInheritance(type):
    def __call__(cls, data, mixins=None):
        if mixins:
            assert isinstance(mixins, tuple)
            new_cls = type(cls.__name__, mixins + (cls,), {})
            return super(DynamicInheritance, new_cls).__call__(data)
        return super(DynamicInheritance, cls).__call__(data)


class Device(plexdevices.compat.with_metaclass(DynamicInheritance)):

    def __init__(self, data):
        self.data = data
        self.connections = [Connection(conn) for conn in data['_children']]
        self.active = None

    @property
    def name(self):
        """ """
        return self.data.get('name')

    @property
    def product(self):
        """Plex product name. e.g. ``Plex Media Server``"""
        return self.data.get('product')

    @property
    def product_version(self):
        """Version of the Plex product. e.g. ``0.9.16.4.1911-ee6e505``"""
        return self.data.get('productVersion')

    @property
    def platform(self):
        """Operating system of the device."""
        return self.data.get('platform')

    @property
    def platform_version(self):
        """Operating system version."""
        return self.data.get('platformVersion')

    @property
    def device(self):
        """ """
        return self.data.get('device')

    @property
    def client_identifier(self):
        """Unique identifier string."""
        return self.data.get('clientIdentifier')

    @property
    def created_at(self):
        """ """
        return self.data.get('createdAt')

    @property
    def last_seen_at(self):
        """ """
        return self.data.get('lastSeenAt')

    @property
    def provides(self):
        """:type: list"""
        return self.data.get('provides').split(',')

    @property
    def access_token(self):
        """ """
        return self.data.get('accessToken')

    @property
    def owned(self):
        """:type: bool"""
        return bool(int(self.data.get('owned', '0')))

    @property
    def public_address_matches(self):
        """:type: bool"""
        return bool(int(self.data.get('publicAddressMatches', '0')))

    @property
    def presence(self):
        """:type: bool"""
        return bool(int(self.data.get('presence', '0')))

    @property
    def synced(self):
        """:type: bool"""
        return bool(int(self.data.get('synced', '0')))

    @property
    def https_required(self):
        """:type: bool"""
        return bool(int(self.data.get('httpsRequired', '0')))

    @property
    def headers(self):
        """ """
        return {'X-Plex-Token': self.access_token}

    def __reduce__(self):
        return (Device, (self.data, tuple([_provides_mixins(p) for p in self.provides])))

    def __repr__(self):
        return '<{}:{} - {}>'.format(self.__class__.__name__, self.name,
                                     self.product)

    def _active_connection(self):
        """Test the connections. Return the working one if possible."""
        for conn in self.connections:
            if conn.test(self.access_token, secure=self.https_required):
                self.active = conn
                return self.active
        self.active = None
        return self.active

    def request(self, endpoint, method='GET', data=None, params=None,
                headers={}, raw=False, allow_redirects=True):
        """Make an HTTP request to the device.

        :param endpoint: location on server. e.g. ``/library/onDeck``.
        :param method: (optional) request function. Defaults to ``GET``.
        :param data: (optional) data to send with the request. Defaults to ``None``.
        :param params: (optional) params to include in the URL. Defaults to ``None``.
        :param headers: (optional) additional headers. Defaults to ``{}``.
        :param raw: (optional) return raw data. Defaults to ``False``.
        :param allow_redirects: (optional) follow 302 redirects. Defaults to ``True``.
        :return: (HTTP status code, data)
        :rtype: Tuple (int, str)
        """
        if self.active is None:
            self._active_connection()
            if self.active is None:
                log.error('request: unable to get an active connection.')
                raise plexdevices.exceptions.DeviceConnectionsError(self)
        if 'X-Plex-Token' not in headers:
            headers.update(self.headers)
        try:
            url = (self.active.uri + endpoint if self.https_required else
                   'http://{}:{}{}'.format(self.active.address,
                                           self.active.port, endpoint))
            log.debug(('request: URL={}, raw={}, headers={}, params={}, '
                       'allow_redirects={}').format(url, raw, headers, params,
                                                    allow_redirects))
            res = requests.request(method=method, url=url, headers=headers,
                                   params=params, data=data,
                                   allow_redirects=allow_redirects)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            log.error('request: error connecting - ' + str(e))
            self.active = None
            raise plexdevices.exceptions.DeviceConnectionsError(self)
        else:
            log.debug('response: %d' % res.status_code)
            if res.status_code == 302:
                return (res.status_code, res.headers['Location'])
            else:
                return (res.status_code, res.content if raw else res.text)


class Server(Device):
    """A :class:`Device <plexdevices.device.Device>` which provides a server."""

    def container(self, endpoint, size=None, page=None, params=None,
                  usejson=True):
        """
        :param endpoint: destination on the server. e.g. ``/library/onDeck``.
        :param size: (optional) the max number of items to retrieve.
        :param page: (optional) the page number for paging large containers.
        :param params: (optional) Dictionary of parameters to be added to the url in the request.
        :return: a Dictionary representing a Plex Media Container.
        :rtype: Dictionary
        """
        headers = self.headers
        if usejson:
            headers['Accept'] = 'application/json'
        if size is not None and page is not None:
            headers['X-Plex-Container-Start'] = page * size
            headers['X-Plex-Container-Size'] = size
        code, msg = self.request(endpoint, method='GET', params=params,
                                 headers=headers)
        return plexdevices.utils.parse_response(msg)

    def media_container(self, endpoint, size=None, page=None, params=None,
                        usejson=True):
        """
        :param endpoint: destination on the server. e.g. ``/library/onDeck``.
        :param size: (optional) the max number of items to retrieve.
        :param page: (optional) the page number for paging large containers.
        :param params: (optional) Dictionary of parameters to be added to the url in the request.
        :return: a :class:`MediaContainer <plexdevices.media.MediaContainer>` representing a Plex Media Container.
        :rtype: :class:`MediaContainer <plexdevices.media.MediaContainer>`
        """
        data = self.container(endpoint, size, page, params, usejson)
        return plexdevices.media.MediaContainer(self, data)

    def image(self, endpoint, w=None, h=None):
        """If w and h are set, the server will transcode the image to the given size.

        :param endpoint: location of the image. This can also be a full URL of an image not on the server (for easy channel support).
        :param w: (optional) width to transcode.
        :param h: (optional) height to transcode.
        :return: Raw data of an image.
        """
        if endpoint.startswith('http'):
            res = requests.get(endpoint)
            return res.content

        endpoint, params = (
            (endpoint, None) if w is None or h is None else
            ('/photo/:/transcode', {'url': endpoint,
                                    'width': w, 'height': h, 'maxSize': 1}))
        code, res = self.request(endpoint, headers=self.headers, params=params,
                                 raw=True)
        return res

    def hub(self, endpoint, size=None, page=None, params=None):
        """`added in 0.4.0`

        :param endpoint: destination on the hubs api. e.g. ``/hubs/onDeck``.
        :param params: (optional) Dictionary of parameters to be added to the url in the request.

        :rtype: :class:`HubsContainer <plexdevices.hubs.HubsContainer>`
        """
        data = self.container(endpoint, size, page, params)
        return plexdevices.hubs.HubsContainer(self, data)


class Player(Device):
    """A :class:`Device <plexdevices.device.Device>` which provides a player."""
    pass


class Connection(object):
    """A Plex device connection."""

    def __init__(self, data):
        self.data = data
        #: indicator of whether the connection is active or not.
        self.active = False
        #: uri set by test()
        self.url = None

    @property
    def protocol(self):
        return self.data.get('protocol')

    @property
    def address(self):
        return self.data.get('address')

    @property
    def port(self):
        return self.data.get('port')

    @property
    def uri(self):
        return self.data.get('uri')

    @property
    def local(self):
        return bool(int(self.data.get('local')))

    def __repr__(self):
        return '<{}:{}>'.format(self.__class__.__name__, self.uri)

    def test(self, token, secure=False, timeout=1):
        """Test the connection with the given X-Plex-Token."""
        try:
            url = (self.uri if secure else
                   'http://{}:{}'.format(self.address, self.port))
            res = requests.get(url, timeout=timeout,
                               headers={'X-Plex-Token': token})
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout):
            self.active = False
        else:
            self.active = 200 <= res.status_code < 400
            self.url = url
        return self.active
