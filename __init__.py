from .device import Device, Connection
from .remote import Remote
from .session import Session
from .exceptions import ProvidesError, DeviceConnectionsError, PlexTVError
from .media import MediaContainer, MediaObject, PlayQueue

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
