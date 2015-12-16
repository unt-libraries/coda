from django.conf.urls import url, patterns
from . import views
from .resourcesync import sitemaps

urlpatterns = [
    url(r'^bag/$', views.all_bags, name='bag-list'),
    url(r'^APP/bag/$', views.app_bag, name='app-bag-list'),
    url(r'^APP/bag/(?P<identifier>.+?)/$', views.app_bag, name='app-bag-detail'),
    url(r'^bag/(?P<identifier>.+?)/$', views.bagHTML, name='bag-detail'),
    url(r'^bag/(?P<identifier>ark:\/\d+\/.+?).urls$', views.bagURLList, name='bag-urls'),
    url(r'^bag/(?P<identifier>ark:\/\d+\/.+?)/(?P<filePath>.+)$', views.bagProxy, name='bag-proxy'),
    url(r'^stats/$', views.stats, name='stats'),
    url(r'^stats.json$', views.json_stats, name='stats-json'),
    url(r'^APP/node/$', views.app_node, name='app-node-list'),
    url(r'^APP/node/(?P<identifier>coda-.*\d+)/$', views.app_node, name='app-node-list'),
    url(r'^node/$', views.showNodeStatus, name='node-list'),
    url(r'^node/(?P<identifier>coda-.*\d+)/$', views.showNodeStatus, name='node-detail'),
    url(r'^extidentifier/(?P<identifier>.+?)/$', views.externalIdentifierSearch, name='identifier-detail'),
    url(r'^extidentifier/$', views.externalIdentifierSearch, name='identifier-search'),
    url(r'^extidentifier.json$', views.externalIdentifierSearchJSON, name='identifier-search-json'),
    url(r'^search/$', views.bagFullTextSearchHTML, name='search'),
    url(r'^about/$', views.about, name='about'),
    url(r'^robots.txt$', views.shooRobot, name='robots'),
    url(r'^feed/$', views.AtomSiteNewsFeed(), name='feed'),
    url(r'^$', views.index, name='index'),
]


urlpatterns += patterns(
    'django.contrib.sitemaps.views',
    (
        r'^resourceindex\.xml$',
        'index',
        {
            'sitemaps': sitemaps,
            'template_name': 'mdstore/resourceindex.xml'
        },
    ),
    (
        r'^resourcelist-(?P<section>.+)\.xml$',
        'sitemap',
        {
            'sitemaps': sitemaps,
            'template_name': 'mdstore/sitemap.xml'
        },
    ),
)
urlpatterns += patterns(
    'coda_mdstore.resourcesync',
    (
        r'^changelist\.xml$',
        'changelist',
        {
            'sitemaps': sitemaps,
            'section': 'changelist',
            'template_name': 'mdstore/changelist.xml'
        },
    ),
    (
        r'^capabilitylist\.xml$',
        'capabilitylist',
    ),
)
