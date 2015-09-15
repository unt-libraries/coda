from datetime import datetime

from lxml import etree
from oaipmh import common, error
import pytest

from .. import factories
from .. import mdstore_oai as oai

OAI_DC = 'oai_dc'
CODA_BAG = 'coda_bag'


@pytest.mark.django_db
class Testmd_storeOAIInterface:

    def test_identify(self):
        md = oai.md_storeOAIInterface()
        identity = md.identify()
        assert isinstance(identity, common.Identify)

    @pytest.mark.xfail(reason='Method is never used.')
    def test__old_solr_getRecord(self):
        assert 0

    def test_getRecord(self):
        bag = factories.FullBagFactory.create()
        md = oai.md_storeOAIInterface()
        record = md.getRecord(OAI_DC, bag.name)

        header, metadata, about = record

        assert isinstance(header, common.Header)
        assert isinstance(metadata, common.Metadata)
        assert about is None

    def test_getRecord_raises_IdDoesNotExistError(self):
        """Test that getRecord raises an exception when an object cannot
        be located with the given identifier.
        """
        md = oai.md_storeOAIInterface()

        with pytest.raises(error.IdDoesNotExistError):
            md.getRecord(OAI_DC, 'ark:/00001/dne')

    def test_listSets_raises_NoSetHierarchyError(self):
        md = oai.md_storeOAIInterface()

        with pytest.raises(error.NoSetHierarchyError):
            md.listSets()

    def test_listMetadataFormats(self):
        md = oai.md_storeOAIInterface()

        formats = md.listMetadataFormats()
        assert formats[0][0] == OAI_DC
        assert formats[1][0] == CODA_BAG

    def test_listMetadataFormats_always_returns_same_data(self):
        """Test the return value is the same when a valid identifier
        is passed to the method and when no identifier is passed to the
        method.
        """
        bag = factories.FullBagFactory.create()
        md = oai.md_storeOAIInterface()

        formats_without_identifier = md.listMetadataFormats()
        formats_with_identifier = md.listMetadataFormats(bag.name)

        assert formats_with_identifier == formats_without_identifier

    def test_listMetadataFormats_raises_IdDoesNotExistError(self):
        """Test listMetadataFormats raises an IdDoesNotExistError when an
        invalid identifier is passed.
        """
        md = oai.md_storeOAIInterface()
        invalid_identifier = 'dne'

        with pytest.raises(error.IdDoesNotExistError):
            md.listMetadataFormats(invalid_identifier)

    def test_listIdentifiers(self):
        """Test listIdentifiers returns a list of Header objects."""
        factories.FullBagFactory.create_batch(30)
        md = oai.md_storeOAIInterface()

        records = md.listIdentifiers(OAI_DC)
        assert len(records) == 10
        assert all(isinstance(r, common.Header) for r in records)

    def test_listRecords(self):
        """Test listRecords returns a list of 3 element tuples."""
        factories.FullBagFactory.create_batch(30)
        md = oai.md_storeOAIInterface()

        records = md.listRecords(OAI_DC)
        assert len(records) == 10
        assert all(True for r in records if len(r) == 3)

    def test_listStuff_raises_CannotDisseminateFormatError(self):
        """Test listStuff will raise a CannotDisseminateFormatError
        when given an invalid prefix.
        """
        md = oai.md_storeOAIInterface()
        invalid_prefix = 'dne'

        with pytest.raises(error.CannotDisseminateFormatError):
            md.listStuff(invalid_prefix)

    def test_listStuff_returns_records(self):
        """Test listStuff returns complete records when the `headersOnly`
        keyword arg is False.
        """
        factories.FullBagFactory.create_batch(30)
        md = oai.md_storeOAIInterface()

        records = md.listStuff(OAI_DC, headersOnly=False)
        assert len(records) == 10
        assert all(True for r in records if len(r) == 3)

    def test_listStuff_only_returns_headers(self):
        """Test listStuff returns Header objects when the `headersOnly`
        keyword arg is True.
        """
        factories.FullBagFactory.create_batch(30)
        md = oai.md_storeOAIInterface()

        records = md.listStuff(OAI_DC, headersOnly=True)
        assert len(records) == 10
        assert all(isinstance(r, common.Header) for r in records)

    @pytest.mark.xfail(reason='When the default metadataPrefix parameter is used, an '
                              'exception is raised.')
    def test_listStuff_with_default_metadataPrefix(self):
        factories.FullBagFactory.create_batch(30)
        md = oai.md_storeOAIInterface()
        md.listStuff()


@pytest.mark.django_db
class TestMakeDataRecord:

    def find_bag_info(self, bag, name):
        """Find the first occurrence of a BagInfo object with
        the provided name.
        """
        gen = (i for i in bag.bag_info_set.all() if i.field_name == name)
        return next(gen, None)

    def test_return_values(self):
        bag = factories.FullBagFactory.create()
        header, metadata, about = oai.makeDataRecord(bag)

        assert isinstance(header, common.Header)
        assert isinstance(metadata, common.Metadata)
        assert about is None

    @pytest.mark.xfail(reason='Exception will never be raised because `dcDict` will '
                              'never be empty.')
    def test_raises_exception(self):
        bag = factories.BagFactory.create(name=None)

        with pytest.raises(Exception):
            oai.makeDataRecord(bag)

    def test_oai_dc_metadata_has_date(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = oai.makeDataRecord(bag)

        metadata_map = metadata.getMap()

        date = self.find_bag_info(bag, 'Bagging-Date')
        assert 'date' in metadata_map.keys()
        assert date.field_body in metadata_map['date']

    def test_oai_dc_metadata_has_identifier(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = oai.makeDataRecord(bag)

        metadata_map = metadata.getMap()

        external_identifier = self.find_bag_info(bag, 'External-Identifier')
        assert 'identifier' in metadata_map.keys()
        assert external_identifier.field_body in metadata_map['identifier']
        assert bag.name in metadata_map['identifier']

    def test_oai_dc_metadata_has_description(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = oai.makeDataRecord(bag)

        metadata_map = metadata.getMap()

        external_description = self.find_bag_info(bag, 'External-Description')
        assert 'description' in metadata_map.keys()
        assert external_description.field_body in metadata_map['description']

    def test_oai_dc_metadata_has_creator(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = oai.makeDataRecord(bag)

        metadata_map = metadata.getMap()

        contact_name = self.find_bag_info(bag, 'Contact-Name')
        assert 'creator' in metadata_map.keys()
        assert contact_name.field_body in metadata_map['creator']

    def test_coda_bag_metadata(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = oai.makeDataRecord(bag, metadataPrefix=CODA_BAG)

        metadata_map = metadata.getMap()
        assert 'bag' in metadata_map
        assert bag is metadata_map['bag']

    def test_header_identifier(self):
        bag = factories.OAIBagFactory.create()
        header, _, _ = oai.makeDataRecord(bag)

        # The bag name will be something like `ark:/00001/id`, but the header
        # identifier should look slightly different. The using the same name,
        # the identifier will be `info:ark/00001/id`.
        identifier = ''.join(bag.name.split(':'))
        identifier = 'info:{0}'.format(identifier)

        assert header.identifier() == identifier

    def test_header_datestamp(self):
        bag = factories.OAIBagFactory.create()
        header, _, _ = oai.makeDataRecord(bag)
        assert isinstance(header.datestamp(), datetime)

    def test_header_setSpec(self):
        bag = factories.OAIBagFactory.create()
        header, _, _ = oai.makeDataRecord(bag)
        assert header.setSpec() == []


def test_arkToInfo_returns_info_uri():
    """Test that a info uri is returned."""
    ark = 'ark:/00001/coda1a'
    actual = oai.arkToInfo(ark)
    expected = 'info:ark/00001/coda1a'
    assert actual == expected


def test_arkToInfo_returns_ark():
    """Test the return value matches the input argument if the ark does
    not contain `ark:`.
    """
    ark = '00001/coda1a'
    actual = oai.arkToInfo(ark)
    assert actual == ark


def test_infoToArk_returns_ark():
    info = 'info:ark/00001/coda1a'
    actual = oai.infoToArk(info)
    expected = 'ark:/00001/coda1a'
    assert actual == expected


def test_infoToArk_returns_info_uri():
    info = '/00001/coda1a'
    actual = oai.infoToArk(info)
    assert actual == info


@pytest.mark.django_db
def test_coda_bag_writer():
    bag = factories.FullBagFactory.create()
    md = oai.md_storeOAIInterface()

    _, metadata, _ = md.getRecord(CODA_BAG, bag.name)
    element = etree.Element("root")

    oai.coda_bag_writer(element, metadata)
    assert 'bag:codaXML' in etree.tostring(element)


@pytest.mark.django_db
@pytest.mark.xfail(reason='Only Metatdata objects that have a `bag` key in the map '
                          'can be passed to the function.')
def test_coda_bag_writer_with_invalid_metadata():
    bag = factories.FullBagFactory.create()
    md = oai.md_storeOAIInterface()

    _, metadata, _ = md.getRecord(OAI_DC, bag.name)
    element = etree.Element("root")

    oai.coda_bag_writer(element, metadata)
