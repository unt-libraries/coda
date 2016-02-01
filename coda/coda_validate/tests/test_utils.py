import pytest
from lxml import etree, objectify

from .. import views, factories
from ..models import Validate


VALIDATE_XML = '{http://digital2.library.unt.edu/coda/validatexml/}validate'


@pytest.mark.parametrize('month, expected', [
    (1, 31),
    (2, 28),
    (3, 31),
    (4, 30),
    (5, 31),
    (6, 30),
    (7, 31),
    (8, 31),
    (9, 30),
    (10, 31),
    (11, 30),
    (12, 31)
])
def test_last_day_of_month(month, expected):
    assert views.last_day_of_month(2015, month) == expected


@pytest.fixture
def validate_feed():
    return """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom">
        <title>ark:/00001/codajom1</title>
        <id>http://example.com/APP/validate/ark:/00001/codajom1/</id>
        <updated>2015-08-17T17:13:07Z</updated>
        <author>
            <name>Coda</name>
            <uri>http://digital2.library.unt.edu/name/nm0004311/</uri>
        </author>
        <content type="application/xml">
            <v:validate xmlns:v="http://digital2.library.unt.edu/coda/validatexml/">
                <v:identifier>ark:/00001/codajom1</v:identifier>
                <v:last_verified>2015-01-01T12:11:43</v:last_verified>
                <v:last_verified_status>Passed</v:last_verified_status>
                <v:priority_change_date>2000-01-01T00:00:00</v:priority_change_date>
                <v:priority>1</v:priority>
                <v:server>arch01.example.com</v:server>
            </v:validate>
        </content>
        </entry>
    """


def test_xmlToValidateObject(validate_feed):
    validate = views.xmlToValidateObject(validate_feed)
    xml_obj = objectify.fromstring(validate_feed)
    validate_xml = xml_obj.content[VALIDATE_XML]

    assert validate_xml.identifier == validate.identifier
    assert validate_xml.last_verified == validate.last_verified.isoformat()
    assert validate_xml.last_verified_status == str(validate.last_verified_status)
    assert validate_xml.priority_change_date == validate.priority_change_date.isoformat()
    assert validate_xml.priority.text == validate.priority
    assert validate_xml.server == validate.server


@pytest.mark.xfail(reason='Exception will never be raised directly from the function.')
def test_xmlToValidateObject_raises_exception():
    assert 0


@pytest.mark.django_db
def test_xmlToUpdateValidateObject_converts_xml(validate_feed):
    xml = objectify.fromstring(validate_feed)
    validate_xml = xml.content[VALIDATE_XML]

    validate = factories.ValidateFactory.create(
        identifier=validate_xml.identifier
    )

    updated_validate = views.xmlToUpdateValidateObject(validate_feed)

    assert isinstance(updated_validate, Validate)
    assert updated_validate.identifier == validate.identifier
    assert validate_xml.identifier == updated_validate.identifier


@pytest.mark.django_db
def test_xmlToUpdateValidateObject_saves_to_db(validate_feed):
    xml = objectify.fromstring(validate_feed)
    validate_xml = xml.content[VALIDATE_XML]

    factories.ValidateFactory.create(
        identifier=validate_xml.identifier
    )

    updated_validate = views.xmlToUpdateValidateObject(validate_feed)
    queried_validate = Validate.objects.get(identifier=updated_validate.identifier)

    assert updated_validate.identifier == queried_validate.identifier
    assert updated_validate.last_verified_status == queried_validate.last_verified_status
    assert updated_validate.priority == queried_validate.priority
    assert updated_validate.server == queried_validate.server


@pytest.mark.django_db
def test_xmlToUpdateValidateObject_does_not_update_server(validate_feed):
    xml = objectify.fromstring(validate_feed)
    validate_xml = xml.content[VALIDATE_XML]

    factories.ValidateFactory.create(
        identifier=validate_xml.identifier,
        server='dne.example.com'
    )

    updated_validate = views.xmlToUpdateValidateObject(validate_feed)
    assert validate_xml.server != updated_validate.server


@pytest.mark.django_db
def test_xmlToUpdateValidateObject_sets_priority_to_zero(validate_feed):
    xml = objectify.fromstring(validate_feed)
    validate_xml = xml.content[VALIDATE_XML]

    factories.ValidateFactory.create(
        identifier=validate_xml.identifier,
        priority=validate_xml.priority
    )

    updated_validate = views.xmlToUpdateValidateObject(validate_feed)

    assert validate_xml.priority > 0
    assert updated_validate.priority == 0


@pytest.mark.xfail(reason='Exception will never be raised directly from the function.')
def test_xmlToUpdateValidateObject_raises_exception():
    assert 0


def test_validateToXML():
    validate = factories.ValidateFactory.build()
    xml = views.validateToXML(validate)

    # Convert the _Element object to an ObjectifiedElement object.
    xml_str = etree.tostring(xml)
    validate_xml = objectify.fromstring(xml_str)

    assert validate_xml.identifier == validate.identifier
    assert validate_xml.last_verified == validate.last_verified.isoformat()
    assert validate_xml.last_verified_status == str(validate.last_verified_status)
    assert validate_xml.priority_change_date == validate.priority_change_date.isoformat()
    assert validate_xml.priority == validate.priority
    assert validate_xml.server == validate.server
