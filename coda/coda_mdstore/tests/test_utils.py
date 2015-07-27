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
