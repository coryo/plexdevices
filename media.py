class MediaContainer(object):
    def __init__(self, server, data):
        self.data = data
        self.server = server
        self.children = [MediaObject(child, self)
                         for child in data['_children']]

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

    def resolve_url(self):
        parts = [part['key'] for part in self['_children'][0]['_children']]
        key = parts[0]

        if key.startswith('/system/services/'):
            data = self.parent.server.parent(key)
            key = data['_children'][0]['key']

        if key.startswith('/:/'):
            data = self.parent.server.parent(key)
            print(data)
            key = data['_children'][0]['key']
            print(key)
            url = key
        else:
            url = '{}{}?X-Plex-Token={}'.format(self.parent.server.active.url,
                                                key,
                                                self.parent.server.access_token)
        return url

    def update_offset(self, new_offset):
        self['viewOffset'] = new_offset
        if 'duration' in self:
            print(self['duration'])
            perc = new_offset / self['duration']
            if perc > 0.96:
                self.mark_watched()
            elif perc < 0.05:
                self.mark_unwatched()
            else:
                if 'ratingKey' in self:
                    self.parent.server.set_view_offset(self['ratingKey'], new_offset)

    def mark_watched(self):
        self.parent.server.mark_watched(self['ratingKey'])
        self['offset'] = 0

    def mark_unwatched(self):
        self.parent.server.mark_unwatched(self['ratingKey'])
        self['offset'] = 0
