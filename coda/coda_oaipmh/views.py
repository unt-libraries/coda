from oaipmh import server, metadata
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.conf import settings
from coda_mdstore.models import Bag, Bag_Info
from coda_mdstore import mdstore_oai
from django.contrib.sites.models import Site


metadata_registry = metadata.MetadataRegistry()
metadata_registry.registerWriter('oai_dc', server.oai_dc_writer)
metadata_registry.registerWriter('coda_bag', mdstore_oai.coda_bag_writer)

def index(request):

    site = Site.objects.get(id = settings.SITE_ID)
    identifyDict = {}
    identifyDict['repositoryName'] = site.name
    identifyDict['adminEmails'] = ["mark.phillips@unt.edu"]
    baseURL = site.domain
    siteBaseURL = baseURL
    
    if baseURL[-1] != '/':
        baseURL = baseURL + '/'
    
    if False:
        try:
            collectionOb = Collection.objects.get(
                sites = brand.sites,
                hidden = False,
                collection_abbreviation = collection,
            )
        except:
            raise Http404, "There is no Collection by that name."
        identifyDict['repositoryName'] = \
            "%s, hosted by the University of North Texas Libraries" % \
            collectionOb.collection_name
        limit.append("untl_collection:%s" % collection)
        baseURL = baseURL + "explore/collections/%s/" % collection
    
    if False:     
        try:
            partnerOb = Partner.objects.get(
                sites = brand.sites,
                hidden = False,
                partner_abbreviation = partner,
            )
        except:
            raise Http404, "There is no Partner by that name."
        identifyDict['repositoryName'] = partnerOb.partner_name
        limit.append("untl_institution:%s" % partner)
        baseURL = baseURL + "explore/partners/%s/" % partner
        
    identifyDict['baseURL'] = "http://" + baseURL + "oai/"
    serverBase = mdstore_oai.md_storeOAIInterface(
        identifyDict=identifyDict,
        domain=siteBaseURL
    )
    oaiServer = server.BatchingServer(
        serverBase, metadata_registry, 
        resumption_batch_size=500
    )

    response = oaiServer.handleRequest(request.REQUEST)
    return HttpResponse(response, mimetype="text/xml")
