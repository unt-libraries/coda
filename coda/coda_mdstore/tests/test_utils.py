from datetime import datetime

from django.core.paginator import Page
from django.conf import settings
from lxml import etree, objectify
from codalib import bagatom
import mock
import pytest

from coda_mdstore import factories, models, presentation, views, exceptions
from coda_mdstore.tests import CODA_XML


def convert_etree(tree):
    """
    Convert etree object to an objectify object.
    """
    return objectify.fromstring(etree.tostring(tree))


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


@pytest.mark.django_db
class TestBagSearch:
    """
    Tests for coda_mdstore.presentation.bagSearch.
    """

    def test_searches_bag_info_objects(self):
        bags = factories.FullBagFactory.create_batch(10)
        bag = bags[0]

        search_term = bag.bag_info_set.first().field_body
        results = presentation.bagSearch(search_term)
        assert len(results) == 10

    def test_search_bags_only(self):
        bags = factories.BagFactory.create_batch(10)
        bag = bags[0]

        results = presentation.bagSearch(bag.name)
        assert len(results) == 10

    def test_search_returns_no_bags(self):
        bag_list = presentation.bagSearch('')
        assert len(bag_list) == 0


@pytest.mark.django_db
class TestMakeBagAtomFeed:
    """
    Tests for coda_mdstore.presentation.makeBagAtomFeed.
    """

    @mock.patch('coda_mdstore.presentation.objectsToXML')
    @mock.patch(
        'coda_mdstore.presentation.wrapAtom',
        lambda *args, **kwargs: etree.Element('atomEntry')
    )
    def test_with_bag_objects(self, *args):
        title = 'test title'
        feed_id = 'test-id'
        bag_list = factories.FullBagFactory.create_batch(5)

        result = presentation.makeBagAtomFeed(bag_list, feed_id, title)
        feed = convert_etree(result)

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
        feed = convert_etree(result)

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
        tree = presentation.objectsToXML(bag)
        bag_xml = convert_etree(tree)

        assert bag_xml.name == bag.name
        assert bag_xml.fileCount == bag.files
        assert bag_xml.payloadSize == bag.size
        assert bag_xml.lastVerified, 'lastVerified should not be empty'
        assert str(bag_xml.bagitVersion) == bag.bagit_version

    def test_bag_info_attribute_conversion(self):
        bag = factories.FullBagFactory.create()
        tree = presentation.objectsToXML(bag)
        bag_xml = convert_etree(tree)

        for i, bag_info in enumerate(bag.bag_info_set.all()):
            bag_info_xml = bag_xml.bagInfo.item[i]
            assert bag_info_xml.name.text == bag_info.field_name
            assert bag_info_xml.body.text == bag_info.field_body
            assert bag_info_xml.countchildren() == 2


class TestNodeEntry:
    """
    Tests for coda_mdstore.presentation.nodeEntry.
    """

    def test_xml_has_node_attributes(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)

        xml_obj = convert_etree(tree)

        node_last_checked = node.last_checked.strftime(
            bagatom.TIME_FORMAT_STRING
        )

        assert xml_obj.content.node.name == node.node_name
        assert xml_obj.content.node.capacity == node.node_capacity
        assert xml_obj.content.node.size == node.node_size
        assert xml_obj.content.node.path == node.node_path
        assert xml_obj.content.node.url == node.node_url
        assert xml_obj.content.node.last_checked == node_last_checked
        assert xml_obj.content.node.countchildren() == 6

    def test_xml_id(self):
        node = factories.NodeFactory.build()
        web_root = 'example.com'

        tree = presentation.nodeEntry(node, web_root)
        xml_obj = convert_etree(tree)

        assert web_root in xml_obj.id.text

    def test_xml_title(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_obj = convert_etree(tree)
        assert xml_obj.title == node.node_name

    def test_xml_has_author_name_element(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_obj = convert_etree(tree)
        assert hasattr(xml_obj.author, 'name')

    def test_xml_has_author_uri_element(self):
        node = factories.NodeFactory.build()
        tree = presentation.nodeEntry(node)
        xml_obj = convert_etree(tree)
        assert hasattr(xml_obj.author, 'uri')


@pytest.mark.django_db
class TestUpdateNode:
    """
    Tests for coda_mdstore.presentation.updateNode.
    """

    def test_node_not_found_raises_exceptions(self, rf):
        node = factories.NodeFactory.build()
        node_tree = presentation.nodeEntry(node)
        node_xml = etree.tostring(node_tree)

        url = '/node/{0}/'.format(node.node_name)
        request = rf.post(url, node_xml, 'application/xml')

        with pytest.raises(models.Node.DoesNotExist):
            presentation.updateNode(request)

    def test_raises_bad_node_name_exception(self, rf):
        node = factories.NodeFactory.build()
        node_tree = presentation.nodeEntry(node)
        node_xml = etree.tostring(node_tree)

        node.save()

        request = rf.post('/', node_xml, 'application/xml')
        with pytest.raises(exceptions.BadNodeName):
            presentation.updateNode(request)

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
            <bag:name>ark:/{ark_naan}/coda2</bag:name>
            <bag:fileCount>43</bag:fileCount>
            <bag:payloadSize>46259062</bag:payloadSize>
            <bag:bagitVersion>0.96</bag:bagitVersion>
            <bag:lastStatus>fail</bag:lastStatus>
            <bag:lastVerified>2015-01-01</bag:lastVerified>
            <bag:baggingDate>2015-01-01</bag:baggingDate>
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
        """.format(ark_naan=settings.ARK_NAAN)
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
        del bag_xml.baggingDate
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert isinstance(bag.bagging_date, datetime)
        assert error is None

    def test_baggingDate_is_set(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)

        assert isinstance(bag.bagging_date, datetime)
        assert error is None

    def test_has_bag_info_objects(self, bag_xml):
        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)
        assert len(bag_infos) == 2
        # Verify that all of the bag_infos are instances of models.Bag_Info
        assert all([isinstance(m, models.Bag_Info) for m in bag_infos])

    def test_has_no_bag_info_objects(self, bag_xml):
        # Remove all of the bagInfo items from bag_xml.
        del bag_xml.bagInfo.item[0:]

        bag, bag_infos, error = presentation.xmlToBagObject(bag_xml)
        assert len(bag_infos) == 0


@pytest.fixture
def bag_xml():
    xml = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom">
        <title>ark:/{ark_naan}/coda2</title>
        <id>ark:/{ark_naan}/coda2</id>
        <updated>2013-06-05T17:05:33Z</updated>
        <author>
            <name>server</name>
        </author>
        <content type="application/xml">
            <bag:codaXML xmlns:bag="http://digital2.library.unt.edu/coda/bagxml/">
            <bag:name>ark:/{ark_naan}/coda2</bag:name>
            <bag:fileCount>43</bag:fileCount>
            <bag:payloadSize>46259062</bag:payloadSize>
            <bag:bagitVersion>0.96</bag:bagitVersion>
            <bag:lastVerified/>
            <bag:bagInfo>
                <bag:item>
                    <bag:name>Bag-Size</bag:name>
                    <bag:body>51.26M</bag:body>
                </bag:item>
                <bag:item>
                    <bag:name>Tag-File-Character-Encoding</bag:name>
                    <bag:body>UTF-8</bag:body>
                </bag:item>
            </bag:bagInfo>
            </bag:codaXML>
        </content>
        </entry>
    """.format(ark_naan=settings.ARK_NAAN)
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
        assert str(e) == 'No content element located'

    @mock.patch('coda_mdstore.presentation.xmlToBagObject')
    def test_raises_exception_when_xmlToBagObject_reports_error(self, mock, bag_xml):
        mock.return_value = (None, None, 'Fake error')
        xml_str = etree.tostring(bag_xml)
        with pytest.raises(Exception) as e:
            presentation.createBag(xml_str)
        assert 'codaXML issue,' in str(e)

    def test_returns_bag_object(self, bag_xml):
        xml_str = etree.tostring(bag_xml)
        created_bag, created_bag_infos = presentation.createBag(xml_str)
        assert isinstance(created_bag, models.Bag)

    def test_returns_bag_info_objects(self, bag_xml):
        xml_str = etree.tostring(bag_xml)
        created_bag, created_bag_infos = presentation.createBag(xml_str)
        for bag_info in created_bag_infos:
            assert isinstance(bag_info, models.Bag_Info)

    def test_existing_bag_info_objects_are_deleted(self, bag_xml):
        """
        Test that existing Bag_Info objects are removed when a Bag is created
        with createBag.

        This test relies on the fact that the Bag_Info objects created from the
        FullBagFactory are different from the bagInfo items in the bag_xml
        fixture.
        """
        # Create a bag with the same name as the bag_xml fixture.
        name = str(bag_xml.content[CODA_XML].name)
        bag = factories.FullBagFactory.create(name=name)

        # Unpack the queryset now so the query is executed
        old_bag_info1, old_bag_info2 = bag.bag_info_set.all()

        xml_str = etree.tostring(bag_xml)
        created_bag, created_bag_infos = presentation.createBag(xml_str)

        # Verify that the each of the previous bag_info objects are not
        # in the list of created bag_info objects returned from createBag.
        assert old_bag_info1.field_name not in [b.field_name for b in created_bag_infos]
        assert old_bag_info2.field_name not in [b.field_name for b in created_bag_infos]


@pytest.mark.django_db
@pytest.mark.usefixture('bag_xml')
class TestUpdateBag:
    """
    Tests for coda_mdstore.presentation.updateBag.
    """

    def test_returns_bag(self, bag_xml, rf):
        bag = factories.FullBagFactory.create(name='ark:/%d/coda2' % settings.ARK_NAAN)
        xml_str = etree.tostring(bag_xml)

        uri = '/APP/bag/{0}/'.format(bag.name)
        request = rf.post(uri, xml_str, 'application/xml')

        updated_bag = presentation.updateBag(request)
        assert isinstance(updated_bag, models.Bag)

    def test_bag_is_updated(self, bag_xml, rf):
        bag = factories.FullBagFactory.create(name='ark:/%d/coda2' % settings.ARK_NAAN)
        xml_str = etree.tostring(bag_xml)

        uri = '/APP/bag/{0}/'.format(bag.name)
        request = rf.post(uri, xml_str, 'application/xml')

        updated_bag = presentation.updateBag(request)

        bag_tree = bag_xml.content[CODA_XML]
        assert updated_bag.name == bag_tree.name
        assert updated_bag.size == bag_tree.payloadSize
        assert updated_bag.bagit_version == str(bag_tree.bagitVersion)
        assert updated_bag.files == str(bag_tree.fileCount)

        assert updated_bag.bag_info_set.count() == 2
        assert updated_bag.external_identifier_set.count() == 0

    def test_raises_bad_bag_name_exception(self, bag_xml, rf):
        factories.FullBagFactory.create(name='ark:/%d/coda2' % settings.ARK_NAAN)
        xml_str = etree.tostring(bag_xml)

        request = rf.post('/', xml_str, 'application/xml')

        with pytest.raises(exceptions.BadBagName):
            presentation.updateBag(request)

    def test_bag_object_not_found_raises_exception(self, bag_xml, rf):
        factories.FullBagFactory.create()
        xml_str = etree.tostring(bag_xml)

        # FIXME: Duplication between the test and the test fixture
        uri = '/APP/bag/ark:/%d/coda2/' % settings.ARK_NAAN
        request = rf.post(uri, xml_str, 'application/xml')

        with pytest.raises(models.Bag.DoesNotExist):
            presentation.updateBag(request)

    def test_existing_bag_info_objects_are_update(self, bag_xml, rf):
        """
        Test that existing Bag_Info objects are removed when a Bag is updated
        with updateBag.

        This test relies on the fact that the Bag_Info objects created from the
        FullBagFactory are different from the bagInfo items in the bag_xml
        fixture.
        """
        # Create a bag with the same name as the bag_xml fixture.
        name = str(bag_xml.content[CODA_XML].name)
        bag = factories.FullBagFactory.create(name=name)

        # Unpack the queryset now so the query is executed
        old_bag_info1, old_bag_info2 = bag.bag_info_set.all()

        # Compose the request to be passed to updateBag.
        xml_str = etree.tostring(bag_xml)
        uri = '/APP/bag/{0}/'.format(bag.name)
        request = rf.post(uri, xml_str, 'application/xml')

        updated_bag = presentation.updateBag(request)

        # Verify that the each of the previous bag_info objects are not in the
        # related set of the new bag object returned from updateBag.
        update_bag_infos = updated_bag.bag_info_set.all()
        assert old_bag_info1.field_name not in [b.field_name for b in update_bag_infos]
        assert old_bag_info2.field_name not in [b.field_name for b in update_bag_infos]


@mock.patch('coda_mdstore.presentation.urllib.request.urlopen')
def test_getFileList(mock_urlopen):
    """ Test all href tags are extracted as files."""
    text = """<html>
                 <body>
                 <tr> <td>test</td> <td>data</td> </tr>
                 <tr> <td>of </td> </tr>
                 <tr> <td>
                    <a href='bag-info.txt'>url</a>
                    <a href='manifest-md5.txt'>here</a>
                    <a href='bagit.txt'>here</a>
                 </td> </tr>
                 </body>
              </html>"""
    mock_urlopen.return_value = text
    filelist = presentation.getFileList('https://coda/testurl')
    assert ['bag-info.txt', 'manifest-md5.txt', 'bagit.txt'] == filelist
