from django.http import HttpResponse, Http404, HttpResponseBadRequest, \
    HttpResponseNotFound
from presentation import xmlToQueueEntry, addQueueEntry, updateQueueEntry
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.shortcuts import render_to_response, get_object_or_404
from django.db.models import Sum, Count, Max, Min, Avg
from django.conf import settings
from django.contrib.sites.models import Site
from django.template import RequestContext
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
from datetime import datetime
from lxml import etree
import urllib
import copy

from codalib import APP_AUTHOR
from codalib.bagatom import makeObjectFeed, queueEntryToXML, wrapAtom
from coda_replication.forms import QueueSearchForm
from coda_replication.models import QueueEntry, STATUS_CHOICES


MAINTENANCE_MSG = settings.MAINTENANCE_MSG
STATUS_LIST = QueueEntry.objects.order_by().values_list(
    'status', flat=True
).distinct()


def queue_stats(request):
    """
    Show a stats page.
    """

    totals = QueueEntry.objects.count()
    # let's build a little dict of the status distribution for a pie chart
    status_counts = {}
    for status in STATUS_CHOICES:
        status_counts.setdefault(
            "%s" % status[1],
            QueueEntry.objects.filter(status=status[0]).count()
        )
    # pass info to template
    return render_to_response(
        'coda_replication/stats.html',
        {
            'totals': totals,
            'status_counts': status_counts,
            'maintenance_message': MAINTENANCE_MSG,
        },
        context_instance=RequestContext(request)
    )


def paginate_entries(request, entries, num_per_page=20):
    """
    paginates a set of entries (set of model objects)
    """

    # create paginator from result set
    paginator = Paginator(entries, num_per_page)
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


def queue_search(request):
    """
    Return a human readable list of search results
    """

    queue = QueueEntry.objects.all()
    DATE_FORMAT = "%m/%d/%Y"
    start_date = '01/01/1999'
    end_date = '12/31/2999'
    status = ''
    sort = ''
    # make initial dict for persistent values
    initial = {}
    # parse the request get variables and filter the search
    if request.GET.get('start_date'):
        start_date = datetime.strptime(
            request.GET.get('start_date'), DATE_FORMAT
        )
        queue = queue.filter(harvest_start__gte=start_date)
        initial.setdefault('start_date', start_date.strftime(DATE_FORMAT))
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), DATE_FORMAT)
        queue = queue.filter(harvest_end__lte=end_date)
        initial.setdefault('end_date', end_date.strftime(DATE_FORMAT))
    if request.GET.get('status'):
        # get corresponding index of human readable status from the choice list
        status = request.GET['status']
        queue = queue.filter(status=status)
        initial.setdefault('status', status)
    if request.GET.get('sort'):
        if request.GET['sort'] == 'size':
            sort = request.GET['sort']
            queue = queue.order_by('bytes')
    if request.GET.get('identifier'):
        # filter by identifier, if it doesn't exist, return empty queryset
        identifier = request.GET.get('identifier')
        try:
            queue = queue.filter(ark__icontains=identifier)
        except Exception, e:
            queue = QueueEntry.objects.none()
        initial.setdefault('identifier', identifier)
    # paginate 20 per page
    if queue.count() > 0:
        paginated_entries = paginate_entries(request, queue, num_per_page=20)
    else:
        paginated_entries = None
    # render to the template
    return render_to_response(
        'coda_replication/search.html',
        {
            'queue_search_form': QueueSearchForm(initial=initial),
            'start_date': start_date,
            'status_list': STATUS_CHOICES,
            'status': status,
            'sort': sort,
            'end_date': end_date,
            'entries': paginated_entries,
            'maintenance_message': MAINTENANCE_MSG,
        },
        context_instance=RequestContext(request),
    )


def queue_search_JSON(request):
    """
    returns json search results for queue entries
    """

    queue = QueueEntry.objects.all()
    DATE_FORMAT = "%m/%d/%Y"
    args = {}
    queue_json = {}
    # parse the request get variables and filter the search
    if request.GET.get('start_date'):
        args['start_date'] = datetime.strptime(
            request.GET.get('start_date'), DATE_FORMAT
        )
        queue = queue.filter(harvest_start__gte=args['start_date'])
    if request.GET.get('end_date'):
        args['end_date'] = datetime.strptime(
            request.GET.get('end_date'), DATE_FORMAT
        )
        queue = queue.filter(harvest_end__lte=args['end_date'])
    if request.GET.get('status'):
        # get corresponding index of human readable status from the choice list
        args['status'] = request.GET['status']
        queue = queue.filter(status=args['status'])
    if request.GET.get('identifier'):
        # get corresponding index of human readable status from the choice list
        args['identifier'] = request.GET['identifier']
        queue = queue.filter(ark=args['identifier'])
    if queue.count() is not 0:
        # paginate 20 per page
        paginated_entries = paginate_entries(request, queue, num_per_page=20)
        # prepare a results set and then append each event to it as a dict
        queue_url_prefix = "%s/queue/search.json" % \
            request.META.get('HTTP_HOST')
        rel_links = []
        entries = []
        cur_page = paginated_entries.number
        # we will ALWAYS have a self, first and last relative link
        args['page'] = paginated_entries.number
        current_page_args = args.copy()
        args['page'] = 1
        first_page_args = args.copy()
        args['page'] = paginated_entries.paginator.num_pages
        last_page_args = args.copy()
        # store links for adjacent events relative to the current event
        rel_links.extend(
            [
                {
                    'rel': 'self',
                    'href': "http://%s%s?%s" % (
                        request.META.get('HTTP_HOST'),
                        request.path, urllib.urlencode(current_page_args)
                    )
                },
                {
                    'rel': 'first',
                    'href': "http://%s%s?%s" % (
                        request.META.get('HTTP_HOST'),
                        request.path, urllib.urlencode(first_page_args)
                    )
                },
                {
                    'rel': 'last',
                    'href': "http://%s%s?%s" % (
                        request.META.get('HTTP_HOST'),
                        request.path, urllib.urlencode(last_page_args)
                    )
                },
            ]
        )
        # if we are past the first event, we can always add a previous event
        if paginated_entries.number > 1:
            args['page'] = current_page_args['page'] - 1
            rel_links.append(
                {
                    'rel': 'previous',
                    'href': "http://%s%s?%s" % (
                        request.META.get('HTTP_HOST'),
                        request.path, urllib.urlencode(args)
                    )
                },
            )
        # if our event is not the last in the list, we add a next event
        if paginated_entries.number < paginated_entries.paginator.num_pages:
            args['page'] = current_page_args['page'] + 1
            rel_links.append(
                {
                    'rel': 'next',
                    'href': "http://%s%s?%s" % (
                        request.META.get('HTTP_HOST'),
                        request.path, urllib.urlencode(args)
                    )
                },
            )
        for entry in paginated_entries.object_list:
            entry_status = [
                i[1] for i in STATUS_CHOICES if str(i[0]) == entry.status
            ][0]
            entries.extend(
                [
                    {
                        'identifier': entry.ark,
                        'status': entry.status,
                        'harvest_start': str(entry.harvest_start),
                        'harvest_end': str(entry.harvest_end),
                        'queue position': entry.queue_position,
                        'oxum': entry.oxum,
                    },
                ],
            )
        queue_json = {
            'feed': {
                'entry': entries,
                'link': rel_links,
                'opensearch:Query': request.GET,
                "opensearch:itemsPerPage": paginated_entries.paginator.per_page,
                "opensearch:startIndex": "1",
                "opensearch:totalResults": queue.count(),
                "title": "Queue Entries"
            }
        }
    response = HttpResponse(content_type='application/json')
    json.dump(
        queue_json,
        fp=response,
        indent=4,
        sort_keys=True,
    )
    return response


def queue_html(request, identifier=None):
    """
    Return a human readable queue object
    """

    queue_object = get_object_or_404(QueueEntry, ark=identifier)
    return render_to_response(
        'coda_replication/queue_entry.html',
        {
            'status_list': STATUS_CHOICES,
            'record': queue_object,
            'maintenance_message': MAINTENANCE_MSG,
        },
        context_instance=RequestContext(request)
    )


def queue_recent(request):
    """
    Show a queue page.
    """

    queue_entries = QueueEntry.objects.all().order_by('-pk')[:10]
    # pass info to template
    return render_to_response(
        'coda_replication/queue.html',
        {
            'entries': queue_entries,
            'status_list': STATUS_CHOICES,
            'num_events': QueueEntry.objects.count(),
            'maintenance_message': MAINTENANCE_MSG,
        },
        context_instance=RequestContext(request)
    )


def queue(request, identifier=None):
    """
    Display the queue status for a given ark
    """

    # respond to a delete request
    if request.method == 'DELETE' and identifier:
        try:
            queueObject = QueueEntry.objects.get(ark=identifier)
        except:
            return HttpResponseNotFound(
                "There is no Queue Entry for ark '%s'.\n" % identifier
            )
        queueObject.delete()
        resp = HttpResponse(
            "Queue entry for ark %s deleted.\n" % identifier,
            status=200, content_type="text/plain"
        )
    # respond to a POST request
    elif request.method == 'POST' and not identifier:
        try:
            queueObject = addQueueEntry(request.body)
        except IntegrityError as e:
            return HttpResponse(
                "Conflict with already-existing resource.\n",
                status=409
            )
        identifier = queueObject.ark
        queueObjectXML = queueEntryToXML(queueObject)
        loc = 'http://%s/%s/' % (request.META['HTTP_HOST'], queueObject.ark)
        atomXML = wrapAtom(
            xml=queueObjectXML,
            id=loc,
            title=queueObject.ark,
        )
        atomText = '<?xml version="1.0"?>\n%s' % etree.tostring(
            atomXML, pretty_print=True
        )
        resp = HttpResponse(
            atomText,
            content_type="application/atom+xml",
            status=201
        )
        resp['Location'] = loc
    # respond to PUT request
    elif request.method == 'PUT' and identifier:
        try:
            queueObject = updateQueueEntry(request.body, 
                    validate_ark=identifier)
        except ObjectDoesNotExist as e:
            return HttpResponseNotFound(e.message, content_type="text/plain")
        except ValidationError as e:
            return HttpResponse(e.message, content_type="text/plain",
                    status=409)
        queueObjectXML = queueEntryToXML(queueObject)
        atomXML = wrapAtom(
            xml=queueObjectXML,
            id='http://%s/%s/' % (request.META['HTTP_HOST'], queueObject.ark),
            title=queueObject.ark,
        )
        atomText = '<?xml version="1.0"?>\n%s' % etree.tostring(
            atomXML, pretty_print=True
        )
        resp = HttpResponse(atomText, content_type="application/atom+xml")
    # respond to GET request
    elif request.method == 'GET' and identifier:
        # if it's a GET, or if we've just PUT or POST'd
        try:
            queueObject = QueueEntry.objects.get(ark=identifier)
        except QueueEntry.DoesNotExist:
            return HttpResponseNotFound(
                "There is no queue entry for ark '%s'.\n" % identifier,
                content_type="text/plain"
            )
        queueObjectXML = queueEntryToXML(queueObject)
        atomXML = wrapAtom(
            xml=queueObjectXML,
            id='http://%s/%s/' % (request.META['HTTP_HOST'], queueObject.ark),
            title=queueObject.ark,
            author=APP_AUTHOR.get('name', None),
            author_uri=APP_AUTHOR.get('uri', None)
        )
        atomText = '<?xml version="1.0"?>\n%s' % etree.tostring(
            atomXML, pretty_print=True
        )
        resp = HttpResponse(atomText, content_type="application/atom+xml")
    elif request.method == 'GET':
        return queue_list(request)
    else:
        if identifier:
            allow = ('GET', 'PUT', 'DELETE')
        else:
            allow = ('GET', 'POST')
        resp = HttpResponse("Method not allowed.\n", status=405, 
            content_type="text/plain")
        resp['Allow'] = ', '.join(allow)
    return resp


def queue_list(request):
    """Get a list of Queues."""
    status = request.GET.get('status')
    sort = request.GET.get('sort')
    page = int(request.GET.get('page', 1))
    count = int(request.GET.get('count', 10))

    queues = QueueEntry.objects.all().order_by('queue_position')
    queues = queues.filter(status=status) if status else queues
    queues = queues.order_by('bytes') if sort == 'size' else queues

    paginator = Paginator(queues, count)

    try:
        atomFeed = makeObjectFeed(
            paginator=paginator,
            objectToXMLFunction=queueEntryToXML,
            feedId=request.path[1:],
            title='Queue Entry Feed',
            webRoot='http://{0}'.format(request.META['HTTP_HOST']),
            idAttr='ark',
            nameAttr='ark',
            request=request,
            page=page,
            author=APP_AUTHOR)
    except EmptyPage:
        return HttpResponseBadRequest('Page does not exist.')

    feedText = etree.tostring(atomFeed, pretty_print=True)
    feedText = '<?xml version="1.0"?>\n{0}'.format(feedText)

    return HttpResponse(feedText, content_type='application/atom+xml')
