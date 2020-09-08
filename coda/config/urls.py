from django.conf import settings
from django.urls import re_path, include
from django.contrib import admin
from coda_oaipmh import views as oai_views

admin.autodiscover()

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^oai/$', oai_views.index),
    re_path(r'', include('premis_event_service.urls')),
    re_path(r'', include('coda_replication.urls')),
    re_path(r'', include('coda_mdstore.urls')),
    re_path(r'', include('coda_validate.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        # For Django versions before 2.0:
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
