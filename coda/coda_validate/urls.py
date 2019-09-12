from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^APP/validate/(?P<identifier>.+?)/$', views.app_validate, name='app-detail'),
    url(r'^APP/validate/$', views.app_validate, name='app-list'),
    url(r'^validate/$', views.index, name='validate-index'),
    url(r'^validate/list/$', views.ValidateListView.as_view(), name='validate-list'),
    url(r'^validate/check.json', views.check_json, name='check-json'),
    url(r'^validate/stats/$', views.stats, name='validate-stats'),
    url(r'^validate/prioritize/$', views.prioritize, name='prioritize'),
    url(r'^validate/prioritize.json', views.prioritize_json, name='prioritize-json'),
    url(r'^validate/next/$', views.AtomNextFeedNoServer(), name='feed-next'),
    url(r'^validate/next/(?P<server>.+)/$', views.AtomNextNewsFeed(), name='feed-next-server'),
    url(r'^validate/(?P<identifier>.+?)/$', views.validate, name='detail'),
]
