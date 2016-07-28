import logging
import requests
import plexdevices.compat
import plexdevices.exceptions
import plexdevices.hubs
import plexdevices.media
import plexdevices.utils
log = logging.getLogger(__name__)


def create_device(data):
    """Create a Device object and mixin the functionality it provides."""
    provides = data.get('provides').split(',')
    mixins = tuple([x for x in [_provides_mixins(p) for p in provides] if x is not None])
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
            mixins = tuple([x for x in mixins if x is not None])
            new_cls = type(cls.__name__, mixins + (cls,), {})
            return super(DynamicInheritance, new_cls).__call__(data)
        return super(DynamicInheritance, cls).__call__(data)


class Device(plexdevices.compat.with_metaclass(DynamicInheritance)):

    def __init__(self, data):
        self.data = data
        self.connections = [Connection(conn) for conn in data['_children']]
        self.active = None

    def __eq__(self, other):
        if self.__class__.__name__ == other.__class__.__name__:
            return self.client_identifier == other.client_identifier
        return False

    @property
    def name(self):
        """:obj:`str`"""
        return self.data.get('name')

    @property
    def product(self):
        """:obj:`str`: Plex product name. e.g. ``Plex Media Server``"""
        return self.data.get('product')

    @property
    def product_version(self):
        """:obj:`str`: Version of the Plex product. e.g. ``0.9.16.4.1911-ee6e505``"""
        return self.data.get('productVersion')

    @property
    def platform(self):
        """:obj:`str`: Operating system of the device."""
        return self.data.get('platform')

    @property
    def platform_version(self):
        """:obj:`str`: Operating system version."""
        return self.data.get('platformVersion')

    @property
    def device(self):
        """:obj:`str`"""
        return self.data.get('device')

    @property
    def client_identifier(self):
        """:obj:`str`: Unique identifier string."""
        return self.data.get('clientIdentifier')

    @property
    def created_at(self):
        """:obj:`str`"""
        return self.data.get('createdAt')

    @property
    def last_seen_at(self):
        """:obj:`str`"""
        return self.data.get('lastSeenAt')

    @property
    def provides(self):
        """:obj:`list`"""
        return self.data.get('provides').split(',')

    @property
    def access_token(self):
        """:obj:`str`"""
        return self.data.get('accessToken')

    @property
    def owned(self):
        """:obj:`bool`"""
        return bool(int(self.data.get('owned', '0')))

    @property
    def public_address_matches(self):
        """:obj:`bool`"""
        return bool(int(self.data.get('publicAddressMatches', '0')))

    @property
    def presence(self):
        """:obj:`bool`"""
        return bool(int(self.data.get('presence', '0')))

    @property
    def synced(self):
        """:obj:`bool`"""
        return bool(int(self.data.get('synced', '0')))

    @property
    def https_required(self):
        """:obj:`bool`"""
        return bool(int(self.data.get('httpsRequired', '0')))

    @property
    def headers(self):
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

    def request(self, endpoint, method='GET', **kwargs):
        """Make a request to the devices. This is a wrapper for
        :obj:`requests.request()`

        Args:
            endpoint (:obj:`str`): destination on the server.
                e.g. ``/library/onDeck``.
            method (:obj:`str`): request method.
            **kwargs: args to pass to :obj:`requests.request()`.

        Returns:
            :obj:`requests.Response`

        Raises:
            ConnectionError
            requests.exceptions.HTTPError
            requests.exceptions.Timeout
        """
        if self.active is None:
            self._active_connection()
            if self.active is None:
                log.error('request: unable to get an active connection.')
                raise ConnectionError('Unable to connect to device.')
        if 'headers' in kwargs:
            if 'X-Plex-Token' not in kwargs['headers']:
                kwargs['headers'].update(self.headers)
        else:
            kwargs['headers'] = self.headers
        url = (self.active.uri + endpoint if self.https_required else
               'http://{}:{}{}'.format(self.active.address,
                                       self.active.port, endpoint))
        log.debug('request: {} {}, {}'.format(method, url, kwargs))
        res = requests.request(method, url, **kwargs)
        res.raise_for_status()
        return res


class Server(Device):
    """A :class:`Device <plexdevices.device.Device>` which provides a server."""

    def container(self, endpoint, size=None, page=None, params=None, **kwargs):
        """
        Args:
            endpoint (:obj:`str`): destination on the server.
                e.g. ``/library/onDeck``.
            size (:obj:`int`, optional): the max number of items to retrieve.
            page (:obj:`int`, optional): the page number for paging large
                containers.
            params (:obj:`dict`, optional): Dictionary of parameters to be
                added to the url in the request.

        Returns:
            :obj:`dict`: a Dictionary representing a Plex Media Container.

        """
        headers = self.headers
        headers['Accept'] = 'application/json'
        if size is not None and page is not None:
            headers['X-Plex-Container-Start'] = page * size
            headers['X-Plex-Container-Size'] = size
        res = self.request(endpoint, method='GET', params=params,
                           headers=headers, stream=True, **kwargs)
        return plexdevices.utils.parse_response(res.text)

    def media_container(self, endpoint, size=None, page=None, params=None, **kwargs):
        """
        Args:
            endpoint (:obj:`str`): destination on the server.
                e.g. ``/library/onDeck``.
            size (:obj:`int`, optional): the max number of items to retrieve.
            page (:obj:`int`, optional): the page number for paging large
                containers.
            params (:obj:`dict`, optional): Dictionary of parameters to be
                added to the url in the request.

        Returns:
            :obj:`MediaContainer <plexdevices.media.MediaContainer>`: an
            object representing a Plex Media Container.

        """
        data = self.container(endpoint, size, page, params, **kwargs)
        return plexdevices.media.MediaContainer(
            self, data, endpoint, params, page, size)

    def image(self, endpoint, w=None, h=None, **kwargs):
        """If w and h are set, the server will transcode the image to the
        given size.

        Args:
            endpoint (:obj:`str`): location of the image. This can also be a
                full URL of an image not on the server.
            w (:obj:`int`, optional): width to transcode.
            h (:obj:`int`, optional): height to transcode.

        Returns:
             :obj:`requests.Response`

        """
        if endpoint.startswith('http'):
            log.debug('requesting image.')
            return requests.get(endpoint, stream=True, **kwargs)

        if not w or not h:
            params = None
        else:
            params = {
                'url': endpoint,
                'width': w,
                'height': h,
                'maxSize': 1
            }
            endpoint = '/photo/:/transcode'

        log.debug('requesting transcoded image  ')
        return self.request(endpoint, headers=self.headers, params=params,
                            stream=True, **kwargs)

    def photo_transcoder_url(self, url, w, h):
        params = {
            'url': url,
            'width': w,
            'height': h,
            'maxSize': 1
        }
        url = 'http://{}:{}/photo/:/transcode?X-Plex-Token={}&{}'.format(
            self.active.address, self.active.port, self.access_token,
            plexdevices.compat.urlencode(params))
        return url

    def hub(self, endpoint, size=None, page=None, params=None, **kwargs):
        """`added in 0.4.0`

        Args:
            endpoint (:obj:`str`): destination on the hubs api.
                e.g. ``/hubs/onDeck``.
            params (:obj:`dict`, optional): parameters to be added to the url
                in the request.

        Returns:
            :obj:`HubsContainer <plexdevices.hubs.HubsContainer>` an object
            representing a Media Container.

        """
        data = self.container(endpoint, size, page, params, **kwargs)
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

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.data == other.data
        return False

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
