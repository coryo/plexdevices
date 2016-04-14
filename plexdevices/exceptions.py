class DeviceConnectionsError(Exception):

    def __init__(self, device):
        self.device = device

    def __str__(self):
        return 'Device has no connectable connections: {}'.format(
            repr(self.device)
        )


class PlexTVError(Exception):

    def __init__(self, error):
        self.error = error

    def __str__(self):
        return 'Plex.tv error: {}'.format(repr(self.error))


class RemoteCallbackError(Exception):
    pass
