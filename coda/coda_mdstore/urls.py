from django.conf.urls import *
from .views import AtomSiteNewsFeed
from .resourcesync import sitemaps

urlpatterns = patterns(
    'coda_mdstore.views',
    # bag urls
    (r'^bag/$', 'all_bags'),
    (r'^APP/bag/$', 'app_bag'),
    (r'^APP/bag/(?P<identifier>.+?)/$', 'app_bag'),
    (r'^bag/(?P<identifier>.+?)/$', 'bagHTML'),
    (r'^bag/(?P<identifier>ark:\/\d+\/.+?).urls$', 'bagURLList'),
    (r'^bag/(?P<identifier>ark:\/\d+\/.+?)/(?P<filePath>.+)$', 'bagProxy'),
    # stats urls
    (r'^stats/$', 'stats'),
    (r'^stats.json$', 'json_stats'),
    # node urls
    (r'^APP/node/$', 'app_node'),
    (r'^APP/node/(?P<identifier>coda-.*\d+)/$', 'app_node'),
    (r'^node/$', 'showNodeStatus'),
    (r'^node/(?P<identifier>coda-.*\d+)/$', 'showNodeStatus'),
    (r'^extidentifier/(?P<identifier>.+?)/$', 'externalIdentifierSearch'),
    (r'^extidentifier/$', 'externalIdentifierSearch'),
    (r'^extidentifier.json$', 'externalIdentifierSearchJSON'),
    (r'^search/$', 'bagFullTextSearchHTML'),
    # Here's some static pages
    (r'^about/$', 'about'),
    (r'^robots.txt$', 'shooRobot'),
    (r'^feed/$', AtomSiteNewsFeed()),
    (r'^$', 'index'),
)
urlpatterns += patterns('django.contrib.sitemaps.views',
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
urlpatterns += patterns('coda_mdstore.resourcesync',
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
