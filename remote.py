import uuid
import time
from collections import deque
import xml.etree.ElementTree as ET
import threading
from .packages import requests
from .compat import (json, urlparse, HTTPServer, BaseHTTPRequestHandler)
from .exceptions import ProvidesError
from .constants import *

LOCATIONS = {'navigation': 'navigation',
             'fullScreenVideo': 'video',
             'fullScreenMusic': 'music',
             'fullScreenPhoto': 'photo'}

class RemoteRequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if 'content-length' not in self.headers:
            return
        content_len = int(self.headers['content-length'])
        if content_len == 0:
            return
        post_body = self.rfile.read(content_len)
        self.server.timeline.append(post_body)
        self.server.remote.timeline_post(post_body)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = (dict([z.split('=') for z in parsed.query.split('&')])
                  if parsed.query else None)
        message = '{}\n{}'.format(parsed.path, params)
        self.wfile.write(message.encode('UTF-8'))
        self.server.remote.command(parsed.path, params)


class RemoteServer(HTTPServer):

    def __init__(self, server_address, RequestHandlerClass, remote):
        self.timeline = deque(maxlen=10)
        self.remote = remote
        HTTPServer.__init__(self, server_address, RequestHandlerClass)

    @property
    def last(self):
        try:
            return list(self.timeline)[-1]
        except IndexError:
            return None


class Remote(object):

    def __init__(self, player, name, port=8000):
        if PROVIDES['PLAYER'] not in player.provides:
            raise ProvidesError(PROVIDES['PLAYER'], player.provides)
        self.identifier = str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
        self.name = name
        self.command_id = 0
        self.player = player
        self.port = port
        self.last_volume = 0
        self.server = None
        self.server_thread = None
        self.poll_thread = None
        self.subscribed = False

    @property
    def headers(self):
        return {'X-Plex-Client-Identifier': self.identifier,
                'X-Plex-Device-Name': self.name}

    @staticmethod
    def parse_timeline(timeline_xml_string):
        """Parse the timeline XML into a dict. the Timeline children are turned into key,value
        pairs where the key is Timeline.type and the value is a dict of the Timeline properties."""
        try:
            container = ET.fromstring(timeline_xml_string)
        except ET.ParseError:
            return None
        else:
            parsed = {k:v for k, v in container.items()}
            parsed.update({child.get('type'): {k:v for k, v in child.items()}
                           for child in container.getchildren()})
            return parsed

    def _create_server(self):
        self.server = RemoteServer(('', self.port), RemoteRequestHandler, self)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.poll_thread = threading.Thread(target=self._timeline_sub_poll)
        self.server_thread.daemon = True
        self.poll_thread.daemon = True

    def _start_server(self):
        self._create_server()
        self.server_thread.start()

    def _stop_server(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass

    def _timeline_sub_poll(self, rate=30):
        while self.subscribed:
            if not self.subscribed:
                break
            self.command('/player/timeline/subscribe', {
                'protocol':'http',
                'port': self.port
            })
            time.sleep(rate)

    def command(self, command, params=None):
        """Send a command to the player with optional parameters."""
        p = {'commandID': self.command_id}
        if params is not None:
            p.update(params)
        code, msg = self.player.request(command, headers=self.headers, params=p)
        self.command_id += 1
        return msg

    def timeline(self):
        """Returns the latest timeline that was POSTed from the player."""
        return self.parse_timeline(self.server.last)

    def timeline_post(self, data):
        """called whenever the player POSTs the timeline to the remote."""
        pass

    def timeline_subscribe(self):
        if self.subscribed:
            return
        self._start_server()
        self.command('/player/timeline/subscribe', {
            'protocol':'http',
            'port': self.port
        })
        self.subscribed = True
        self.poll_thread.start()

    def timeline_unsubscribe(self):
        if not self.subscribed:
            return
        self.command('/player/timeline/unsubscribe')
        self._stop_server()
        self.command_id = 0
        self.subscribed = False

    def timeline_poll(self):
        """This is an alternative to the subscribe command for controllers that cannot use
        persistent connections to receive updates from the player."""
        res = self.command('/player/timeline/poll', {'wait': 0})
        return self.parse_timeline(res)

    def timeline_active(self):
        t = self.timeline()
        if t is None or t['location'] == 'navigation':
            return None
        return t[LOCATIONS[t['location']]]

    def is_playing(self):
        t = self.timeline()
        return t is not None and t['location'] != 'navigation'

    def mirror(self, server, key, **kwargs):
        if PROVIDES['SERVER'] not in server.provides:
            raise ProvidesError(PROVIDES['SERVER'], server.provides)
        self.command('/player/mirror/details', {
            'key': key,
            'machineIdentifier': server.client_identifier,
            'address': server.active.address,
            'port': server.active.port,
            'protocol': ('http' if not server.https_required
                         else server.active.protocol),
            'token': server.access_token,
            'commandID': self.command_id
        })

    def play_media(self, server, key, mtype='video'):
        if PROVIDES['SERVER'] not in server.provides:
            raise ProvidesError(PROVIDES['SERVER'], server.provides)
        headers = self.headers
        headers.update({
            'X-Plex-Target-Client-Identifier': self.player.client_identifier,
            'X-Plex-Token': server.access_token,
            'Accept': 'application/json'
        })
        if mtype in ['track', 'album']:
            media = 'music'
        elif mtype in ['episode', 'season', 'movie', 'video']:
            media = 'video'
        elif mtype == 'photo':
            media = 'photo'
        elif mtype == 'mixed':
            media = 'video'
        # make a playQueue on `server`
        uri = 'library://{}/directory/{}'.format(
            headers['X-Plex-Client-Identifier'], key)
        code, data = server.request('/playQueues', requests.post,
                                    headers=headers,
                                    params={'type': media, 'uri': uri})
        # extract playQueueID from response
        pqid = json.loads(data).get('playQueueID', 0)
        self.command('/player/playback/playMedia', {
            'key': key,
            'machineIdentifier': server.client_identifier,
            'address': server.active.address,
            'port': server.active.port,
            'protocol': server.active.protocol,
            'token': server.access_token,
            'offset': 0,
            'containerKey': '/playQueues/{}?own=1&window=200'.format(pqid),
            'commandID': self.command_id
        })

    # NAV
    def up(self):
        self.command('/player/navigation/moveUp')

    def down(self):
        self.command('/player/navigation/moveDown')

    def left(self):
        self.command('/player/navigation/moveLeft')

    def right(self):
        self.command('/player/navigation/moveRight')

    def select(self):
        self.command('/player/navigation/select')

    def back(self):
        self.command('/player/navigation/back')

    def home(self):
        self.command('/player/navigation/home')

    def music(self):
        self.command('/player/navigation/music')
    # PLAYBACK
    def pause(self):
        self.command('/player/playback/pause')

    def play(self):
        self.command('/player/playback/play')

    def skip_next(self):
        self.command('/player/playback/skipNext')

    def skip_previous(self):
        self.command('/player/playback/skipPrevious')

    def stop(self):
        self.command('/player/playback/stop')

    def seek(self, offset): # milliseconds
        self.command('/player/playback/seekTo', {'offset': offset})

    def skip(self, key):
        self.command('/player/playback/skipTo', {'key': key})

    def step_back(self):
        self.command('/player/playback/stepBack')

    def step_forward(self):
        self.command('/player/playback/stepForward')

    def volume(self, v): # 0-100
        self.command('/player/playback/setParameters', {'volume': v})
