"""
plexdevices Tests

XML data from Plex Media Server 0.9.16.5
"""
import unittest
import unittest.mock

import plexdevices

from .xml_samples import SAMPLE_MOVIES, HUB_SEARCH


class TestUtils(unittest.TestCase):

    def setUp(self):
        self.xml_response = SAMPLE_MOVIES
        self.server = unittest.mock.Mock()

    def test_parse_response(self):
        parsed = plexdevices.utils.parse_response(self.xml_response)
        self.assertTrue(type(parsed) == dict)
        self.assertTrue('_elementType' in parsed)
        if '_children' in parsed:
            self.assertTrue(type(parsed['_children'] == list))
            self.assertTrue('_elementType' in parsed['_children'][0])


class TestDeviceCreation(unittest.TestCase):

    def test_create_device(self):
        dev = plexdevices.device.create_device({
            'provides': '',
            '_children': []
        })
        self.assertTrue(isinstance(dev, plexdevices.device.Device))

    def test_server(self):
        dev = plexdevices.device.create_device({
            'provides': 'server',
            '_children': []
        })
        self.assertTrue(isinstance(dev, plexdevices.device.Device))
        self.assertTrue(isinstance(dev, plexdevices.device.Server))
        self.assertFalse(isinstance(dev, plexdevices.device.Player))

    def test_server(self):
        dev = plexdevices.device.create_device({
            'provides': 'player',
            '_children': []
        })
        self.assertTrue(isinstance(dev, plexdevices.device.Device))
        self.assertTrue(isinstance(dev, plexdevices.device.Player))
        self.assertFalse(isinstance(dev, plexdevices.device.Server))

    def test_all(self):
        dev = plexdevices.device.create_device({
            'provides': 'player,server',
            '_children': []
        })
        self.assertTrue(isinstance(dev, plexdevices.device.Device))
        self.assertTrue(isinstance(dev, plexdevices.device.Player))
        self.assertTrue(isinstance(dev, plexdevices.device.Server))

    def test_pickle(self):
        import pickle
        dev = plexdevices.device.create_device({
            'provides': 'player,server',
            '_children': []
        })
        self.assertTrue(isinstance(dev, plexdevices.device.Device))
        self.assertTrue(isinstance(dev, plexdevices.device.Player))
        self.assertTrue(isinstance(dev, plexdevices.device.Server))
        pickled = pickle.dumps(dev)
        unpickled = pickle.loads(pickled)
        self.assertTrue(isinstance(dev, plexdevices.device.Device))
        self.assertTrue(isinstance(dev, plexdevices.device.Player))
        self.assertTrue(isinstance(dev, plexdevices.device.Server))

    def test_pickle(self):
        import pickle
        dev = plexdevices.device.create_device({
            'provides': 'server',
            '_children': []
        })
        self.assertTrue(isinstance(dev, plexdevices.device.Device))
        self.assertFalse(isinstance(dev, plexdevices.device.Player))
        self.assertTrue(isinstance(dev, plexdevices.device.Server))
        pickled = pickle.dumps(dev)
        unpickled = pickle.loads(pickled)
        self.assertTrue(isinstance(dev, plexdevices.device.Device))
        self.assertFalse(isinstance(dev, plexdevices.device.Player))
        self.assertTrue(isinstance(dev, plexdevices.device.Server))


class TestMovie(unittest.TestCase):

    def setUp(self):
        self.server = unittest.mock.Mock()
        self.server.access_token = 'ACCESS_TOKEN'
        self.server.active = plexdevices.device.Connection({
            'protocol': 'pro',
            'address': 'addr',
            'port': 1234,
            'uri': 'uri'
        })
        self.server.active.url = 'URL'

        data = plexdevices.utils.parse_response(SAMPLE_MOVIES)
        self.container = plexdevices.media.MediaContainer(self.server, data)
        self.assertTrue(self.container.server == self.server)

    def test_length(self):
        self.assertTrue(len(self.container) == 16)

    def test_type(self):
        for item in self.container.children:
            self.assertTrue(isinstance(item, plexdevices.media.Movie))

    def test_resolve_url(self):
        url = self.container.children[0].resolve_url()
        first_part_key = self.container.children[0].media[0].parts[0].key
        self.assertEqual(url, 'URL{}?X-Plex-Token=ACCESS_TOKEN'.format(first_part_key))


class TestHubSearch(unittest.TestCase):

    def setUp(self):
        self.server = unittest.mock.Mock()
        data = plexdevices.utils.parse_response(HUB_SEARCH)
        self.container = plexdevices.hubs.HubsContainer(self.server, data)

    def test_length(self):
        self.assertEqual(self.container.size, 12)

    def test_type(self):
        for item in self.container.children:
            self.assertTrue(isinstance(item, plexdevices.hubs.Hub))

    def test_results(self):
        for hub in self.container.children:
            for child in hub.children:
                self.assertTrue(isinstance(child, plexdevices.hubs.SearchMixin))

    def test_references(self):
        for hub in self.container.children:
            for child in hub.children:
                self.assertEqual(child.hub, hub)
                self.assertEqual(child.container, self.container)
                self.assertEqual(child.container.server, self.server)


if __name__ == "__main__":
    unittest.main()
