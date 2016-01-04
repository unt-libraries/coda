from django.conf.urls import url, include
from django.contrib import admin


admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^oai/$', 'coda_oaipmh.views.index'),
    url(r'', include('premis_event_service.urls')),
    url(r'', include('coda_replication.urls', namespace='replication')),
    url(r'', include('coda_mdstore.urls', namespace='mdstore')),
    url(r'', include('coda_validate.urls', namespace='validate')),
]
