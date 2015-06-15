from django.test import TestCase
from datetime import datetime
from .models import QueueEntry
from django.conf import settings
import os
import tests
from django.test import Client
from django.contrib.sites.models import Site

settings.SITE_ID = 1

class QueueEntryCase(TestCase):
    '''
    Lets make a queue test case so we dont redo our setups over and over
    '''

    def setUp(self):
        self.client = Client()
        self.queue = QueueEntry.objects.get_or_create(
            ark='ark:/67531/coda4fnk',
            bytes=123,
            files=321,
            url_list='http://example.com/ark:/67531/coda4fnk.urls',
            status=1,
            harvest_start=datetime.now(),
            harvest_end=datetime.now(),
            queue_position=2,
        )


class QueueIndexViewTest(TestCase):
    """
    A class to test the index page.
    """

    def test_view(self):
        response = self.client.get('/queue/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "queue entries")


class QueueEntryViewTest(QueueEntryCase):
    """
    A class to test the single queue item page.
    """

    def test_view(self):
        response = self.client.get('/queue/ark:/67531/coda4fnk/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "123.321")


class QueueSearchViewTest(QueueEntryCase):
    """
    A class to test the queue search page.
    """

    def test_view(self):
        response = self.client.get(
            '/queue/search/',
            HTTP_HOST=Site.objects.get_current().domain
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Search Queue")


class APPQueueEntryHTTPTest(QueueEntryCase):
    """
    This tests the APP/queue/ HTTP header cases GET, POST, PUT, and DELETE
    """

    def test_GET(self):
        # create the base level get request and test it's response
        response = self.client.get(
            '/APP/queue/',
            HTTP_HOST=Site.objects.get_current().domain
        )
        self.assertEqual(response.status_code, 200)
        # test GETting our test queue
        response = self.client.get(
            '/APP/queue/ark:/67531/coda4fnk/',
            HTTP_HOST=Site.objects.get_current().domain
        )
        self.assertEqual(response.status_code, 200)

    def test_POST(self):
        self.client.delete('/APP/queue/ark:/67531/coda4fnk/')
        with open(
            os.path.join(os.path.dirname(tests.__file__), 'test_resources', 'queue_entry.xml')
        ) as f:
            data = f.read()
            response = self.client.post(
                '/APP/queue/',
                data,
                content_type='text/xml',
                HTTP_HOST=Site.objects.get_current().domain
            )
        self.assertEqual(response.status_code, 201)

    def test_PUT(self):
        with open(
            os.path.join(os.path.dirname(tests.__file__), 'test_resources', 'queue_entry.xml')
        ) as f:
            data = f.read()
            response = self.client.put(
                '/APP/queue/ark:/67531/coda4fnk/',
                data,
                content_type='text/xml',
                HTTP_HOST=Site.objects.get_current().domain
            )
        self.assertEqual(response.status_code, 200)

    def test_DELETE(self):
        response = self.client.delete('/APP/queue/ark:/67531/coda4fnk/')
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
