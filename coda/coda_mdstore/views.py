import codecs
import urlparse
import re
import copy
import urllib2
try:
    # the json module was included in the stdlib in python 2.6
    # http://docs.python.org/library/json.html
    import json
except ImportError:
    # simplejson 2.0.9 is available for python 2.4+
    # http://pypi.python.org/pypi/simplejson/2.0.9
    # simplejson 1.7.3 is available for python 2.3+
    # http://pypi.python.org/pypi/simplejson/1.7.3
    import simplejson as json
from django.http import HttpResponse, Http404, HttpResponseBadRequest, \
    HttpResponseNotFound
from django.shortcuts import render_to_response, get_object_or_404, \
    get_list_or_404
from django.core.servers.basehttp import FileWrapper
from django.db.models import Sum, Count, Max, Min
from django.conf import settings
from django.utils.feedgenerator import Atom1Feed
from django.contrib.syndication.views import Feed
from django.template import RequestContext
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from lxml import etree
from premis_event_service.models import Agent, Event
from coda_replication.models import QueueEntry
from coda_validate.models import Validate
from .models import Bag, Bag_Info, Node, External_Identifier
from codalib import APP_AUTHOR, bagatom
from presentation import getFileList, getFileHandle, bagSearch, \
    makeBagAtomFeed, createBag, updateBag, objectsToXML, getERC, \
    getERCSupport, updateNode, nodeEntry, createNode
from dateutil import rrule
from datetime import datetime
from django.contrib.sites.models import Site
from django.db import connection

MAINTENANCE_MSG = settings.MAINTENANCE_MSG
utf8_decoder = codecs.getdecoder("utf-8")
latin_decoder = codecs.getdecoder("latin_1")
XML_HEADER = "<?xml version=\"1.0\"?>\n%s"


def prepare_graph_date_range():
    """
    Several functions use the same code to prepare the dates and values for
    the graphing of event data, so we can make a function for it. DRY 4 LYPHE
    returns list of lists
    """

    # grab the dates for the bounds of the graphs
    dates = Bag.objects.aggregate(Min("bagging_date"), Max('bagging_date'))
    system_start_date = dates['bagging_date__min']
    system_end_date = dates['bagging_date__max']
    # setup list for month call data
    daily_edit_counts = []
    # we need to first fill in the first month, becuase it wont grab that when
    # the for loop iterates to a new month.
    month = system_start_date.strftime('%Y-%m')
    daily_edit_counts.append([datetime.strptime(month, '%Y-%m'), 0])
    # start with a zero count and reset this as we cross a month
    monthly_count = 0
    for dt in rrule.rrule(
        rrule.DAILY,
        dtstart=system_start_date,
        until=system_end_date,
    ):
        # if we change months
        if month != dt.strftime('%Y-%m'):
            month = dt.strftime('%Y-%m')
            #make the year and drop in if i doenst exist
            daily_edit_counts.append([datetime.strptime(month, '%Y-%m'), 0])
    return daily_edit_counts


def calc_total_by_month(**kwargs):
    """
    totals for the bag / file count by month.
    Returns an ordered dict
    """

    # make current total events count
    current_total = 0
    month_skeleton = kwargs.get('month_skeleton')
    daily_counts = kwargs.get('daily_counts')
    running = kwargs.get('running')
    metric = kwargs.get('metric')
    # fill in totals
    for u in month_skeleton:
        # replace existing value of zero with sum of nums in certain month
        current_month_counts = [e for e in daily_counts if \
            datetime.strftime(e['day'], '%Y-%m') == \
            datetime.strftime(u[0], '%Y-%m')]
        for n in current_month_counts:
            if metric == 'bags':
                current_total += n['bagging_date_num']
            elif metric == 'files':
                current_total += n['files_total']
            elif metric == 'size':
                current_total += n['sizes_total']
        u[1] = current_total
        if not running:
            current_total = 0
    return month_skeleton


def paginate_entries(request, entries_result, num_per_page=20):
    """
    paginates a set of entries (set of model objects)
    """

    # create paginator from result set
    paginator = Paginator(entries_result, num_per_page)
    # try to resolve the current page
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        paginated_entries = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paginated_entries = paginator.page(paginator.num_pages)
    # send back the paginated entries
    return paginated_entries


def index(request):
    """
    Just a standard base page
    """

    totals = Bag.objects.all().aggregate(
        Sum('files'),
        Sum('size'),
        Count('pk'),
        Max('bagging_date'),
    )
    queue_total = QueueEntry.objects.count()
    event_total = Event.objects.count()
    validation_total = Validate.objects.count()
    if not totals['files__sum']:
        totals['files__sum'] = 0
    # render back with a dict of details
    return render_to_response(
        'mdstore/index.html',
        {
            'site_title': Site.objects.get_current().name,
            'totals': totals,
            'queue_total': queue_total,
            'validation_total': validation_total,
            'event_total': event_total,
            'maintenance_message': MAINTENANCE_MSG,
        },
        context_instance=RequestContext(request)
    )


def about(request):
    """
    Just a standard about page
    """

    # render back with a dict of details
    return render_to_response(
        'mdstore/about.html',
        {
            'site_title': Site.objects.get_current().name,
            'maintenance_message': MAINTENANCE_MSG,
        },
        context_instance=RequestContext(request)
    )


def all_bags(request):
    """
    list all the bags
    """

    all_bags = Bag.objects.all()
    # paginate 15 per page and apply ordering
    paginated_entries = paginate_entries(
        request,
        all_bags.order_by('-bagging_date')
    )
    # render back with a dict of details
    return render_to_response(
        'mdstore/bag_search_results.html',
        {
            'site_title': Site.objects.get_current().name,
            'entries': paginated_entries,
            'maintenance_message': MAINTENANCE_MSG,
        },
        context_instance=RequestContext(request)
    )


class CustomFeed(Atom1Feed):
    """
    Sets up atom feed
    """

    mime_type = 'application/xml'

    def add_root_elements(self, handler):
        handler.addQuickElement(u"title", self.feed['title'])
        handler.startElement(u"author", {})
        # add author subelements when not None nor ""
        if self.feed['author_name']:
            handler.addQuickElement(u"name", self.feed['author_name'])
        if self.feed['author_link']:
            handler.addQuickElement(u"uri", self.feed['author_link'])
        handler.endElement(u"author")
        handler.addQuickElement(
            u"link", "", {u"rel": u"alternate", u"href": self.feed['link']}
        )
        handler.addQuickElement(
            u"link", "", {u"rel": u"self", u"href": self.feed['feed_url']}
        )
        # we always have a first and last element
        handler.addQuickElement(
            u"link",
            "",
            {u"rel": u"first", u"href": self.feed['link'] + '?p=1'}
        )
        handler.addQuickElement(
            u"link",
            "",
            {
                u"rel": u"last",
                u"href": self.feed['link'] + '?p=%s' % self.feed['last_link']
            }
        )
        # put in prev/next links if they are indeed there.
        if self.feed.get('prev_link', None) is not None:
            handler.addQuickElement(
                u"link",
                "",
                {
                    u"rel": u"previous",
                    u"href": '%s?p=%s' % (
                        self.feed['link'],
                        self.feed['prev_link']
                    )
                }
            )
        if self.feed.get('next_link', None) is not None:
            handler.addQuickElement(
                u"link",
                "",
                {
                    u"rel": u"next",
                    u"href": '%s?p=%s' % (
                        self.feed['link'],
                        self.feed['next_link']
                    )
                }
            )
        handler.addQuickElement(u"id", self.feed['id'])
        if self.feed['subtitle'] is not None:
            handler.addQuickElement(u"subtitle", self.feed['subtitle'])
        for cat in self.feed['categories']:
            handler.addQuickElement(u"category", "", {u"term": cat})
        if self.feed['feed_copyright'] is not None:
            handler.addQuickElement(u"rights", self.feed['feed_copyright'])


class AtomSiteNewsFeed(Feed):
    """
    Sets up atom feed
    """

    feed_type = CustomFeed
    link = "/feed/"
    title = "UNT Coda App"
    subtitle = "Recent Bags"
    author_name = APP_AUTHOR.get('name', None)
    author_link = APP_AUTHOR.get('uri', None)

    def feed_extra_kwargs(self, display):
        extra_dict = {}
        d = Paginator(display[0], 20)
        p = display[1]
        if p is None:
            p = 1
        cur_page = d.page(p)
        if cur_page.has_next():
            extra_dict.setdefault('next_link', cur_page.next_page_number())
        if cur_page.has_previous():
            extra_dict.setdefault('prev_link', cur_page.previous_page_number())
        extra_dict.setdefault('last_link', str(d.num_pages))
        return extra_dict

    def items(self, display):
        p = display[1]
        if p is None:
            p = 1
        d = Paginator(display[0], 20)
        # assert False, dir(d.page(p))
        return d.page(p).object_list

    def item_title(self, display):
        return '/bag/%s/' % display.name

    def item_link(self, display):
        return '/bag/%s/' % display.name

    def get_object(self, request):
        display = Bag.objects.order_by('-bagging_date')
        return (display, request.GET.get('p'))

    def item_description(self, display):
        bag_model_values = []

        info = Bag_Info.objects.filter(bag_name=display.name).values()
        for i in info:
            bag_model_values.append(
                "%s: %s" % (i['field_name'], i['field_body'])
            )
        return bag_model_values


def stats(request):
    """
    returns stats page with graphs and such
    """

    if Bag.objects.count() > 0:
        # totals for the 3 big blue buttons
        totals = Bag.objects.aggregate(
            Sum('files'),
            Sum('size'),
            Count('pk'),
            Max('bagging_date'),
        )
        # this is so we minimize our DB lookups, we only need to query these
        # once. Then, we can just make copies of them afterward for the
        # multiple graphs.
        month_skeleton = prepare_graph_date_range()
        daily_counts = Bag.objects.extra(
                    select={'day': 'date(bagging_date)'}
                ).values('day').annotate(
                    bagging_date_num=Count('bagging_date'),
                    files_total=Sum('files'),
                    sizes_total=Sum('size'),
                )
        # make sure we send in !!!COPIES!!! of the month_skeleton so we dont
        # end up rewriting over the initial data, need that for the other
        # datasets.
        monthly_bags = calc_total_by_month(
            metric='bags',
            month_skeleton=copy.deepcopy(month_skeleton),
            daily_counts=daily_counts,
            running=False,
        )
        monthly_files = calc_total_by_month(
            metric='files',
            month_skeleton=copy.deepcopy(month_skeleton),
            daily_counts=daily_counts,
            running=False,
        )
        monthly_running_file_total = calc_total_by_month(
            metric='files',
            month_skeleton=copy.deepcopy(month_skeleton),
            daily_counts=daily_counts,
            running=True,
        )
        monthly_running_bag_total = calc_total_by_month(
            metric='bags',
            month_skeleton=copy.deepcopy(month_skeleton),
            daily_counts=daily_counts,
            running=True,
        )
        monthly_size = calc_total_by_month(
            metric='size',
            month_skeleton=copy.deepcopy(month_skeleton),
            daily_counts=daily_counts,
            running=False,
        )
        monthly_running_size = calc_total_by_month(
            metric='size',
            month_skeleton=copy.deepcopy(month_skeleton),
            daily_counts=daily_counts,
            running=True,
        )
        # pass info to template
        return render_to_response(
            'mdstore/stats.html',
            {
                'site_title': Site.objects.get_current().name,
                'totals': totals,
                'monthly_bags': monthly_bags,
                'monthly_files': monthly_files,
                'monthly_running_bag_total': monthly_running_bag_total,
                'monthly_running_file_total': monthly_running_file_total,
                'monthly_size': monthly_size,
                'monthly_running_size': monthly_running_size,
                'maintenance_message': MAINTENANCE_MSG,
            },
            context_instance=RequestContext(request)
        )
    else:
        # pass info to template
        return render_to_response(
            'mdstore/stats.html',
            {
                'site_title': Site.objects.get_current().name,
                'totals': 0,
                'monthly_bags': [],
                'monthly_files': [],
                'monthly_running_bag_total': [],
                'monthly_running_file_total': [],
                'maintenance_message': MAINTENANCE_MSG,
            },
            context_instance=RequestContext(request)
        )


def json_stats(request):
    """
    returns a consumable json for robots with some basic info
    """

    # get data for json dictionary
    nodes = Node.objects.aggregate(Sum('node_capacity'))
    bags = Bag.objects.aggregate(
        Count('pk'),
        Max('bagging_date'),
        Sum('size'),
        Sum('files'),
    )
    # dump the dict to as an HttpResponse
    response = HttpResponse(content_type='application/json')
    # construct the dictionary with values from aggregates
    if bags['bagging_date__max'] != None:
        jsonDict = {
            'bags': bags['pk__count'],
            'files': bags['files__sum'],
            'capacity': nodes['node_capacity__sum'],
            'capacity_used': bags['size__sum'],
            'updated': bags['bagging_date__max'].strftime('%Y-%m-%d'),
        }
    else:
        jsonDict = {
            'bags': 0,
            'files': 0,
            'capacity': nodes['node_capacity__sum'],
            'capacity_used': 0,
            'updated': '',
        }
    # dump to response
    json.dump(
        jsonDict,
        fp=response,
        indent=4,
        sort_keys=True,
    )
    return response


def shooRobot(request):
    """
    View that tells robots how to treat the website
    """

    return HttpResponse(
        'User-agent: *' + "\n" + 'Disallow: /',
        content_type='text/plain'
    )


def bagHTML(request, identifier):
    """
    Return the bag-info.txt in html table form
    """

    # try and get the bag
    bag = get_object_or_404(Bag, name__exact=identifier)
    bag_info = Bag_Info.objects.filter(bag_name__exact=bag)
    # determine some values that will be databased better in the future
    payload_oxum_file_count = (
        item for item in bag_info if item.field_name == "Payload-Oxum"
    ).next().field_body.split(".")[1]
    payload_oxum_size = (
        item for item in bag_info if item.field_name == "Payload-Oxum"
    ).next().field_body.split(".")[0]
    bag_date = datetime.strptime((
        item for item in bag_info if item.field_name == "Bagging-Date"
    ).next().field_body, '%Y-%m-%d')
    try:
        # grab the related premis events from the json search for
        # linked object id
        event_json_url = 'http://%s/event/search.json?link_object_id=%s' % (
            request.META.get('HTTP_HOST'), bag
        )
        json_response = urllib2.urlopen(event_json_url)
        json_events = json.load(json_response)
    except:
        json_events = json.loads('{}')
    return render_to_response(
        'mdstore/bag_info.html',
        {
            'site_title': Site.objects.get_current().name,
            'json_events': json_events,
            'payload_oxum_file_count': payload_oxum_file_count,
            'payload_oxum_size': payload_oxum_size,
            'bag_date': bag_date,
            'bag': bag,
            'bag_info': bag_info,
            'maintenance_message': MAINTENANCE_MSG,
        },
        context_instance=RequestContext(request)
    )


def bagURLList(request, identifier):
    """
    Return a list of URLS in the bag
    """

    # assign the proxy url
    proxyRoot = "http://%s/" % request.META.get('HTTP_HOST')
    pathList = []
    transList = []
    # attempt to grab a bag,
    try:
        bagObject = Bag.objects.get(name=identifier)
    except Bag.DoesNotExist:
        return HttpResponseNotFound(
            "There is no bag with id {0}.".format(identifier)
        )
    handle = getFileHandle(identifier, "manifest-md5.txt")
    if not handle:
        raise Http404
    bag_root = handle.url.rsplit('/', 1)[0]
    line = handle.readline()
    # iterate over handle and append urls to pathlist
    while line:
        line = line.strip()
        parts = line.split(None, 1)
        if len(parts) > 1:
            pathList.append(parts[1])
        line = handle.readline()
    # iterate top tiles and append to pathlist
    try:
        topFileHandle = getFileHandle(identifier, "")
        topFiles = getFileList(topFileHandle.url)
        for topFile in topFiles:
            pathList.append(topFile)
    except:
        pass
    # iterate pathlist and resolve a unicode path dependent on proxy mode
    for path in pathList:
        # path = urllib2.quote(path)
        try:
            unipath = unicode(path)
        except UnicodeDecodeError, ude:
            try:
                unipath = utf8_decoder(path)[0]
            except UnicodeDecodeError, ude:
                unipath = latin_decoder(path)[0]
        # CODA_PROXY_MODE is a settings variable
        if settings.CODA_PROXY_MODE:
            uni = '%sbag/%s/%s' % (
                unicode(proxyRoot), unicode(identifier), unipath
            )
        else:
            uni = unicode(bag_root) + u"/" + unipath
        # throw the final path into a list
        transList.append(uni)
    outputText = "\n".join(reversed(transList))
    resp = HttpResponse(outputText, content_type="text/plain")
    resp.status_code = 200
    return resp


def bagURLListScrape(request, identifier):
    """
    Scrape the index to get a list of files
    """

    try:
        bagObject = Bag.objects.get(name=identifier)
    except Bag.DoesNotExist:
        return HttpResponseNotFound(
            "There is no bag with id '%s'." % identifier
        )
    handle = getFileHandle(identifier, "", pairtreeCandidateList)
    if not handle:
        raise Http404("Unable to browse bag contents.")
    fileList = getFileList(handle.url)
    fileListString = "\n".join(fileList)
    resp = HttpResponse(fileListString)
    return resp


def bagProxy(request, identifier, filePath):
    """
    Attempt to proxy a file from within the given bag
    """

    try:
        bagObject = Bag.objects.get(name=identifier)
    except Bag.DoesNotExist:
        return HttpResponseNotFound(
            "There is no bag with id '%s'." % identifier
        )
    handle = getFileHandle(identifier, filePath)
    if handle:
        pass
        resp = HttpResponse(
            FileWrapper(handle),
            content_type=handle.info().getheader('Content-Type')
        )
        resp['Content-Length'] = handle.info().getheader('Content-Length')
    else:
        raise Http404
    return resp


def externalIdentifierSearch(request, identifier=None):
    """
    Return a collection based on an identifier
    """

    if identifier or request.REQUEST.get('ark'):
        feed_id = request.path
        if request.REQUEST.get('ark') and 'ark:/67531' not in \
            request.REQUEST.get('ark'):
            identifier = 'ark:/67531/%s' % request.REQUEST.get('ark')
            feed_id = request.path + identifier + '/'
        elif request.REQUEST.get('ark'):
            identifier = request.REQUEST.get('ark')
            feed_id = request.path + identifier + '/'
        identifier = identifier[:-1] if identifier[-1] == '/' else identifier
        if 'metadc' in identifier or 'metapth' in identifier:
            bagInfoObjectList = External_Identifier.objects.select_related('belong_to_bag').filter(
                value=identifier
            )
        elif 'coda' in identifier:
            bagInfoObjectList = External_Identifier.objects.select_related('belong_to_bag').filter(
                belong_to_bag=identifier
            )
        bagList = []
        for bagInfoObject in bagInfoObjectList:
            bag = bagInfoObject.belong_to_bag
            if not bag in bagList:
                bagList.append(bag)
        feedTag = makeBagAtomFeed(
            bagObjectList=bagList,
            id=feed_id,
            title="Bags matching external identifier of %s" % identifier,
        )
        feedText = XML_HEADER % etree.tostring(feedTag, pretty_print=True)
        resp = HttpResponse(feedText, content_type="application/atom+xml")
        resp.status_code = 200
        return resp
    else:
        return render_to_response(
            'mdstore/external_identifier.html',
            {
                'site_title': Site.objects.get_current().name,
                'maintenance_message': MAINTENANCE_MSG,
            },
            context_instance=RequestContext(request)
        )


def externalIdentifierSearchJSON(request):
    """
    Return a json based on an ext identifier search
    """

    ark = request.REQUEST.get('ark')
    if 'ark:/67531' not in ark:
        ark = 'ark:/67531/%s' % ark
    # get data for json dictionary
    externalIdBagInfoList = External_Identifier.objects.select_related(
        'belong_to_bag'
    ).filter(
        value=ark
    )
    jsonList = []
    for ext_id in externalIdBagInfoList.distinct():
        ext_id_dict = {
            'name': ext_id.belong_to_bag.name,
            'oxum': '%s.%s' % (
                ext_id.belong_to_bag.size, ext_id.belong_to_bag.files
            ),
            'bagging_date': ext_id.belong_to_bag.bagging_date.strftime(
                '%Y-%m-%d'
            ),
        }
        if ext_id_dict not in jsonList:
            jsonList.append(ext_id_dict)
    response = HttpResponse(content_type='application/json')
    # construct the dictionary with values from aggregates
    # dump to response
    json.dump(
        jsonList,
        fp=response,
        indent=4,
        sort_keys=True,
    )
    return response


def bagFullTextSearchHTML(request):
    """
    Return bag search results as pretty HTML with pagination links
    """

    searchString = ""
    paginated_entries = None
    if request.REQUEST.get('search'):
        searchString = request.REQUEST["search"]
        paginated_entries = paginate_entries(
            request, bagSearch(searchString), 20
        )
    return render_to_response(
        'mdstore/bag_search_results.html',
        {
            'site_title': Site.objects.get_current().name,
            'searchString': searchString,
            'entries': paginated_entries,
            'maintenance_message': MAINTENANCE_MSG,
            'query': connection.queries,

        },
        context_instance=RequestContext(request)
    )


def bagFullTextSearchATOM(request):
    """
    Return bag search results as ATOM
    """

    searchString = request.REQUEST["search"]
    offset = 0
    listSize = 50
    if "offset" in request.REQUEST:
        offset = int(request.REQUEST["offset"]) - 1
    bagList, resultCount = bagFullTextSearch(searchString, offset, listSize)
    feedTag = makeBagAtomFeed(
        bagList,
        request.path,
        "Bags found by search string '%s'" % searchString
    )
    feedText = XML_HEADER % etree.tostring(feedTag, pretty_print=True)
    resp = HttpResponse(feedText, content_type="application/atom+xml")
    resp.status_code = 200
    return resp


def bagFullTextSearch(searchString, listSize=50):
    """
    Generic interface to take a search string and return a feed of bags
    """

    bagList = bagSearch(searchString)
    bagListLength = bagList.count()
    return Paginator(bagList, listSize)


def percent(numerator, denominator):
    """
    calculate the percentage from numerator and denominator
    returns a float rounded to two decimals
    """

    # calculate the percent as float
    raw_percent = float(numerator) / float(denominator) * 100.0
    rounded_percent = round(raw_percent, 2)
    return rounded_percent


def showNodeStatus(request, identifier=None):
    """
    A view to show node status at a glance
    """

    if identifier:
        node = Node.objects.get(node_name=identifier)
        return render_to_response(
            'mdstore/node.html',
            {
                'site_title': Site.objects.get_current().name,
                'node': node,
                'filled': percent(node.node_size, node.node_capacity),
                'available': node.node_capacity - node.node_size,
                'maintenance_message': MAINTENANCE_MSG,
            },
            context_instance=RequestContext(request)
        )
    else:
        nodes = Node.objects.all()
        status_list = []
        total_capacity = 0
        total_size = 0
        total_filled = 0
        total_available = 0
        for node in nodes:
            node_status = {}
            node_status["node"] = node
            if node.node_capacity:
                node_status["filled"] = percent(
                    node.node_size, node.node_capacity
                )
                node_status["available"] = node.node_capacity - node.node_size
            else:
                node_status["filled"] = 0
            total_capacity += node.node_capacity
            total_size += node.node_size
            total_available += node_status["available"]
            status_list.append(node_status)
        if total_capacity:
            total_filled = percent(total_size, total_capacity)
        return render_to_response(
            'mdstore/node_status.html',
            {
                'site_title': Site.objects.get_current().name,
                'status_list': status_list,
                'total_capacity': total_capacity,
                'total_size': total_size,
                'total_available': total_available,
                'total_filled': total_filled,
                'maintenance_message': MAINTENANCE_MSG,
            },
            context_instance=RequestContext(request)
        )


def app_bag(request, identifier=None):
    """
    This URL handles either a GET to get a collection of bags, or a POST to
    add a new bag to the collection
    """

    if request.method == 'GET' and identifier:
        try:
            bagObject = Bag.objects.get(name=identifier)
        except Bag.DoesNotExist:
            return HttpResponseNotFound(
                "There is no bag with id \'%s\'." % identifier
            )
        bagInfoObjectList = Bag_Info.objects.filter(bag_name=identifier)
        try:
            url_test = len(re.compile("\w*/\?{2}$").search(
                request._req.unparsed_uri, 1
            ).group())
        except:
            pass
        else:
            if url_test > 2:
                return HttpResponse(getERC(request, bagObject) + "\n" +\
                    getERCSupport(request), mimetype='text/plain')
        # Test url for ERC structure (?)
        try:
            url_test = len(re.compile("\w*/\?{1}$").search(
                request._req.unparsed_uri, 1
            ).group())
        except:
            pass
        else:
            if url_test > 1:
                return HttpResponse(
                    getERC(request, bagObject), mimetype='text/plain'
                )
        returnXML = objectsToXML(bagObject)
        returnEntry = bagatom.wrapAtom(
            xml=returnXML,
            id='http://%s/APP/bag/%s/' % (
                request.META['HTTP_HOST'], identifier
            ),
            title=identifier,
            author=APP_AUTHOR.get('name', None),
            author_uri=APP_AUTHOR.get('uri', None)
        )
        entryText = XML_HEADER % etree.tostring(returnEntry, pretty_print=True)
        resp = HttpResponse(entryText, content_type="application/atom+xml")
        return resp
    elif request.method == 'GET' and not identifier:
        requestString = request.path
        bags = Paginator(Bag.objects.order_by('-bagging_date'), 20)
        if len(request.GET):
            requestString = "%s?%s" % (request.path, request.GET.urlencode())
            page = request.GET.get('page')
        else:
            page = 1
        atomFeed = bagatom.makeObjectFeed(
            paginator=bags,
            objectToXMLFunction=objectsToXML,
            feedId=request.path[1:],
            title="Bag Feed",
            webRoot='http://%s' % request.META['HTTP_HOST'],
            idAttr="name",
            request=request,
            page=page,
            author=APP_AUTHOR
        )
        feedText = XML_HEADER % etree.tostring(atomFeed, pretty_print=True)
        resp = HttpResponse(feedText, content_type="application/atom+xml")
        resp.status_code = 200
        return resp
    elif request.method == 'POST' and not identifier:
        # attempt to parse POST'd XML
        xml = request.body
        bagObject, bagInfos = createBag(xml)
        loc = 'http://%s/APP/bag/%s/' % (
            request.META['HTTP_HOST'], bagObject.name
        )
        returnXML = objectsToXML(bagObject)
        returnEntry = bagatom.wrapAtom(
            xml=returnXML,
            id=loc,
            title=bagObject.name
        )
        entryText = XML_HEADER % etree.tostring(returnEntry, pretty_print=True)
        resp = HttpResponse(entryText, content_type="application/atom+xml")
        resp.status_code = 201
        resp['Location'] = loc
        return resp
    elif request.method == 'PUT' and identifier:
        bagObject = updateBag(request)
        if type(bagObject) == HttpResponse:
            return bagObject
        returnXML = objectsToXML(bagObject)
        returnEntry = bagatom.wrapAtom(
            returnXML, bagObject.name, bagObject.name
        )
        entryText = XML_HEADER % etree.tostring(returnEntry, pretty_print=True)
        resp = HttpResponse(entryText, content_type="application/atom+xml")
        resp.status_code = 200
        return resp
    elif request.method == 'DELETE' and identifier:
        bagObject = get_object_or_404(Bag, name=identifier)
        bag_ext_ids = get_list_or_404(
            External_Identifier, belong_to_bag=bagObject
        )
        for ext_id in bag_ext_ids:
            ext_id.delete()
        bagObject.delete()
        resp = HttpResponse("Deleted %s.\n" % identifier)
        resp.status_code = 200
        return resp
    else:
        return HttpResponseBadRequest("Invalid method.")


def app_node(request, identifier=None):
    """
    Return an ATOM feed of all of the nodes
    """

    # ENTRY
    if request.method == 'GET' and identifier:
        try:
            # and identifier means we are looking for an existing node
            node = Node.objects.get(node_name=identifier)
        except Node.DoesNotExist:
            return HttpResponseNotFound(
                "There is no node with name '%s'." % identifier
            )
        atomXML = nodeEntry(node, webRoot=request.META['HTTP_HOST'])
        atomText = XML_HEADER % etree.tostring(atomXML, pretty_print=True)
        resp = HttpResponse(atomText, content_type="application/atom+xml")
        resp.status_code = 200
        return resp
    # FEED
    elif request.method == 'GET' and not identifier:
        nodes = Paginator(Node.objects.all(), 15)
        requestString = request.path
        if len(request.GET):
            requestString = "%s?%s" % (request.path, request.GET.urlencode())
            page = request.GET.get('page')
        else:
            page = 1
        atomFeed = bagatom.makeObjectFeed(
            paginator=nodes,
            objectToXMLFunction=bagatom.nodeToXML,
            feedId=request.path[1:],
            title="Node Feed",
            webRoot='http://%s' % request.META['HTTP_HOST'],
            idAttr="node_name",
            nameAttr="node_name",
            request=request,
            page=page,
            author=APP_AUTHOR
        )
        feedText = XML_HEADER % etree.tostring(atomFeed, pretty_print=True)
        resp = HttpResponse(feedText, content_type="application/atom+xml")
        resp.status_code = 200
        return resp
    # NEW ENTRY
    elif request.method == 'POST' and not identifier:
        node = createNode(request)
        node.save()
        loc = 'http://%s/APP/node/%s/' % (
            request.META['HTTP_HOST'], node.node_name
        )
        atomXML = nodeEntry(node, webRoot=request.META['HTTP_HOST'])
        atomText = XML_HEADER % etree.tostring(atomXML, pretty_print=True)
        resp = HttpResponse(atomText, content_type="application/atom+xml")
        resp.status_code = 201
        resp['Location'] = loc
        return resp
    # UPDATE ENTRY
    elif request.method == 'PUT' and identifier:
        node = updateNode(request)
        if type(node) == HttpResponse:
            return node
        node.save()
        atomXML = nodeEntry(node, webRoot=request.META['HTTP_HOST'])
        atomText = XML_HEADER % etree.tostring(atomXML, pretty_print=True)
        resp = HttpResponse(atomText, content_type="application/atom+xml")
        resp.status_code = 200
        return resp
    # DELETE ENTRY
    elif request.method == 'DELETE' and identifier:
        try:
            node = Node.objects.get(node_name=identifier)
        except Node.DoesNotExist:
            return HttpResponseNotFound(
                "There is no node with name '%s'." % identifier
            )
        node.delete()
        resp = HttpResponse("Deleted '%s'.\n" % identifier)
        resp.status_code = 200
        return resp
