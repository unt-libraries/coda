from lxml import objectify
import pytest
from coda_mdstore import factories


@pytest.fixture(autouse=True)
def set_debug_to_false(settings):
    settings.DEBUG = False
    settings.DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: False
    }


@pytest.mark.django_db
class TestAtomSiteNewsFeed:

    def test_num_entries_per_page(self, client):
        factories.BagFactory.create_batch(30)
        response = client.get('/feed/')

        feed = objectify.fromstring(response.content)
        assert len(feed.entry) == 20

    def test_has_pagination_links(self, client):
        factories.BagFactory.create_batch(50)
        response = client.get('/feed/')

        feed = objectify.fromstring(response.content)

        assert '?p=1' in feed.link[2].get('href')
        assert feed.link[2].get('rel') == 'first'

        assert '?p=3' in feed.link[3].get('href')
        assert feed.link[3].get('rel') == 'last'

        assert '?p=2' in feed.link[4].get('href')
        assert feed.link[4].get('rel') == 'next'

    def test_next_related_link_not_present(self, client):
        factories.BagFactory.create_batch(19)
        response = client.get('/feed/')

        feed = objectify.fromstring(response.content)
        assert feed.link[-1].get('rel') == 'last'

    def test_has_previous_related_link(self, client):
        factories.BagFactory.create_batch(30)
        response = client.get('/feed/', {'p': 2})

        feed = objectify.fromstring(response.content)

        assert '?p=1' in feed.link[-1].get('href')
        assert feed.link[-1].get('rel') == 'previous'

    @pytest.mark.xfail(reason="EmptyPage exception should not be raised.")
    def test_invalid_page_raises_exception(self, client):
        factories.BagFactory.create_batch(19)
        client.get('/feed/', {'p': 2})
