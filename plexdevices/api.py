import plexdevices.session
import plexdevices.remote
import plexdevices.media
import plexdevices.compat


def create_session(user=None, password=None, token=None):
    """Create a :class:`Session <plexdevices.session.Session>`.

    :param user: (optional) Plex.tv username.
    :param password: (optional) Plex.tv password.
    :param token: (optional) an `X-Plex-Token`.
    :return: :class:`Session <plexdevices.session.Session>` object.
    :rtype: plexdevices.session.Session

    Plex.TV Usage::

      >>> import plexdevices
      >>> s = plexdevices.create_session(username, password)
      >>> s.refresh_devices()
      >>> on_deck = s.servers[0].media_container('/library/onDeck')
      >>> on_deck.children[0].resolve_url()
      http://server/file.mp4?X-Plex-Token=XXXXXXXXXXX

    Manual Usage::

      >>> import plexdevices
      >>> s = plexdevices.create_session()
      >>> s.manual_add_server('192.168.1.1', 32400)
      >>> s.manual_add_server('192.168.1.2', 32400, token='w1zWSdJXzdeQEnpgdmLxB')
      >>> s.servers
      [<Device:A - Plex Media Server>, <Device:B - Plex Media Server>]

    **note**: manually connecting to a server requires either an `X-Plex-Token` (see `Plex support article`_)
    or an ip address added to the ``List of networks that are allowed without auth`` PMS Network setting.

    .. _Plex support article: https://support.plex.tv/hc/en-us/articles/204059436-Finding-your-account-token-X-Plex-Token
    """
    return plexdevices.session.Session(user, password, token)


def create_remote(player, name, port=8000, callback=None):
    """Create a :class:`Remote <plexdevices.remote.Remote>`.

    :param player: the :class:`Player <plexdevices.device.Player>` to create the remote for.
    :param name: the name of the remote.
    :param port: (optional) HTTP port to allow the Player to communicate to the remote.
    :param callback: (optional) a function that will be called with a single argument when the player `POSTs` data. (when using the subscribe method).
    :return: :class:`Remote <plexdevices.remote.Remote>` object.
    :rtype: plexdevices.remote.Remote

    Setup::

      >>> import plexdevices
      >>> s = plexdevices.create_session(username, password)
      >>> s.refresh_devices()
      >>> s.players
      [<Device:My-PC - Plex Media Player>]
      >>> player = s.players[0]

    Usage (subscribe method)::

      >>> r = plexdevices.create_remote(player, 'myremote')
      >>> r.timeline_subscribe()
      >>> r.down()
      >>> r.select()
      >>> r.timeline_unsubscribe()

    Usage (poll method)::

      >>> r = plexdevices.create_remote(player, 'myremote')
      >>> timeline_data = r.timeline_poll()
      >>> timeline_data
      {
          'video': {'type': 'video', 'time': '0', 'seekRange': '0-0'},
          'photo': {'type': 'photo', 'time': '0', 'seekRange': '0-0',
                    'controllable': 'playPause,stop,skipPrevious,skipNext'}
          'music': {'type': 'music', 'time': '0', 'seekRange': '0-0',
                    'controllable': 'playPause,stop,skipPrevious,skipNext,seekTo'},
          'location': 'navigation',
          'commandID': '0'
      }
      >>> r.down()
      >>> r.select()

    """
    return plexdevices.remote.Remote(player, name, port, callback)


def create_play_queue(media_item, player_identifier, player_name):
    player_headers = {'X-Plex-Client-Identifier': client_identifier,
                      'X-Plex-Client-Name': client_name}

    server = media_item.container.server
    headers = server.headers
    headers['Accept'] = 'application/json'
    headers.update(player_headers)
    media, uri = plexdevices.media.PlayQueue.media_uri(media_item, player_headers)
    code, data = server.request('/playQueues',
                                method='POST',
                                headers=headers,
                                params={'type': media, 'uri': uri})
    pqid = plexdevices.compat.json.loads(data)['playQueueID']
    return plexdevices.media.PlayQueue(server, server.container('/playQueues/{}'.format(pqid)))

