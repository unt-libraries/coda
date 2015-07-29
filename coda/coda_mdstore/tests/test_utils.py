from django.core.paginator import Paginator
from lxml import etree, objectify
import mock
import pytest

from .. import presentation
from .. import views
from .. import factories


class TestBagFullTextSearch:

    @pytest.mark.xfail(reason='FULLTEXT index is required.')
    def test_returns_paginator_object(self):
        factories.FullBagFactory.create_batch(15)
        paginator = views.bagFullTextSearch('test search')
        assert isinstance(paginator, Paginator)


@pytest.mark.django_db
@pytest.mark.xfail(reason='FULLTEXT index is required.')
class TestBagSearch:
    """
    Tests for coda_mdstore.presentation.bagSearch.
    """

    def test_searches_bag_info_objects(self):
        factories.FullBagFactory.create_batch(10)
        bag_list = presentation.bagSearch('3.14')
        assert len(bag_list) == 10

    def test_search_bags_only(self):
        # The BagFactory will not create any assocated Bag_Info objects.
        factories.BagFactory.create_batch(10)
        bag_list = presentation.bagSearch('id')
        assert len(bag_list) == 10

    def test_search_returns_no_bags(self):
        bag_list = presentation.bagSearch('')
        assert len(bag_list) == 0

    def test_search_finds_bag_by_name():
        assert 0

    def test_search_finds_bag_by_bag_info():
        assert 0


@pytest.mark.django_db
class TestMakeBagAtomFeed:
    """
    Tests for coda_mdstore.presentation.makeBagAtomFeed.
    """

    @mock.patch('coda_mdstore.presentation.objectsToXML')
    @mock.patch('coda_mdstore.presentation.wrapAtom', lambda *args: etree.Element('atomEntry'))
    def test_with_bag_objects(self, *args):
        title = 'test title'
        _id = 'test-id'
        bag_list = factories.FullBagFactory.create_batch(5)

        result = presentation.makeBagAtomFeed(bag_list, _id, title)
        feed = objectify.fromstring(etree.tostring(result))

        assert len(feed.atomEntry) == 5
        assert feed.id == _id
        assert feed.title == title
        assert feed.updated.text is None
        assert feed.link.get('href') == _id
        assert feed.link.get('rel') == 'self'

    def test_without_bag_objects(self):
        title = 'test title'
        _id = 'test-id'
        bag_list = []

        result = presentation.makeBagAtomFeed(bag_list, _id, title)
        feed = objectify.fromstring(etree.tostring(result))

        assert feed.id == _id
        assert feed.title == title
        assert feed.updated.text is None
        assert feed.link.get('href') == _id
        assert feed.link.get('rel') == 'self'
        assert feed.countchildren() == 4


@pytest.mark.django_db
class TestObjectsToXML:
    """
    Test for coda_mdstore.presentation.objectsToXML.
    """

    def test_bag_attribute_conversion(self):
        bag = factories.FullBagFactory.create()
        xml = etree.tostring(presentation.objectsToXML(bag))
        bag_xml = objectify.fromstring(xml)

        assert bag_xml.name == bag.name
        assert bag_xml.fileCount == bag.files
        assert bag_xml.payloadSize == bag.size
        assert bag_xml.payloadSize == bag.size

    def test_bag_info_attribute_conversion(self):
        bag = factories.FullBagFactory.create()
        xml = etree.tostring(presentation.objectsToXML(bag))
        bag_xml = objectify.fromstring(xml)

        for i, bag_info in enumerate(bag.bag_info_set.all()):
            bag_info_xml = bag_xml.bagInfo.item[i]
            assert bag_info_xml.name.text == bag_info.field_name
            assert bag_info_xml.body.text == bag_info.field_body
            assert bag_info_xml.countchildren() == 2


@pytest.fixture
def person_xml():
    return etree.fromstring(
        """
        <person>
            <name>John Doe</name>
            <age>34</age>
        </person>
        """
    )


@pytest.mark.usefixture('person_xml')
class TestGetValueByName:
    """
    Tests for coda_mdstore.presentation.getValueByName.
    """

    @pytest.mark.parametrize('name, value', [
        ('name', 'John Doe'),
        ('age', '34')
    ])
    def test_returns_value(self, name, value, person_xml):
        assert presentation.getValueByName(person_xml, name) == value


@pytest.mark.usefixture('person_xml')
class TestGetNodeByName:
    """
    Tests for coda_mdstore.presentation.getNodeByName.
    """

    @pytest.mark.parametrize('name, value', [
        ('name', 'John Doe'),
        ('age', '34')
    ])
    def test_returns_node(self, name, value, person_xml):
        node = presentation.getNodeByName(person_xml, name)
        assert node.tag == name
        assert node.text == value


class TestNodeEntry:
    """
    Tests for coda_mdstore.presentation.nodeEntry.
    """

    def test_xml_has_node_attributes(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_str = etree.tostring(tree)

        xml_obj = objectify.fromstring(xml_str)
        assert xml_obj.content.node.name == node.node_name
        assert xml_obj.content.node.capacity == node.node_capacity
        assert xml_obj.content.node.size == node.node_size
        assert xml_obj.content.node.path == node.node_path
        assert xml_obj.content.node.url == node.node_url
        assert xml_obj.content.node.last_checked == str(node.last_checked)
        assert xml_obj.content.node.countchildren() == 6

    def test_xml_id(self):
        node = factories.NodeFactory.build()
        web_root = 'example.com'

        tree = presentation.nodeEntry(node, web_root)
        xml_str = etree.tostring(tree)
        xml_obj = objectify.fromstring(xml_str)

        assert web_root in xml_obj.id.text

    def test_xml_title(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_str = etree.tostring(tree)

        xml_obj = objectify.fromstring(xml_str)
        assert xml_obj.title == node.node_name

    def test_xml_has_author_name_element(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_str = etree.tostring(tree)

        xml_obj = objectify.fromstring(xml_str)
        assert hasattr(xml_obj.author, 'name')

    def test_xml_has_author_uri_element(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_str = etree.tostring(tree)

        xml_obj = objectify.fromstring(xml_str)
        assert hasattr(xml_obj.author, 'uri')


@pytest.mark.django_db
class TestUpdateNode:

    def test_node_not_found(self, rf):
        node = factories.NodeFactory.build()
        node_tree = presentation.nodeEntry(node)
        node_xml = etree.tostring(node_tree, pretty_print=True)

        request = rf.post('/', node_xml, 'application/xml')
        response = presentation.updateNode(request)
        assert response.status_code == 404

    @pytest.mark.xfail(reason='Response should not have status code 200.')
    def test_node_found_and_path_does_not_include_node_name(self, rf):
        node = factories.NodeFactory.build()
        node_tree = presentation.nodeEntry(node)
        node_xml = etree.tostring(node_tree, pretty_print=True)

        node.save()

        request = rf.post('/', node_xml, 'application/xml')
        response = presentation.updateNode(request)

        assert response.status_code != 200
        assert 'URL does not match the XML' in response.content

    def test_node_updated(self, rf):
        node = factories.NodeFactory.build()
        node.save()

        node.node_size = '0'
        node_tree = presentation.nodeEntry(node)
        node_xml = etree.tostring(node_tree, pretty_print=True)

        url = '/node/{0}/detail'.format(node.node_name)
        request = rf.post(url, node_xml, 'application/xml')
        updated_node = presentation.updateNode(request)
        assert updated_node.node_size == 0
