from django.conf.urls.defaults import url, patterns, include
from .models import Validate
from .views import AtomNextNewsFeed, AtomNextFeedNoServer


urlpatterns = patterns(
    '',
    (r'^APP/validate/(?P<identifier>.+?)/$', 'coda_validate.views.app_validate'),
    (r'^APP/validate/$', 'coda_validate.views.app_validate'),
    (r'^validate/$', 'coda_validate.views.index'),
    (r'^validate/stats/$', 'coda_validate.views.stats'),
    (r'^validate/prioritize/$', 'coda_validate.views.prioritize'),
    url(r'^validate/prioritize.json', 'coda_validate.views.prioritize_json', name='prioritize_json'),
    (r'^validate/next/$', AtomNextFeedNoServer()),
    (r'^validate/next/(?P<server>.+)/$', AtomNextNewsFeed()),
    (r'^validate/(?P<identifier>.+?)/$', 'coda_validate.views.validate'),
)
