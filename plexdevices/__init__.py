__title__ = 'plexdevices'
__version__ = '0.2.0'
__author__ = 'Cory Parsons'


from .device import Device, Server, Player, Connection
from .remote import Remote
from .session import Session
from .exceptions import DeviceConnectionsError, PlexTVError
from .media import MediaContainer, BaseObject, MediaObject, DirectoryObject, PlayQueue
from .types import PlexType

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
