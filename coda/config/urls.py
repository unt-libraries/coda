from django.conf.urls import url, include
from django.contrib import admin


admin.autodiscover()

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^oai/$', 'coda_oaipmh.views.index'),
    url(r'', include('premis_event_service.urls')),
    url(r'', include('coda_replication.urls')),
    url(r'', include('coda_mdstore.urls')),
    url(r'', include('coda_validate.urls')),
]
