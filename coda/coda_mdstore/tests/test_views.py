from datetime import datetime
import json
import urllib2

from lxml import etree
import mock
import pytest

from django.core.urlresolvers import reverse
from django import http
from django.core.paginator import Paginator

from .. import views
from .. import models
from .factories import BagWithBag_InfoFactory, NodeFactory


# Add this mark so that we are not loading all the urls for
# the entire project when using reverse.
pytestmark = pytest.mark.urls('coda_mdstore.urls')


@pytest.fixture
def patch_site(monkeypatch):
    Site = mock.Mock()
    Site.objects.get_current().name = 'example.com'
    monkeypatch.setattr('coda_mdstore.views.Site', Site)
    return Site


@pytest.mark.usefixtures('patch_site')
class TestIndexView:

    # @pytest.fixture(autouse=True)
    def setup_method(self, method):
        """
        Setup the tests for ..views.index by mocking the database
        models. This will be automatically provided to all the
        test methods.
        """
        self.bag_patcher = mock.patch('coda_mdstore.views.Bag')
        self.queue_entry_patcher = mock.patch('coda_mdstore.views.QueueEntry')
        self.validate_patcher = mock.patch('coda_mdstore.views.Validate')
        self.event_patcher = mock.patch('coda_mdstore.views.Event')

        self.mock_bag = self.bag_patcher.start()
        self.mock_queue_entry = self.queue_entry_patcher.start()
        self.mock_validate = self.validate_patcher.start()
        self.mock_event = self.event_patcher.start()

        self.mock_bag.objects.all().aggregate.return_value = {'files__sum': 1}
        self.mock_queue_entry.objects.count.return_value = 10
        self.mock_validate.objects.count.return_value = 10
        self.mock_event.objects.count.return_value = 10

    def teardown_method(self, method):
        self.bag_patcher.stop()
        self.queue_entry_patcher.stop()
        self.validate_patcher.stop()
        self.event_patcher.stop()

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
        self.mock_bag.objects.all().aggregate.return_value = {
            'files__sum': None
        }

        response = client.get(reverse('coda_mdstore.views.index'))
        assert response.context[-1]['totals']['files__sum'] == 0


@pytest.mark.usefixtures('patch_site')
class TestAboutView:

    def test_renders_correct_template(self, client):
        response = client.get(reverse('coda_mdstore.views.about'))
        assert response.template[0].name == 'mdstore/about.html'


@pytest.mark.django_db
@pytest.mark.usefixtures('patch_site')
class TestStatsView:

    def test_no_bags_available(self, client):
        response = client.get(reverse('coda_mdstore.views.stats'))

        assert response.status_code == 200

        assert response.context[-1]['totals'] == 0
        assert response.context[-1]['monthly_bags'] == []
        assert response.context[-1]['monthly_files'] == []
        assert response.context[-1]['monthly_running_bag_total'] == []
        assert response.context[-1]['monthly_running_file_total'] == []

    @pytest.mark.xfail
    def test_with_bags(self):
        assert 0


class TestJSONStatsView:

    @mock.patch('coda_mdstore.views.Bag')
    @mock.patch('coda_mdstore.views.Node')
    def test_no_bags_or_nodes(self, mock_node, mock_bag, client):
        mock_node.objects.aggregate.return_value = {'node_capacity__sum': 0}
        mock_bag.objects.aggregate.return_value = {
            'bagging_date__max': None,
            'pk__count': 0,
            'size__sum': 0,
            'files__sum': 0
        }

        response = client.get(reverse('coda_mdstore.views.json_stats'))
        payload = json.loads(response.content)

        assert len(payload) == 5
        assert payload['bags'] == 0
        assert payload['capacity'] == 0
        assert payload['capacity_used'] == 0
        assert payload['files'] == 0
        assert payload['updated'] == ''

    @mock.patch('coda_mdstore.views.Bag')
    @mock.patch('coda_mdstore.views.Node')
    def test_with_bags_and_nodes(self, mock_node, mock_bag, client):
        mock_node.objects.aggregate.return_value = {
            'node_capacity__sum': 1000000
        }
        mock_bag.objects.aggregate.return_value = {
            'bagging_date__max': datetime(2015, 01, 01),
            'pk__count': 50,
            'size__sum': 100000,
            'files__sum': 1000,
        }

        response = client.get(reverse('coda_mdstore.views.json_stats'))
        payload = json.loads(response.content)

        assert len(payload) == 5
        assert payload['bags'] == 50
        assert payload['capacity'] == 1000000
        assert payload['capacity_used'] == 100000
        assert payload['files'] == 1000
        assert payload['updated'] == '2015-01-01'


@pytest.mark.usefixtures('patch_site')
class TestAllBagsView:

    @pytest.fixture(autouse=True)
    def mock_pe(self, monkeypatch):
        """Patches the paginate_entries with a Mock object."""
        mock_pe = mock.Mock()
        monkeypatch.setattr(
            'coda_mdstore.views.paginate_entries', mock_pe)

        return mock_pe

    def test_renders_correct_template(self, client):
        response = client.get(reverse('coda_mdstore.views.all_bags'))
        assert response.template[0].name == 'mdstore/bag_search_results.html'

    def test_uses_paginated_entries(self, mock_pe, client, monkeypatch):
        mock_pe.return_value = 'fake data'

        response = client.get(reverse('coda_mdstore.views.all_bags'))
        assert mock_pe.call_count == 1
        assert response.context[-1]['entries'] == 'fake data'

    @pytest.mark.parametrize('key', [
        'site_title',
        'entries',
        'maintenance_message'
    ])
    def test_context_has_key(self, key, client):
        response = client.get(reverse('coda_mdstore.views.all_bags'))
        assert key in response.context[-1]


class TestRobotsView:

    def test_user_agent_is_all(self, rf):
        request = rf.get('/')
        response = views.shooRobot(request)
        assert 'User-agent: *' in response.content

    def test_disallow(self, rf):
        request = rf.get('/')
        response = views.shooRobot(request)
        assert 'Disallow: /' in response.content


@pytest.mark.usefixtures('patch_site')
class TestBagHTMLView:

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        Bag = mock.Mock()
        monkeypatch.setattr('coda_mdstore.views.get_object_or_404', Bag)

        self.payload_oxum = mock.MagicMock()
        self.payload_oxum.field_name = 'Payload-Oxum'

        self.bagging_date = mock.MagicMock()
        self.bagging_date.field_name = 'Bagging-Date'
        self.bagging_date.field_body = '2015-01-01'

        Bag_Info = mock.Mock()
        Bag_Info.objects.filter.return_value = [
            self.bagging_date,
            self.payload_oxum
        ]
        monkeypatch.setattr('coda_mdstore.views.Bag_Info', Bag_Info)

    @pytest.mark.xfail(reason='View cannot handle bag without a member '
                              'Payload-Oxum Bag_Info')
    def test_bag_info_does_not_have_payload_oxum(self, rf):
        self.payload_oxum.field_name = ''
        response = views.bagHTML(rf.get('/'), 'ark:/00001/id')

        assert response.status_code in (200, 404)

    @pytest.mark.xfail(reason='View cannot handle bag without a member '
                              'Bagging-Date Bag_Info')
    def test_bag_info_does_not_have_bagging_date(self, rf):
        self.bagging_date.field_name = ''
        response = views.bagHTML(rf.get('/'), 'ark:/00001/id')

        assert response.status_code in (200, 404)

    def test_catches_urlerror(self, client, monkeypatch):
        urlopen = mock.Mock(side_effect=urllib2.URLError('Fake Exception'))
        monkeypatch.setattr('coda_mdstore.views.urllib2.urlopen', urlopen)

        response = client.get(
            reverse('coda_mdstore.views.bagHTML', args=['ark:/00001/id']))

        assert urlopen.call_count == 1
        assert response.context[-1]['json_events'] == {}

    def test_renders_correct_template(self, client):
        response = client.get(
            reverse('coda_mdstore.views.bagHTML', args=['ark:/00001/id']))

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


@pytest.mark.django_db
class TestBagProxyView:

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, monkeypatch):
        self.bag = BagWithBag_InfoFactory.create()

        # The mocked value that getFileHandle will return.
        file_handle = mock.Mock()
        file_handle.info().getheader.side_effect = ['text/plain', '255']

        self.getFileHandle = mock.Mock(return_value=file_handle)
        monkeypatch.setattr(
            'coda_mdstore.views.getFileHandle', self.getFileHandle)

    def test_returns_status_code_200(self, rf):
        request = rf.get('/')
        response = views.bagProxy(request, self.bag.name, '/foo/bar')
        assert response.status_code == 200

    def test_response_has_correct_headers(self, rf):
        request = rf.get('/')
        response = views.bagProxy(request, self.bag.name, '/foo/bar')
        assert response['Content-Length'] == '255'
        assert response['Content-Type'] == 'text/plain'

    def test_raises_not_found_when_object_not_found(self, rf):
        request = rf.get('/')
        response = views.bagProxy(request, 'ark:/00002/id', '/foo/bar')

        assert response.status_code == 404
        assert response.content == "There is no bag with id 'ark:/00002/id'."

    def test_raises_http404_when_file_handle_is_false(self, rf):
        self.getFileHandle.return_value = False
        request = rf.get('/')

        with pytest.raises(http.Http404):
            views.bagProxy(request, self.bag.name, '/foo/bar')

    @pytest.mark.xfail
    def test_bag_proxy_catches_exception_raised_by_getFileHandler(self):
        assert 0


@pytest.mark.django_db
class TestBagURLListView:

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, monkeypatch):
        self.bag = BagWithBag_InfoFactory.create()

        # The mocked value that getFileHandle will return.
        file_handle = mock.Mock()
        file_handle.info().getheader.side_effect = ['text/plain', '255']

        self.getFileHandle = mock.Mock(return_value=file_handle)
        monkeypatch.setattr(
            'coda_mdstore.views.getFileHandle', self.getFileHandle)

    @pytest.mark.xfail(msg='Response content does not match other responses.')
    def test_raises_not_found_when_object_not_found(self, rf):
        request = rf.get('/')
        response = views.bagURLList(request, 'ark:/00002/id')

        assert isinstance(response, http.HttpResponseNotFound)
        assert response.content == "There is no bag with id 'ark:/00002/id'."

    @pytest.mark.xfail
    def test_raises_http404_file_handle_is_falsy(self):
        assert 0

    @pytest.mark.xfail
    def test_output_text(self):
        assert 0

    @pytest.mark.xfail
    def test_top_files_block(self):
        # TODO: rename once implemented.
        assert 0

    @pytest.mark.xfail
    def test_path_is_not_unicode_safe(self):
        assert 0

    @pytest.mark.xfail
    def test_returns_status_code_200(self):
        assert 0

@pytest.mark.django_db
class TestBagURLListScrapeView:

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, monkeypatch):
        file_handle = mock.Mock()
        file_handle.info().getheader.side_effect = ['text/plain', '255']

        self.getFileHandle = mock.Mock(return_value=file_handle)
        monkeypatch.setattr(
            'coda_mdstore.views.getFileHandle', self.getFileHandle)


    def test_raises_not_found_when_object_not_found(self, rf):
        request = rf.get('/')
        response = views.bagURLListScrape(request, 'ark:/00001/id')

        assert response.status_code == 404
        assert isinstance(response, http.HttpResponseNotFound)
        assert response.content == "There is no bag with id 'ark:/00001/id'."

    @pytest.mark.xfail(msg='pairtreeCandidateList is not available in scope.')
    def test_raises_http404_file_handle_is_falsy(self, rf):
        BagWithBag_InfoFactory.create()
        self.getFileHandle.return_value = False

        request = rf.get('/')
        with pytest.raises(http.Http404):
            views.bagURLListScrape(request, 'ark:/00001/id')

    @pytest.mark.xfail(msg='pairtreeCandidateList is not available in scope.')
    def test_response_content(self):
        assert 0


class TestBagFullTextSearchATOMView:

    @pytest.mark.xfail(msg='The function bagFullTextSearchATOM is not used.')
    def test_smoke(self):
        assert 0


@pytest.mark.django_db
class TestBagFullTextSearchView:

    @pytest.mark.xfail(msg='FULLTEXT index is required.')
    def test_returns_paginator_object(self):
        [BagWithBag_InfoFactory.create() for _ in range(15)]
        paginator = views.bagFullTextSearch('test search')

        assert isinstance(paginator, Paginator)


@pytest.mark.django_db
@pytest.mark.usefixtures('patch_site')
class TestShowNodeStatusView:

    def test_gets_status_for_single_node(self, rf):
        node = NodeFactory.create()
        request = rf.get('/')
        response = views.showNodeStatus(request, node.node_name)

        assert response.status_code == 200

    def test_single_node_context(self, client):
        # TODO: Update the url ordering so that we can get the url with
        #       reverse.
        node = NodeFactory.create()
        url = '/node/{0}/'.format(node.node_name)
        response = client.get(url)

        assert response.context[-1].get('node', False)
        assert response.context[-1].get('filled', False)
        assert response.context[-1].get('available', False)

    def test_response_with_all_nodes(self, rf):
        [NodeFactory.create() for _ in range(10)]

        request = rf.get('/')
        response = views.showNodeStatus(request)
        assert response.status_code == 200

    def test_context_with_all_nodes(self, client):
        [NodeFactory.create() for _ in range(10)]

        response = client.get(reverse('coda_mdstore.views.showNodeStatus'))
        context = response.context[-1]

        assert len(context.get('status_list')) == 10
        assert context.get('total_capacity') == 1024 * 1000 * 10
        assert context.get('total_size') == 512 * 900 * 10
        assert context.get('total_filled') == 45.0

    def test_no_nodes_available(self, rf):
        request = rf.get('/')
        response = views.showNodeStatus(request)
        assert response.status_code == 200


@pytest.mark.django_db
class TestAppNode:

    # @pytest.fixture(autouse=True)
    # def setup_fixtures(self, monkeypatch):
    #     self.node = mock.MagicMock(node_name='coda-001')
    #     monkeypatch.setattr('coda_mdstore.views.Node', self.node)

    #     xml = etree.Element('root')
    #     self.nodeEntry = mock.MagicMock(return_value=xml)
    #     monkeypatch.setattr('coda_mdstore.views.nodeEntry', self.nodeEntry)

    #     self.createNode = mock.MagicMock(return_value=self.node)
    #     monkeypatch.setattr('coda_mdstore.views.createNode', self.createNode)

    #     self.updateNode = mock.MagicMock(return_value=self.node)
    #     monkeypatch.setattr('coda_mdstore.views.updateNode', self.updateNode)

    def test_get_request_without_identifier(self, rf):
        [NodeFactory.create() for _ in range(10)]
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_node(request)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

        tree = etree.fromstring(response.content)
        # There should be atleast 10 elements, which is the number of
        # node objects Node.objects.all() will return.
        assert len(tree) >= 10

    def test_get_request_with_identifier(self, rf):
        node = NodeFactory.create()
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_node(request, node.node_name)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'
        # TODO: test the response content.

    def test_get_request_with_identifier_raises_exception(self, rf):
        request = rf.get('/')
        response = views.app_node(request, '001')
        assert response.status_code == 404

    @mock.patch('coda_mdstore.views.createNode')
    def test_post_request(self, mock_createNode, rf):
        node = NodeFactory.create()
        mock_createNode.return_value = node

        request = rf.post('/', HTTP_HOST='example.com')
        response = views.app_node(request)

        assert response.status_code == 201
        assert response['Content-Type'] == 'application/atom+xml'
        assert response['Location'] == (
            'http://example.com/APP/node/{0}/'.format(node.node_name)
        )

    @mock.patch('coda_mdstore.views.updateNode')
    def test_put_request(self, mock_updateNode, rf):
        node = NodeFactory.create()
        mock_updateNode.return_value = node

        request = rf.put('/', HTTP_HOST='example.com')
        response = views.app_node(request, node.node_name)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    def test_delete_request(self, rf):
        node = NodeFactory.create()

        request = rf.delete('/', HTTP_HOST='example.com')
        response = views.app_node(request, node.node_name)

        assert response.status_code == 200

    def test_delete_request_returns_not_found(self, rf):
        request = rf.delete('/', HTTP_HOST='example.com')
        response = views.app_node(request, 'DNE-001')

        assert response.status_code == 404


@pytest.mark.django_db
class TestAppBag:

    def test_get_request_returns_not_found(self, rf):
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_bag(request, 'ark:/00002/id')
        assert response.status_code == 404

    def test_get_request(self, rf):
        [BagWithBag_InfoFactory.create() for _ in range(10)]

        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_bag(request)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

        tree = etree.fromstring(response.content)
        assert len(tree) >= 10

    @pytest.mark.xfail
    def test_get_request_with_identifier(self):
        assert 0

    @mock.patch('coda_mdstore.views.createBag')
    def test_post_request(self, mock_createBag, rf):
        bag = BagWithBag_InfoFactory.create()
        mock_createBag.return_value = bag, bag.bag_info_set

        request = rf.post('/', HTTP_HOST='example.com')
        response = views.app_bag(request)

        assert response.status_code == 201
        assert response['Content-Type'] == 'application/atom+xml'
        assert response['Location'] == (
            'http://example.com/APP/bag/{0}/'.format(bag.name)
        )

    def test_delete_request_is_successful(self, rf):
        bag = BagWithBag_InfoFactory.create()
        request = rf.delete('/', HTTP_HOST='example.com')
        response = views.app_bag(request, bag.name)

        assert response.status_code == 200
        assert models.Bag.objects.exists() is False

    def test_delete_request_returns_bad_request(self, rf):
        request = rf.delete('/', HTTP_HOST='example.com')
        response = views.app_bag(request)
        assert response.status_code == 400

    @pytest.mark.xfail
    def test_delete_request_removes_member_bag_info_objects(self):
        pass
