import os
import unittest

from datetime import date, datetime
from django.conf import settings
from django.core.urlresolvers import resolve
from django.test import TestCase, Client

import coda_mdstore
from coda_mdstore.models import Bag, Bag_Info, Node, External_Identifier
from coda_mdstore.views import *


settings.SITE_ID = 1

class CodaCase(TestCase):
    '''
    Lets make a bag test case so we dont redo our setups over and over
    '''

    def setUp(self):
        self.c = Client()
        self.bag = Bag.objects.get_or_create(
            name='ark:/67531/coda2',
            files=99,
            size=123456,
            bagit_version='0.6',
            last_verified_date=datetime.now(),
            last_verified_status='doin good',
            bagging_date=datetime.now(),
        )
        Bag_Info.objects.get_or_create(bag_name=self.bag[0], field_name='Payload-Oxum', field_body='1234.4321')
        Bag_Info.objects.get_or_create(bag_name=self.bag[0], field_name='Bagging-Date', field_body=date.today())
        Bag_Info.objects.get_or_create(bag_name=self.bag[0], field_name='Contact-Name', field_body='TESTY TESTERSON')
        # Every test needs access to a node
        self.node = Node.objects.get_or_create(
            node_name='coda-123',
            node_url='http://fake.com/',
            node_size=123456,
            node_capacity=654321,
            node_path='/home/test/path',
            last_checked=datetime.now(),
        )
        self.external_identifier = External_Identifier.objects.get_or_create(
            value='test_value',
            belong_to_bag=self.bag[0],
        )
        self.bag = Bag.objects.get_or_create(
            name='Reginald',
            files=99,
            size=123456,
            bagit_version='0.6',
            last_verified_date=datetime.now(),
            last_verified_status='doin good',
            bagging_date=datetime.now(),
        )
                # Every test needs access to a bag
        self.bag = Bag.objects.get_or_create(
            name='ark:/67531/coda2', files=99, size=123456, bagit_version='0.6',
            last_verified_date=datetime.now(), last_verified_status='doin good',
            bagging_date=datetime.now(),
        )
        self.bag_info = Bag_Info.objects.get_or_create(bag_name=self.bag[0], field_name='Payload-Oxum', field_body='123.321')
        self.external_identifier = External_Identifier.objects.get_or_create(
            value='test value',
            belong_to_bag=self.bag[0],
        )
        fixtures = ['site']


class BagTest(CodaCase):
    """
    Tests bag creation
    """

    def test_urls_resolve_correctly(self):
        self.assertEqual(resolve('/').func, index)
        self.assertEqual(resolve('/bag/').func, all_bags)
        self.assertEqual(resolve('/APP/bag/').func, app_bag)
        self.assertEqual(resolve('/APP/bag/ark:/67531/coda2/').func, app_bag)
        self.assertEqual(resolve('/bag/ark:/67531/coda2/').func, bagHTML)
        self.assertEqual(resolve('/bag/ark:/67531/coda2.urls').func, bagURLList)
        # stats urls
        self.assertEqual(resolve('/stats/').func, stats)
        self.assertEqual(resolve('/stats.json').func, json_stats)
        # node urls
        self.assertEqual(resolve('/APP/node/').func, app_node)
        self.assertEqual(resolve('/APP/node/coda-123/').func, app_node)
        self.assertEqual(resolve('/node/').func, showNodeStatus)
        self.assertEqual(resolve('/node/coda-123/').func, showNodeStatus)
        self.assertEqual(resolve('/extidentifier/test_value/').func, externalIdentifierSearch)
        self.assertEqual(resolve('/extidentifier/').func, externalIdentifierSearch)
        self.assertEqual(resolve('/extidentifier.json').func, externalIdentifierSearchJSON)
        self.assertEqual(resolve('/search/').func, bagFullTextSearchHTML)
        # Here's some static pages
        self.assertEqual(resolve('/about/').func, about)
        self.assertEqual(resolve('/robots.txt').func, shooRobot)

    def test_bag_contents(self):
        b = Bag.objects.get(name='Reginald')
        self.assertIsNotNone(b.name)
        self.assertIsNotNone(b.files)
        self.assertIsNotNone(b.size)
        self.assertIsNotNone(b.bagit_version)
        self.assertIsNotNone(b.last_verified_date)
        self.assertIsNotNone(b.last_verified_status)
        self.assertIsNotNone(b.bagging_date)

    @unittest.skip('Search requires a FULLTEXT index which is not '
                   'currently part the build process.')
    def test_can_search_for_bags(self):
        # check out its homepage
        response = self.c.get('/')
        # notice the page title
        self.assertIn('Dashboard', response.content)
        # find search box and enter a query and submit
        response = self.c.post('/search/', {'search': 'Reginald'})
        self.assertIn('Reginald', response.content)

    def test_urls_view(self):
        response = self.c.get('/bag/ark:/67531/coda2.urls', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_specific_bag_view(self):
        response = self.c.get('/bag/ark:/67531/coda2/')
        self.assertContains(response, "Contact-Name")
        self.assertEqual(response.status_code, 200)

    def test_bag_view(self):
        response = self.c.get('/bag/')
        self.assertContains(response, "ark:/67531/coda2")
        self.assertEqual(response.status_code, 200)


class CodaViewTest(CodaCase):
    """
    A class to test the coda pages.
    """

    def test_view(self):
        response = self.c.get('/')
        self.assertEqual(response.status_code, 200)

    def test_stats_view(self):
        response = self.c.get('/stats/')
        self.assertContains(response, " bags")
        self.assertEqual(response.status_code, 200)

    def test_json_view(self):
        response = self.c.get('/stats.json')
        self.assertContains(response, "bag")
        self.assertEqual(response.status_code, 200)

    def test_about_view(self):
        response = self.c.get('/about/')
        self.assertContains(response, "Introduction")

    def test_feed_view(self):
        response = self.c.get('/feed/')
        self.assertContains(response, "<?xml version=\"1.0\" encoding=\"utf-8\"?>")
        self.assertEqual(response.status_code, 200)

    @unittest.skip('Search requires a FULLTEXT index which is not '
                   'currently part the build process.')
    def test_search_view(self):
        response = self.c.get('/search/')
        self.assertEqual(response.status_code, 200)
        response = self.c.get('/search/?search=america')
        self.assertEqual(response.status_code, 200)


class CodaNodeTest(CodaCase):
    """
    A class to test the /node page.
    """

    def test_view(self):
        response = self.c.get('/node/')
        self.assertContains(response, "Storage Node Status")
        self.assertEqual(response.status_code, 200)

    def test_node_view(self):
        response = self.c.get('/node/coda-123/')
        self.assertContains(response, "node")
        self.assertEqual(response.status_code, 200)


class APPBagHTTPTest(CodaCase):
    """
    This tests the APP/bag/ HTTP header cases GET, POST, PUT, and DELETE
    """

    fixtures =['site', 'initial_data']


    def test_GET(self):
        # create the base level get request and test it's response
        response = self.c.get('/APP/bag/', HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)
        # test GETting our test bag
        response = self.c.get('/APP/bag/ark:/67531/coda2/', HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)

    def test_POST(self):
        with open(
            os.path.join(os.path.dirname(coda_mdstore.__file__), 'test_resources', 'bag_entry.xml')
            ) as f:
            data = f.read()
            response = self.c.post(
                '/APP/bag/',
                data,
                HTTP_HOST='example.com',
                content_type='text/xml',
            )
        self.assertEqual(response.status_code, 201)

    def test_PUT(self):
        with open(
            os.path.join(os.path.dirname(coda_mdstore.__file__), 'test_resources', 'bag_entry.xml')
        ) as f:
            data = f.read()
            response = self.c.put(
                '/APP/bag/ark:/67531/coda2/',
                data,
                HTTP_HOST='example.com',
                content_type='text/xml',
            )
        self.assertEqual(response.status_code, 200)
        bag = Bag.objects.get(name='ark:/67531/coda2')
        bag_infos_before = Bag_Info.objects.filter(bag_name=bag)
        ext_id_before = External_Identifier.objects.filter(belong_to_bag=bag)
        # PUT again the same bag
        with open(
            os.path.join(os.path.dirname(coda_mdstore.__file__), 'test_resources', 'bag_entry.xml')
        ) as f:
            data = f.read()
            response = self.c.put(
                '/APP/bag/ark:/67531/coda2/',
                data,
                HTTP_HOST='example.com',
                content_type='text/xml',
            )
        bag = Bag.objects.get(name='ark:/67531/coda2')
        bag_infos_after = Bag_Info.objects.filter(bag_name=bag)
        ext_id_after = External_Identifier.objects.filter(belong_to_bag=bag)
        # test that a PUT doesn't make extra bag infos
        self.assertEqual(bag_infos_before.count(), bag_infos_after.count())
        self.assertEqual(ext_id_before.count(), ext_id_after.count())

    def test_DELETE(self):
        response = self.c.delete('/APP/bag/ark:/67531/coda2/', HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)


class APPNodeHTTPTest(CodaCase):
    """
    This tests the APP/node/ HTTP header cases GET, POST, PUT, and DELETE
    """

    fixtures =['site', 'initial_data']

    def test_GET(self):
        # create the base level get request and test it's response
        response = self.c.get('/APP/node/', HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)
        # test GETting our test node
        response = self.c.get('/APP/node/coda-123/', HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)

    def test_POST(self):
        with open(
            os.path.join(os.path.dirname(coda_mdstore.__file__), 'test_resources', 'node_entry.xml')
        ) as f:
            data = f.read()
            response = self.c.post(
                '/APP/node/',
                data,
                HTTP_HOST='example.com',
                content_type='text/xml',
            )
        self.assertEqual(response.status_code, 201)

    def test_PUT(self):
        # Every test needs access to a node
        self.node = Node.objects.get_or_create(
            node_name='coda-001',
            node_url='http://fake.com/',
            node_size=123456,
            node_capacity=654321,
            node_path='/home/test/path',
            last_checked=datetime.now(),
        )
        with open(
            os.path.join(os.path.dirname(coda_mdstore.__file__), 'test_resources', 'node_entry.xml')
        ) as f:
            data = f.read()
            response = self.c.put(
                '/APP/node/coda-001/',
                data,
                HTTP_HOST='example.com',
                content_type='text/xml',
            )
        self.assertEqual(response.status_code, 200)

    def test_DELETE(self):
        response = self.c.delete('/APP/node/coda-123/', HTTP_HOST='example.com')
        self.assertEqual(response.status_code, 200)

