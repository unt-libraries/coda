import os
import pytest
from lxml import etree

from django.contrib.sitemaps import Sitemap

from coda_mdstore import factories
from coda_mdstore import resourcesync

pytestmark = pytest.mark.django_db()

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'schema')


@pytest.fixture
def siteindex_schema():
    """Provides an lxml schema object for the sitemap schema (including
    resourcesync 1.1) for validation.
    """
    with open(os.path.join(SCHEMA_DIR, "siteindex.xsd")) as schema_file:
        schema_doc = etree.parse(schema_file)
        schema = etree.XMLSchema(schema_doc)
    return schema


class FakeSitemap(Sitemap):
    """Fake Sitemap object similar to resourcesync.BaseSitemap.

    This will build but not persist model instances for testing
    purposes.
    """
    lastmod = None
    protocol = 'http'

    def items(self):
        # A miniumum of 5001 Bag objects are required to get multiple
        # resource locations from the index view.
        return factories.FullBagFactory.build_batch(5001)

    def location(self, obj):
        return "/bag/%s" % obj.name


def test_index_context(rf, siteindex_schema):
    """Test the context data in the response returned from `index`.

    `index` is essentially the function defined in
    django.contrib.sitemaps.views.index, but it alters the data included
    in the response context slightly. This tests that the data is in the
    correct form.
    """
    sitemaps = {'001': FakeSitemap}
    request = rf.get('/', HTTP_HOST="example.com")
    response = resourcesync.index(request, sitemaps, 'mdstore/resourceindex.xml')

    # Expected filenames. The full location would look something like
    # http://example.com/resourcelist-001.xml
    resource_list_1 = 'resourcelist-001.xml'
    resource_list_2 = 'resourcelist-002.xml'

    locations = response.context_data['sitemaps']

    assert resource_list_1 in locations[0]
    assert resource_list_2 in locations[1]
    if response.is_rendered:
        raw_xml = response.content
    else:
        raw_xml = response.rendered_content
    siteindex_xml = etree.fromstring(raw_xml.encode('utf-8'))
    siteindex_schema.assert_(siteindex_xml)


def test_sitemap_context(rf):
    """Tests the context data in the response returned from
    `sitemap`.

    `sitemap` is essentially the function defined in
    django.contrib.sitemaps.views.sitemap, but it alters the data included
    in the response context slightly. This verifies the structure of the
    context.
    """

    factories.FullBagFactory.create_batch(10)
    request = rf.get('/')
    response = resourcesync.sitemap(request, resourcesync.sitemaps, 1, 'mdstore/sitemap.xml')

    urlset = response.context_data['urlset']

    # Check that all the dictionaries in `urlset` have the following keys.
    reqd_keys = ('priority', 'lastmod', 'changefreq', 'location', 'oxum')
    def has_keys(d):
        for reqd_key in reqd_keys:
            if reqd_key in d:
                continue
            else:
                return False
        return True
    assert all(map(has_keys, urlset))

    assert 'MOST_RECENT_BAGGING_DATE' in response.context_data


def test_sitemap_locations(rf):
    """Test the locations in the response context returned from `sitemap`.

    See `test_sitemap_context`. This checks that all bags in the batch
    have a corresponding location in the context.
    """
    bags = factories.FullBagFactory.create_batch(10)

    request = rf.get('/')
    response = resourcesync.sitemap(request, resourcesync.sitemaps, 1, 'mdstore/sitemap.xml')

    urlset = response.context_data['urlset']

    # Verify that each bag in the batch has a location in the context.
    for bag in bags:
        assert any(True for u in urlset if bag.name in u['location'])


def test_changelist(rf):
    """Test that `changelist` uses the template and content_type
    parameters in the response.
    """
    request = rf.get('/')
    template_name = 'mdstore/changelist.xml'
    content_type = 'application/xml'

    response = resourcesync.changelist(request, resourcesync.sitemaps, None,
                                       'mdstore/changelist.xml')

    assert response.template_name == template_name
    assert response.get('Content-Type', False) == content_type


def test_changelist_context(rf):
    """Test the context data from the response object returned from
    `changelist`.
    """
    factories.FullBagFactory.create_batch(10)
    request = rf.get('/', HTTP_HOST="example.com")
    response = resourcesync.changelist(request, resourcesync.sitemaps, None,
                                       'mdstore/changelist.xml')
    response.render()

    urlset = response.context_data['urlset']

    # Check that all the dictionaries in `urlset` have the following keys.
    assert all(True for item in urlset if 'name' in item.keys())
    assert all(True for item in urlset if 'size' in item.keys())
    assert all(True for item in urlset if 'files' in item.keys())
    assert all(True for item in urlset if 'bagging_date' in item.keys())

    assert 'MOST_RECENT_BAGGING_DATE' in response.context_data


def test_capabilitylist(rf):
    """Test that `capabilitylist` uses the template and content_type
    parameters in the response.
    """
    request = rf.get('/')
    template_name = 'mdstore/capabilitylist.xml'
    content_type = 'application/xml'

    response = resourcesync.capabilitylist(request, template_name, content_type)

    assert response.template_name == template_name
    assert response.get('Content-Type', False) == content_type

    assert 'MOST_RECENT_BAGGING_DATE' in response.context_data


class TestBaseSitemap:

    def test_items(self):
        factories.FullBagFactory.create_batch(10)
        sitemap = resourcesync.BaseSitemap()
        items = sitemap.items()

        assert items.count() == 10
        assert all(True for i in items if 'name' in i.keys())

    def test_location(self):
        obj = {'name': 'ark:/00001/coda1k'}
        sitemap = resourcesync.BaseSitemap()

        location = sitemap.location(obj)
        assert location == '/bag/ark:/00001/coda1k'
