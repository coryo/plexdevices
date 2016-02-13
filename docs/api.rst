.. _api:

API Documentation
=================

.. module:: plexdevices

____

Sessions
~~~~~~~~

.. autoclass:: plexdevices.Session
    :inherited-members:

____

Device Objects
~~~~~~~~~~~~~~

Device
------

.. autoclass:: plexdevices.Device()
    :inherited-members:

Server
------

.. autoclass:: plexdevices.Server()
    :members:

Player
------

.. autoclass:: plexdevices.Player()
    :members:

____

Containers
~~~~~~~~~~

Media Container
---------------

.. autoclass:: plexdevices.MediaContainer()
    :inherited-members:

Play Queues
-----------

.. inheritance-diagram:: plexdevices.MediaContainer plexdevices.PlayQueue
   :parts: 1

.. autoclass:: plexdevices.PlayQueue()
    :inherited-members:

____

Items in Containers
~~~~~~~~~~~~~~~~~~~

Deciding what to do with the items in a container should be done by checking the type with :func:`isinstance`.
::

    def item_clicked(item):
        if isinstance(item, (plexdevices.Movie, plexdevices.Episode)):
            video_player.play(item.resolve_url())
        elif isinstance(item, Directory):
            next_container = server.media_container(item.key)


Base Objects
------------

.. autoclass:: plexdevices.BaseObject()

.. autoclass:: plexdevices.Directory()
    :members: title, key

.. autoclass:: plexdevices.InputDirectory()

.. autoclass:: plexdevices.PreferencesDirectory()


Media Directories
-----------------

.. autoclass:: plexdevices.MediaDirectory()
    :inherited-members:

PhotoAlbum
^^^^^^^^^^

.. autoclass:: plexdevices.PhotoAlbum()
    :members:

Album
^^^^^

.. autoclass:: plexdevices.Album()
    :members:

Artist
^^^^^^

.. autoclass:: plexdevices.Artist()
    :members:

Season
^^^^^^

.. autoclass:: plexdevices.Season()
    :members:

Show
^^^^

.. autoclass:: plexdevices.Show()
    :members:

Media Items
-----------

.. autoclass:: plexdevices.MediaItem()
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

.. autoclass:: plexdevices.Episode()
    :members:

Movie
^^^^^

.. autoclass:: plexdevices.Movie()
    :members:

Track
^^^^^

.. autoclass:: plexdevices.Track()
    :members:

Photo
^^^^^

.. autoclass:: plexdevices.Photo()
    :members:

____

Remote
~~~~~~

.. autoclass:: plexdevices.Remote
    :inherited-members:

