from datetime import datetime

import pytest
from oaipmh.common import Header, Metadata

from .. import factories
from ..mdstore_oai import (
    md_storeOAIInterface,
    makeDataRecord,
)


class Testmd_storeOAIInterface:

    def test_smoke(self):
        md = md_storeOAIInterface()
        print md
        print md.identify()

    @pytest.mark.xfail
    def test__old_solr_getRecord(self):
        """Not used."""
        pass

    @pytest.mark.xfail
    def test_getRecord(self):
        assert 0

    @pytest.mark.xfail
    def test_listSets(self):
        assert 0

    @pytest.mark.xfail
    def test_listMetadataFormats(self):
        assert 0

    @pytest.mark.xfail
    def test_listIdentifiers(self):
        assert 0

    @pytest.mark.xfail
    def test_listRecords(self):
        assert 0

    @pytest.mark.xfail
    def test_listStuff(self):
        assert 0


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
        header, metadata, about = makeDataRecord(bag)

        assert isinstance(header, Header)
        assert isinstance(metadata, Metadata)
        assert about is None

    def test_oai_dc_metadata_has_date(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = makeDataRecord(bag)

        metadata_map = metadata.getMap()

        date = self.find_bag_info(bag, 'Bagging-Date')
        assert 'date' in metadata_map.keys()
        assert date.field_body in metadata_map['date']

    def test_oai_dc_metadata_has_identifier(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = makeDataRecord(bag)

        metadata_map = metadata.getMap()

        external_identifier = self.find_bag_info(bag, 'External-Identifier')
        assert 'identifier' in metadata_map.keys()
        assert external_identifier.field_body in metadata_map['identifier']
        assert bag.name in metadata_map['identifier']

    def test_oai_dc_metadata_has_description(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = makeDataRecord(bag)

        metadata_map = metadata.getMap()

        external_description = self.find_bag_info(bag, 'External-Description')
        assert 'description' in metadata_map.keys()
        assert external_description.field_body in metadata_map['description']

    def test_oai_dc_metadata_has_creator(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = makeDataRecord(bag)

        metadata_map = metadata.getMap()

        contact_name = self.find_bag_info(bag, 'Contact-Name')
        assert 'creator' in metadata_map.keys()
        assert contact_name.field_body in metadata_map['creator']

    def test_coda_bag_metadata_has_creator(self):
        bag = factories.OAIBagFactory.create()
        _, metadata, _ = makeDataRecord(bag, metadataPrefix='coda_bag')

        metadata_map = metadata.getMap()
        assert 'bag' in metadata_map
        assert bag is metadata_map['bag']

    def test_header_identifier(self):
        bag = factories.OAIBagFactory.create()
        header, _, _ = makeDataRecord(bag)

        # The bag name will be something like `ark:/00001/id`, but the header
        # identifier should look slightly different. The using the same name,
        # the identifier will be `info:ark/00001/id`.
        identifier = ''.join(bag.name.split(':'))
        identifier = 'info:{0}'.format(identifier)

        assert header.identifier() == identifier

    def test_header_datestamp(self):
        bag = factories.OAIBagFactory.create()
        header, _, _ = makeDataRecord(bag)
        assert isinstance(header.datestamp(), datetime)

    def test_header_setSpec(self):
        bag = factories.OAIBagFactory.create()
        header, _, _ = makeDataRecord(bag)
        assert header.setSpec() == []


@pytest.mark.xfail
def test_arkToInfo():
    assert 0


@pytest.mark.xfail
def test_infoToArk():
    assert 0


@pytest.mark.xfail
def test_coda_bag_writer():
    assert 0
