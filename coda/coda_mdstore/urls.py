from django.urls import re_path
from . import views
from django.contrib.sitemaps import views as sitemap_views
from .resourcesync import changelist, capabilitylist, sitemaps

urlpatterns = [
    re_path(r'^bag/$', views.all_bags, name='bag-list'),
    re_path(r'^APP/bag/$', views.app_bag, name='app-bag-list'),
    re_path(r'^APP/bag/(?P<identifier>.+?)/$', views.app_bag, name='app-bag-detail'),
    re_path(r'^bag/(?P<identifier>.+?)/$', views.bagHTML, name='bag-detail'),
    re_path(r'^bag/(?P<identifier>ark:\/\d+\/.+?).urls$', views.bagURLList, name='bag-urls'),
    re_path(
        r'^bag/(?P<identifier>ark:\/\d+\/.+?)/bagfiles$',
        views.download_files, name='bag-files'
    ),
    re_path(
        r'^bag/(?P<identifier>ark:\/\d+\/.+?)/(?P<filePath>.+)$',
        views.bagProxy, name='bag-proxy'
    ),
    re_path(r'^stats/$', views.stats, name='stats'),
    re_path(r'^stats.json$', views.json_stats, name='stats-json'),
    re_path(r'^APP/node/$', views.app_node, name='app-node-list'),
    re_path(r'^APP/node/(?P<identifier>coda-.*\d+)/$', views.app_node, name='app-node-list'),
    re_path(r'^node/$', views.showNodeStatus, name='node-list'),
    re_path(r'^node/(?P<identifier>coda-.*\d+)/$', views.showNodeStatus, name='node-detail'),
    re_path(
        r'^extidentifier/(?P<identifier>.+?)/$',
        views.externalIdentifierSearch, name='identifier-detail'
    ),
    re_path(r'^extidentifier/$', views.externalIdentifierSearch, name='identifier-search'),
    re_path(
        r'^extidentifier.json$',
        views.externalIdentifierSearchJSON, name='identifier-search-json'
    ),
    re_path(r'^search/$', views.bagFullTextSearchHTML, name='search'),
    re_path(r'^about/$', views.about, name='about'),
    re_path(r'^robots.txt$', views.shooRobot, name='robots'),
    re_path(r'^feed/$', views.AtomSiteNewsFeed(), name='feed'),
    re_path(
        r'^resourceindex\.xml$',
        sitemap_views.index,
        {
            'sitemaps': sitemaps,
            'template_name': 'mdstore/resourceindex.xml'
        },
    ),
    re_path(
        r'^resourcelist-(?P<section>.+)\.xml$',
        sitemap_views.sitemap,
        {
            'sitemaps': sitemaps,
            'template_name': 'mdstore/sitemap.xml'
        },
        name='resourcelist',
    ),
    re_path(
        r'changelist\.xml$',
        changelist,
        {
            'sitemaps': sitemaps,
            'section': 'changelist',
            'template_name': 'mdstore/changelist.xml'
        },
    ),
    re_path(r'^capabilitylist\.xml$', capabilitylist),
    re_path(r'^$', views.index, name='index'),
]
