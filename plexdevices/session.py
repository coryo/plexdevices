import logging
import xml.etree.ElementTree as ET
import uuid
import requests
import plexdevices.compat
import plexdevices.device
import plexdevices.exceptions
import plexdevices.utils
from plexdevices import __version__
log = logging.getLogger(__name__)


class Session(object):
    """A Plex session. You can use pickle to save and load existing session objects.
    """

    def __init__(self, user=None, password=None, token=None):
        self.product = 'plexdevices-session'
        self.identifier = str(uuid.uuid5(uuid.NAMESPACE_DNS, self.product))
        self.version = __version__
        self.token = token
        self.user = user
        #: List of :class:`Server <plexdevices.device.Server>`'s accessible by the current user.
        self.servers = []
        #: List of :class:`Player <plexdevices.device.Player>`'s accessible by the current user.
        self.players = []
        #: List of Plex Home users.
        self.users = []

        if user is not None and password is not None:
            self.login(password)

    def __repr__(self):
        return '<{}:{}>'.format(self.__class__.__name__, self.token)

    @property
    def headers(self):
        headers = {'X-Plex-Client-Identifier': self.identifier,
                   'X-Plex-Product': self.product,
                   'X-Plex-Version': self.version}
        if self.token is not None:
            headers['X-Plex-Token'] = self.token
        return headers

    def refresh_devices(self):
        """Retrieve the devices for the current user from ``https://plex.tv/api/resources``"""
        del self.servers[:]
        del self.players[:]
        try:
            log.debug('getting devices.')
            res = requests.get('https://plex.tv/api/resources',
                               headers=self.headers,
                               params={'includeHttps': 1})
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            log.error(str(e))
            raise plexdevices.exceptions.PlexTVError(str(e))

        if 200 > res.status_code >= 400:
            log.error('Response: %d - %s' % (res.status_code, res.text))
            raise plexdevices.exceptions.PlexTVError(res.status_code)

        try:
            xml = ET.fromstring(res.text)
            data = plexdevices.utils.parse_xml(xml)
        except Exception:
            log.error('Response: %d - %s' % (res.status_code, res.text))
            raise plexdevices.exceptions.PlexTVError(res.text)
        else:
            for item in data['_children']:
                if item['_elementType'] == 'error':
                    log.error('Response: %s' % item.text)
                    raise plexdevices.exceptions.PlexTVError(item.text)
                elif item['_elementType'] == 'Device':
                    device = plexdevices.device.create_device(item)
                    log.debug(device)
                    if isinstance(device, plexdevices.device.Server):
                        self.servers.append(device)
                    if isinstance(device, plexdevices.device.Player):
                        self.players.append(device)

    def login(self, password):
        """Retrieve the token for the session user from ``https://plex.tv/users/sign_in.json.``"""
        try:
            log.debug('Signing in to plex.tv as "%s"' % self.user)
            res = requests.post('https://plex.tv/users/sign_in.json',
                                data={'user[login]': self.user,
                                      'user[password]': password},
                                headers=self.headers)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            log.error(str(e))
            raise plexdevices.exceptions.PlexTVError(str(e))

        if 200 > res.status_code >= 400:
            log.error('Response: %d - %s' % (res.status_code, res.text))
            raise plexdevices.exceptions.PlexTVError(res.status_code)

        try:
            data = plexdevices.compat.json.loads(res.text)
        except Exception:
            log.error('Response: %d - %s' % (res.status_code, res.text))
            raise plexdevices.exceptions.PlexTVError(res.text)
        else:
            error = data.get('error', None)
            if error is not None:
                log.error('Response: %d - %s' % (res.status_code, res.text))
                raise plexdevices.exceptions.PlexTVError(error)
            self.token = data['user']['authentication_token']

    def refresh_users(self):
        """Retrieve the Plex Home users from ``https://plex.tv/api/home/users``."""
        try:
            res = requests.get('https://plex.tv/api/home/users', headers=self.headers)
        except Exception as e:
            raise plexdevices.exceptions.PlexTVError(str(e))
        else:
            try:
                xml = ET.fromstring(res.text)
                data = plexdevices.utils.parse_xml(xml)
                self.users = data['_children']
            except Exception as e:
                log.error('refresh users {}'.format(str(e)))

    def switch_user(self, user_id, pin=None):
        """Switch the current user to the given user id, and refresh the available devices.

        :param user_id: the `id` of the user. As given from ``https://plex.tv/api/home/users``.
        :param pin: (optional) the 4-digit PIN code of the user.
        """
        try:
            params = {'pin': pin} if pin is not None else None
            res = requests.post('https://plex.tv/api/home/users/{}/switch'.format(user_id),
                                headers=self.headers,
                                params=params)
            xml = ET.fromstring(res.text)
            data = plexdevices.utils.parse_xml(xml)
            log.debug(data)
            if data['_elementType'] == 'Response':
                raise plexdevices.exceptions.PlexTVError(data['status'])
        except Exception as e:
            raise plexdevices.exceptions.PlexTVError(str(e))
        else:
            self.token = data['authenticationToken']
            self.refresh_devices()

    def manual_add_server(self, address, port=32400, protocol='http', token=''):
        """Add a :class:`Server <plexdevices.device.Server>` to the session.

        :param address: address to the server. e.g. ``127.0.0.1``.
        :param token: (optional) the ``X-Plex-Token`` to use when accessing this server.
        """
        uri = '{}://{}:{}'.format(protocol, address, port)
        log.debug('manual_add_server: connecting to: ' + uri)
        params = {'X-Plex-Token': token} if token else {}
        try:
            res = requests.get(uri, params=params)
        except Exception as e:
            raise ConnectionError(e)
        if 200 > res.status_code >= 400:
            log.error('Response: %d - %s' % (res.status_code, res.text))
            raise ConnectionError('Response: %d - %s' % (res.status_code, res.text))
        xml = ET.fromstring(res.text)
        data = plexdevices.utils.parse_xml(xml)
        log.debug(data)
        device_data = {
            'name': data.get('friendlyName'),
            'product': 'Plex Media Server',
            'productVersion': data.get('version'),
            'clientIdentifier': data.get('machineIdentifier'),
            'provides': 'server',
            'accessToken': token,
            'httpsRequired': str(int(protocol == 'https')),
            '_children': [
                {'protocol': protocol, 'address': address, 'port': port, 'uri': uri, 'local': '1'}
            ]
        }
        try:
            server = plexdevices.device.create_device(device_data)
        except Exception as e:
            log.error('manual_add_server: ' + str(e))
            raise ConnectionError('Cannot connect to device.')
        else:
            if server._active_connection() is None:
                log.error('manual_add_server: Cannot connect to device.')
                raise ConnectionError('Cannot connect to device.')
            self.servers.append(server)
