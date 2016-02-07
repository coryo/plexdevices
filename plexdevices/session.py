import logging
import xml.etree.ElementTree as ET
import uuid
from .packages import requests
from .compat import json
from .device import Device, Server, Player, create_device
from .exceptions import PlexTVError
from .utils import *
log = logging.getLogger(__name__)


class Session(object):
    """A Plex session.

    Basic Usage::

      >>> import plexdevices
      >>> s = plexdevices.Session(user=username, password=password)
      >>> s.refresh_devices()
      >>> on_deck = s.servers[0].media_container('/library/onDeck')
      >>> on_deck.children[0].resolve_url()
      http://server/file.mp4?X-Plex-Token=XXXXXXXXXXX
    """

    def __init__(self, user=None, password=None, token=None):
        self.product = 'plexapi-session'
        self.identifier = str(uuid.uuid5(uuid.NAMESPACE_DNS, self.product))
        self.version = 1
        self.token = token
        self.user = user
        self._devices = []
        #: List of :class:`Device <Device>`'s that provide `server` accessible by the current user.
        self.servers = []
        #: List of :class:`Device <Device>`'s that provide `player` accessible by the current user.
        self.players = []
        #: List of Plex Home users.
        self.users = []
        self._last_devices, self._last_users = None, None

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
        del self._devices[:]
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
            raise PlexTVError(str(e))

        if 200 > res.status_code >= 400:
            log.error('Response: %d - %s' % (res.status_code, res.text))
            raise PlexTVError(res.status_code)

        self._last_devices = res.text
        self._refresh_devices(res.text)

    def _refresh_devices(self, data):
        try:
            xml = ET.fromstring(data).getchildren()
        except Exception:
            log.error('Response: %d - %s' % (res.status_code, res.text))
            raise PlexTVError(res.text)
        else:
            for item in xml:
                if item.tag == 'error':
                    log.error('Response: %s' % item.text)
                    raise PlexTVError(item.text)
                elif item.tag == 'Device':
                    device = create_device(item)
                    log.debug(device)
                    self._devices.append(device)
                    if isinstance(device, Server):
                        self.servers.append(device)
                    elif isinstance(device, Player):
                        self.players.append(device)

    def dump(self):
        """Dump the session to a json string. It can be stored on disk and loaded with load() to prevent needed to connect to plex.tv."""
        session = {'user': self.user,
                   'token': self.token,
                   'identifier': self.identifier,
                   'devices': self._last_devices,
                   'users': self._last_users}
        return json.dumps(session)

    @staticmethod
    def load(session_json):
        """Load a session that has been dumped with dump()."""
        data = json.loads(session_json)
        session = Session(user=data['user'], token=data['token'])
        session._refresh_devices(data['devices'])
        session._refresh_users(data['users'])
        session.identifier = data['identifier']
        return session

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
            raise PlexTVError(str(e))

        if 200 > res.status_code >= 400:
            log.error('Response: %d - %s' % (res.status_code, res.text))
            raise PlexTVError(res.status_code)

        try:
            data = json.loads(res.text)
        except Exception:
            log.error('Response: %d - %s' % (res.status_code, res.text))
            raise PlexTVError(res.text)
        else:
            error = data.get('error', None)
            if error is not None:
                log.error('Response: %d - %s' % (res.status_code, res.text))
                raise PlexTVError(error)
            self.token = data['user']['authentication_token']

    def refresh_users(self):
        """Retrieve the Plex Home users from ``https://plex.tv/api/home/users``."""
        try:
            res = requests.get('https://plex.tv/api/home/users', headers=self.headers)
        except Exception as e:
            raise PlexTVError(str(e))
        else:
            self._last_users = res.text
            self._refresh_users(res.text)

    def _refresh_users(self, data):
        try:
            xml = ET.fromstring(data)
            data = parse_xml(xml)
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
            data = parse_xml(xml)
            log.debug(data)
            if data['_elementType'] == 'Response':
                raise PlexTVError(data['status'])
        except Exception as e:
            raise PlexTVError(str(e))
        else:
            self.token = data['authenticationToken']
            self.refresh_devices()
