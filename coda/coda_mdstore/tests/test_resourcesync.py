import pytest

from django.contrib.sitemaps import Sitemap

from .. import factories
from .. import resourcesync

pytestmark = [
    pytest.mark.urls('coda_mdstore.urls'),
    pytest.mark.django_db()
]


class FakeSitemap(Sitemap):
    lastmod = None
    protocol = 'http'

    def items(self):
        return factories.FullBagFactory.build_batch(5001)

    def location(self, obj):
        return "/bag/%s" % obj.name


def test_index(rf):
    sitemaps = {'001': FakeSitemap}
    request = rf.get('/')
    response = resourcesync.index(request, sitemaps, 'mdstore/resourceindex.xml')

    content = response.render()

    locations = [
        'resourcelist-001.xml',
        'resourcelist-002.xml'
    ]

    for loc in locations:
        assert loc in str(content)


def test_sitemap(rf):
    bags = factories.FullBagFactory.create_batch(10)
    request = rf.get('/')
    response = resourcesync.sitemap(request, resourcesync.sitemaps, 1, 'mdstore/sitemap.xml')
    response.render()

    for bag in bags:
        assert 'http://example.com/bag/{0}'.format(bag.name) in response.content
        assert 'http://example.com/bag/{0}.urls'.format(bag.name) in response.content


def test_sitemap_context(rf):
    factories.FullBagFactory.create_batch(10)
    request = rf.get('/')
    response = resourcesync.sitemap(request, resourcesync.sitemaps, 1, 'mdstore/sitemap.xml')

    urlset = response.context_data['urlset']

    assert all(True for item in urlset if 'priority' in item.keys())
    assert all(True for item in urlset if 'lastmod' in item.keys())
    assert all(True for item in urlset if 'changefreq' in item.keys())
    assert all(True for item in urlset if 'location' in item.keys())
    assert all(True for item in urlset if 'oxum' in item.keys())

    assert 'MOST_RECENT_BAGGING_DATE' in response.context_data


def test_changelist(rf):
    request = rf.get('/')
    template_name = 'mdstore/changelist.xml'
    content_type = 'application/xml'

    response = resourcesync.changelist(request, resourcesync.sitemaps, None,
                                       'mdstore/changelist.xml')

    assert response.template_name == template_name
    assert response.get('Content-Type', False) == content_type


def test_changelist_context(rf):
    factories.FullBagFactory.create_batch(10)
    request = rf.get('/')
    response = resourcesync.changelist(request, resourcesync.sitemaps, None,
                                       'mdstore/changelist.xml')
    response.render()

    urlset = response.context_data['urlset']

    assert all(True for item in urlset if 'name' in item.keys())
    assert all(True for item in urlset if 'size' in item.keys())
    assert all(True for item in urlset if 'files' in item.keys())
    assert all(True for item in urlset if 'bagging_date' in item.keys())

    assert 'MOST_RECENT_BAGGING_DATE' in response.context_data


def test_capabilitylist(rf):
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
