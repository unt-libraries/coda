from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
import coda_oaipmh
admin.autodiscover()


urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^oai/$', 'coda_oaipmh.views.index'),
    url(r'', include('premis_event_service.urls')),
    url(r'', include('coda_replication.urls')),
    url(r'', include('coda_mdstore.urls')),
    url(r'', include('coda_validate.urls')),
)


# For local development
if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns(
        '',
        (
            r'^media/(?P<path>.*)$',
            'django.views.static.serve',
            {
                'document_root': settings.MEDIA_ROOT,
            },
        ),
    )
