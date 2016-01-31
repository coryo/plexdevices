from __future__ import absolute_import
import sys

try:
    from . import requests
except ImportError:
    import requests
    sys.modules['%s.requests' % __name__] = requests

try:
    from . import chardet
except ImportError:
    import chardet
    sys.modules['%s.chardet' % __name__] = chardet