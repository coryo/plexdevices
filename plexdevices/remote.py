import uuid
import time
import collections
import xml.etree.ElementTree as ET
import threading
import plexdevices.exceptions
import plexdevices.device
import plexdevices.compat
import plexdevices.media

LOCATIONS = {'navigation': 'navigation',
             'fullScreenVideo': 'video',
             'fullScreenMusic': 'music',
             'fullScreenPhoto': 'photo'}


class RemoteRequestHandler(plexdevices.compat.BaseHTTPRequestHandler):

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
        parsed = plexdevices.compat.urlparse(self.path)
        params = (dict([z.split('=') for z in parsed.query.split('&')])
                  if parsed.query else None)
        message = '{}\n{}'.format(parsed.path, params)
        self.wfile.write(message.encode('UTF-8'))
        self.server.remote.command(parsed.path, params)


class RemoteServer(plexdevices.compat.HTTPServer):

    def __init__(self, server_address, RequestHandlerClass, remote):
        self.timeline = collections.deque(maxlen=10)
        self.remote = remote
        super(RemoteServer, self).__init__(server_address, RequestHandlerClass)

    @property
    def last(self):
        try:
            return list(self.timeline)[-1]
        except IndexError:
            return None


class Remote(object):
    """A remote control for a Plex device.
    """
    def __init__(self, player, name, port=8000, post_callback=None):
        #: The unique identifier string for this device.
        self.identifier = str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
        #:
        self.name = name
        self.command_id = 0
        #:
        self.player = player
        #:
        self.port = port
        self.last_volume = 0
        self.server = None
        self.server_thread = None
        self.poll_thread = None
        self.subscribed = False
        self._callback = post_callback

    @property
    def headers(self):
        """Dictionary of the remote's ``X-Plex-Client-Identifier`` and ``X-Plex-Device-Name``."""
        return {'X-Plex-Client-Identifier': self.identifier,
                'X-Plex-Device-Name': self.name}

    @staticmethod
    def parse_timeline(timeline_xml_string):
        # Parse the timeline XML into a dict. the Timeline children are turned into key,value
        # pairs where the key is Timeline.type and the value is a dict of the Timeline properties.
        try:
            container = ET.fromstring(timeline_xml_string)
        except ET.ParseError:
            return None
        else:
            parsed = {k: v for k, v in container.items()}
            parsed.update({child.get('type'): {k: v for k, v in child.items()}
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
                'protocol': 'http',
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
        if self._callback is not None:
            try:
                self._callback(self.parse_timeline(data))
            except Exception as e:
                raise plexdevices.exceptions.RemoteCallbackError(e)

    def timeline_subscribe(self):
        """Subscribe to the timeline."""
        if self.subscribed:
            return
        self._start_server()
        self.command('/player/timeline/subscribe', {
            'protocol': 'http',
            'port': self.port
        })
        self.subscribed = True
        self.poll_thread.start()

    def timeline_unsubscribe(self):
        """Unsubscribe from the timeline."""
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

    def mirror(self, plex_object, **kwargs):
        """Send the player to the preplay screen of the given :class:`BaseObject <plexdevices.media.BaseObject>`."""
        server, key = plex_object.container.server, plex_object.key
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

    def play_media(self, media_object):
        """Make the player play the given :class:`MediaItem <plexdevices.media.MediaItem>`."""
        server, key = media_object.container.server, media_object.key
        headers = self.headers
        headers['X-Plex-Target-Client-Identifier'] = self.player.client_identifier
        play_queue = plexdevices.media.PlayQueue.create(server, media_object, headers)
        pqid = play_queue.id
        self.command('/player/playback/playMedia', {
            'key': key,
            'machineIdentifier': server.client_identifier,
            'address': server.active.address,
            'port': server.active.port,
            'protocol': server.active.protocol,
            'token': server.access_token,
            'offset': media_object.view_offset if media_object.in_progress else 0,
            'containerKey': '/playQueues/{}?own=1&window=200'.format(pqid),
            'commandID': self.command_id
        })

    # convenience commands
    def up(self):
        """ Navigation: up """
        self.command('/player/navigation/moveUp')

    def down(self):
        """ Navigation: down """
        self.command('/player/navigation/moveDown')

    def left(self):
        """ Navigation: left """
        self.command('/player/navigation/moveLeft')

    def right(self):
        """ Navigation: right """
        self.command('/player/navigation/moveRight')

    def select(self):
        """ Navigation: select """
        self.command('/player/navigation/select')

    def back(self):
        """ Navigation: back """
        self.command('/player/navigation/back')

    def home(self):
        """ Navigation: home """
        self.command('/player/navigation/home')

    def music(self):
        """ Navigation: music

        Navigate to the player’s music playback view, if music is currently playing.
        """
        self.command('/player/navigation/music')

    def pause(self, media_type=None):
        """ Playback control: pause

        :param media_type: (optional) ``music, photo, video`` in case there are multiple things happening."""
        args = None if media_type is None else {'type': media_type}
        self.command('/player/playback/pause', args)

    def play(self, media_type=None):
        """ Playback control: play """
        args = None if media_type is None else {'type': media_type}
        self.command('/player/playback/play', args)

    def skip_next(self, media_type=None):
        """ Playback control: skip next """
        args = None if media_type is None else {'type': media_type}
        self.command('/player/playback/skipNext', args)

    def skip_previous(self, media_type=None):
        """ Playback control: skip previous"""
        args = None if media_type is None else {'type': media_type}
        self.command('/player/playback/skipPrevious', args)

    def stop(self, media_type=None):
        """ Playback control: stop """
        args = None if media_type is None else {'type': media_type}
        self.command('/player/playback/stop', args)

    def seek(self, media_type, offset):
        """ Playback control: seek to

        :param offset: absolute position in milliseconds.
        """
        self.command('/player/playback/seekTo', {'offset': offset, 'type': media_type})

    def skip(self, media_type, key):
        """ Playback control: skip to item with matching key """
        self.command('/player/playback/skipTo', {'key': key, 'type': media_type})

    def step_back(self, media_type):
        """ Playback control: step back """
        self.command('/player/playback/stepBack', {'type': media_type})

    def step_forward(self, media_type):
        """ Playback control: step forward """
        self.command('/player/playback/stepForward', {'type': media_type})

    def volume(self, media_type, level):
        """ Playback control: set volume.

        :param media_type: mandatory. ``music, photo, video``.
        :param level: volume level [0-100]."""
        self.command('/player/playback/setParameters', {'volume': level, 'type': media_type})
