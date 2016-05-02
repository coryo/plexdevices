__title__ = 'plexdevices'
__version__ = '0.4.1'
__author__ = 'Cory Parsons'

from plexdevices.exceptions import (DeviceConnectionsError, PlexTVError,
                                    RemoteCallbackError)
from plexdevices.api import create_session, create_remote, create_play_queue

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
