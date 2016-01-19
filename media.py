from .packages import requests


class MediaContainer(object):
    def __init__(self, server, data):
        self.data = data
        self.server = server
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


class PlayQueue(MediaContainer):
    def __init__(self, server, data):
        super(PlayQueue, self).__init__(server, data)
        self.selected_item = self.get_selected_item()

    def get_selected_item(self):
        try:
            return [x for x in self.children
                    if x['playQueueItemID'] == self['playQueueSelectedItemID']
                    ][0]
        except Exception:
            return None


class MediaObject(object):

    def __init__(self, data, parent):
        self.data = data
        self.parent = parent

    def __getitem__(self, key):
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

    def get_all_keys(self):
        """return a list of tuples of (height, key) for each key in the item.
        resolve_key one of the keys to get the final url"""
        items = self['_children']
        parts = [(part.get('height', part.get('title', 1)), part['_children'][0]['key'])
                 for part in items if part['_elementType'] == 'Media']
        return parts

    def resolve_key(self, key):
        if key.startswith('/system/services/'):
            data = self.parent.server.container(key)
            key = data['_children'][0]['key']

        if key.startswith('/:/'):
            data = self.parent.server.container(key, allow_redirects=False)
            if isinstance(data, str):
                return data
            key = data['_children'][0]['key']
            url = key
        else:
            url = '{}{}?X-Plex-Token={}'.format(self.parent.server.active.url,
                                                key,
                                                self.parent.server.access_token)
        return url

    def resolve_url(self):
        """return the url of the first part regardless of how many there are"""
        parts = [part['key'] for part in self['_children'][0]['_children']]
        key = parts[0]
        return self.resolve_key(key)

    def mark_watched(self):
        self.parent.server.request('/:/scrobble', params={
            'key': self['ratingKey'],
            'identifier': self.parent['identifier'],
        })
        self['offset'] = 0

    def mark_unwatched(self):
        self.parent.server.request('/:/unscrobble', params={
            'key': self['ratingKey'],
            'identifier': self.parent['identifier'],
        })
        self['offset'] = 0

    @property
    def markable(self):
        return (
            self['_elementType'] in ['Video', 'Track']
            and self.parent.get('identifier') == 'com.plexapp.plugins.library'
        )

    @property
    def is_video(self):
        return self['_elementType'] == 'Video'

    @property
    def is_audio(self):
        return self['_elementType'] == 'Track'

    @property
    def is_photo(self):
        return self['_elementType'] == 'Photo'

    @property
    def is_photo_album(self):
        return (self['_elementType'] == 'Directory' and
                self.get('type', None) == 'photoalbum'
                or (self.get('type', None) == 'photo'
                    and self.get('index', 0) == 1))

    @property
    def is_input(self):
        return int(self.get('search', 0)) == 1

    @property
    def is_settings(self):
        return int(self.get('settings', 0)) == 1

    @property
    def has_parent(self):
        return 'parentKey' in self

    @property
    def has_grandparent(self):
        return 'grandparentKey' in self

    @property
    def in_progress(self):
        return 'viewOffset' in self

    @property
    def watched(self):
        return 'lastViewedAt' in self and not self.in_progress

    @property
    def parent_name(self):
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
        media = self['type']
        if media == 'track':
            return 'Artist'
        elif media == 'episode':
            return 'Show'
        else:
            return 'Grandparent'
