import copy
import uuid

from urllib.request import urlopen
from urllib.parse import urlencode
import json
from django.http import HttpResponse, Http404, HttpResponseBadRequest, \
    HttpResponseNotFound, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from wsgiref.util import FileWrapper
from django.db import IntegrityError
from django.db.models import Sum, Count, Max, Min
from django.conf import settings
from django.utils.feedgenerator import Atom1Feed
from django.contrib.syndication.views import Feed
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from lxml import etree
from premis_event_service.models import Event
from coda_replication.models import QueueEntry
from coda_validate.models import Validate
from .models import Bag, Bag_Info, Node, External_Identifier
from codalib import APP_AUTHOR, bagatom
from .presentation import getFileHandle, bagSearch, \
    makeBagAtomFeed, createBag, updateBag, objectsToXML, updateNode, \
    nodeEntry, createNode, zip_file_streamer, generateBagFiles
from dateutil import rrule
from datetime import datetime
# for historical reasons that are not entirely clear, the tests for
# this module do some monkeypatching that expects this import
# because Site isn't used, the line has to be muted so flake8 doesn't
# carp about it
from django.contrib.sites.models import Site  # noqa
from django.db import connection

from django.urls import reverse

from coda_mdstore import exceptions

MAINTENANCE_MSG = settings.MAINTENANCE_MSG
XML_HEADER = b"<?xml version=\"1.0\"?>\n%s"


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
    for dt in rrule.rrule(
        rrule.DAILY,
        dtstart=system_start_date,
        until=system_end_date,
    ):
        # if we change months
        if month != dt.strftime('%Y-%m'):
            month = dt.strftime('%Y-%m')
            # make the year and drop in if it doesn't exist
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
        current_month_counts = [
            e for e in daily_counts
            if datetime.strftime(e['day'], '%Y-%m') == datetime.strftime(u[0], '%Y-%m')
        ]
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
    return render(
        request,
        'mdstore/index.html',
        {
            'totals': totals,
            'queue_total': queue_total,
            'validation_total': validation_total,
            'event_total': event_total,
            'maintenance_message': MAINTENANCE_MSG,
        }
    )


def about(request):
    """
    Just a standard about page
    """

    # render back with a dict of details
    return render(
        request,
        'mdstore/about.html',
        {
            'maintenance_message': MAINTENANCE_MSG,
        }
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
    return render(
        request,
        'mdstore/bag_search_results.html',
        {
            'entries': paginated_entries,
            'maintenance_message': MAINTENANCE_MSG,
        }
    )


class CustomFeed(Atom1Feed):
    """
    Sets up atom feed
    """

    mime_type = 'application/xml'

    def add_root_elements(self, handler):
        handler.addQuickElement("title", self.feed['title'])
        handler.startElement("author", {})
        # add author subelements when not None nor ""
        if self.feed['author_name']:
            handler.addQuickElement("name", self.feed['author_name'])
        if self.feed['author_link']:
            handler.addQuickElement("uri", self.feed['author_link'])
        handler.endElement("author")
        handler.addQuickElement(
            "link", "", {"rel": "alternate", "href": self.feed['link']}
        )
        handler.addQuickElement(
            "link", "", {"rel": "self", "href": self.feed['feed_url']}
        )
        # we always have a first and last element
        handler.addQuickElement(
            "link",
            "",
            {"rel": "first", "href": self.feed['link'] + '?p=1'}
        )
        handler.addQuickElement(
            "link",
            "",
            {
                "rel": "last",
                "href": self.feed['link'] + '?p=%s' % self.feed['last_link']
            }
        )
        # put in prev/next links if they are indeed there.
        if self.feed.get('prev_link', None) is not None:
            handler.addQuickElement(
                "link",
                "",
                {
                    "rel": "previous",
                    "href": '%s?p=%s' % (
                        self.feed['link'],
                        self.feed['prev_link']
                    )
                }
            )
        if self.feed.get('next_link', None) is not None:
            handler.addQuickElement(
                "link",
                "",
                {
                    "rel": "next",
                    "href": '%s?p=%s' % (
                        self.feed['link'],
                        self.feed['next_link']
                    )
                }
            )
        handler.addQuickElement("id", self.feed['id'])
        if self.feed['subtitle'] is not None:
            handler.addQuickElement("subtitle", self.feed['subtitle'])
        for cat in self.feed['categories']:
            handler.addQuickElement("category", "", {"term": cat})
        if self.feed['feed_copyright'] is not None:
            handler.addQuickElement("rights", self.feed['feed_copyright'])


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
        extra_dict.setdefault('last_link', d.num_pages)
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
            select={'day': 'date(bagging_date)'}).values('day').annotate(
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
        return render(
            request,
            'mdstore/stats.html',
            {
                'totals': totals,
                'monthly_bags': monthly_bags,
                'monthly_files': monthly_files,
                'monthly_running_bag_total': monthly_running_bag_total,
                'monthly_running_file_total': monthly_running_file_total,
                'monthly_size': monthly_size,
                'monthly_running_size': monthly_running_size,
                'maintenance_message': MAINTENANCE_MSG,
            }
        )
    else:
        # pass info to template
        return render(
            request,
            'mdstore/stats.html',
            {
                'totals': 0,
                'monthly_bags': [],
                'monthly_files': [],
                'monthly_running_bag_total': [],
                'monthly_running_file_total': [],
                'maintenance_message': MAINTENANCE_MSG,
            }
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
    if bags['bagging_date__max'] is not None:
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
    # Put the bag info in a dict
    bag_info_d = dict((info.field_name, info.field_body) for info in bag_info)
    oxum_bytes = oxum_file_count = -1
    try:
        oxum = bag_info_d.get('Payload-Oxum', '')
        oxum_bytes, oxum_file_count = map(int, oxum.split('.', 1))
    except:
        pass
    try:
        bag_date = datetime.strptime(bag_info_d.get('Bagging-Date'), '%Y-%m-%d')
    except:
        bag_date = None
    # grab the related premis events from the json search for
    # linked object id
    linked_events = []
    total_events = None
    try:
        filters = {'linked_object_id': bag}
        event_json_url = 'http://%s/event/search.json?%s' % (
            # TODO: Maybe this should be configurable?
            request.META.get('HTTP_HOST'),
            urlencode(filters)
        )
        json_response = urlopen(event_json_url)
        json_events = json.load(json_response)
        if json_events:
            total_events = json_events.get('feed', {})
            total_events = total_events.get('opensearch:totalResults', 0)
        # Follow next url in results until we hit the last page
        while json_events:
            this_page = json_events.get('feed', {})
            this_page = this_page.get('entry', [])
            linked_events += this_page
            next_url = json_events.get('feed', {})
            next_url = next_url.get('link', [])
            next_url = {link.get('rel'): link.get('href') for link in next_url}
            next_url = next_url.get('next')
            if next_url:
                try:
                    json_response = urlopen(next_url)
                    json_events = json.load(json_response)
                except:
                    json_events = None
            else:
                json_events = None
    except:
        pass
    return render(
        request,
        'mdstore/bag_info.html',
        {
            'linked_events': linked_events,
            'total_events': total_events,
            'payload_oxum_file_count': oxum_file_count,
            'payload_oxum_size': oxum_bytes,
            'bag_date': bag_date,
            'bag': bag,
            'bag_info': bag_info_d,
            'maintenance_message': MAINTENANCE_MSG,
        }
    )


def bagURLList(request, identifier):
    """
    Return a list of URLS in the bag
    """

    # assign the proxy url
    proxyRoot = request.build_absolute_uri('/')
    # attempt to grab a bag,
    get_object_or_404(Bag, name__exact=identifier)
    try:
        transList = generateBagFiles(identifier, proxyRoot, settings.CODA_PROXY_MODE)
    except Exception:
        raise Http404

    outputText = "\n".join(reversed(transList))
    resp = HttpResponse(outputText, content_type="text/plain")
    resp.status_code = 200
    return resp


def bagURLLinks(request, identifier):
    """
        Return links to URLS in the bag
    """
    # assign the proxy url
    proxyRoot = request.build_absolute_uri('/')
    # attempt to grab a bag,
    get_object_or_404(Bag, name__exact=identifier)
    try:
        transList = generateBagFiles(identifier, proxyRoot, settings.CODA_PROXY_MODE)
    except Exception:
        raise Http404
    return render(request, 'mdstore/bag_files_download.html',
                  {'links': sorted(transList)})


def bagDownload(request, identifier):
    """
        Return a downloadable bag zipped file.
    """
    # assign the proxy url
    proxyRoot = request.build_absolute_uri('/')
    # attempt to grab a bag,
    get_object_or_404(Bag, name__exact=identifier)
    try:
        transList = generateBagFiles(identifier, proxyRoot, settings.CODA_PROXY_MODE)
    except Exception:
        raise Http404
    meta_id = identifier.split('/')[-1]
    zip_filename = meta_id + '.zip'
    response = StreamingHttpResponse(zip_file_streamer(transList, meta_id),
                                     content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=%s' % zip_filename
    return response


def bagProxy(request, identifier, filePath):
    """
    Attempt to proxy a file from within the given bag
    """

    get_object_or_404(Bag, name__exact=identifier)
    handle = getFileHandle(identifier, filePath)
    if handle:
        resp = HttpResponse(
            content_type=handle.info().get('Content-Type')
        )
        resp['Content-Length'] = handle.info().get('Content-Length')
        if getattr(settings, 'REPROXY', False):
            # Have a proxy server point the client to where to download
            # the file directly in order to bypass serving through Django.
            resp['X-REPROXY-URL'] = handle.geturl()
            resp['ETag'] = '"%s"' % uuid.uuid4().hex
        else:
            # Serve the data file through Django.
            resp.content = FileWrapper(handle)
    else:
        raise Http404
    return resp


def externalIdentifierSearch(request, identifier=None):
    """
    Return a collection based on an identifier
    """

    if identifier or request.GET.get('ark'):
        feed_id = request.path
        if request.GET.get('ark') and ('ark:/%d' % settings.ARK_NAAN) not in \
                request.GET.get('ark'):
            identifier = 'ark:/%d/%s' % (settings.ARK_NAAN, request.GET.get('ark'))
            feed_id = request.path + identifier + '/'
        elif request.GET.get('ark'):
            identifier = request.GET.get('ark')
            feed_id = request.path + identifier + '/'
        identifier = identifier[:-1] if identifier[-1] == '/' else identifier
        bagInfoObjectList = External_Identifier.objects.none()
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
            if bag not in bagList:
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
        return render(
            request,
            'mdstore/external_identifier.html',
            {
                'maintenance_message': MAINTENANCE_MSG,
            }
        )


def externalIdentifierSearchJSON(request):
    """External_Identifier search formatted in JSON."""
    ark = request.GET.get('ark', '')
    showAll = request.GET.get('showAll', 'false')
    if ('ark:/%d' % settings.ARK_NAAN) not in ark:
        ark = 'ark:/%d/%s' % (settings.ARK_NAAN, ark)
    data = []
    identifiers = (External_Identifier.objects
                                      .select_related('belong_to_bag')
                                      .filter(value=ark)
                                      .order_by('-belong_to_bag__bagging_date')
                                      .values_list('belong_to_bag__name',
                                                   'belong_to_bag__size',
                                                   'belong_to_bag__files',
                                                   'belong_to_bag__bagging_date')
                                      .distinct())
    if identifiers:
        if showAll.lower() != 'true':
            identifiers = identifiers[:1]
        data = [
            {
                'name': exid[0],
                'oxum': '%s.%s' % (exid[1], exid[2]),
                'bagging_date': exid[3].strftime('%Y-%m-%d')
            }
            for exid in identifiers
        ]
    data = json.dumps(data, indent=4, sort_keys=True)
    return HttpResponse(data, content_type='application/json')


def bagFullTextSearchHTML(request):
    """
    Return bag search results as pretty HTML with pagination links
    """

    searchString = ""
    paginated_entries = None
    if request.GET.get('search'):
        searchString = request.GET["search"]
        paginated_entries = paginate_entries(
            request, bagSearch(searchString), 20
        )
    return render(
        request,
        'mdstore/bag_search_results.html',
        {
            'searchString': searchString,
            'entries': paginated_entries,
            'maintenance_message': MAINTENANCE_MSG,
            'query': connection.queries,

        }
    )


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
        node = get_object_or_404(Node, node_name__exact=identifier)
        return render(
            request,
            'mdstore/node.html',
            {
                'node': node,
                'filled': percent(node.node_size, node.node_capacity),
                'available': node.node_capacity - node.node_size,
                'maintenance_message': MAINTENANCE_MSG,
            }
        )
    else:
        nodes = Node.objects.order_by('node_name')
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
        return render(
            request,
            'mdstore/node_status.html',
            {
                'status_list': status_list,
                'total_capacity': total_capacity,
                'total_size': total_size,
                'total_available': total_available,
                'total_filled': total_filled,
                'maintenance_message': MAINTENANCE_MSG,
            }
        )


def app_bag(request, identifier=None):
    """
    This URL handles either a GET to get a collection of bags, or a POST to
    add a new bag to the collection
    """

    if request.method == 'GET' and identifier:
        try:
            bag = Bag.objects.get(name=identifier)
        except Bag.DoesNotExist:
            return HttpResponseNotFound(
                "There is no bag with id '{0}'.\n".format(identifier),
                content_type="text/plain"
            )

        object_xml = objectsToXML(bag)
        url = request.build_absolute_uri(reverse('app-bag-detail', args=[identifier]))
        althref = request.build_absolute_uri(reverse('bag-detail', args=[identifier]))

        entries = bagatom.wrapAtom(xml=object_xml, id=url, title=identifier,
                                   author=APP_AUTHOR.get('name', None),
                                   author_uri=APP_AUTHOR.get('uri', None),
                                   alt=althref)

        entry_text = XML_HEADER % etree.tostring(entries, pretty_print=True)
        return HttpResponse(entry_text, content_type="application/atom+xml")
    elif request.method == 'GET':
        bags = Paginator(Bag.objects.order_by('-bagging_date'), 20)
        if len(request.GET):
            page = request.GET.get('page')
        else:
            page = 1
        try:
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
        except EmptyPage:
            return HttpResponse(
                "That page doesn't exist.\n",
                status=400, content_type='text/plain'
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
        try:
            bagObject = updateBag(request)
        except Bag.DoesNotExist as e:
            return HttpResponseNotFound(
                "%s\n" % (e,),
                content_type="text/plain"
            )
        except exceptions.BadBagName as e:
            return HttpResponseBadRequest(
                "%s\n" % (e,),
                content_type="text/plain"
            )

        returnXML = objectsToXML(bagObject)
        returnEntry = bagatom.wrapAtom(
            returnXML, bagObject.name, bagObject.name
        )
        entryText = XML_HEADER % etree.tostring(returnEntry, pretty_print=True)
        resp = HttpResponse(entryText, content_type="application/atom+xml")
        resp.status_code = 200
        return resp
    elif request.method == 'DELETE' and identifier:
        try:
            bag = Bag.objects.get(name=identifier)
        except Bag.DoesNotExist:
            return HttpResponse(
                "There is no bag with id '{0}'.\n".format(identifier),
                content_type="text/plain", status=404
            )
        try:
            bag_ext_ids = External_Identifier.objects.select_related('belong_to_bag')
        except:
            return HttpResponse(
                "Could not retrieve external ids for this bag.\n",
                content_type="text/plain", status=500
            )
        for ext_id in bag_ext_ids:
            ext_id.delete()
        bag.delete()
        resp = HttpResponse("Deleted %s.\n" % identifier)
        resp.status_code = 200
        return resp
    else:
        if identifier:
            allow = ('GET', 'PUT', 'DELETE')
        else:
            allow = ('GET', 'POST')
        resp = HttpResponse(
            "Invalid method.\n",
            status=405, content_type="text/plain"
        )
        resp['Allow'] = ', '.join(allow)
        return resp


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
    elif request.method == 'GET':
        nodes = Node.objects.filter(status='1')
        paginator = Paginator(nodes, max(1, len(nodes)))
        if len(request.GET):
            page = request.GET.get('page')
        else:
            page = 1
        try:
            atomFeed = bagatom.makeObjectFeed(
                paginator=paginator,
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
        except EmptyPage:
            return HttpResponse(
                "That page doesn't exist.\n",
                status=400, content_type='text/plain'
            )
        feedText = XML_HEADER % etree.tostring(atomFeed, pretty_print=True)
        resp = HttpResponse(feedText, content_type="application/atom+xml")
        resp.status_code = 200
        return resp
    # NEW ENTRY
    elif request.method == 'POST' and not identifier:
        try:
            node = createNode(request)
        except etree.LxmlError:
            return HttpResponse(
                "Invalid XML in request body.\n",
                status=400, content_type="text/plain"
            )
        try:
            node.save()
        except IntegrityError:
            return HttpResponse(
                "Conflict with already-existing resource.\n",
                status=409, content_type="text/plain"
            )
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
        try:
            node = updateNode(request)
        except Node.DoesNotExist as e:
            return HttpResponseNotFound(str(e))
        except exceptions.BadNodeName as e:
            return HttpResponseBadRequest(str(e))

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
