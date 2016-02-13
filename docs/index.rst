.. plexdevices documentation master file, created by
   sphinx-quickstart on Sun Jan 31 14:37:53 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

plexdevices
===========

A Python module for working with plex devices.

::

    >>> import plexdevices
    >>> s = plexdevices.Session(user=username, password=password)
    >>> s.refresh_devices()
    >>> s.servers
    [<Device:Server1 - Plex Media Server>, <Device:Server2 - Plex Media Server>]
    >>> on_deck = s.servers[0].media_container('/library/onDeck')
    >>> on_deck.children[0].media[0].parts[0].resolve_url()
    http://server/file.mp4?X-Plex-Token=XXXXXXXXXXX

.. toctree::
   :maxdepth: 3

   api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

