__title__ = 'plexdevices'
__version__ = '0.3.1'
__author__ = 'Cory Parsons'


from .device import Device, Server, Player, Connection
from .remote import Remote
from .session import Session
from .exceptions import DeviceConnectionsError, PlexTVError
from .media import (MediaContainer, PlayQueue, BaseObject, Directory, InputDirectory, PreferencesDirectory,
                    MediaItem, Episode, Movie, Track, Photo, VideoClip,
                    MediaDirectory, Season, Show, PhotoAlbum, Artist, Album)
from .types import PlexType, get_type_string, get_parent_type

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
