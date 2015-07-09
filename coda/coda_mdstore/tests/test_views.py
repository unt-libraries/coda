import urllib2

import pytest
from mock import Mock, MagicMock, patch

from django.core.urlresolvers import reverse
from django import http

from .. import views
from .. import models


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

    def test_returns_status_code_200(self, rf):
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

        PayloadOxum = MagicMock()
        PayloadOxum.field_name = 'Payload-Oxum'
        self.payload_oxum = PayloadOxum

        BaggingDate = MagicMock()
        BaggingDate.field_name = 'Bagging-Date'
        BaggingDate.field_body = '2015-01-01'
        self.bagging_date = BaggingDate

        Bag_Info = Mock()
        Bag_Info.objects.filter.return_value = [PayloadOxum, BaggingDate]
        monkeypatch.setattr('coda_mdstore.views.Bag_Info', Bag_Info)

        Site = Mock()
        Site.objects.get_current().name = 'example.com'
        monkeypatch.setattr('coda_mdstore.views.Site', Site)

    @pytest.mark.xfail(reason='View cannot handle bag without a member '
                              'Payload-Oxum Bag_Info')
    def test_bag_info_does_not_have_payload_oxum(self, rf):
        self.payload_oxum.field_name = ''
        response = views.bagHTML(rf.get('/'), 'fake-identifier')

        assert response.status_code in (200, 404)

    @pytest.mark.xfail(reason='View cannot handle bag without a member '
                              'Bagging-Date Bag_Info')
    def test_bag_info_does_not_have_bagging_date(self, rf):
        self.bagging_date.field_name = ''
        response = views.bagHTML(rf.get('/'), 'fake-identifier')

        assert response.status_code in (200, 404)

    def test_catches_urlerror(self, client, monkeypatch):
        urlopen = Mock(side_effect=urllib2.URLError('Fake Exception'))
        monkeypatch.setattr('coda_mdstore.views.urllib2.urlopen', urlopen)

        response = client.get(
            reverse('coda_mdstore.views.bagHTML', args=['fake-identifier']))

        assert urlopen.call_count == 1
        assert response.context[-1]['json_events'] == {}

    def test_renders_correct_template(self, client):
        response = client.get(
            reverse('coda_mdstore.views.bagHTML', args=['fake-identifier']))

        assert response.template[0].name == 'mdstore/bag_info.html'

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


class Test_bagProxy:

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        Bag = Mock()
        Bag.objects.get.return_value = Bag
        monkeypatch.setattr('coda_mdstore.views.Bag', Bag)

        # The mocked value that getFileHandle will return.
        fileHandle = Mock()
        fileHandle.info().getheader.side_effect = ['text/plain', '255']
        monkeypatch.setattr(
            'coda_mdstore.views.getFileHandle', Mock(return_value=fileHandle))

    def test_returns_status_code_200(self, rf):
        request = rf.get('/')
        response = views.bagProxy(request, 'fake-identifier', '/foo/bar')
        assert response.status_code == 200

    def test_response_has_correct_headers(self, rf):
        request = rf.get('/')
        response = views.bagProxy(request, 'fake-identifier', '/foo/bar')
        assert response['Content-Length'] == '255'
        assert response['Content-Type'] == 'text/plain'

    # FIXME
    @pytest.mark.xfail(msg="Figure out how to mock AND catch the DoesNotExist")
    def test_raises_not_found_when_object_not_found(self, rf, monkeypatch):
        Bag = Mock()
        Bag.objects.get.side_effect = models.Bag.DoesNotExist
        monkeypatch.setattr('coda_mdstore.views.Bag', Bag)
        request = rf.get('/')

        with pytest.raises(http.HttpResponseNotFound):
            views.bagProxy(request, 'fake-identifier', '/foo/bar')

    def test_raises_http404_when_file_handle_is_false(self, rf, monkeypatch):
        monkeypatch.setattr(
            'coda_mdstore.views.getFileHandle', Mock(return_value=False))
        request = rf.get('/')

        with pytest.raises(http.Http404):
            views.bagProxy(request, 'fake-identifier', '/foo/bar')

    @pytest.mark.xfail
    def test_bag_proxy_catches_exception_raised_by_getFileHandler(self):
        assert 0


class IntegrationTests:
    pass
