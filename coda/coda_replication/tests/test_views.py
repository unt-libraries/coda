import json

from lxml import objectify
import pytest

from django.core.paginator import Page
from django.core.urlresolvers import reverse

from .. import factories
from .. import views
from ..models import STATUS_CHOICES, QueueEntry


pytestmark = [
    pytest.mark.urls('coda_replication.urls'),
    pytest.mark.django_db()
]


class TestQueueStats:
    """
    Tests for coda_replication.views.queue_stats.
    """

    def test_status_ok_without_entries(self, rf):
        request = rf.get('/')
        response = views.queue_stats(request)
        assert response.status_code == 200

    def test_status_ok(self, rf):
        factories.QueueEntryFactory.create_batch(30)

        request = rf.get('/')
        response = views.queue_stats(request)

        assert response.status_code == 200

    def test_totals_context_variable(self, client):
        entries = factories.QueueEntryFactory.create_batch(30)

        response = client.get(reverse('coda_replication.views.queue_stats'))
        totals = response.context[-1].get('totals')

        assert len(entries) == totals

    def test_status_count_context_variable(self, client):
        entries = factories.QueueEntryFactory.create_batch(30)

        response = client.get(
            reverse('coda_replication.views.queue_stats'))

        status_counts = response.context[-1].get('status_counts')
        assert len(status_counts) == 10

        # Verify the calculated number of QueueEntries, grouped by status, are
        # correct.
        for status_id, status in STATUS_CHOICES:
            assert status_counts.get(status) == sum(e.status == status_id for e in entries)

    def test_template_used(self, client):
        response = client.get(reverse('coda_replication.views.queue_stats'))
        assert response.template[0].name == 'coda_replication/stats.html'


class TestQueueSearch:
    """
    Tests for coda_replication.views.queue_search.
    """

    def test_status_ok_without_entries(self, rf):
        request = rf.get('/')
        response = views.queue_search(request)
        assert response.status_code == 200

    def test_status_ok(self, rf):
        factories.QueueEntryFactory.create_batch(30)
        request = rf.get('/')
        response = views.queue_search(request)
        assert response.status_code == 200

    def test_entries_context_variable_is_page_object(self, client):
        factories.QueueEntryFactory.create_batch(20)

        response = client.get(
            reverse('coda_replication.views.queue_search'))

        page = response.context[-1]['entries']
        assert isinstance(page, Page)

    def test_blank_search_returns_all_queues(self, client):
        entries = factories.QueueEntryFactory.create_batch(20)

        response = client.get(
            reverse('coda_replication.views.queue_search'))

        results = response.context[-1]['entries']
        assert len(entries) == len(results.object_list)

    def test_filtering_by_status(self, client):
        entries = factories.QueueEntryFactory.create_batch(20)
        status = '2'

        response = client.get(
            reverse('coda_replication.views.queue_search'),
            {'status': status})

        results = response.context[-1]['entries']
        assert sum(q.status == status for q in entries) == len(results.object_list)

    def test_sorting_by_size(self, client):
        """
        Tests that the QueueEntry search results are ordered by the bytes
        attribute in ascending order with the sort query is `size`.
        """
        entries = factories.QueueEntryFactory.create_batch(20)
        response = client.get(
            reverse('coda_replication.views.queue_search'),
            {'sort': 'size'})

        results = response.context[-1]['entries']
        entries.sort(key=lambda x: x.bytes)

        for entry, result in zip(entries, results.object_list):
            assert entry.bytes == result.bytes

    def test_filtering_by_harvest_end(self, client):
        entry = factories.QueueEntryFactory.create()
        date_string = entry.harvest_end.strftime('%m/%d/%Y')

        response = client.get(
            reverse('coda_replication.views.queue_search'),
            {'end_date': date_string})

        end_date = response.context[-1]['end_date']

        assert end_date.year == entry.harvest_end.year
        assert end_date.month == entry.harvest_end.month
        assert end_date.day == entry.harvest_end.day

    def test_filtering_by_harvest_start(self, client):
        entry = factories.QueueEntryFactory.create()
        date_string = entry.harvest_start.strftime('%m/%d/%Y')

        response = client.get(
            reverse('coda_replication.views.queue_search'),
            {'start_date': date_string})

        start_date = response.context[-1]['start_date']

        assert start_date.year == entry.harvest_start.year
        assert start_date.month == entry.harvest_start.month
        assert start_date.day == entry.harvest_start.day

    def test_filtering_by_identifier(self, client):
        # Populate the database with a numerous QueueEntry objects so we can
        # verify that the search will find the correct object among many.
        factories.QueueEntryFactory.create_batch(30)
        entry = factories.QueueEntryFactory.create()

        response = client.get(
            reverse('coda_replication.views.queue_search'),
            {'identifier': entry.ark})

        # Verify the results contain only 1 QueueEntry.
        results = response.context[-1]['entries']
        assert len(results.object_list) == 1

        # Verify that the single object has the same identifier.
        result = results.object_list[0]
        assert result.ark == entry.ark


class TestQueueSearchJSON:
    """
    Test for coda_replication.views.queue_search_JSON.
    """

    def test_without_entries(self, rf):
        request = rf.get('/')
        response = views.queue_search_JSON(request)

        data = json.loads(response.content)
        assert {} == data

    def test_feed_entry_fields(self, rf):
        factories.QueueEntryFactory.create_batch(10)
        request = rf.get('/')
        response = views.queue_search_JSON(request)

        data = json.loads(response.content)
        entry = data['feed']['entry'][0]

        assert entry.get('oxum', False)
        assert entry.get('harvest_start', False)
        assert entry.get('harvest_end', False)
        assert entry.get('queue position', False)
        assert entry.get('identifier', False)
        assert entry.get('status', False)

    def test_pagination_links_first_page(self, rf):
        factories.QueueEntryFactory.create_batch(50)

        request = rf.get('/')
        response = views.queue_search_JSON(request)

        data = json.loads(response.content)
        links = data['feed']['link']

        assert len(links) == 4

        current_page = links[0]
        first_page = links[1]
        last_page = links[2]
        next_page = links[3]

        assert '?page=1' in current_page['href']
        assert 'self' == current_page['rel']
        assert '?page=1' in first_page['href']
        assert 'first' == first_page['rel']
        assert '?page=3' in last_page['href']
        assert 'last' == last_page['rel']
        assert '?page=2' in next_page['href']
        assert 'next' == next_page['rel']

    def test_pagination_links_last_page(self, rf):
        factories.QueueEntryFactory.create_batch(50)

        request = rf.get('/', {'page': 3})
        response = views.queue_search_JSON(request)

        data = json.loads(response.content)
        links = data['feed']['link']

        assert len(links) == 4

        current_page = links[0]
        first_page = links[1]
        last_page = links[2]
        previous_page = links[3]

        assert '?page=3' in current_page['href']
        assert 'self' == current_page['rel']
        assert '?page=1' in first_page['href']
        assert 'first' == first_page['rel']
        assert '?page=3' in last_page['href']
        assert 'last' == last_page['rel']
        assert '?page=2' in previous_page['href']
        assert 'previous' == previous_page['rel']

    def test_pagination_links_middle_page(self, rf):
        factories.QueueEntryFactory.create_batch(50)

        request = rf.get('/', {'page': 2})
        response = views.queue_search_JSON(request)

        data = json.loads(response.content)
        links = data['feed']['link']

        assert len(links) == 5

        current_page = links[0]
        first_page = links[1]
        last_page = links[2]
        previous_page = links[3]
        next_page = links[4]

        assert '?page=2' in current_page['href']
        assert 'self' == current_page['rel']
        assert '?page=1' in first_page['href']
        assert 'first' == first_page['rel']
        assert '?page=3' in last_page['href']
        assert 'last' == last_page['rel']
        assert '?page=1' in previous_page['href']
        assert 'previous' == previous_page['rel']
        assert '?page=3' in next_page['href']
        assert 'next' == next_page['rel']


class TestQueueRecent:
    """
    Tests for coda_replication.views.queue_recent.
    """

    def test_status_ok_without_entries(self, rf):
        request = rf.get('/')
        response = views.queue_recent(request)
        assert response.status_code == 200

    def test_status_ok(self, rf):
        factories.QueueEntryFactory.create_batch(30)
        request = rf.get('/')
        response = views.queue_recent(request)
        assert response.status_code == 200

    def test_number_entries_returned(self, client):
        factories.QueueEntryFactory.create_batch(30)
        response = client.get(
            reverse('coda_replication.views.queue_recent'))

        entries = response.context[-1]['entries']
        assert len(entries) == 10

    def test_template_used(self, client):
        factories.QueueEntryFactory.create_batch(30)
        response = client.get(
            reverse('coda_replication.views.queue_recent'))

        assert response.template[0].name == 'coda_replication/queue.html'


class TestQueue:
    """
    Tests for coda_replication.views.queue.
    """

    @pytest.fixture
    def queue_xml(self):
        return """<?xml version="1.0"?>
            <entry xmlns="http://www.w3.org/2005/Atom">
            <title>ark:/67531/coda4fnk</title>
            <id>http://example.com/ark:/67531/coda4fnk/</id>
            <updated>2014-04-23T15:39:20Z</updated>
            <content type="application/xml">
                <queueEntry xmlns="http://digital2.library.unt.edu/coda/queuexml/">
                <ark>ark:/67531/coda4fnk</ark>
                <oxum>3640551.188</oxum>
                <urlListLink>http://example.com/ark:/67531/coda4fnk.urls</urlListLink>
                <status>1</status>
                <start>2013-05-17T01:35:04Z</start>
                <end>2013-05-17T01:35:13Z</end>
                <position>2</position>
                </queueEntry>
            </content>
            </entry>
        """

    def test_get_with_identifier(self, rf):
        entry = factories.QueueEntryFactory.create()
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.queue(request, entry.ark)

        queue_xml = objectify.fromstring(response.content)
        assert queue_xml.title == entry.ark
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    def test_get_without_identifier(self, rf):
        factories.QueueEntryFactory.create_batch(30)
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.queue(request)

        xml = objectify.fromstring(response.content)
        assert len(xml.entry) == 10
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    def test_get_without_identifier_with_not_entries(self, rf):
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.queue(request)

        xml = objectify.fromstring(response.content)
        assert hasattr(xml, 'entry') is False
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    def test_delete(self, rf):
        entry = factories.QueueEntryFactory.create()
        request = rf.delete('/')
        response = views.queue(request, entry.ark)

        assert response.status_code == 200
        assert QueueEntry.objects.count() == 0

    def test_delete_returns_not_found(self, rf):
        request = rf.delete('/')
        response = views.queue(request, 'ark:/000001/dne')
        assert response.status_code == 404

    def test_put(self, queue_xml, rf):
        entry = factories.QueueEntryFactory.create(ark='ark:/67531/coda4fnk', bytes='4')

        request = rf.put('/', queue_xml, 'application/xml', HTTP_HOST='example.com')
        response = views.queue(request, entry.ark)

        updated_entry = QueueEntry.objects.get(ark=entry.ark)

        assert entry.oxum != updated_entry.oxum
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    def test_post(self, queue_xml, rf):
        assert QueueEntry.objects.count() == 0

        request = rf.post('/', queue_xml, 'application/xml', HTTP_HOST='example.com')
        response = views.queue(request)

        assert QueueEntry.objects.count() == 1
        assert response.status_code == 201
        assert response['Content-Type'] == 'application/atom+xml'
        assert response.has_header('Location')

    @pytest.mark.xfail
    def test_post_with_identifier(self, queue_xml, rf):
        request = rf.post('/', queue_xml, 'application/xml')
        response = views.queue(request, 'ark:/000001/dne')
        assert response.status_code == 400
