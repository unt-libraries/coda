from oaipmh import server, metadata
from django.http import HttpResponse
from django.conf import settings
from coda_mdstore import mdstore_oai
from django.contrib.sites.models import Site


metadata_registry = metadata.MetadataRegistry()
metadata_registry.registerWriter('oai_dc', server.oai_dc_writer)
metadata_registry.registerWriter('coda_bag', mdstore_oai.coda_bag_writer)


def index(request):
    site = Site.objects.get(id=settings.SITE_ID)
    identifyDict = {}
    identifyDict['repositoryName'] = site.name
    identifyDict['adminEmails'] = ["mark.phillips@unt.edu"]
    baseURL = site.domain
    siteBaseURL = baseURL
    if baseURL[-1] != '/':
        baseURL = baseURL + '/'
    identifyDict['baseURL'] = "http://" + baseURL + "oai/"
    serverBase = mdstore_oai.OAIInterface(
        identifyDict=identifyDict,
        domain=siteBaseURL
    )
    oaiServer = server.BatchingServer(
        serverBase, metadata_registry,
        resumption_batch_size=500
    )

    response = oaiServer.handleRequest(request.GET)
    return HttpResponse(response, content_type="text/xml")
