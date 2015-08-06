import pytest

from django.core.paginator import Page
from django.core.urlresolvers import reverse

from .. import factories
from .. import views
from ..models import STATUS_CHOICES


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
