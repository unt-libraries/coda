from django.conf.urls import url
from . import views
from django.contrib.sitemaps import views as sitemap_views
from .resourcesync import changelist, capabilitylist

urlpatterns = [
    url(r'^bag/$', views.all_bags, name='bag-list'),
    url(r'^APP/bag/$', views.app_bag, name='app-bag-list'),
    url(r'^APP/bag/(?P<identifier>.+?)/$', views.app_bag, name='app-bag-detail'),
    url(r'^bag/(?P<identifier>.+?)/$', views.bagHTML, name='bag-detail'),
    url(r'^bag/(?P<identifier>ark:\/\d+\/.+?).urls$', views.bagURLList, name='bag-urls'),
    url(
        r'^bag/(?P<identifier>ark:\/\d+\/.+?)/(?P<filePath>.+)$',
        views.bagProxy, name='bag-proxy'
    ),
    url(r'^stats/$', views.stats, name='stats'),
    url(r'^stats.json$', views.json_stats, name='stats-json'),
    url(r'^APP/node/$', views.app_node, name='app-node-list'),
    url(r'^APP/node/(?P<identifier>coda-.*\d+)/$', views.app_node, name='app-node-list'),
    url(r'^node/$', views.showNodeStatus, name='node-list'),
    url(r'^node/(?P<identifier>coda-.*\d+)/$', views.showNodeStatus, name='node-detail'),
    url(
        r'^extidentifier/(?P<identifier>.+?)/$',
        views.externalIdentifierSearch, name='identifier-detail'
    ),
    url(r'^extidentifier/$', views.externalIdentifierSearch, name='identifier-search'),
    url(
        r'^extidentifier.json$',
        views.externalIdentifierSearchJSON, name='identifier-search-json'
    ),
    url(r'^search/$', views.bagFullTextSearchHTML, name='search'),
    url(r'^about/$', views.about, name='about'),
    url(r'^robots.txt$', views.shooRobot, name='robots'),
    url(r'^feed/$', views.AtomSiteNewsFeed(), name='feed'),
    url(r'^resourceindex\.xml$', sitemap_views.index),
    url(r'^resourcelist-(?P<section>.+)\.xml$', sitemap_views.sitemap, name='sitemaps_views'),
    url(r'changelist\.xml$', changelist),
    url(r'^capabilitylist\.xml$', capabilitylist),
    url(r'^$', views.index, name='index'),
]
