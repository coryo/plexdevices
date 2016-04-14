# Constants borrowed from OpenPHT


class PlexType(object):
    """Enum. The various types of objects."""
    #:
    UNKNOWN = 1
    #:
    MOVIE = 2
    #:
    SHOW = 3
    #:
    SEASON = 4
    #:
    EPISODE = 5
    #:
    ARTIST = 6
    #:
    ALBUM = 7
    #:
    TRACK = 8
    #:
    PHOTO = 9
    #:
    VIDEO = 10
    #:
    DIRECTORY = 11
    #:
    SECTION = 12
    #:
    SERVER = 13
    #:
    DEVICE = 14
    #:
    SYNCITEM = 15
    #:
    MEDIASETTINGS = 16
    #:
    POLICY = 17
    #:
    LOCATION = 18
    #:
    MEDIA = 19
    #:
    PART = 20
    #:
    SYNCITEMS = 21
    #:
    STREAM = 22
    #:
    STATUS = 23
    #:
    TRANSCODEJOB = 24
    #:
    TRANSCODESESSION = 25
    #:
    PROVIDER = 26
    #:
    CLIP = 27
    #:
    PLAYLIST = 28
    #:
    CHANNEL = 29
    #:
    SECONDARY = 30
    #:
    GENRE = 31
    #:
    ROLE = 32
    #:
    WRITER = 33
    #:
    PRODUCER = 34
    #:
    COUNTRY = 35
    #:
    DIRECTOR = 36
    #:
    THUMB = 37
    #:
    IMAGE = 38
    #:
    CHANNELS = 39
    #:
    USER = 40
    #:
    RELEASE = 41
    #:
    PACKAGE = 42
    #:
    PHOTOALBUM = 43
    #:
    INPUT = 44
    #:
    PREFERENCES = 45
    #:
    TRAILER = 46
    #:
    PICTURE = 47
    #:
    PLAYLISTITEM = 48
    #:
    COMIC = 49
    #:
    NONE = 50
    #:
    PERSON = 51
    #:
    ACTOR = 52
    #:
    DIRECTOR = 53
    #:
    MIXED = 54


def get_type(type_str):
    try:
        return {
            'unknown': PlexType.UNKNOWN,
            'movie': PlexType.MOVIE,
            'show': PlexType.SHOW,
            'season': PlexType.SEASON,
            'episode': PlexType.EPISODE,
            'artist': PlexType.ARTIST,
            'album': PlexType.ALBUM,
            'song': PlexType.TRACK,
            'photo': PlexType.PHOTO,
            'video': PlexType.VIDEO,
            'directory': PlexType.DIRECTORY,
            'section': PlexType.SECTION,
            'server': PlexType.SERVER,
            'device': PlexType.DEVICE,
            'syncitem': PlexType.SYNCITEM,
            'mediasettings': PlexType.MEDIASETTINGS,
            'policy': PlexType.POLICY,
            'location': PlexType.LOCATION,
            'media': PlexType.MEDIA,
            'part': PlexType.PART,
            'syncitems': PlexType.SYNCITEMS,
            'stream': PlexType.STREAM,
            'status': PlexType.STATUS,
            'transcodejob': PlexType.TRANSCODEJOB,
            'transcodesession': PlexType.TRANSCODESESSION,
            'provider': PlexType.PROVIDER,
            'clip': PlexType.CLIP,
            'playlist': PlexType.PLAYLIST,
            'channel': PlexType.CHANNEL,
            'secondary': PlexType.SECONDARY,
            'genre': PlexType.GENRE,
            'role': PlexType.ROLE,
            'writer': PlexType.WRITER,
            'producer': PlexType.PRODUCER,
            'country': PlexType.COUNTRY,
            'director': PlexType.DIRECTOR,
            'thumb': PlexType.THUMB,
            'image': PlexType.IMAGE,
            'plugin': PlexType.CHANNELS,
            'user': PlexType.USER,
            'release': PlexType.RELEASE,
            'package': PlexType.PACKAGE,
            'photoalbum': PlexType.PHOTOALBUM,
            'input': PlexType.INPUT,
            'prefs': PlexType.PREFERENCES,
            'trailer': PlexType.TRAILER,
            'picture': PlexType.PICTURE,
            'playlistitem': PlexType.PLAYLISTITEM,
            'track': PlexType.TRACK,
            'comic': PlexType.COMIC,
            'none': PlexType.NONE,
            'person': PlexType.PERSON,
            'actor': PlexType.ACTOR,
            'director': PlexType.DIRECTOR,
            'mixed': PlexType.MIXED
        }[type_str]
    except KeyError:
        return PlexType.UNKNOWN


def get_parent_type(plex_type):
    try:
        return {
            PlexType.TRACK: PlexType.ALBUM,
            PlexType.EPISODE: PlexType.SEASON,
            PlexType.SEASON: PlexType.SHOW,
            PlexType.ALBUM: PlexType.ARTIST,
            PlexType.PHOTO: PlexType.PHOTOALBUM,
            PlexType.PHOTOALBUM: PlexType.DIRECTORY
        }[plex_type]
    except KeyError:
        return PlexType.UNKNOWN


def get_type_string(plex_type):
    try:
        return [x for x in dir(PlexType)
                if getattr(PlexType, x) == plex_type][0].capitalize()
    except Exception:
        return 'None'
