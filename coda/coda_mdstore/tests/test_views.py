import pytest
from mock import Mock

from django.core.urlresolvers import reverse

from .. import views


# Add this mark so that we are not loading all the urls for
# the entire project when using reverse.
pytestmark = pytest.mark.urls('coda_mdstore.urls')


class TestIndexView:

    @pytest.fixture(autouse=True)
    def patched_models(self, monkeypatch):
        Bag = Mock()
        Bag.objects.all().aggregate.return_value = {'files__sum': 1}
        monkeypatch.setattr('coda_mdstore.views.Bag', Bag)

        QueueEntry = Mock()
        QueueEntry.objects.count.return_value = 10
        monkeypatch.setattr('coda_mdstore.views.QueueEntry', QueueEntry)

        Validate = Mock()
        Validate.objects.count.return_value = 10
        monkeypatch.setattr('coda_mdstore.views.Validate', Validate)

        Site = Mock()
        Site.objects.get_current().name = 'example.com'
        monkeypatch.setattr('coda_mdstore.views.Site', Site)

        Event = Mock()
        Event.objects.count.return_value = 10
        monkeypatch.setattr('coda_mdstore.views.Event', Event)

    def test_status_code_200(self, rf):
        request = rf.get('/')
        response = views.index(request)
        assert response.status_code == 200

    @pytest.mark.parametrize('key', [
        'site_title',
        'totals',
        'queue_total',
        'validation_total',
        'event_total',
        'maintenance_message'
    ])
    def test_context_has_key(self, key, client):
        response = client.get(reverse('coda_mdstore.views.index'))
        assert key in response.context[-1]

    def test_renders_correct_template(self, client):
        response = client.get(reverse('coda_mdstore.views.index'))
        assert response.template[0].name == 'mdstore/index.html'
