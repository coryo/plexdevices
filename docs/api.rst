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

.. autoclass:: plexdevices.Device
    :inherited-members:

Server
------

.. autoclass:: plexdevices.Server
    :members:

Player
------

.. autoclass:: plexdevices.Player
    :members:

____

Media Objects
~~~~~~~~~~~~~

Media Container
---------------

.. autoclass:: plexdevices.MediaContainer
    :inherited-members:

Base Object
-----------

.. autoclass:: plexdevices.BaseObject
    :inherited-members:

.. inheritance-diagram:: plexdevices.BaseObject plexdevices.MediaObject plexdevices.DirectoryObject
   :parts: 1

Media
-----

.. autoclass:: plexdevices.MediaObject
    :members:

Directory
---------

.. autoclass:: plexdevices.DirectoryObject
    :members:

PlayQueues
----------

.. inheritance-diagram:: plexdevices.MediaContainer plexdevices.PlayQueue
   :parts: 1

.. autoclass:: plexdevices.PlayQueue
    :inherited-members:

____

Remote
~~~~~~

.. autoclass:: plexdevices.Remote
    :inherited-members:

____

Types
~~~~~

.. autoclass:: plexdevices.PlexType
    :inherited-members:
