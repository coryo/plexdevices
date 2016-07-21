class User(object):
    """An object representing a Plex user."""

    def __init__(self, data, machine_id=None):
        self.machine_identifier = machine_id
        #: :obj:`str`: the users id.
        self.id = data['id']
        #: :obj:`str`:
        self.uuid = data['uuid']
        #: :obj:`bool`: the users admin status.
        self.admin = bool(int(data['admin']))
        #: :obj:`bool`: the users guest status.
        self.guest = bool(int(data['guest']))
        #: :obj:`bool`:
        self.restricted = bool(int(data['restricted']))
        #: :obj:`bool`: True if the user has a pin.
        self.protected = bool(int(data['protected']))
        #: :obj:`str`: the users name.
        self.title = data['title']
        #: :obj:`str`: the users plex username.
        self.username = data['username']
        #: :obj:`str`: the users email.
        self.email = data['email']
        #: :obj:`str`: URL to the users avatar.
        self.thumb = data['thumb']

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.title)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id and self.uuid == other.uuid
        return False
