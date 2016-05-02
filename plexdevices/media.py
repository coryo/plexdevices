import logging
import time
import datetime
import plexdevices.factory
import plexdevices.compat
log = logging.getLogger(__name__)


class MediaContainer(object):
    """An object representing a Plex MediaContainer."""

    def __init__(self, server, data):
        #: Dictionary of the MediaContainer's values.
        self.data = data
        #: The :class:`Server <plexdevices.device.Server>` which this container was retrieved from.
        self.server = server
        if '_children' in data:
            #: List of items in the container.
            self.children = []
            for c in data['_children']:
                cls = plexdevices.factory.MediaFactory.factory(c)
                if cls is not None:
                    item = cls(c, self)
                    self.children.append(item)
            del self.data['_children']
        else:
            self.children = []

    def __len__(self):
        return len(self.children)

    @property
    def identifier(self):
        return self.data.get('identifier')

    @property
    def title1(self):
        return self.data.get('title1', '')

    @property
    def title2(self):
        return self.data.get('title2', '')

    @property
    def total_size(self):
        return int(self.data.get('totalSize', 0))

    @property
    def view_group(self):
        return self.data.get('viewGroup')

    @property
    def mixed_parents(self):
        return bool(int(self.data.get('mixedParents', 0)))

    @property
    def filters(self):
        return bool(int(self.data.get('filters', 0)))

    @property
    def is_library(self):
        return self.identifier == 'com.plexapp.plugins.library'

    @property
    def has_parent(self):
        return 'parentKey' in self.data

    @property
    def parent_index(self):
        return int(self.data.get('parentIndex', -1))

    @property
    def parent_title(self):
        return self.data.get('parentTitle')


class PlayQueue(MediaContainer):
    """An object representing a Plex PlayQueue. A PlayQueue is a playlist that is maintained by the server.

    When you want to play a Media item, use the :func:`~plexdevices.PlayQueue.create` method. Then during
    playback, use :func:`~plexdevices.PlayQueue.timeline_update` to let the server know about the players
    state."""

    @property
    def selected_item_id(self):
        return self.data.get('playQueueSelectedItemID')

    @property
    def selected_item_offset(self):
        return int(self.data.get('playQueueSelectedItemOffset', 0))

    @property
    def id(self):
        return self.data.get('playQueueID')

    @property
    def selected_item(self):
        """The selected :class:`MediaItem <plexdevices.media.MediaItem>`"""
        try:
            return self.children[self.selected_item_offset]
        except Exception:
            return None

    def update(self):
        """Update the :class:`PlayQueue <plexdevices.media.PlayQueue>`'s data from its server."""
        data = self.server.request('/playQueues/{}'.format(self.id))
        self.__init__(self.server, data)

    def select(self, item):
        if item not in self.children or 'playQueueItemID' not in item.data:
            log.debug('select: item is not valid.')
            return None
        self.data['playQueueSelectedItemID'] = item.data['playQueueItemID']
        self.data['playQueueSelectedItemOffset'] = self.children.index(item)
        return item

    def get_next(self):
        """Select and return the next :class:`MediaItem <plexdevices.media.MediaItem>` in the PlayQueue, or `None`."""
        if self.selected_item is None:
            return None
        i = self.children.index(self.selected_item) + 1
        return self.select(self.children[i]) if 0 <= i <= len(self) - 1 else None

    def get_prev(self):
        """Select and return the previous :class:`MediaItem <plexdevices.media.MediaItem>` in the PlayQueue, or `None`."""
        if self.selected_item is None:
            return None
        i = self.children.index(self.selected_item) - 1
        return self.select(self.children[i]) if 0 <= i <= len(self) - 1 else None

    def remove_item(self, item):
        """Remove a :class:`MediaItem <plexdevices.media.MediaItem>` from the PlayQueue."""
        url = '/playQueues/{}/items/{}'.format(self.id,
                                               item.data['playQueueItemID'])
        code, data = self.server.request(url, method='DELETE',
                                         headers={'Accept': 'application/json'})
        if 200 <= code < 400:
            self.__init__(self.server, plexdevices.compat.json.loads(data))
        else:
            log.error('playqueue: could not remove item from playqueue.')

    def add_item(self, item, player_headers):
        """Add a :class:`MediaDirectory <plexdevices.media.MediaDirectory>` or
        :class:`MediaItems <plexdevices.media.MediaItem>` to the PlayQueue."""
        headers = self.server.headers
        headers['Accept'] = 'application/json'
        headers.update(player_headers)
        media, uri = self.media_uri(item, player_headers)
        code, data = self.server.request('/playQueues/{}'.format(self.id),
                                         method='PUT',
                                         headers=headers,
                                         params={'type': media, 'uri': uri})
        if 200 <= code < 400:
            self.__init__(self.server, plexdevices.compat.json.loads(data))
        else:
            log.error('playqueue: could not add item to playqueue.')

    def timeline_update(self, item, time, headers, state='playing'):
        """Update the timeline. This should be done frequently during playback.
        The server will update the view offset of the item and handle the watched/unwatched state.

        :param item: the play queue item.
        :param time: the current playback time in ms.
        :param headers: the players headers. ``X-Plex-Client-Identifier``, ``X-Plex-Device-Name``.
        :param state: playing, stopped, paused"""
        if item is None or 'playQueueItemID' not in item.data:
            return False
        code, res = self.server.request('/:/timeline', headers=headers, params={
            'state': state,
            'identifier': self.identifier,
            'playQueueItemID': item.data['playQueueItemID'],
            'ratingKey': item.rating_key,
            'duration': item.duration,
            'time': min(time, item.duration),
            'key': item.key
        })
        log.debug(('PlayQueue: TIMELINE '
                   '{}/{} - {}'.format(time, item.duration, code)))
        return True

    @staticmethod
    def media_uri(item, player_headers):
        item_type = 'directory' if isinstance(item, Directory) else 'item'
        if isinstance(item, (Track, Album)):
            media = 'music'
        elif isinstance(item, (Episode, Movie, VideoClip)):
            media = 'video'
        elif isinstance(item, Photo):
            media = 'photo'
        else:
            media = 'video'
        uri = 'library://{}/{}/{}'.format(
            player_headers['X-Plex-Client-Identifier'],
            item_type,
            plexdevices.compat.quote(item.key, safe=''))
        return (media, uri)

    @staticmethod
    def create(item, player_headers):
        """Create a PlayQueue on a server and return a PlayQueue object.

        :param item: the :class:`Media <plexdevices.media.Media>` to be the initial item added to the PlayQueue.
        :param player_headers: Dictionary of headers identifying the player using the PlayQueue. Must include X-Plex-Client-Identifier and X-Plex-Device-Name.
        :return: :class:`PlayQueue <plexdevices.media.PlayQueue>` object
        :rtype: plexdevices.PlayQueue
        """
        if 'X-Plex-Client-Identifier' not in player_headers:
            return None
        server = item.container.server
        headers = server.headers
        headers['Accept'] = 'application/json'
        headers.update(player_headers)
        media, uri = PlayQueue.media_uri(item, player_headers)
        code, data = server.request('/playQueues',
                                    method='POST',
                                    headers=headers,
                                    params={'type': media, 'uri': uri})
        pqid = plexdevices.compat.json.loads(data)['playQueueID']
        return PlayQueue(server, server.container('/playQueues/{}'.format(pqid)))


class BaseObject(object):
    """Abstract base class. The base class of all items in containers.
    ::

        # generically emit an item in PyQt5
        item_selected = pyqtSignal(plexdevices.BaseObject)
    """

    def __init__(self, data, container):
        # Dictionary of the item's values.
        self.data = data
        #: The :class:`MediaContainer <plexdevices.media.MediaContainer>` which holds this item.
        self.container = container

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.title)

    @property
    def markable(self):
        return False

    @property
    def key(self):
        """The endpoint on the server which this object points to. This can be relative or absolute."""
        return self.data.get('key')

    @property
    def title(self):
        """ """
        return self.data.get('title')

    @property
    def thumb(self):
        """Either the key to the thumb, or ``None``. Use :func:`~plexdevices.Server.image` to get the image data."""
        return self.data.get('thumb')

    @property
    def type(self):
        return plexdevices.factory.MediaFactory.type(self.data)

    @property
    def has_parent(self):
        return 'parentKey' in self.data or self.container.has_parent

    @property
    def has_grandparent(self):
        if 'grandparentKey' in self.data:
            return True
        else:
            for key in self.container.data:
                if key.startswith('grandparent'):
                    return True
            return False

    @property
    def parent_type(self):
        return plexdevices.types.get_parent_type(self.type)

    @property
    def grandparent_type(self):
        return plexdevices.types.get_parent_type(self.parent_type)


class Metadata(object):
    """The basic metadata all media objects will have."""
    def _originally_available_at(self):
        return datetime.strptime(self.data.get('originallyAvailableAt',
                                               '0000-00-00'),
                                 '%Y-%m-%d').date()

    def _grandparent_key(self):
        if 'grandparentKey' in self.data:
            return self.data['grandparentKey']
        elif 'grandparentKey' in self.container.data:
            return self.container.data['grandparentKey']
        else:
            return '/library/metadata/{}/children'.format(self.container.data['grandparentRatingKey'])

    def _granparent_rating_key(self):
        return (self.data['grandparentRatingKey'] if 'grandparentRatingKey' in self.data else
                self.container.data.get('grandparentRatingKey'))

    def _grandparent_thumb(self):
        return (self.data['grandparentThumb'] if 'grandparentThumb' in self.data else
                self.container.data.get('grandparentThumb'))

    def _grandparent_title(self):
        return (self.data['grandparentTitle'] if 'grandparentTitle' in self.data else
                self.container.data.get('grandparentTitle'))

    def _parent_index(self):
        return (int(self.data['parentIndex'] if 'parentIndex' in self.data else
                self.container.data.get('parentIndex', 0)))

    def _parent_key(self):
        return (self.data['parentKey'] if 'parentKey' in self.data else
                self.container.data.get('parentKey'))

    def _parent_rating_key(self):
        return (self.data['parentRatingKey'] if 'parentRatingKey' in self.data else
                self.container.data.get('parentRatingKey'))

    def _parent_thumb(self):
        return (self.data['parentThumb'] if 'parentThumb' in self.data else
                self.container.data.get('parentThumb'))

    def _parent_title(self):
        return (self.data['parentTitle'] if 'parentTitle' in self.data else
                self.container.data.get('parentTitle'))

    def _index(self):
        return int(self.data.get('index', 0))

    def _duration(self):
        return int(self.data.get('duration', 0))

    @property
    def rating_key(self):
        return self.data['ratingKey']

    @property
    def allow_sync(self):
        """:type: bool"""
        return bool(int(self.data['allowSync'] if 'allowSync' in self.data else self.container.data.get('allowSync', 0)))

    @property
    def added_at(self):
        """Unix timestamp."""
        return int(self.data['addedAt'])

    @property
    def updated_at(self):
        """Unix timestamp."""
        return int(self.data['updatedAt'])

    @property
    def summary(self):
        """Description of the item."""
        return self.data.get('summary')

    @property
    def art(self):
        """Art key."""
        return self.data['art'] if 'art' in self.data else self.container.data.get('art')

    def mark_watched(self):
        """Mark this item as watched on its server."""
        if self.in_progress:
            del self.data['viewOffset']
        self.data['lastViewedAt'] = int(time.time())
        self.container.server.request('/:/scrobble', params={
            'key': self.rating_key,
            'identifier': self.container.identifier,
        })

    def mark_unwatched(self):
        """Mark this item as unwatched on its server."""
        if self.in_progress:
            del self.data['viewOffset']
        if 'lastViewedAt' in self.data:
            del self.data['lastViewedAt']
        self.container.server.request('/:/unscrobble', params={
            'key': self.rating_key,
            'identifier': self.container.identifier,
        })


class MediaItem(BaseObject, Metadata):
    """An object representing a piece of Media."""
    def __init__(self, data, container):
        super(MediaItem, self).__init__(data, container)
        #: List of :class:`Media <plexdevices.media.Media>` objects that hold information about the file.
        self.media = [Media(x, self) for x in data['_children']
                      if x['_elementType'] == 'Media']

    @property
    def in_progress(self):
        """``True`` if the item is in progress."""
        return 'viewOffset' in self.data

    @property
    def view_offset(self):
        """The resume position in ms."""
        return int(self.data.get('viewOffset', 0))

    @view_offset.setter
    def view_offset(self, value):
        self.data['viewOffset'] = value

    @property
    def year(self):
        """ """
        return int(self.data.get('year', 0))

    @property
    def last_viewed_at(self):
        """not always available."""
        return int(self.data.get('lastViewedAt', 0))

    @property
    def watched(self):
        """``True`` if the item is watched."""
        return bool(self.last_viewed_at) and not self.in_progress

    def resolve_url(self):
        """Return the url of the first part regardless of how many there are."""
        try:
            return self.media[0].parts[0].resolve_key()
        except Exception:
            return None


class Movie(MediaItem):
    """:class:`MediaItem <plexdevices.media.MediaItem>` with extra metadata for a Movie."""
    @property
    def markable(self):
        return self.container.is_library

    @property
    def duration(self):
        """Duration in ms."""
        return self._duration()

    @property
    def originally_available_at(self):
        """:type: datetime.date"""
        return self._originally_available_at()

    @property
    def rating(self):
        """Movie rating as a floating point number."""
        return float(self.data.get('rating', 0.0))

    @property
    def studio(self):
        """ """
        return self.data.get('studio')

    @property
    def tagline(self):
        """ """
        return self.data.get('tagline')


class Track(MediaItem):
    """:class:`MediaItem <plexdevices.media.MediaItem>` with extra metadata for a Music Track."""
    @property
    def markable(self):
        return self.container.is_library

    @property
    def duration(self):
        """Duration in ms."""
        return self._duration()

    @property
    def grandparent_key(self):
        """Artist key."""
        return self._grandparent_key()

    @property
    def grandparent_rating_key(self):
        return self._grandparent_rating_key()

    @property
    def grandparent_thumb(self):
        """ """
        return self._grandparent_thumb()

    @property
    def grandparent_title(self):
        """Artist name."""
        return self._grandparent_title()

    @property
    def parent_index(self):
        return self._parent_index()

    @property
    def parent_key(self):
        """Album key."""
        return self._parent_key()

    @property
    def parent_rating_key(self):
        return self._parent_rating_key()

    @property
    def parent_thumb(self):
        """ """
        return self._parent_thumb()

    @property
    def parent_title(self):
        """Album name."""
        return self._parent_title()

    @property
    def index(self):
        """Track number."""
        return self._index()


class Photo(MediaItem):
    """:class:`MediaItem <plexdevices.media.MediaItem>` with extra metadata for a Photo."""
    @property
    def originally_available_at(self):
        """ """
        return self._originally_available_at()

    @property
    def parent_key(self):
        """Key to the album which holds this photo."""
        return self._parent_key()

    @property
    def grandparent_key(self):
        """Key to the folder which holds the photoalbum."""
        return self._grandparent_key()


class Episode(MediaItem):
    """:class:`MediaItem <plexdevices.media.MediaItem>` with extra metadata for a TV Show Episode."""
    @property
    def markable(self):
        return self.container.is_library

    @property
    def duration(self):
        """Duration in ms."""
        return self._duration()

    @property
    def index(self):
        """Episode number."""
        return self._index()

    @property
    def originally_available_at(self):
        """Air date."""
        return self._originally_available_at()

    @property
    def grandparent_key(self):
        """Key of the show."""
        return self._grandparent_key()

    @property
    def grandparent_title(self):
        """Title of the show."""
        return self._grandparent_title()

    @property
    def parent_key(self):
        """Key of the season."""
        return self._parent_key()

    @property
    def parent_index(self):
        """Season number."""
        return self._parent_index()


class VideoClip(MediaItem):
    """:class:`MediaItem <plexdevices.media.MediaItem>` with extra metadata for a Video Clip."""
    @property
    def duration(self):
        """Duration in ms."""
        return self._duration()


class Directory(BaseObject):
    """a directory that is used for navigation."""


class PreferencesDirectory(Directory):
    """A special :class:`Directory <plexdevices.media.Directory>` used in channels for channel preferences."""


class InputDirectory(Directory):
    """A special :class:`Directory <plexdevices.media.Directory>` where you should get a string from the user and send it to the key as a `query` parameter.
    ::

        if isinstance(item, InputDirectory):
            user_input = get_string()
            next_container = server.media_container(item.key, params={'query': user_input})
    """


class MediaDirectory(Directory, Metadata):
    """A directory that holds MediaItems. These directories have metadata, can be added to a :class:`PlayQueue <plexdevices.media.PlayQueue>`, and can be marked watched/unwatched.
    A :class:`MediaContainer <plexdevices.media.MediaContainer>` with its key will contain all the :class:`MediaItems <plexdevices.media.MediaItem>`."""


class PhotoAlbum(MediaDirectory):
    """:class:`MediaDirectory <plexdevices.media.MediaDirectory>` with extra metadata for a Photo Album."""


class Season(MediaDirectory):
    """:class:`MediaDirectory <plexdevices.media.MediaDirectory>` with extra metadata for a TV Season."""
    @property
    def markable(self):
        return self.container.is_library

    @property
    def parent_summary(self):
        """Show summary."""
        return self._parent_summary()

    @property
    def parent_key(self):
        """Show key."""
        return self._parent_key()

    @property
    def parent_rating_key(self):
        return self._parent_rating_key()

    @property
    def parent_thumb(self):
        """Show thumb."""
        return self._parent_thumb()

    @property
    def parent_title(self):
        """Show name."""
        return self._parent_title()

    @property
    def count(self):
        """Number of episodes."""
        return int(self.data['leafCount'])

    @property
    def watched_count(self):
        """ """
        return int(self.data['viewedLeafCount'])

    @property
    def unwatched_count(self):
        """ """
        return self.count - self.watched_count


class Artist(MediaDirectory):
    """:class:`MediaDirectory <plexdevices.media.MediaDirectory>` with extra metadata for a music Artist."""
    @property
    def markable(self):
        return self.container.is_library

    @property
    def genres(self):
        """:type: list"""
        return [x['tag'] for x in self.data['_children'] if x['_elementType'] == 'Genre']

    @property
    def country(self):
        """:type: list"""
        try:
            return [x['tag'] for x in self.data['_children'] if x['_elementType'] == 'Country'][0]
        except IndexError:
            return []


class Album(MediaDirectory):
    """:class:`MediaDirectory <plexdevices.media.MediaDirectory>` with extra metadata for a music Album."""
    @property
    def markable(self):
        return self.container.is_library

    @property
    def genres(self):
        """:type: list"""
        return [x['tag'] for x in self.data['_children'] if x['_elementType'] == 'Genre']

    @property
    def year(self):
        """ """
        return int(self.data.get('year', 0))

    @property
    def originally_available_at(self):
        """Release date."""
        return self._originally_available_at()

    @property
    def parent_key(self):
        """Artist key."""
        return self._parent_key()

    @property
    def parent_title(self):
        """Artist name."""
        return self._parent_title()

    @property
    def parent_rating_key(self):
        return self._parent_rating_key()

    @property
    def parent_thumb(self):
        return self._parent_thumb()


class Show(MediaDirectory):
    """:class:`MediaDirectory <plexdevices.media.MediaDirectory>` with extra metadata for a TV Show."""
    @property
    def markable(self):
        return self.container.is_library

    @property
    def banner(self):
        """ """
        return self.data.get('banner')

    @property
    def child_count(self):
        """Number of seasons."""
        return int(self.data.get('childCount', 0))

    @property
    def duration(self):
        """Length of one episode in ms."""
        return self._duration()

    @property
    def index(self):
        return self._index()

    @property
    def count(self):
        """Number of episodes."""
        return int(self.data.get('leafCount', 0))

    @property
    def originally_available_at(self):
        """Premiere date."""
        return self._originally_available_at()

    @property
    def studio(self):
        """ """
        return self._studio

    @property
    def watched_count(self):
        """ """
        return int(self.data.get('viewedLeafCount', 0))

    @property
    def unwatched_count(self):
        """ """
        return self.count - self.watched_count


class Media(object):
    """A Media object represents a single copy of a :class:`MediaItem <plexdevices.media.MediaItem>`.
    In most cases, a :class:`MediaItem <plexdevices.media.MediaItem>` will have a single Media object.
    If the server has a 480p and a 1080p copy of a movie, there will be two Media objects.
    """

    def __init__(self, data, parent):
        self.parent = parent
        self.data = data
        #: List of :class:`Part <plexdevices.media.Part>` objects which references the actual files. Typically there is only one part.
        self.parts = [Part(x, self) for x in data['_children']
                      if x['_elementType'] == 'Part']

    @property
    def video_resolution(self):
        """Vertical resolution as an integer. e.g. ``1080``"""
        return self.data.get('videoResolution') if 'id' in self.data else None

    @property
    def id(self):
        """ """
        return int(self.data['id']) if 'id' in self.data else None

    @property
    def duration(self):
        """Duration in ms."""
        return int(self.data['duration']) if 'duration' in self.data else None

    @property
    def bitrate(self):
        """ """
        return int(self.data['bitrate']) if 'bitrate' in self.data else None

    @property
    def width(self):
        """Horizontal resolution."""
        return int(self.data['width']) if 'width' in self.data else None

    @property
    def height(self):
        """Vertical resolution."""
        return int(self.data['height']) if 'height' in self.data else None

    @property
    def aspect_ratio(self):
        """Aspect ratio as floating point number. e.g. ``1.78`` for 16:9."""
        return float(self.data['aspectRatio']) if 'aspectRatio' in self.data else None

    @property
    def audio_channels(self):
        """Number of audio channels."""
        return int(self.data['audioChannels']) if 'audioChannels' in self.data else None

    @property
    def audio_codec(self):
        """Audio codec as a string."""
        return self.data['audioCodec'] if 'audioCodec' in self.data else None

    @property
    def video_codec(self):
        """Video codec as a string."""
        return self.data['videoCodec'] if 'videoCodec' in self.data else None

    @property
    def container(self):
        """Container file format. e.g. ``mkv``."""
        return self.data['container'] if 'container' in self.data else None

    @property
    def video_frame_rate(self):
        """Framerate as a string. e.g. ``24p``, ``NTSC``."""
        return self.data['videoFrameRate'] if 'videoFrameRate' in self.data else None

    @property
    def video_profile(self):
        """``main``, ``high``, ..."""
        return self.data['videoProfile'] if 'videoProfile' in self.data else None

    @property
    def indirect(self):
        return bool(int(self.data.get('indirect', 0)))


class Part(object):
    """A part represents an actual file."""
    def __init__(self, data, parent):
        self.parent = parent
        self.data = data

    @property
    def id(self):
        """ """
        return int(self.data['id']) if 'id' in self.data else None

    @property
    def key(self):
        """The key to playing this item. It either points to the file on the server,
        or to a function on the server that will resolve it to a playable url."""
        return self.data['key'] if 'key' in self.data else None

    @property
    def duration(self):
        """Duration in ms."""
        return int(self.data['duration']) if 'duration' in self.data else None

    @property
    def file(self):
        """The path to the file on the server. use the key to actually access it."""
        return self.data['file'] if 'file' in self.data else None

    @property
    def size(self):
        """Size of the file in bytes."""
        return int(self.data['size']) if 'size' in self.data else None

    @property
    def container(self):
        """Container file format. e.g. ``mkv``."""
        return self.data['container'] if 'container' in self.data else None

    @property
    def video_profile(self):
        """``main``, ``high``, ..."""
        return self.data['videoProfile'] if 'videoProfile' in self.data else None

    def resolve_key(self):
        """Resolve the key into a url which can be given to a media player."""
        log.debug('attempting so resolve the key %s' % self.key)
        server = self.parent.parent.container.server
        wkey = self.key
        if self.key.startswith('/system/services/'):
            log.debug('key is a system service.')
            c = server.media_container(wkey)
            wkey = c.children[0].media[0].parts[0].key
            log.debug('got key: %s' % wkey)

        if wkey.startswith('/:/'):
            log.debug('key is a some server function.')
            log.debug('indirect? ' + str(self.parent.indirect))
            if self.parent.indirect:
                log.debug('media is indirect.')
                ires = server.media_container(wkey)
                url = ires.children[0].media[0].parts[0].key
            else:
                url = '{}{}&X-Plex-Token={}'.format(server.active.url, wkey,
                                                    server.access_token)
        else:
            url = '{}{}?X-Plex-Token={}'.format(server.active.url, wkey,
                                                server.access_token)
        log.debug('resolved url: %s' % url)
        return url
