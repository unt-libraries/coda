from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^APP/queue/(?P<identifier>ark:\/\d+\/.+?)/$', views.queue, name='app-detail'),
    re_path(r'^APP/queue/$', views.queue, name='app-list'),
    re_path(r'^queue/$', views.queue_recent, name='replication-index'),
    re_path(r'^queue/(?P<identifier>ark:\/\d+\/.+?)/$', views.queue_html, name='replication-detail'),
    re_path(r'^queue/search/$', views.queue_search, name='replication-search'),
    re_path(r'^queue/search.json$', views.queue_search_JSON, name='search-json'),
    re_path(r'^queue/stats/$', views.queue_stats, name='replication-stats'),
]
