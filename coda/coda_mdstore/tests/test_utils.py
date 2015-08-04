from datetime import datetime

from django.core.paginator import Paginator, Page
from django.http import HttpResponse
from lxml import etree, objectify
import mock
import pytest

from .. import factories
from .. import models
from .. import presentation
from .. import views


class TestPaginateEntries:
    """
    Tests for coda_mdstore.views.paginate_entries.
    """

    def test_returns_paginator_object(self, rf):
        request = rf.get('/')
        page = views.paginate_entries(request, [])
        assert isinstance(page, Page)

    def test_page_number_defaults_to_one(self, rf):
        request = rf.get('/', {'page': 'foo'})
        page = views.paginate_entries(request, [])
        assert page.number == 1

    def test_invalid_page_defaults_to_last_page(self, rf):
        request = rf.get('/', {'page': 5})
        page = views.paginate_entries(request, [1, 2, 3], 1)
        assert page.number == 3


class TestPercent:
    """
    Tests for coda_mdstore.views.percent.
    """

    def test_returns_float(self):
        result = views.percent(1, 2)
        assert isinstance(result, float)

    def test_return_value(self):
        result = views.percent(1, 2)
        assert result == 50.0


class TestBagFullTextSearch:
    """
    Tests for coda_mdstore.views.bagFullTextSearch.
    """

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
        feed_id = 'test-id'
        bag_list = factories.FullBagFactory.create_batch(5)

        result = presentation.makeBagAtomFeed(bag_list, feed_id, title)
        feed = objectify.fromstring(etree.tostring(result))

        assert len(feed.atomEntry) == 5
        assert feed.id == feed_id
        assert feed.title == title
        assert feed.updated.text is None
        assert feed.link.get('href') == feed_id
        assert feed.link.get('rel') == 'self'

    def test_without_bag_objects(self):
        title = 'test title'
        feed_id = 'test-id'
        bag_list = []

        result = presentation.makeBagAtomFeed(bag_list, feed_id, title)
        feed = objectify.fromstring(etree.tostring(result))

        assert feed.id == feed_id
        assert feed.title == title
        assert feed.updated.text is None
        assert feed.link.get('href') == feed_id
        assert feed.link.get('rel') == 'self'
        assert feed.countchildren() == 4


@pytest.mark.django_db
class TestObjectsToXML:
    """
    Tests for coda_mdstore.presentation.objectsToXML.
    """

    def test_bag_attribute_conversion(self):
        bag = factories.FullBagFactory.create()
        xml = etree.tostring(presentation.objectsToXML(bag))
        bag_xml = objectify.fromstring(xml)

        assert bag_xml.name == bag.name
        assert bag_xml.fileCount == bag.files
        assert bag_xml.payloadSize == bag.size
        assert str(bag_xml.bagitVersion) == bag.bagit_version

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

    def convert_etree(self, tree):
        """
        Test case helper method to convert etree XML to objectify XML.
        """
        return objectify.fromstring(etree.tostring(tree))

    def test_xml_has_node_attributes(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)

        xml_obj = self.convert_etree(tree)

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
        xml_obj = self.convert_etree(tree)

        assert web_root in xml_obj.id.text

    def test_xml_title(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_obj = self.convert_etree(tree)
        assert xml_obj.title == node.node_name

    def test_xml_has_author_name_element(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_obj = self.convert_etree(tree)
        assert hasattr(xml_obj.author, 'name')

    def test_xml_has_author_uri_element(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_obj = self.convert_etree(tree)
        assert hasattr(xml_obj.author, 'uri')


@pytest.mark.django_db
class TestUpdateNode:
    """
    Tests for coda_mdstore.presentation.updateNode.
    """

    def test_node_not_found(self, rf):
        node = factories.NodeFactory.build()
        node_tree = presentation.nodeEntry(node)
        node_xml = etree.tostring(node_tree)

        request = rf.post('/', node_xml, 'application/xml')
        response = presentation.updateNode(request)
        assert response.status_code == 404

    @pytest.mark.xfail(reason='Response should not have status code 200.')
    def test_node_found_and_path_does_not_include_node_name(self, rf):
        node = factories.NodeFactory.build()
        node_tree = presentation.nodeEntry(node)
        node_xml = etree.tostring(node_tree)

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
        node_xml = etree.tostring(node_tree)

        url = '/node/{0}/detail'.format(node.node_name)
        request = rf.post(url, node_xml, 'application/xml')
        updated_node = presentation.updateNode(request)
        assert updated_node.node_size == 0


class TestCreateNode:
    """
    Tests for coda_mdstore.presentation.createNode.
    """

    def test_returns_node_object(self, rf):
        node = factories.NodeFactory.build()
        node_tree = presentation.nodeEntry(node)
        node_xml = etree.tostring(node_tree)

        request = rf.post('/', node_xml, 'application/xml')
        created_node = presentation.createNode(request)
        assert isinstance(created_node, models.Node)

    def test_created_node_attributes(self, rf):
        node = factories.NodeFactory.build()
        node_tree = presentation.nodeEntry(node)
        node_xml = etree.tostring(node_tree)

        request = rf.post('/', node_xml, 'application/xml')
        created_node = presentation.createNode(request)

        assert node.node_name == created_node.node_name
        assert node.node_capacity == created_node.node_capacity
        assert node.node_size == created_node.node_size
        assert node.node_path == created_node.node_path
        assert node.node_url == created_node.node_url

        # Verify that the attribute exists, but do not attempt to guess
        # the value.
        assert hasattr(node, 'last_checked')


class TestXmlToBagObject:

    @pytest.fixture
    def bag_xml(self):
        xml = """
            <bag:codaXML xmlns:bag="http://digital2.library.unt.edu/coda/bagxml/">
            <bag:name>ark:/67531/coda2</bag:name>
            <bag:fileCount>43</bag:fileCount>
            <bag:payloadSize>46259062</bag:payloadSize>
            <bag:bagitVersion>0.96</bag:bagitVersion>
            <bag:lastStatus>fail</bag:lastStatus>
            <bag:lastVerified>2015-01-01</bag:lastVerified>
            <bag:bagInfo>
                <bag:item>
                    <bag:name>Bagging-Date</bag:name>
                    <bag:body>2009-09-24</bag:body>
                </bag:item>
                <bag:item>
                    <bag:name>Payload-Oxum</bag:name>
                    <bag:body>46259062.43</bag:body>
                </bag:item>
            </bag:bagInfo>
            </bag:codaXML>
        """
        return objectify.fromstring(xml)

    def test_name_not_set(self, bag_xml):
        del bag_xml.name
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag is None
        assert bag_infos is None
        assert error == "Unable to set 'name' attribute"

    def test_name_is_set(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag.name == bag_xml.name
        assert error is None

    def test_fileCount_not_set(self, bag_xml):
        del bag_xml.fileCount
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag is None
        assert bag_infos is None
        assert error == "Unable to set 'files' attribute"

    def test_fileCount_is_set(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag.files == str(bag_xml.fileCount)
        assert error is None

    def test_payloadSize_not_set(self, bag_xml):
        del bag_xml.payloadSize
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag is None
        assert bag_infos is None
        assert "Unable to set 'size' attribute" in error

    def test_payloadSize_is_set(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag.size == bag_xml.payloadSize
        assert error is None

    def test_lastStatus_not_set(self, bag_xml):
        del bag_xml.lastStatus
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag.last_verified_status == 'pass'
        assert error is None

    def test_lastStatus_is_set(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag.last_verified_status == bag_xml.lastStatus
        assert error is None

    def test_lastVerified_not_set(self, bag_xml):
        del bag_xml.lastVerified
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert isinstance(bag.last_verified_date, datetime)
        assert error is None

    def test_lastVerified_is_set(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert isinstance(bag.last_verified_date, datetime)
        assert error is None

    def test_bagitVersion_not_set(self, bag_xml):
        del bag_xml.bagitVersion
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag.bagit_version == ''
        assert error is None

    def test_bagitVersion_is_set(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert bag.bagit_version == str(bag_xml.bagitVersion)
        assert error is None

    def test_baggingDate_not_set(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert isinstance(bag.bagging_date, datetime)
        assert error is None

    def test_has_bag_info_objects(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)
        assert len(bag_infos) == 2
        # Verify that all of the bag_infos are instances of models.Bag_Info
        assert all([isinstance(m, models.Bag_Info) for m in bag_infos])

    def test_has_no_bag_info_objects(self, bag_xml):
        del bag_xml.bagInfo.item
        del bag_xml.bagInfo.item
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)
        assert len(bag_infos) == 0


@pytest.fixture
def bag_xml():
    xml = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom">
        <title>ark:/67531/coda2</title>
        <id>ark:/67531/coda2</id>
        <updated>2013-06-05T17:05:33Z</updated>
        <author>
            <name>server</name>
        </author>
        <content type="application/xml">
            <bag:codaXML xmlns:bag="http://digital2.library.unt.edu/coda/bagxml/">
            <bag:name>ark:/67531/coda2</bag:name>
            <bag:fileCount>43</bag:fileCount>
            <bag:payloadSize>46259062</bag:payloadSize>
            <bag:bagitVersion>0.96</bag:bagitVersion>
            <bag:lastVerified/>
            <bag:bagInfo>
                <bag:item>
                    <bag:name>Payload-Oxum</bag:name>
                    <bag:body>46259062.43</bag:body>
                </bag:item>
                <bag:item>
                    <bag:name>Tag-File-Character-Encoding</bag:name>
                    <bag:body>UTF-8</bag:body>
                </bag:item>
            </bag:bagInfo>
            </bag:codaXML>
        </content>
        </entry>
    """
    return objectify.fromstring(xml)


@pytest.mark.django_db
@pytest.mark.usefixture('bag_xml')
class TestCreateBag:
    """
    Tests for coda_mdstore.presentation.createBag.
    """

    @pytest.mark.xfail(reason='Exception in function will never be raised.')
    def test_raises_exception_when_xml_cannot_be_parsed(self):
        with pytest.raises(Exception) as e:
            presentation.createBag('')
        assert str(e) == 'Unable to parse uploaded XML'

    @pytest.mark.xfail(reason='Exception in function will never be raised.')
    def test_raises_exception_when_content_element_not_present(self):
        with pytest.raises(Exception) as e:
            presentation.createBag('<root/>')
        assert str(e) == 'No content to parse uploaded XML'

    def test_returns_bag_object(self, bag_xml, rf):
        xml_str = etree.tostring(bag_xml)
        created_bag, created_bag_infos = presentation.createBag(xml_str)
        assert isinstance(created_bag, models.Bag)

    def test_returns_bag_info_objects(self, bag_xml, rf):
        xml_str = etree.tostring(bag_xml)
        created_bag, created_bag_infos = presentation.createBag(xml_str)
        for bag_info in created_bag_infos:
            assert isinstance(bag_info, models.Bag_Info)


@pytest.mark.django_db
@pytest.mark.usefixture('bag_xml')
class TestUpdateBag:
    """
    Tests for coda_mdstore.presentation.updateBag.
    """
    CODA_XML = '{http://digital2.library.unt.edu/coda/bagxml/}codaXML'

    def test_returns_bag(self, bag_xml, rf):
        bag = factories.FullBagFactory.create(name='ark:/67531/coda2')
        xml_str = etree.tostring(bag_xml)

        request = rf.post('/APP/bag/{0}/'.format(bag.name), xml_str, 'application/xml')
        updated_bag = presentation.updateBag(request)
        assert isinstance(updated_bag, models.Bag)

    def test_bag_is_updated(self, bag_xml, rf):
        bag = factories.FullBagFactory.create(name='ark:/67531/coda2')
        xml_str = etree.tostring(bag_xml)

        request = rf.post('/APP/bag/{0}/'.format(bag.name), xml_str, 'application/xml')
        updated_bag = presentation.updateBag(request)

        bag_tree = bag_xml.content[self.CODA_XML]
        assert updated_bag.name == bag_tree.name
        assert updated_bag.size == bag_tree.payloadSize
        assert updated_bag.bagit_version == str(bag_tree.bagitVersion)
        assert updated_bag.files == str(bag_tree.fileCount)

        assert updated_bag.bag_info_set.count() == 2
        assert updated_bag.external_identifier_set.count() == 0

    def test_request_path_does_not_match_name(self, bag_xml, rf):
        factories.FullBagFactory.create(name='ark:/67531/coda2')
        xml_str = etree.tostring(bag_xml)

        request = rf.post('/', xml_str, 'application/xml')
        resp = presentation.updateBag(request)

        assert isinstance(resp, HttpResponse)
        assert resp.status_code == 200
        assert 'name supplied in the URL does not match' in resp.content

    def test_bag_object_not_found(self, bag_xml, rf):
        factories.FullBagFactory.create()
        xml_str = etree.tostring(bag_xml)

        request = rf.post('/', xml_str, 'application/xml')
        resp = presentation.updateBag(request)

        assert isinstance(resp, HttpResponse)
        assert resp.status_code == 200
        assert resp.content == 'Cannot find bag_name'
