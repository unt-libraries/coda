from django.urls import re_path
from . import views


urlpatterns = [
    re_path(r'^APP/validate/(?P<identifier>.+?)/$', views.app_validate, name='app-detail'),
    re_path(r'^APP/validate/$', views.app_validate, name='app-list'),
    re_path(r'^validate/$', views.index, name='validate-index'),
    re_path(r'^validate/list/$', views.ValidateListView.as_view(), name='validate-list'),
    re_path(r'^validate/check.json', views.check_json, name='check-json'),
    re_path(r'^validate/stats/$', views.stats, name='validate-stats'),
    re_path(r'^validate/prioritize/$', views.prioritize, name='prioritize'),
    re_path(r'^validate/prioritize.json', views.prioritize_json, name='prioritize-json'),
    re_path(r'^validate/next/$', views.AtomNextFeedNoServer(), name='feed-next'),
    re_path(r'^validate/next/(?P<server>.+)/$', views.AtomNextNewsFeed(), name='feed-next-server'),
    re_path(r'^validate/(?P<identifier>.+?)/$', views.validate, name='detail'),
]
