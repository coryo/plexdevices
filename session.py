import xml.etree.ElementTree as ET
import uuid
import requests
from .compat import json
from .device import Device
from .exceptions import PlexTVError
from .constants import *

class Session(object):

    def __init__(self, user=None, password=None, token=None):
        self.product = 'plexapi-session'
        self.identifier = str(uuid.uuid5(uuid.NAMESPACE_DNS, self.product))
        self.version = 1
        self.token = token
        self.user = user
        self.password = password
        self._devices = []
        self.servers = []
        self.players = []

        if user is not None and password is not None:
            self.login()

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
        """XML Only. get devices from api/resources"""
        del self._devices[:]
        del self.servers[:]
        del self.players[:]
        try:
            res = requests.get('https://plex.tv/api/resources',
                               headers=self.headers,
                               params={'includeHttps': 1})
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            raise PlexTVError(str(e))

        if 200 > res.status_code >= 400:
            raise PlexTVError(res.status_code)

        try:
            xml = ET.fromstring(res.text).getchildren()
        except Exception:
            raise PlexTVError(res.text)
        else:
            for item in xml:
                if item.tag == 'error':
                    raise PlexTVError(item.text)
                elif item.tag == 'Device':
                    device = Device(item, self.identifier)
                    self._devices.append(device)
                    if PROVIDES['SERVER'] in device.provides:
                        self.servers.append(device)
                    elif PROVIDES['PLAYER'] in device.provides:
                        self.players.append(device)

    def login(self):
        """JSON. """
        try:
            res = requests.post('https://plex.tv/users/sign_in.json',
                                data={'user[login]': self.user,
                                      'user[password]': self.password},
                                headers=self.headers)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            raise PlexTVError(str(e))

        if 200 > res.status_code >= 400:
            raise PlexTVError(res.status_code)

        try:
            data = json.loads(res.text)
        except Exception:
            raise PlexTVError(res.text)
        else:
            error = data.get('error', None)
            if error is not None:
                raise PlexTVError(error)
            self.token = data['user']['authentication_token']
