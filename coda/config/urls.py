from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from coda_oaipmh import views as oai_views

admin.autodiscover()

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^oai/$', oai_views.index),
    url(r'', include('premis_event_service.urls')),
    url(r'', include('coda_replication.urls')),
    url(r'', include('coda_mdstore.urls')),
    url(r'', include('coda_validate.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        # For Django versions before 2.0:
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
