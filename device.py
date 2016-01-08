from .packages import requests
import shutil
import xml.etree.ElementTree as ET
from .compat import json, quote
from .exceptions import ProvidesError, DeviceConnectionsError
from .constants import *

class Device(object):

    def __init__(self, data, cid):
        self.cid = cid
        self.name = data.get('name')
        self.product = data.get('product')
        self.product_version = data.get('productVersion')
        self.platform = data.get('platform')
        self.platform_version = data.get('platformVersion')
        self.device = data.get('device')
        self.client_identifier = data.get('clientIdentifier')
        self.created_at = data.get('createdAt')
        self.last_seen_at = data.get('lastSeenAt')
        self.provides = data.get('provides').split(',')
        self.access_token = data.get('accessToken')
        self.owned = bool(int(data.get('owned')))
        self.public_address_matches = bool(
            int(data.get('publicAddressMatches')))
        self.presence = bool(int(data.get('presence')))
        self.synced = bool(int(data.get('synced', '0')))
        self.https_required = bool(int(data.get('httpsRequired', '0')))
        self.connections = [Connection(conn) for conn in data.getchildren()]
        self.active = None

    def __repr__(self):
        return '<{}:{} - {}>'.format(self.__class__.__name__, self.name,
                                     self.product)

    @property
    def headers(self):
        return {'X-Plex-Token': self.access_token}

    def active_connection(self):
        for conn in self.connections:
            if conn.test(self.access_token, secure=self.https_required):
                self.active = conn
                return self.active
        self.active = None
        return self.active

    def request(self, endpoint, method=requests.get, data=None, params=None,
                headers=None, raw=False):
        if self.active is None:
            self.active_connection()
            if self.active is None:
                raise DeviceConnectionsError(self)
        try:
            url = (self.active.uri + endpoint if self.https_required else
                   'http://{}:{}{}'.format(self.active.address,
                                           self.active.port, endpoint))
            res = method(url, headers=headers, params=params, data=data)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout):
            return None
        else:
            return (res.status_code, res.content if raw else res.text)

    def container(self, endpoint, size=None, page=None, params=None, usejson=True):
        if PROVIDES['SERVER'] not in self.provides:
            raise ProvidesError(PROVIDES['SERVER'], self.provides)
        headers = self.headers
        if usejson:
            headers['Accept'] = 'application/json'
        if size is not None and page is not None:
            headers['X-Plex-Container-Start'] = page*size
            headers['X-Plex-Container-Size'] = size
        code, msg = self.request(endpoint, method=requests.get, params=params,
                                 headers=headers)
        try:
            data = json.loads(msg)
        except Exception:
            try:
                # channels only return xml, maybe it's xml
                xml = ET.fromstring(msg)
            except Exception:
                return {}
            else:
                data = self._parse_xml(xml)
                if 'totalSize' not in data:
                    data['totalSize'] = 1
                return data
        else:
            return data

    def _parse_xml(self, root):
        children = root.getchildren()
        x = {k:v for k, v in root.items()}
        x['_elementType'] = root.tag
        if len(children):
            x['_children'] = [self._parse_xml(child) for child in children]
        return x

    def image(self, endpoint, w=None, h=None):
        if endpoint.startswith('http'):
            res = requests.get(endpoint)
            return res.content

        if PROVIDES['SERVER'] not in self.provides:
            raise ProvidesError(PROVIDES['SERVER'], self.provides)

        endpoint, params = (
            (endpoint, None) if w is None or h is None else
            ('/photo/:/transcode', {'url': self.active.url+endpoint,
                                    'width': w, 'height': h, 'maxSize': 1}))
        code, res = self.request(endpoint, headers=self.headers, params=params,
                                 raw=True)
        return res

    def set_view_offset(self, key, offset):
        if PROVIDES['SERVER'] not in self.provides:
            raise ProvidesError(PROVIDES['SERVER'], self.provides)
        code, res = self.request('/:/progress', headers=self.headers, params={
            'key': key,
            'identifier': 'com.plexapp.plugins.library',
            'time': offset
        })

    def mark_watched(self, key):
        if PROVIDES['SERVER'] not in self.provides:
            raise ProvidesError(PROVIDES['SERVER'], self.provides)
        code, res = self.request('/:/scrobble', headers=self.headers, params={
            'key': key,
            'identifier': 'com.plexapp.plugins.library',
        })
    def mark_unwatchd(self, key):
        if PROVIDES['SERVER'] not in self.provides:
            raise ProvidesError(PROVIDES['SERVER'], self.provides)
        code, res = self.request('/:/unscrobble', headers=self.headers, params={
            'key': key,
            'identifier': 'com.plexapp.plugins.library',
        })


class Connection(object):

    def __init__(self, data):
        self.protocol = data.get('protocol')
        self.address = data.get('address')
        self.port = data.get('port')
        self.uri = data.get('uri')
        self.local = bool(int(data.get('local')))
        self.active = False

    def __repr__(self):
        return '<{}:{}>'.format(self.__class__.__name__, self.uri)

    def test(self, token, secure=False, timeout=1):
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
