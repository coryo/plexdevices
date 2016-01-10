from .packages import requests
import shutil
import xml.etree.ElementTree as ET
from .compat import json, quote
from .exceptions import ProvidesError, DeviceConnectionsError
from .constants import *
from .media import MediaContainer, PlayQueue

class Device(object):

    def __init__(self, data):
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
                headers={}, raw=False, allow_redirects=True):
        if self.active is None:
            self.active_connection()
            if self.active is None:
                raise DeviceConnectionsError(self)
        if 'X-Plex-Token' not in headers:
            headers.update(self.headers)
        try:
            url = (self.active.uri + endpoint if self.https_required else
                   'http://{}:{}{}'.format(self.active.address,
                                           self.active.port, endpoint))
            res = method(url, headers=headers, params=params, data=data,
                         allow_redirects=allow_redirects)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout):
            return None
        else:
            if res.status_code == 302:
                return (res.status_code, res.headers['Location'])
            else:
                return (res.status_code, res.content if raw else res.text)

    def container(self, endpoint, size=None, page=None, params=None,
                  usejson=True, allow_redirects=True):
        if PROVIDES['SERVER'] not in self.provides:
            raise ProvidesError(PROVIDES['SERVER'], self.provides)
        headers = self.headers
        if usejson:
            headers['Accept'] = 'application/json'
        if size is not None and page is not None:
            headers['X-Plex-Container-Start'] = page*size
            headers['X-Plex-Container-Size'] = size
        code, msg = self.request(endpoint, method=requests.get, params=params,
                                 headers=headers,
                                 allow_redirects=allow_redirects)
        if code == 302:
            return msg
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

    def media_container(self, endpoint, size=None, page=None, params=None,
                        usejson=True):
        return MediaContainer(self, self.container(endpoint, size, page,
                                                   params, usejson))

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

    def play_queue(self, player_headers, media_object):
        if PROVIDES['SERVER'] not in self.provides:
            raise ProvidesError(PROVIDES['SERVER'], self.provides)
        headers = self.headers
        headers['Accept'] = 'application/json'
        headers.update(player_headers)
        if 'type' not in media_object:
            media = 'video'
        else:
            if media_object['type'] in ['track', 'album']:
                media = 'music'
            elif media_object['type'] in ['episode', 'season', 'movie',
                                          'video', 'clip']:
                media = 'video'
            elif media_object['type'] == 'photo':
                media = 'photo'
            else:
                media = 'video'
        # make a playQueue
        uri = 'library://{}/item/{}'.format(
            headers['X-Plex-Client-Identifier'],
            quote(media_object['key'], safe='')
        )
        code, data = self.request('/playQueues', requests.post,
                                  headers=headers,
                                  params={'type': media, 'uri': uri})
        # extract playQueueID from response
        pqid = json.loads(data)['playQueueID']
        return PlayQueue(self, self.container('/playQueues/{}'.format(pqid)))


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
