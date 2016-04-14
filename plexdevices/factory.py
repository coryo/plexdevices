import plexdevices.media
import plexdevices.hubs
import plexdevices.types


class MediaFactory(object):
    @staticmethod
    def factory(data):
        t = MediaFactory.type(data)
        if data['_elementType'] == 'Directory':
            if 'ratingKey' in data:
                if t == plexdevices.types.PlexType.SEASON:
                    return plexdevices.media.Season
                elif t == plexdevices.types.PlexType.SHOW:
                    return plexdevices.media.Show
                elif t == plexdevices.types.PlexType.ARTIST:
                    return plexdevices.media.Artist
                elif t == plexdevices.types.PlexType.ALBUM:
                    return plexdevices.media.Album
                elif t == plexdevices.types.PlexType.PHOTO:
                    return plexdevices.media.PhotoAlbum
                else:
                    return plexdevices.media.Directory
            else:
                if t == plexdevices.types.PlexType.PREFERENCES:
                    return plexdevices.media.PreferencesDirectory
                elif t == plexdevices.types.PlexType.INPUT:
                    return plexdevices.media.InputDirectory
                else:
                    return plexdevices.media.Directory
        elif data['_elementType'] in ['Video', 'Track', 'Photo']:
            if t == plexdevices.types.PlexType.EPISODE:
                return plexdevices.media.Episode
            elif t == plexdevices.types.PlexType.MOVIE:
                return plexdevices.media.Movie
            elif t == plexdevices.types.PlexType.TRACK:
                return plexdevices.media.Track
            elif t == plexdevices.types.PlexType.PHOTO:
                return plexdevices.media.Photo
            elif t == plexdevices.types.PlexType.CLIP:
                return plexdevices.media.VideoClip
        elif data['_elementType'] == 'Hub':
            return plexdevices.hubs.Hub
        return None

    @staticmethod
    def type(data):
        if 'settings' in data:
            dtype = 'prefs'
        elif 'search' in data:
            dtype = 'input'
        else:
            dtype = data.get('type', 'unknown')
        return plexdevices.types.get_type(dtype)
