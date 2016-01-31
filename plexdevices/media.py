import logging
from .packages import requests
from .compat import quote, json
log = logging.getLogger(__name__)


class MediaContainer(object):
    """An object representing a Plex MediaContainer.
    """

    def __init__(self, server, data):
        #: Dictionary of the MediaContainer's values.
        self.data = data
        #: The :class:`Device <Device>` which this container was retrieved from.
        self.server = server
        #: List of :class:`MediaObject <MediaObject>`'s in the container.
        self.children = ([MediaObject(child, self)
                         for child in data['_children']] if '_children' in data
                         else [])

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __contains__(self, key):
        return key in self.data

    def __len__(self):
        return len(self.children)

    def get(self, key, default=None):
        try:
            return self.data[key]
        except Exception:
            return default

    @property
    def is_library(self):
        return self.get('identifier', None) == 'com.plexapp.plugins.library'


class PlayQueue(MediaContainer):
    """An object representing a Plex PlayQueue.
    """

    def __init__(self, server, data):
        super(PlayQueue, self).__init__(server, data)
        log.debug(self.data)

    @property
    def selected_item(self):
        """The selected :class:`MediaObject <MediaObject>`"""
        try:
            return self.children[int(self['playQueueSelectedItemOffset'])]
        except Exception:
            return None

    def update(self):
        """Update the :class:`PlayQueue <PlayQueue>`'s data from its server."""
        data = self.server.request('/playQueues/{}'.format(self['playQueueID']))
        self.__init__(self.server, data)

    def select(self, item):
        if item not in self.children or 'playQueueItemID' not in item:
            log.debug('select: item is not valid.')
            return None
        self['playQueueSelectedItemID'] = item['playQueueItemID']
        self['playQueueSelectedItemOffset'] = self.children.index(item)
        return item

    def get_next(self):
        """Return the next :class:`MediaObject <MediaObject>` in the PlayQueue, or `None`."""
        if self.selected_item is None:
            return None
        i = self.children.index(self.selected_item) + 1
        return self.select(self.children[i]) if 0 <= i <= len(self) - 1 else None

    def get_prev(self):
        """Return the previous :class:`MediaObject <MediaObject>` in the PlayQueue, or `None`."""
        if self.selected_item is None:
            return None
        i = self.children.index(self.selected_item) - 1
        return self.select(self.children[i]) if 0 <= i <= len(self) - 1 else None

    def remove_item(self, item):
        """Remove a :class:`MediaObject <MediaObject>` to the PlayQueue.
        """
        url = '/playQueues/{}/items/{}'.format(self['playQueueID'],
                                               item['playQueueItemID'])
        code, data = self.server.request(url, method=requests.delete,
                                         headers={'Accept': 'application/json'})
        if 200 <= code < 400:
            self.__init__(self.server, json.loads(data))
        else:
            log.error('playqueue: could not remove item from playqueue.')

    def add_item(self, media_object, player_headers):
        """Add a :class:`MediaObject <MediaObject>` to the PlayQueue.
        """
        headers = self.server.headers
        headers['Accept'] = 'application/json'
        headers.update(player_headers)
        media, uri = self.media_uri(media_object, player_headers)
        code, data = self.server.request('/playQueues/{}'.format(self['playQueueID']),
                                         method=requests.put,
                                         headers=headers,
                                         params={'type': media, 'uri': uri})
        if 200 <= code < 400:
            self.__init__(self.server, json.loads(data))
        else:
            log.error('playqueue: could not add item to playqueue.')

    @staticmethod
    def media_uri(media_object, player_headers):
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
        uri = 'library://{}/{}/{}'.format(
            player_headers['X-Plex-Client-Identifier'],
            'directory' if media_object.is_directory else 'item',
            quote(media_object['key'], safe=''))
        return (media, uri)

    @staticmethod
    def create(server, media_object, player_headers):
        """Create a PlayQueue on a server and return a PlayQueue object.

        :param server: the :class:`Device <Device>` to create the PlayQueue on.
        :param media_object: the :class:`MediaObject <MediaObject>` to be the initial item added to the PlayQueue.
        :param player_headers: Dictionary of headers identifying the player using the PlayQueue. Must include X-Plex-Client-Identifier and X-Plex-Device-Name.
        :return: :class:`PlayQueue <PlayQueue>` object
        :rtype: plexdevices.PlayQueue
        """
        if 'X-Plex-Client-Identifier' not in player_headers:
            return None
        headers = server.headers
        headers['Accept'] = 'application/json'
        headers.update(player_headers)
        media, uri = PlayQueue.media_uri(media_object, player_headers)
        code, data = server.request('/playQueues',
                                    method=requests.post,
                                    headers=headers,
                                    params={'type': media, 'uri': uri})
        pqid = json.loads(data)['playQueueID']
        return PlayQueue(server, server.container('/playQueues/{}'.format(pqid)))


class MediaObject(object):
    """An object representing a Plex MediaObject.
    """

    def __init__(self, data, parent):
        #: Dictionary of the item's values.
        self.data = data
        #: The :class:`MediaContainer <MediaContainer>` which holds this item.
        self.parent = parent

    def __getitem__(self, key):
        """Get values of the MediaObjects data."""
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __contains__(self, key):
        return key in self.data

    def get(self, key, default=None):
        try:
            return self.data[key]
        except Exception:
            return default

    def follow_key(self):
        return self.parent.server.container(self['key'])

    def get_all_keys(self):
        """Return a list of tuples of (height, key) for each key in the item.
        resolve_key one of the keys to get the final url. Use this to prompt a
        user for a selection, then resolve_key() the selection."""
        log.debug('get_all_keys: {}'.format(self['_children']))
        items = self['_children']
        parts = [(part.get('height', part.get('title', 1)), part['_children'][0]['key'])
                 for part in items if part['_elementType'] == 'Media']
        log.debug('get_all_keys: parts={}'.format(parts))
        return parts

    def resolve_key(self, key):
        """Resolve the given key into a url which can be given to a media player."""
        log.debug('attempting so resolve the key %s' % key)
        if key.startswith('/system/services/'):
            log.debug('key is a system service.')
            data = self.parent.server.container(key)
            key = data['_children'][0]['key']
            log.debug('got key: %s' % key)

        if key.startswith('/:/'):
            log.debug('key is a some server function.')
            data = self.parent.server.container(key, allow_redirects=False)
            if isinstance(data, str):
                log.debug('key caused a redirect. target=%s' % data)
                return data
            url = data['_children'][0]['key']
        else:
            url = '{}{}?X-Plex-Token={}'.format(self.parent.server.active.url,
                                                key,
                                                self.parent.server.access_token)
        log.debug('resolved url: %s' % url)
        return url

    def resolve_url(self):
        """Return the url of the first part regardless of how many there are."""
        parts = [part['key'] for part in self['_children'][0]['_children']]
        key = parts[0]
        return self.resolve_key(key)

    def mark_watched(self):
        """Mark this item as watched on its server."""
        self.parent.server.request('/:/scrobble', params={
            'key': self['ratingKey'],
            'identifier': self.parent['identifier'],
        })

    def mark_unwatched(self):
        """Mark this item as unwatched on its server."""
        self.parent.server.request('/:/unscrobble', params={
            'key': self['ratingKey'],
            'identifier': self.parent['identifier'],
        })

    @property
    def markable(self):
        """``True`` if the item can be marked watched/unwatched."""
        return (self.is_audio or self.is_video) and self.parent.is_library

    @property
    def is_video(self):
        """``True`` if the item is video."""
        return self['_elementType'] == 'Video'

    @property
    def is_audio(self):
        """``True`` if the item is audio."""
        return self['_elementType'] == 'Track'

    @property
    def is_photo(self):
        """``True`` if the item is a photo."""
        return self['_elementType'] == 'Photo'

    @property
    def is_directory(self):
        """``True`` if the item is a directory."""
        return self['_elementType'] == 'Directory'

    @property
    def is_album(self):
        """``True`` if the item is a audio album."""
        return self.is_directory and self.get('type', None) == 'album'

    @property
    def is_photo_album(self):
        """``True`` if the item is a photo album."""
        return (self.is_directory and
                self.get('type', None) == 'photoalbum' or
                (self.get('type', None) == 'photo' and
                 self.get('index', 0) == 1))

    @property
    def is_input(self):
        """``True`` if the item is an InputDirectoryObject."""
        return int(self.get('search', 0)) == 1

    @property
    def is_settings(self):
        """``True`` if the item is a PrefsObject."""
        return int(self.get('settings', 0)) == 1

    @property
    def has_parent(self):
        return 'parentKey' in self

    @property
    def has_grandparent(self):
        return 'grandparentKey' in self

    @property
    def in_progress(self):
        """``True`` if the item is in progress."""
        return 'viewOffset' in self

    @property
    def watched(self):
        """``True`` if the item is watched."""
        return 'lastViewedAt' in self and not self.in_progress

    @property
    def parent_name(self):
        """String. The name of the parent of this item. (Artist, Album, Season, etc..)."""
        media = self['type']
        if media == 'album':
            return 'Artist'
        elif media == 'track':
            return 'Album'
        elif media == 'season':
            return 'Show'
        elif media == 'episode':
            return 'Season'
        elif media == 'photo':
            return 'Album'
        else:
            return 'Parent'

    @property
    def grandparent_name(self):
        """String. The name of the grandparent of this item."""
        media = self['type']
        if media == 'track':
            return 'Artist'
        elif media == 'episode':
            return 'Show'
        else:
            return 'Grandparent'