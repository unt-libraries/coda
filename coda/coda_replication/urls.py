from django.conf.urls import *

urlpatterns = patterns('coda_replication.views',
#    (r'^servicedocument/$', 'serviceDocument'),
    (r'^APP/queue/(?P<identifier>ark:\/\d+\/.+?)/$', 'queue'),
    (r'^APP/queue/$', 'queue'),
    (r'^queue/$', 'queue_recent'),
    (r'^queue/(?P<identifier>ark:\/\d+\/.+?)/$', 'queue_html'),
    (r'^queue/search/$', 'queue_search'),
    (r'^queue/search.json$', 'queue_search_JSON'),
    (r'^queue/stats/$', 'queue_stats'),
#    (r"^robots.txt$", 'shooRobot'),
#    (r'^$','index'),
)
