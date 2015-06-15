from django.test import TestCase, Client
from datetime import datetime
from coda_validate.models import Validate
import os
from django.conf import settings
from django.contrib.sites.models import Site


settings.SITE_ID = 1


class ValidateTest(TestCase):
    """
    all the validate tests want the test object
    """

    def setUp(self):
        # Every test needs access to a validate
        self.validate = Validate.objects.get_or_create(
            identifier='ark:/12345/coda123459',
            added=datetime.now(),
            last_verified=datetime.now(),
            last_verified_status='Unverified',
            priority_change_date=datetime.now(),
            priority=0,
            server='library',
        )
        self.client = Client()


class IndexViewTest(ValidateTest):
    """
    A class to test the validate 'index' page.
    """

    def test_view(self):
        response = self.client.get('/validate/')
        self.assertEqual(response.status_code, 200)


class StatsViewTest(ValidateTest):
    """
    A class to test the validate 'stats' page.
    """

    def test_view(self):
        response = self.client.get('/validate/stats/')
        self.assertEqual(response.status_code, 200)


class ViewTest(ValidateTest):
    """
    A class to test the validate lookup page.
    """

    def test_view(self):
        response = self.client.get('/validate/ark:/12345/coda123459/')
        self.assertEqual(response.status_code, 200)


class PrioritizeViewTest(ValidateTest):
    """
    A class to test the validate 'prioritize' page.
    """

    def test_index_view(self):
        response = self.client.get('/validate/prioritize/')
        self.assertEqual(response.status_code, 200)


class APPValidateHTTPTest(ValidateTest):
    """
    This tests the APP/validate/ HTTP header cases GET, POST, PUT, and DELETE
    """

    def test_GET(self):
        '''tests GET capability of the API'''

        # create the base level get request and test it's response
        response = self.client.get(
            '/APP/validate/',
            HTTP_HOST=Site.objects.get_current().domain
        )
        self.assertEqual(response.status_code, 200)
        # test GETting our test validate
        response = self.client.get(
            '/APP/validate/ark:/12345/coda123459/',
            HTTP_HOST=Site.objects.get_current().domain
        )
        self.assertEqual(response.status_code, 200)

    def test_POST(self):
        '''This tests the POST functionality of the API'''

        with open(
            os.path.join(
                os.path.dirname(__file__),
                'test_resources',
                'entry.xml'
            )
        ) as f:
            data = f.read()
            response = self.client.post(
                '/APP/validate/',
                data,
                content_type='text/xml',
                HTTP_HOST=Site.objects.get_current().domain
            )
        self.assertEqual(response.status_code, 201)
        # delete it for the put test
        response = self.client.delete(
            '/APP/validate/ark:/12345/coda123459/',
            HTTP_HOST=Site.objects.get_current().domain
        )

    def test_PUT(self):
        '''This view tests the ability to PUT an xml to the api'''

        # we have to POST first, because tests are run in arbitrary order
        with open(
            os.path.join(
                os.path.dirname(__file__),
                'test_resources',
                'entry.xml'
            )
        ) as f:
            data = f.read()
            response = self.client.post(
                '/APP/validate/',
                data,
                content_type='text/xml',
                HTTP_HOST=Site.objects.get_current().domain
            )
        # then put the record.
        with open(
            os.path.join(
                os.path.dirname(__file__),
                'test_resources',
                'put_entry.xml')
        ) as f:
            data = f.read()
            response = self.client.put(
                '/APP/validate/ark:/12345/coda123459/',
                data,
                content_type='text/xml',
                HTTP_HOST=Site.objects.get_current().domain
            )
        self.assertEqual(response.status_code, 200)
        # delete it for the post test
        response = self.client.delete(
            '/APP/validate/ark:/12345/coda123459/',
            HTTP_HOST=Site.objects.get_current().domain
        )

    def test_DELETE(self):
        '''test the DELETE capability of the API'''

        response = self.client.delete(
            '/APP/validate/ark:/12345/coda123459/',
            HTTP_HOST=Site.objects.get_current().domain
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            '/APP/validate/ark:/12345/coda123459/',
            HTTP_HOST=Site.objects.get_current().domain
        )
        self.assertEqual(response.status_code, 404)
