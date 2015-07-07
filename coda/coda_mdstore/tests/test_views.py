import pytest
from mock import Mock, MagicMock

from django.core.urlresolvers import reverse

from .. import views


# Add this mark so that we are not loading all the urls for
# the entire project when using reverse.
pytestmark = pytest.mark.urls('coda_mdstore.urls')


class TestIndexView:

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        """
        Setup the tests for ..views.index by mocking the database
        models. This will be automatically provided to all the
        test methods.
        """
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

    def test_totals_files__sum_key_is_none(self, client, monkeypatch):
        """
        Check that the `files__sum` key is set 0 if the db returns
        None.
        """
        # Re-patch the Bag entity to modify the return value from the
        # database query.
        Bag = Mock()
        Bag.objects.all().aggregate.return_value = {'files__sum': None}
        monkeypatch.setattr('coda_mdstore.views.Bag', Bag)

        response = client.get(reverse('coda_mdstore.views.index'))
        assert response.context[-1]['totals']['files__sum'] == 0


class TestAboutView:

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        Site = Mock()
        Site.objects.get_current().name = 'example.com'
        monkeypatch.setattr('coda_mdstore.views.Site', Site)

    def test_renders_correct_template(self, client):
        response = client.get(reverse('coda_mdstore.views.about'))
        assert response.template[0].name == 'mdstore/about.html'


class TestAllBagsView:

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        Site = Mock()
        Site.objects.get_current().name = 'example.com'
        monkeypatch.setattr('coda_mdstore.views.Site', Site)

        paginate_entries = Mock(return_value='fake data')
        monkeypatch.setattr(
            'coda_mdstore.views.paginate_entries', paginate_entries)

    def test_renders_correct_template(self, client):
        response = client.get(reverse('coda_mdstore.views.all_bags'))
        assert response.template[0].name == 'mdstore/bag_search_results.html'

    def test_uses_paginated_entries(self, client, monkeypatch):
        paginate_entries = Mock(return_value='fake data')
        monkeypatch.setattr(
            'coda_mdstore.views.paginate_entries', paginate_entries)

        response = client.get(reverse('coda_mdstore.views.all_bags'))
        assert paginate_entries.call_count == 1
        assert response.context[-1]['entries'] == 'fake data'

    @pytest.mark.parametrize('key', [
        'site_title',
        'entries',
        'maintenance_message'
    ])
    def test_context_has_key(self, key, client):
        response = client.get(reverse('coda_mdstore.views.all_bags'))
        assert key in response.context[-1]


class Test_shooRobot:

    def test_user_agent_is_all(self, rf):
        request = rf.get('/')
        response = views.shooRobot(request)
        assert 'User-agent: *' in response.content

    def test_disallow(self, rf):
        request = rf.get('/')
        response = views.shooRobot(request)
        assert 'Disallow: /' in response.content


class Test_bagHTML:

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        Bag = Mock()
        monkeypatch.setattr('coda_mdstore.views.get_object_or_404', Bag)

        Bag_Info1 = MagicMock()
        Bag_Info1.field_name = 'Payload-Oxum'

        Bag_Info2 = MagicMock()
        Bag_Info2.field_name = 'Bagging-Date'
        Bag_Info2.field_body = '2015-01-01'

        Bag_Info = Mock()
        Bag_Info.objects.filter.return_value = [Bag_Info1, Bag_Info2]
        monkeypatch.setattr('coda_mdstore.views.Bag_Info', Bag_Info)

        Site = Mock()
        Site.objects.get_current().name = 'example.com'
        monkeypatch.setattr('coda_mdstore.views.Site', Site)

    def test_bag_info_does_not_have_payload_oxum(self):
        pass

    def test_bag_info_does_not_have_bagging_date(self):
        pass

    def test_catches_urlerror(self):
        pass

    def test_renders_correct_template(self):
        pass

    @pytest.mark.parametrize('key', [
        'site_title',
        'json_events',
        'payload_oxum_file_count',
        'payload_oxum_size',
        'bag_date',
        'bag',
        'bag_info',
        'maintenance_message'
    ])
    def test_context_has_key(self, key, client):
        response = client.get(
            reverse('coda_mdstore.views.bagHTML', args=['fakeid']))

        assert key in response.context[-1]
