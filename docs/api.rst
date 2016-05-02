.. _api:

API Documentation
=================

.. module:: plexdevices

Main Interface
~~~~~~~~~~~~~~

.. autofunction:: create_session
.. autofunction:: create_remote

____

Sessions
~~~~~~~~

.. autoclass:: plexdevices.session.Session()
    :inherited-members:

____

Devices
~~~~~~~

Device
------

.. autoclass:: plexdevices.device.Device()
    :inherited-members:

Server
------

.. autoclass:: plexdevices.device.Server()
    :show-inheritance:
    :members:

Player
------

.. autoclass:: plexdevices.device.Player()
    :show-inheritance:
    :members:

____

Containers
~~~~~~~~~~

Media Container
---------------

.. autoclass:: plexdevices.media.MediaContainer()
    :inherited-members:

Play Queues
-----------

.. autoclass:: plexdevices.media.PlayQueue()
    :inherited-members:
    :show-inheritance:

Hubs
----

`added in 0.4.0`

These are for the Plex Media Server api at ``/hubs``.

.. autoclass:: plexdevices.hubs.HubsContainer()
    :show-inheritance:
    :members:

.. autoclass:: plexdevices.hubs.Hub()
    :members:

____

Items in Containers
~~~~~~~~~~~~~~~~~~~

Deciding what to do with the items in a container should be done by checking the type with :func:`isinstance`.
::

    def item_clicked(item):
        if isinstance(item, (plexdevices.media.Movie, plexdevices.media.Episode)):
            video_player.play(item.resolve_url())
        elif isinstance(item, plexdevices.media.Directory):
            next_container = server.media_container(item.key)


Directories
-----------

.. autoclass:: plexdevices.media.Directory()
    :show-inheritance:
    :members: title, key

.. autoclass:: plexdevices.media.InputDirectory()
    :show-inheritance:

.. autoclass:: plexdevices.media.PreferencesDirectory()
    :show-inheritance:

Media Directories
-----------------

MediaDirectory
^^^^^^^^^^^^^^

.. autoclass:: plexdevices.media.MediaDirectory()
    :show-inheritance:
    :inherited-members:

PhotoAlbum
^^^^^^^^^^

.. autoclass:: plexdevices.media.PhotoAlbum()
    :show-inheritance:
    :members:

Album
^^^^^

.. autoclass:: plexdevices.media.Album()
    :show-inheritance:
    :members:

Artist
^^^^^^

.. autoclass:: plexdevices.media.Artist()
    :show-inheritance:
    :members:

Season
^^^^^^

.. autoclass:: plexdevices.media.Season()
    :show-inheritance:
    :members:

Show
^^^^

.. autoclass:: plexdevices.media.Show()
    :show-inheritance:
    :members:

Media Items
-----------

MediaItem
^^^^^^^^^

.. autoclass:: plexdevices.media.MediaItem()
    :show-inheritance:
    :inherited-members:

Media
^^^^^

.. autoclass:: plexdevices.media.Media()
    :members:

Parts
^^^^^

.. autoclass:: plexdevices.media.Part()
    :members:

Episode
^^^^^^^

.. autoclass:: plexdevices.media.Episode()
    :show-inheritance:
    :members:

Movie
^^^^^

.. autoclass:: plexdevices.media.Movie()
    :show-inheritance:
    :members:

Track
^^^^^

.. autoclass:: plexdevices.media.Track()
    :show-inheritance:
    :members:

Photo
^^^^^

.. autoclass:: plexdevices.media.Photo()
    :show-inheritance:
    :members:

____

Remote
~~~~~~

.. autoclass:: plexdevices.remote.Remote()
    :member-order: bysource
    :inherited-members:


