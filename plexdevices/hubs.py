import plexdevices.media
import plexdevices.factory


class HubsContainer(plexdevices.media.MediaContainer):

    def __init__(self, server, data):
        #: Dictionary of the HubsContainer's values.
        self.data = data
        #: The :class:`Server <Server>` which this container was retrieved from.
        self.server = server
        if '_children' in data:
            #: List of items in the container. :class:`BaseObject <BaseObject>`, :class:`Hub <plexdevices.hubs.Hub>`
            self.children = []
            for c in data['_children']:
                cls = plexdevices.factory.MediaFactory.factory(c)
                if cls is not None:
                    item = cls(c, self)
                    self.children.append(item)
            del self.data['_children']
        else:
            self.children = []

    def __len__(self):
        return len(self.children)

    @property
    def size(self):
        """ """
        return int(self.data.get('size', 0))

    @property
    def allow_sync(self):
        """ """
        return bool(int(self.data.get('allow_sync', 0)))

    @property
    def is_library(self):
        """ """
        return True


class HubsItemBase(object):
    pass


class SearchMixin(object):
    @property
    def has_reason(self):
        return 'reason' in self.data

    @property
    def reason(self):
        return self.data.get('reason')

    @property
    def reason_id(self):
        return int(self.data.get('reasonID'))

    @property
    def reason_title(self):
        return self.data.get('reasonTitle')


class Hub(HubsItemBase):
    """
    A Hub is a container inside a :class:`HubsContainer <plexdevices.hubs.HubsContainer>` which groups
    together multiple items."""

    def __init__(self, data, container):
        # Dictionary of the item's values.
        self.data = data
        #: The :class:`HubsContainer     <plexdevices.hubs.HubsContainer>` which holds this item.
        self.container = container
        if '_children' in data:
            #: List of :class:`BaseObject <BaseObject>`'s in the Hub.
            self.children = []
            for c in data['_children']:
                cls = plexdevices.factory.MediaFactory.factory(c)
                if cls is not None:
                    newclass = type('HubsItem', (cls, HubsItemBase, SearchMixin), {})
                    item = newclass(c, self)
                    item.container = container
                    item.hub = self
                    self.children.append(item)
            del self.data['_children']
        else:
            self.children = []

    def __repr__(self):
        return '<{}: {} {}>'.format(self.__class__.__name__, self.title, self.type)

    @property
    def hub_key(self):
        """ """
        return self.data.get('hubKey')

    @property
    def key(self):
        """ """
        return self.data.get('key')

    @property
    def type(self):
        """ """
        return plexdevices.factory.MediaFactory.type(self.data)

    @property
    def hub_identifier(self):
        """ """
        return self.data.get('hubIdentifier')

    @property
    def size(self):
        """ """
        return int(self.data.get('size', 0))

    @property
    def title(self):
        """ """
        return self.data.get('title')

    @property
    def more(self):
        """ """
        return bool(int(self.data.get('more', 0)))
