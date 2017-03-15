from datetime import datetime
import json
import urllib2

from lxml import objectify
import mock
import pytest

from django.core.urlresolvers import reverse
from django import http

from coda_mdstore import views, models, exceptions
from coda_mdstore.factories import FullBagFactory, NodeFactory, ExternalIdentifierFactory
from coda_mdstore.tests import CODA_XML


pytestmark = pytest.mark.django_db()


@pytest.fixture(autouse=True)
def patch_site(monkeypatch):
    Site = mock.Mock()
    Site.objects.get_current().name = 'example.com'
    monkeypatch.setattr('coda_mdstore.views.Site', Site)
    return Site


class TestIndexView:
    """
    Tests for coda_mdstore.views.index.
    """

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, monkeypatch):
        """
        Setup the tests for ..views.index by mocking the database
        models. This will be automatically provided to all the
        test methods.
        """

        self.mock_bag = mock.Mock()
        self.mock_bag.objects.all().aggregate.return_value = {
            'files__sum': 1,
            'pk__count': 1,
            'size_sum': 1000000,
        }
        monkeypatch.setattr('coda_mdstore.views.Bag', self.mock_bag)

        self.mock_queue_entry = mock.Mock()
        self.mock_queue_entry.objects.count.return_value = 10
        monkeypatch.setattr('coda_mdstore.views.QueueEntry',
                            self.mock_queue_entry)

        self.mock_validate = mock.Mock()
        self.mock_validate.objects.count.return_value = 10
        monkeypatch.setattr('coda_mdstore.views.Validate', self.mock_validate)

        self.mock_event = mock.Mock()
        self.mock_event.objects.count.return_value = 10
        monkeypatch.setattr('coda_mdstore.views.Event', self.mock_event)

    @pytest.mark.ignore_template_errors
    def test_returns_status_code_200(self, rf):
        request = rf.get('/', HTTP_HOST="example.com")
        response = views.index(request)
        assert response.status_code == 200

    @pytest.mark.parametrize('key', [
        'totals',
        'queue_total',
        'validation_total',
        'event_total',
        'maintenance_message'
    ])
    def test_context_has_key(self, key, client):
        response = client.get(reverse('coda_mdstore.views.index'), HTTP_HOST="example.com")
        assert key in response.context[-1]

    def test_renders_correct_template(self, client):
        response = client.get(reverse('coda_mdstore.views.index'), HTTP_HOST="example.com")
        assert response.templates[0].name == 'mdstore/index.html'

    def test_totals_files__sum_key_is_none(self, client):
        """
        Check that the `files__sum` key is set to 0 if the query returns
        None.
        """
        # Re-patch the Bag entity to modify the return value from the
        # database query.
        self.mock_bag.objects.all().aggregate.return_value = {
            'files__sum': None,
            'pk__count': 0,
            'size__sum': 0,
        }

        response = client.get(reverse('coda_mdstore.views.index'), HTTP_HOST="example.com")
        assert response.context[-1]['totals']['files__sum'] == 0


class TestAboutView:
    """
    Tests for coda_mdstore.views.about.
    """

    def test_renders_correct_template(self, client):
        response = client.get(reverse('coda_mdstore.views.about'), HTTP_HOST="example.com")
        assert response.templates[0].name == 'mdstore/about.html'


class TestStatsView:
    """
    Tests for coda_mdstore.views.stats.
    """

    def test_no_bags_available(self, client):
        """
        Test the context values when no bags are in the database.
        """
        response = client.get(reverse('coda_mdstore.views.stats'), HTTP_HOST="example.com")

        assert response.status_code == 200
        assert response.context[-1]['totals'] == 0
        assert response.context[-1]['monthly_bags'] == []
        assert response.context[-1]['monthly_files'] == []
        assert response.context[-1]['monthly_running_bag_total'] == []
        assert response.context[-1]['monthly_running_file_total'] == []

    def test_with_bags(self, client):
        """
        Test the context values when bags are in the database.
        """
        FullBagFactory.create_batch(20)

        response = client.get(reverse('coda_mdstore.views.stats'), HTTP_HOST="example.com")
        context = response.context[-1]

        assert response.status_code == 200
        assert type(context['totals']) is dict
        assert len(context['monthly_bags']) != 0
        assert len(context['monthly_files']) != 0
        assert len(context['monthly_running_bag_total']) != 0
        assert len(context['monthly_running_file_total']) != 0


class TestJSONStatsView:
    """
    Tests for coda_mdstore.views.json_stats.
    """

    @mock.patch('coda_mdstore.views.Bag')
    @mock.patch('coda_mdstore.views.Node')
    def test_no_bags_or_nodes(self, mock_node, mock_bag, client):
        """
        Test the outcome when the database does not contain any bags or
        nodes.
        """
        mock_node.objects.aggregate.return_value = {'node_capacity__sum': 0}
        mock_bag.objects.aggregate.return_value = {
            'bagging_date__max': None,
            'pk__count': 0,
            'size__sum': 0,
            'files__sum': 0
        }

        response = client.get(reverse('coda_mdstore.views.json_stats'), HTTP_HOST="example.com")
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
        """
        Test the outcome when the database does contain bags and nodes.
        """
        mock_node.objects.aggregate.return_value = {
            'node_capacity__sum': 1000000
        }
        mock_bag.objects.aggregate.return_value = {
            'bagging_date__max': datetime(2015, 01, 01),
            'pk__count': 50,
            'size__sum': 100000,
            'files__sum': 1000,
        }

        response = client.get(reverse('coda_mdstore.views.json_stats'), HTTP_HOST="example.com")
        payload = json.loads(response.content)

        assert len(payload) == 5
        assert payload['bags'] == 50
        assert payload['capacity'] == 1000000
        assert payload['capacity_used'] == 100000
        assert payload['files'] == 1000
        assert payload['updated'] == '2015-01-01'


class TestAllBagsView:
    """
    Tests for coda_mdstore.views.all_bags.
    """

    @pytest.fixture(autouse=True)
    def mock_pe(self, monkeypatch):
        """Patches the paginate_entries with a Mock object."""
        self.mock_paginate_entries = mock.MagicMock()
        monkeypatch.setattr(
            'coda_mdstore.views.paginate_entries', self.mock_paginate_entries)

    def test_renders_correct_template(self, client):
        response = client.get(reverse('coda_mdstore.views.all_bags'), HTTP_HOST="example.com")
        assert response.templates[0].name == 'mdstore/bag_search_results.html'

    @pytest.mark.ignore_template_errors
    def test_uses_paginated_entries(self, client, monkeypatch):
        """
        Verify that the view calls paginate_entries.
        """
        self.mock_paginate_entries.return_value = 'fake data'
        response = client.get(reverse('coda_mdstore.views.all_bags'), HTTP_HOST="example.com")

        assert self.mock_paginate_entries.call_count == 1
        assert response.context[-1]['entries'] == 'fake data'

    @pytest.mark.parametrize('key', [
        'entries',
        'maintenance_message'
    ])
    def test_context_has_key(self, key, client):
        response = client.get(reverse('coda_mdstore.views.all_bags'), HTTP_HOST="example.com")
        assert key in response.context[-1]


class TestRobotsView:
    """
    Tests for coda_mdstore.views.shooRobot.
    """

    def test_user_agent_is_all(self, rf):
        request = rf.get('/', HTTP_HOST="example.com")
        response = views.shooRobot(request)
        assert 'User-agent: *' in response.content

    def test_disallow(self, rf):
        request = rf.get('/', HTTP_HOST="example.com")
        response = views.shooRobot(request)
        assert 'Disallow: /' in response.content


class TestBagHTMLView:
    """
    Tests for coda_mdstore.views.bagHTML.
    """

    @pytest.mark.xfail(reason='View cannot handle bag without a member '
                              'Payload-Oxum Bag_Info')
    def test_bag_info_does_not_have_payload_oxum(self, rf):
        """
        Verify the outcome when a Bag does not have a member Bag_Info
        that has the `Payload-Oxum` key.
        """
        bag = FullBagFactory.create()
        payload, bagging_date = bag.bag_info_set.all()
        payload.field_name = ''
        payload.save()

        response = views.bagHTML(rf.get('/', HTTP_HOST="example.com"), bag.name)
        assert response.status_code in (200, 404)

    @pytest.mark.xfail(reason='View cannot handle bag without a member '
                              'Bagging-Date Bag_Info')
    def test_bag_info_does_not_have_bagging_date(self, rf):
        """
        Verify the outcome when a Bag does not have a member Bag_Info
        that has the `Bagging-Date` key.
        """
        bag = FullBagFactory.create()
        _, bagging_date = bag.bag_info_set.all()
        bagging_date.field_name = ''
        bagging_date.save()

        response = views.bagHTML(rf.get('/', HTTP_HOST="example.com"), bag.name)
        assert response.status_code in (200, 404)

    @mock.patch('coda_mdstore.views.urllib2.urlopen')
    def test_catches_urlerror(self, mock_urlopen, client):
        bag = FullBagFactory.create()
        mock_urlopen.side_effect = urllib2.URLError('Fake Exception')

        response = client.get(
            reverse('coda_mdstore.views.bagHTML', args=[bag.name]), HTTP_HOST="example.com")

        assert mock_urlopen.call_count == 1
        assert response.context[-1]['json_events'] == {}

    def test_renders_correct_template(self, client):
        bag = FullBagFactory.create()
        response = client.get(
            reverse('coda_mdstore.views.bagHTML', args=[bag.name]), HTTP_HOST="example.com")

        assert response.templates[0].name == 'mdstore/bag_info.html'

    @pytest.mark.parametrize('key', [
        'json_events',
        'payload_oxum_file_count',
        'payload_oxum_size',
        'bag_date',
        'bag',
        'bag_info',
        'maintenance_message'
    ])
    def test_context_has_key(self, key, client):
        bag = FullBagFactory.create()
        response = client.get(
            reverse('coda_mdstore.views.bagHTML', args=[bag.name]), HTTP_HOST="example.com")

        assert key in response.context[-1]


class TestBagProxyView:
    """
    Tests for coda_mdstore.views.bagProxy.
    """

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, monkeypatch):
        self.bag = FullBagFactory.create()

        # The mocked value that getFileHandle will return.
        file_handle = mock.Mock()
        file_handle.info().getheader.side_effect = ['text/plain', '255']

        self.getFileHandle = mock.Mock(return_value=file_handle)
        monkeypatch.setattr(
            'coda_mdstore.views.getFileHandle', self.getFileHandle)

        monkeypatch.setattr('coda_mdstore.views.FileWrapper', mock.Mock())

    def test_returns_status_code_200(self, rf):
        request = rf.get('/', HTTP_HOST="example.com")
        response = views.bagProxy(request, self.bag.name, '/foo/bar')
        assert response.status_code == 200

    def test_response_has_correct_headers(self, rf):
        request = rf.get('/', HTTP_HOST="example.com")
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


class TestExternalIdentiferSearch:
    """
    Tests for coda_mdstore.views.externalIdentifierSearch.
    """

    def test_no_identifier_renders_html(self, rf):
        request = rf.get('/')
        response = views.externalIdentifierSearch(request)
        assert 'text/html' in response['Content-Type']

    def test_with_valid_coda_identifier_renders_xml(self, rf):
        bag = FullBagFactory.create(name='coda-001')
        ExternalIdentifierFactory.create(belong_to_bag=bag)

        request = rf.get('/')
        response = views.externalIdentifierSearch(request, bag.name)

        assert response['Content-Type'] == 'application/atom+xml'
        assert response.status_code == 200

    def test_content_with_coda_identifier(self, rf):
        bag = FullBagFactory.create(name='coda-001')
        ExternalIdentifierFactory.create(belong_to_bag=bag)

        request = rf.get('/')
        response = views.externalIdentifierSearch(request, bag.name)

        bagxml = objectify.fromstring(response.content)
        bag_entry = bagxml.entry.content[CODA_XML]

        assert str(bag_entry.bagitVersion) == bag.bagit_version
        assert bag_entry.payloadSize == bag.size
        assert bag_entry.fileCount == bag.files
        assert bag_entry.name == bag.name
        assert len(list(bag_entry.bagInfo.iterchildren())) == 2

    def test_with_valid_metadc_identifier_renders_xml(self, rf):
        bag = FullBagFactory.create()
        ext_id = ExternalIdentifierFactory.create(
            belong_to_bag=bag,
            value='metadc000001'
        )

        request = rf.get('/')
        response = views.externalIdentifierSearch(request, ext_id.value)

        assert response['Content-Type'] == 'application/atom+xml'
        assert response.status_code == 200

    def test_content_with_metadc_identifier(self, rf):
        bag = FullBagFactory.create()
        ext_id = ExternalIdentifierFactory.create(
            belong_to_bag=bag,
            value='metadc000001'
        )

        request = rf.get('/')
        response = views.externalIdentifierSearch(request, ext_id.value)

        bagxml = objectify.fromstring(response.content)
        bag_entry = bagxml.entry.content[CODA_XML]

        assert str(bag_entry.bagitVersion) == bag.bagit_version
        assert bag_entry.payloadSize == bag.size
        assert bag_entry.fileCount == bag.files
        assert bag_entry.name == bag.name
        assert len(list(bag_entry.bagInfo.iterchildren())) == 2

    def test_request_with_short_ark_parameter(self, client, rf):
        bag = FullBagFactory.create()
        ext_id = ExternalIdentifierFactory.create(
            belong_to_bag=bag,
            value='ark:/67531/metadc000001'
        )

        # URL with the identifier as a URL parameter. We will feed the URL to
        # the request factory because the view will use the path to determine
        # the id field.
        url = reverse(
            'coda_mdstore.views.externalIdentifierSearch', args=[ext_id.value])
        request = rf.get(url)
        response1 = views.externalIdentifierSearch(request, ext_id.value)

        # URL with the ark id as a query parameter.
        url = reverse('coda_mdstore.views.externalIdentifierSearch')
        request = rf.get(url, {'ark': 'metadc000001'})
        response2 = views.externalIdentifierSearch(request)

        # this won't work because atom updated elements contain
        # xsdatetime values that differ at least in the milliseconds
        # field
        # assert response1.content == response2.content
        assert response1['Content-Type'] == response2['Content-Type']

        bagxml1 = objectify.fromstring(response1.content)
        bagxml2 = objectify.fromstring(response2.content)
        bag_entry1 = bagxml1.entry.content[CODA_XML]
        bag_entry2 = bagxml2.entry.content[CODA_XML]

        assert bag_entry1.name == bag_entry2.name
        assert bag_entry1.fileCount == bag_entry2.fileCount
        assert bag_entry1.bagitVersion == bag_entry2.bagitVersion
        assert bag_entry1.payloadSize == bag_entry2.payloadSize

        bag_info_count1 = bag_entry1.bagInfo.countchildren()
        bag_info_count2 = bag_entry2.bagInfo.countchildren()
        assert bag_info_count1 == bag_info_count2

    def test_request_with_long_ark_parameter(self, rf):
        bag = FullBagFactory.create()
        ext_id = ExternalIdentifierFactory.create(
            belong_to_bag=bag,
            value='ark:/67531/metadc000001'
        )

        # Just like in the previous test, feed the real URL to the request
        # factory because the request path is used in the response content.
        url = reverse(
            'coda_mdstore.views.externalIdentifierSearch', args=[ext_id.value])
        request = rf.get(url)
        response1 = views.externalIdentifierSearch(request, ext_id.value)

        # URL with the ark id as a query parameter.
        url = reverse('coda_mdstore.views.externalIdentifierSearch')
        request = rf.get(url, {'ark': 'ark:/67531/metadc000001'})
        response2 = views.externalIdentifierSearch(request)

        assert response1['Content-Type'] == response2['Content-Type']

        bagxml1 = objectify.fromstring(response1.content)
        bagxml2 = objectify.fromstring(response2.content)
        bag_entry1 = bagxml1.entry.content[CODA_XML]
        bag_entry2 = bagxml2.entry.content[CODA_XML]

        assert bag_entry1.name == bag_entry2.name
        assert bag_entry1.fileCount == bag_entry2.fileCount
        assert bag_entry1.bagitVersion == bag_entry2.bagitVersion
        assert bag_entry1.payloadSize == bag_entry2.payloadSize

        bag_info_count1 = bag_entry1.bagInfo.countchildren()
        bag_info_count2 = bag_entry2.bagInfo.countchildren()
        assert bag_info_count1 == bag_info_count2


class TestExternalIdentiferSearchJSON:
    """
    Tests for coda_mdstore.views.externalIdentifierSearchJSON.
    """

    def test_without_ark_parameter(self, rf):
        request = rf.get('/')
        response = views.externalIdentifierSearchJSON(request)
        assert response.content == '[]'

    def test_with_invalid_ark_id(self, rf):
        request = rf.get('/', {'ark': 'ark:/67351/metadc000001'})
        response = views.externalIdentifierSearchJSON(request)

        assert response.content == '[]'
        assert response['Content-Type'] == 'application/json'

    def test_with_valid_ark_id(self, rf):
        bag = FullBagFactory.create()
        ext_id = ExternalIdentifierFactory.create(
            belong_to_bag=bag,
            value='ark:/67531/metadc000001'
        )

        request = rf.get('/', {'ark': ext_id.value})
        response = views.externalIdentifierSearchJSON(request)
        content = json.loads(response.content)

        assert len(content) == 1
        assert 'bagging_date' in content[0]
        assert content[0]['name'] == bag.name
        assert content[0]['oxum'] == '{0}.{1}'.format(bag.size, bag.files)


class TestBagURLListView:
    """
    Tests for coda_mdstore.views.bagURLList.
    """

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, monkeypatch):
        self.bag = FullBagFactory.create()

        # The mocked value that getFileHandle will return.
        file_handle = mock.Mock()
        file_handle.info().getheader.side_effect = ['text/plain', '255']

        self.getFileHandle = mock.Mock(return_value=file_handle)
        monkeypatch.setattr(
            'coda_mdstore.views.getFileHandle', self.getFileHandle)

    @pytest.mark.xfail(reason='The response content does not match other '
                              'responses.')
    def test_raises_not_found_when_object_not_found(self, rf):
        request = rf.get('/')
        response = views.bagURLList(request, 'ark:/00002/id')

        assert isinstance(response, http.HttpResponseNotFound)
        assert response.content == "There is no bag with id 'ark:/00002/id'."

    def test_raises_http404_file_handle_is_falsy(self, rf):
        self.getFileHandle.return_value = False
        bag = FullBagFactory.create()
        request = rf.get('/')

        with pytest.raises(http.Http404):
            views.bagURLList(request, bag.name)

    @pytest.mark.xfail(reason='Refactor is required.')
    def test_output_text(self):
        assert 0

    @pytest.mark.xfail(reason='Refactor is required.')
    def test_top_files_block(self):
        # TODO: rename once implemented.
        assert 0

    @pytest.mark.xfail(reason='Refactor is required.')
    def test_path_is_not_unicode_safe(self):
        assert 0

    @pytest.mark.xfail(reason='Refactor is required.')
    def test_returns_status_code_200(self):
        assert 0


class TestBagURLListScrapeView:
    """
    Tests for coda_mdstore.views.bagURLListScrape.
    """

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

    @pytest.mark.xfail(reason='pairtreeCandidateList is not available '
                              'in scope.')
    def test_raises_http404_file_handle_is_falsy(self, rf):
        FullBagFactory.create()
        self.getFileHandle.return_value = False
        request = rf.get('/')

        with pytest.raises(http.Http404):
            views.bagURLListScrape(request, 'ark:/00001/id')

    @pytest.mark.xfail(reason='pairtreeCandidateList is not available '
                              'in scope.')
    def test_response_content(self):
        assert 0


class TestBagFullTextSearchATOMView:
    """
    Tests for coda_mdstore.views.bagFullTextSearchAtom.
    """

    @pytest.mark.xfail(reason='bagFullTextSearchATOM is never called.')
    def test_smoke(self):
        assert 0


class TestBagFullTextSearchHTMLView:
    """
    Tests for coda_mdstore.views.bagFullTextSearchHTML.
    """

    def test_response_with_search_query(self, client):
        client.get(
            reverse('coda_mdstore.views.bagFullTextSearchHTML'),
            {'search': 'metadc000001'}, HTTP_HOST="example.com"
        )

    def test_with_no_search_query(self, client):
        response = client.get(
            reverse('coda_mdstore.views.bagFullTextSearchHTML'),
            HTTP_HOST="example.com"
        )
        context = response.context[-1]

        assert context['searchString'] == ''
        assert context['entries'] is None
        assert 'query' in context

    def test_renders_correct_template(self, client):
        response = client.get(
            reverse('coda_mdstore.views.bagFullTextSearchHTML'),
            HTTP_HOST="example.com"
        )
        assert response.templates[0].name == 'mdstore/bag_search_results.html'


class TestShowNodeStatusView:
    """
    Tests for coda_mdstore.views.showNodeStatus.
    """

    def test_gets_status_for_single_node(self, rf):
        node = NodeFactory.create()

        request = rf.get('/')
        response = views.showNodeStatus(request, node.node_name)

        assert response.status_code == 200

    def test_single_node_context(self, client):
        # TODO: Update the URL ordering so that we can get the URL with
        #       reverse.
        node = NodeFactory.create()
        url = '/node/{0}/'.format(node.node_name)
        response = client.get(url, HTTP_HOST="example.com")

        assert response.context[-1].get('node', False)
        assert response.context[-1].get('filled', False)
        assert response.context[-1].get('available', False)

    def test_response_with_all_nodes(self, rf):
        NodeFactory.create_batch(10)

        request = rf.get('/')
        response = views.showNodeStatus(request)

        assert response.status_code == 200

    def test_context_with_all_nodes(self, client):
        NodeFactory.create_batch(10)

        response = client.get(
            reverse('coda_mdstore.views.showNodeStatus'),
            HTTP_HOST="example.com"
        )
        context = response.context[-1]

        assert len(context.get('status_list')) == 10
        assert context.get('total_capacity') == NodeFactory.node_capacity * 10
        assert context.get('total_size') == NodeFactory.node_size * 10
        assert context.get('total_filled') == 45.0

    def test_no_nodes_available(self, rf):
        request = rf.get('/')
        response = views.showNodeStatus(request)
        assert response.status_code == 200


class TestAppNode:
    """
    Tests for coda_mdstore.views.showNodeStatus.
    """

    def test_get_request_without_identifier(self, rf):
        NodeFactory.create_batch(10)
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_node(request)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    def test_get_request_without_identifier_response_content(self, rf):
        NodeFactory.create_batch(10)
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_node(request)
        tree = objectify.fromstring(response.content)

        # Check that all of the Nodes are listed in the feed.
        assert len(tree.entry) == 10

    def test_get_request_with_identifier_response(self, rf):
        node = NodeFactory.create()
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_node(request, node.node_name)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    def test_get_request_with_identifier_content(self, rf):
        node = NodeFactory.create()
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_node(request, node.node_name)
        tree = objectify.fromstring(response.content)

        assert len(tree.content.node) == 1
        assert tree.content.node.name == node.node_name
        assert tree.content.node.capacity == node.node_capacity
        assert tree.content.node.path == node.node_path
        assert tree.content.node.url == node.node_url

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
    def test_put_request(self, updateNode, rf):
        node = NodeFactory.create()
        updateNode.return_value = node

        request = rf.put('/', HTTP_HOST='example.com')
        response = views.app_node(request, node.node_name)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    @mock.patch('coda_mdstore.views.updateNode')
    def test_put_request_returns_not_found(self, updateNode, rf):
        node = NodeFactory.create()
        updateNode.side_effect = models.Node.DoesNotExist

        request = rf.put('/', HTTP_HOST='example.com')
        response = views.app_node(request, node.node_name)

        assert response.status_code == 404

    @mock.patch('coda_mdstore.views.updateNode')
    def test_put_request_returns_bad_request(self, updateNode, rf):
        node = NodeFactory.create()
        updateNode.side_effect = exceptions.BadNodeName

        request = rf.put('/', HTTP_HOST='example.com')
        response = views.app_node(request, node.node_name)

        assert response.status_code == 400

    def test_delete_request(self, rf):
        node = NodeFactory.create()
        request = rf.delete('/', HTTP_HOST='example.com')
        response = views.app_node(request, node.node_name)
        assert response.status_code == 200

    def test_delete_request_returns_not_found(self, rf):
        request = rf.delete('/', HTTP_HOST='example.com')
        response = views.app_node(request, 'DNE-001')
        assert response.status_code == 404


class TestAppBag:
    """
    Tests for coda_mdstore.views.app_bag.
    """

    def test_get_request_returns_not_found(self, rf):
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_bag(request, 'ark:/00002/id')
        assert response.status_code == 404

    def test_get_request(self, rf):
        FullBagFactory.create_batch(10)

        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_bag(request)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    def test_get_request_response_content(self, rf):
        FullBagFactory.create_batch(10)

        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_bag(request)

        tree = objectify.fromstring(response.content)
        assert len(tree.entry) == 10

    def test_get_request_with_invalid_identifier(self, rf):
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_bag(request, 'ark:/000002/id1')
        assert response.status_code == 404

    def test_get_request_with_identifier(self, rf):
        bag = FullBagFactory.create()
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_bag(request, bag.name)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

        tree = objectify.fromstring(response.content)
        bag_xml = tree.content[CODA_XML]
        assert bag_xml.name == bag.name

    @mock.patch('coda_mdstore.views.createBag')
    def test_post_request(self, mock_createBag, rf):
        bag = FullBagFactory.create()
        mock_createBag.return_value = bag, bag.bag_info_set

        request = rf.post('/', HTTP_HOST='example.com')
        response = views.app_bag(request)

        assert response.status_code == 201
        assert response['Content-Type'] == 'application/atom+xml'
        assert response['Location'] == (
            'http://example.com/APP/bag/{0}/'.format(bag.name)
        )

    @mock.patch('coda_mdstore.views.updateBag')
    def test_put_request(self, updateBag, rf):
        bag = FullBagFactory.create()
        updateBag.return_value = bag

        request = rf.put('/', HTTP_HOST='example.com')
        response = views.app_bag(request, bag.name)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    @mock.patch('coda_mdstore.views.updateBag')
    def test_put_request_returns_not_found(self, updateBag, rf):
        bag = FullBagFactory.create()
        updateBag.side_effect = models.Bag.DoesNotExist

        request = rf.put('/', HTTP_HOST='example.com')
        response = views.app_bag(request, bag.name)

        assert response.status_code == 404

    @mock.patch('coda_mdstore.views.updateBag')
    def test_put_request_returns_bad_request(self, updateBag, rf):
        bag = FullBagFactory.create()
        updateBag.side_effect = exceptions.BadBagName

        request = rf.put('/', HTTP_HOST='example.com')
        response = views.app_bag(request, bag.name)

        assert response.status_code == 400

    def test_delete_request_is_successful(self, rf):
        bag = FullBagFactory.create()
        request = rf.delete('/', HTTP_HOST='example.com')
        response = views.app_bag(request, bag.name)

        assert response.status_code == 200
        assert models.Bag.objects.exists() is False

    def test_request_returns_bad_request(self, rf):
        """
        Test that a status code 400 is returned if the request method
        is not one of GET, POST, PUT, or DELETE.
        """
        request = rf.head('/', HTTP_HOST='example.com')
        response = views.app_bag(request)
        assert response.status_code == 405

    def test_delete_request_removes_member_ext_identifier_objects(self, rf):
        bag = FullBagFactory.create()
        request = rf.delete('/', HTTP_HOST='example.com')

        assert models.External_Identifier.objects.exists() is True

        response = views.app_bag(request, bag.name)
        assert response.status_code == 200
        assert models.External_Identifier.objects.exists() is False
