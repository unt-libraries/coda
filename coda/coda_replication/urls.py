from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^APP/queue/(?P<identifier>ark:\/\d+\/.+?)/$', views.queue, name='app-detail'),
    url(r'^APP/queue/$', views.queue, name='app-list'),
    url(r'^queue/$', views.queue_recent, name='replication_index'),
    url(r'^queue/(?P<identifier>ark:\/\d+\/.+?)/$', views.queue_html, name='replication_detail'),
    url(r'^queue/search/$', views.queue_search, name='replication_search'),
    url(r'^queue/search.json$', views.queue_search_JSON, name='search-json'),
    url(r'^queue/stats/$', views.queue_stats, name='replication_stats'),
]
