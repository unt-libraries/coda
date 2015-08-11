import pytest
from lxml import etree, objectify

from django.core.paginator import Page

from .. import presentation
from .. import factories
from .. import views
from ..models import QueueEntry

QUEUE_ENTRY = '{http://digital2.library.unt.edu/coda/queuexml/}queueEntry'


def test_paginate_entries_returns_paginator_object(rf):
    request = rf.get('/')
    page = views.paginate_entries(request, [])
    assert isinstance(page, Page)


def test_paginate_entries_page_number_defaults_to_one(rf):
    request = rf.get('/', {'page': 'foo'})
    page = views.paginate_entries(request, [])
    assert page.number == 1


def test_paginate_entries_invalid_page_defaults_to_last_page(rf):
    request = rf.get('/', {'page': 5})
    page = views.paginate_entries(request, [1, 2, 3], 1)
    assert page.number == 3


@pytest.fixture
def queue_entry_xml():
    return """<queueEntry>
            <ark>ark:/67531/coda4fnk</ark>
            <oxum>3640551.188</oxum>
            <urlListLink>http://example.com/ark:/67531/coda4fnk.urls</urlListLink>
            <status>1</status>
            <start>2013-05-17T01:35:04Z</start>
            <end>2013-05-17T01:35:13Z</end>
            <position>2</position>
        </queueEntry>
    """


def test_xmlToQueueEntry_returns_QueueEntry(queue_entry_xml):
    tree = etree.fromstring(queue_entry_xml)
    entry_obj = presentation.xmlToQueueEntry(tree)
    assert isinstance(entry_obj, QueueEntry)


def test_xmlToQueueEntry_sets_ark_attribute(queue_entry_xml):
    tree = etree.fromstring(queue_entry_xml)
    entry_obj = presentation.xmlToQueueEntry(tree)

    xml_obj = objectify.fromstring(queue_entry_xml)
    assert xml_obj.ark == entry_obj.ark


def test_xmlToQueueEntry_sets_oxum_attributes(queue_entry_xml):
    tree = etree.fromstring(queue_entry_xml)
    entry_obj = presentation.xmlToQueueEntry(tree)

    xml_obj = objectify.fromstring(queue_entry_xml)
    oxum = '{0}.{1}'.format(entry_obj.bytes, entry_obj.files)
    assert oxum == str(xml_obj.oxum)


def test_xmlToQueueEntry_sets_url_list_attribute(queue_entry_xml):
    tree = etree.fromstring(queue_entry_xml)
    entry_obj = presentation.xmlToQueueEntry(tree)

    xml_obj = objectify.fromstring(queue_entry_xml)
    assert xml_obj.urlListLink == entry_obj.url_list


def test_xmlToQueueEntry_sets_status_attribute(queue_entry_xml):
    tree = etree.fromstring(queue_entry_xml)
    entry_obj = presentation.xmlToQueueEntry(tree)

    xml_obj = objectify.fromstring(queue_entry_xml)
    assert str(xml_obj.status) == entry_obj.status


@pytest.mark.xfail(reason='xmlToQueueEntry incorrectly set the position attribute '
                          'instead of the queue_position attribute.')
def test_xmlToQueueEntry_sets_queue_position_attribute(queue_entry_xml):
    tree = etree.fromstring(queue_entry_xml)
    entry_obj = presentation.xmlToQueueEntry(tree)

    xml_obj = objectify.fromstring(queue_entry_xml)
    assert str(xml_obj.position) == entry_obj.queue_position


@pytest.fixture
def queue_xml():
    return """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom">
        <title>ark:/67531/coda4fnk</title>
        <id>http://example.com/ark:/67531/coda4fnk/</id>
        <updated>2014-04-23T15:39:20Z</updated>
        <content type="application/xml">
            <queueEntry xmlns="http://digital2.library.unt.edu/coda/queuexml/">
            <ark>ark:/67531/coda4fnk</ark>
            <oxum>3640551.188</oxum>
            <urlListLink>http://example.com/ark:/67531/coda4fnk.urls</urlListLink>
            <status>1</status>
            <start>2013-05-17T01:35:04Z</start>
            <end>2013-05-17T01:35:13Z</end>
            <position>2</position>
            </queueEntry>
        </content>
        </entry>
    """


@pytest.mark.django_db
def test_addQueueEntry_returns_QueueEntry_object(queue_xml):
    entry = presentation.addQueueEntry(queue_xml)
    assert isinstance(entry, QueueEntry)


@pytest.mark.django_db
def test_addQueueEntry_saves_entry_to_db(queue_xml):
    assert QueueEntry.objects.count() == 0
    presentation.addQueueEntry(queue_xml)
    assert QueueEntry.objects.count() == 1


@pytest.mark.django_db
def test_addQueueEntry_calculates_queue_position(queue_xml):
    factories.QueueEntryFactory.create_batch(30)

    entries = QueueEntry.objects.order_by('-queue_position')
    last_entry_position = entries[0].queue_position

    entry = presentation.addQueueEntry(queue_xml)
    assert entry.queue_position == last_entry_position + 1


@pytest.mark.django_db
def test_updateQueueEntry_finds_correct_object(queue_xml):
    xml_obj = objectify.fromstring(queue_xml)
    queue_entry_xml = xml_obj.content[QUEUE_ENTRY]
    factories.QueueEntryFactory.create(ark=queue_entry_xml.ark)

    entry = presentation.updateQueueEntry(queue_xml)
    assert entry.ark == queue_entry_xml.ark


@pytest.mark.xfail(reason='The `queue_position` attribute is not updated because '
                          'xmlToQueueEntry does not correctly set the attribute.')
@pytest.mark.django_db
def test_updateQueueEntry_updates_queue_position_attribute(queue_xml):
    xml_obj = objectify.fromstring(queue_xml)
    queue_entry_xml = xml_obj.content[QUEUE_ENTRY]
    factories.QueueEntryFactory.create(ark=queue_entry_xml.ark)

    entry = presentation.updateQueueEntry(queue_xml)
    assert entry.queue_position == str(queue_entry_xml.position)


@pytest.mark.django_db
def test_updateQueueEntry_updates_oxum_attributes(queue_xml):
    xml_obj = objectify.fromstring(queue_xml)
    queue_entry_xml = xml_obj.content[QUEUE_ENTRY]
    factories.QueueEntryFactory.create(ark=queue_entry_xml.ark)

    entry = presentation.updateQueueEntry(queue_xml)
    assert entry.oxum == str(queue_entry_xml.oxum)


@pytest.mark.django_db
def test_updateQueueEntry_updates_url_list_attribute(queue_xml):
    xml_obj = objectify.fromstring(queue_xml)
    queue_entry_xml = xml_obj.content[QUEUE_ENTRY]
    factories.QueueEntryFactory.create(ark=queue_entry_xml.ark)

    entry = presentation.updateQueueEntry(queue_xml)
    assert entry.url_list == queue_entry_xml.urlListLink


@pytest.mark.django_db
def test_updateQueueEntry_updates_status_attribute(queue_xml):
    xml_obj = objectify.fromstring(queue_xml)
    queue_entry_xml = xml_obj.content[QUEUE_ENTRY]
    factories.QueueEntryFactory.create(ark=queue_entry_xml.ark)

    entry = presentation.updateQueueEntry(queue_xml)
    assert entry.status == str(queue_entry_xml.status)
