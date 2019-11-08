import json
import random
import datetime

from codalib import APP_AUTHOR
from codalib.bagatom import wrapAtom, makeObjectFeed
from dateutil import parser
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, render
from django.utils.feedgenerator import Atom1Feed
from lxml import etree
from django.core.exceptions import ValidationError

from django.views.generic import ListView

from .models import Validate


XML_HEADER = b"<?xml version=\"1.0\"?>\n%s"


class CorrectMimeTypeFeed(Atom1Feed):
    mime_type = 'application/xml'


class AtomNextNewsFeed(Feed):
    """
    next view.
    an atom pub representation of the next validation to occur.
    should be a single item.
    """

    feed_type = Atom1Feed
    link = "/validate/next/"
    title = "UNT Coda Validate App"
    subtitle = "The highest priority validation item"
    reason = 'None'
    author_name = APP_AUTHOR.get('name', None)
    author_link = APP_AUTHOR.get('uri', None)
    feed_type = CorrectMimeTypeFeed

    def get_object(self, request, server):
        if server:
            return server
        else:
            return None

    def items(self, obj):
        # need to filter by server first, if provided
        reason = ''
        if obj:
            validations = Validate.objects.all().filter(server=obj)
            reason = 'This selection was filtered to only consider \
 server %s. ' % obj
        else:
            validations = Validate.objects.all()
        # next check if we have any with a priority above 0
        v = validations.filter(
            priority__gt=0).order_by('priority_change_date')
        if v.exists():
            reason += 'Item was chosen because it is the \
oldest prioritized.'
        # if set is empty, go with any priority with last_verified older than
        # settings.VALIDATION_PERIOD
        else:
            # It might seem natural to use django's built-in random ordering,
            # but that technique becomes slow when using large sets
            # because 'order by ?' is very expensive against MySQL dbs.
            # v = Validate.objects.all().filter(
            #     last_verified__gte=datetime.datetime.now() -
            #         settings.VALIDATION_PERIOD
            # ).order_by('?')
            # instead, let's do this:
            # http://elpenia.wordpress.com/2010/05/11/getting-random-objects-from-a-queryset-in-django/
            now = datetime.datetime.now()
            v = validations.filter(
                last_verified__lte=now - settings.VALIDATION_PERIOD
            )
            if v.exists():
                random_slice = int(random.random() * v.count())
                v = v[random_slice:]
                reason += 'Item was randomly selected and within the \
past year because there is no prioritized record.'
            # if that set has no objects, pick the oldest verified item.
            else:
                v = validations.order_by('last_verified')
                reason += 'Item was chosen because there \
is no prioritized record and it had not been validated in the longest \
duration of time.'
        self.reason = reason
        return v[:1]

    def item_title(self, item):
        return item.identifier

    def item_description(self, item):
        return self.reason

    def item_link(self, item):
        return '/APP/validate/%s/' % item.identifier


# for some reason, I couldn't get AtomNextFeed to work without a server
# I don't think optional arguments are supported for class-based syndication
# feeds, so I have this work around to make it work.
class AtomNextFeedNoServer(AtomNextNewsFeed):
    def get_object(self, request):
        pass


def index(request):
    context = {
        'recently_prioritized': Validate.objects.filter(
            priority__gt=0).order_by('-priority_change_date')[:20],
        'recently_verified': Validate.objects.all().order_by('-last_verified')[:20],
        'verified_counts': Validate.objects.last_verified_status_counts()
    }

    return render(request, 'coda_validate/index.html', context)


def last_day_of_month(year, month):
    """ Work out the last day of the month """
    last_days = [31, 30, 29, 28, 27]
    for i in last_days:
        try:
            end = datetime.datetime(year, month, i)
        except ValueError:
            continue
        else:
            return end.day
    return None


def stats(request):
    """
    stats page
    """
    if not Validate.objects.exists():
        return render(
            request,
            'coda_validate/stats.html',
            {
                'sums_by_date': {},
                'validations': None,
                'this_month': None,
                'last_24h': None,
                'last_vp': None,
                'unverified': 0,
                'passed': 0,
                'failed': 0,
                'validation_period': '%s days' % str(
                    settings.VALIDATION_PERIOD.days
                ),
            }
        )
    # resolve the range for last month filter
    today = datetime.date.today()
    first = datetime.date(day=1, month=today.month, year=today.year)
    last_day = last_day_of_month(first.year, first.month)
    this_month_range = [
        '%s-%s-01 00:00:00' % (first.year, first.month),
        '%s-%s-%s 23:59:59' % (first.year, first.month, last_day),
    ]
    # resolve the range for last 24 hours filter
    now = datetime.datetime.now()
    twenty_four_hours_ago = now - datetime.timedelta(hours=24)
    since_validation_period = now - datetime.timedelta(
        days=settings.VALIDATION_PERIOD.days)
    # make a set of data that makes sense for the heatmap
    result_counts = Validate.objects.last_verified_status_counts()
    total = sum(result_counts.values())
    sums_by_date = Validate.sums_by_date()
    sums_by_date_g = {}
    years = set()
    for dt, ct in sums_by_date.items():
        y, m, d = dt
        dt = (y, m - 1, d)
        sums_by_date_g[dt] = ct
        years.add(y)
    sums_by_date = sums_by_date_g
    num_years = len(years)
    return render(
        request,
        'coda_validate/stats.html',
        {
            'sums_by_date': dict((('%d, %d, %d' % s, c)
                                 for s, c in sums_by_date.items())),
            'num_years': num_years,
            'validations': total,
            'this_month': Validate.objects.filter(
                last_verified__range=this_month_range).count(),
            'last_24h': Validate.objects.filter(
                last_verified__range=[twenty_four_hours_ago, now]).count(),
            'last_vp': Validate.objects.filter(
                last_verified__range=[since_validation_period, now]).count(),
            'unverified': result_counts.get('Unverified'),
            'passed': result_counts.get('Passed'),
            'failed': result_counts.get('Failed'),
            'validation_period': '%s days' % str(settings.VALIDATION_PERIOD.days),
        }
    )


def prioritize(request):
    """
    prioritize view
    """

    identifier = request.GET.get('identifier')
    prioritized = False
    if identifier:
        v = get_object_or_404(Validate, identifier=identifier)
        v.priority = 1
        v.priority_change_date = datetime.datetime.now()
        v.save()
        prioritized = True
    return render(
        request,
        'coda_validate/prioritize.html',
        {
            'identifier': identifier,
            'prioritized': prioritized,
        }
    )


def validate(request, identifier):
    """
    prioritize view
    """

    # this view always gets an identifier, if it's wrong, 404
    v = get_object_or_404(Validate, identifier=identifier)
    # clicked priority button on validate detail page
    p = request.GET.get('priority')
    if p == '1':
        v.priority = 1
        v.priority_change_date = datetime.datetime.now()
        v.save()
    return render(
        request,
        'coda_validate/validate.html',
        {
            'validate': v,
        }
    )


def prioritize_json(request):
    """
    prioritize json view
    """

    DOMAIN = Site.objects.get_current().domain
    identifier = request.GET.get('identifier')
    json_dict = {}
    json_dict['status'] = 'failure'
    status = 404
    if identifier:
        json_dict['requested_identifier'] = identifier
        try:
            v = Validate.objects.get(identifier=identifier)
        except Exception:
            v = None
        if v:
            v.priority = 1
            v.priority_change_date = datetime.datetime.now()
            v.save()
            json_dict['status'] = 'success'
            json_dict['priority'] = v.priority
            json_dict['priority_change_date'] = str(v.priority_change_date)
            json_dict['atom_pub_url'] = '%s/APP/validate/%s' % \
                (DOMAIN, v.identifier)
            status = 200
        else:
            json_dict['response'] = 'identifier was not found'
            json_dict['requested_identifier'] = identifier
    else:
        json_dict['response'] = 'missing identifier parameter'
        json_dict['requested_identifier'] = ''
        status = 400
    response = HttpResponse(content_type='application/json', status=status)
    json.dump(
        json_dict,
        fp=response,
        indent=4,
        sort_keys=True,
    )
    return response


def validateToXML(validateObject):
    """
    This is the reverse of xmlToValidateObject.
    Given a "Validate" object, it generates an
    XML object representative of such.
    """

    # define namespace
    validate_namespace = "http://digital2.library.unt.edu/coda/validatexml/"
    val = "{%s}" % validate_namespace
    validate_nsmap = {"validate": validate_namespace}

    # build xml from object and return
    XML = etree.Element("{0}validate".format(val), nsmap=validate_nsmap)

    label = etree.SubElement(XML, "{0}identifier".format(val))
    label.text = validateObject.identifier

    last_verified = etree.SubElement(XML, "{0}last_verified".format(val))
    last_verified.text = validateObject.last_verified.isoformat()

    last_verified_status = etree.SubElement(XML, "{0}last_verified_status".format(val))
    last_verified_status.text = validateObject.last_verified_status

    priority_change_date = etree.SubElement(XML, "{0}priority_change_date".format(val))
    priority_change_date.text = validateObject.priority_change_date.isoformat()

    priority = etree.SubElement(XML, "{0}priority".format(val))
    priority.text = str(validateObject.priority)

    server = etree.SubElement(XML, "{0}server".format(val))
    server.text = validateObject.server

    return XML


def xmlToValidateObject(validateXML):
    """
    Parse the XML in a POST request and create the validate object
    """

    entryRoot = etree.XML(validateXML)
    if entryRoot is None:
        raise ValueError("Unable to parse uploaded XML")
    # parse XML
    contentElement = entryRoot.xpath("*[local-name() = 'content']")[0]
    validateXML = contentElement.xpath("*[local-name() = 'validate']")[0]
    identifier = validateXML.xpath(
        "*[local-name() = 'identifier']")[0].text.strip()

    last_verified = validateXML.xpath(
        "*[local-name() = 'last_verified']")[0].text.strip()
    last_verified = parser.parse(last_verified)

    last_verified_status = validateXML.xpath(
        "*[local-name() = 'last_verified_status']")[0].text.strip()

    priority_change_date = validateXML.xpath(
        "*[local-name() = 'priority_change_date']")[0].text.strip()
    priority_change_date = parser.parse(priority_change_date)

    priority = validateXML.xpath(
        "*[local-name() = 'priority']")[0].text.strip()

    server = validateXML.xpath("*[local-name() = 'server']")[0].text.strip()

    # make the object and return
    validate = Validate(
        identifier=identifier,
        last_verified=last_verified,
        last_verified_status=last_verified_status,
        priority_change_date=priority_change_date,
        priority=priority,
        server=server,
    )
    return validate


def xmlToUpdateValidateObject(validateXML):
    """
    Parse the XML in a PUT request and adjust the validate based on that
    *ONLY MODIFIES 'last_verified_status'*
    """

    entryRoot = etree.XML(validateXML)
    if entryRoot is None:
        raise ValidationError("Unable to parse uploaded XML")
    # parse XML
    contentElement = entryRoot.xpath("*[local-name() = 'content']")[0]
    validateXML = contentElement.xpath("*[local-name() = 'validate']")[0]
    identifier = validateXML.xpath(
        "*[local-name() = 'identifier']")[0].text.strip()
    last_verified_status = validateXML.xpath(
        "*[local-name() = 'last_verified_status']")[0].text.strip()
    # get the object (or 404) and return to the APP view to finish up.
    validate = get_object_or_404(Validate, identifier=identifier)
    validate.last_verified_status = last_verified_status
    validate.last_verified = datetime.datetime.now()
    validate.priority = 0
    validate.save()
    return validate


def app_validate(request, identifier=None):
    """
    This method handles the ATOMpub protocol for validate objects
    """

    # are we POSTing a new identifier here?
    if request.method == 'POST' and not identifier:
        # to object
        validateObject = xmlToValidateObject(request.body)
        validateObject.save()
        # and back to xml
        validateObjectXML = validateToXML(validateObject)
        atomXML = wrapAtom(
            xml=validateObjectXML,
            id='http://%s/APP/validate/%s/' % (
                request.META['HTTP_HOST'], validateObject.identifier
            ),
            title=validateObject.identifier,
        )
        atomText = XML_HEADER % etree.tostring(atomXML, pretty_print=True)
        resp = HttpResponse(atomText, content_type="application/atom+xml")
        resp.status_code = 201
        resp['Location'] = 'http://%s/APP/validate/%s/' % \
            (request.META['HTTP_HOST'], validateObject.identifier)
    elif request.method == 'HEAD':
        resp = HttpResponse(content_type="application/atom+xml")
        resp.status_code = 200
    # if not, return a feed
    elif request.method == 'GET' and not identifier:
        # negotiate the details of our feed here
        validates = Validate.objects.all()
        page = int(request.GET['page']) if request.GET.get('page') else 1
        atomFeed = makeObjectFeed(
            paginator=Paginator(validates, 20),
            objectToXMLFunction=validateToXML,
            feedId=request.path[1:],
            webRoot='http://%s' % request.META.get('HTTP_HOST'),
            title="validate Entry Feed",
            idAttr="identifier",
            nameAttr="identifier",
            dateAttr="added",
            request=request,
            page=page,
            author={
                "name": APP_AUTHOR.get('name', None),
                "uri": APP_AUTHOR.get('uri', None)
            },
        )
        atomFeedText = XML_HEADER % etree.tostring(atomFeed, pretty_print=True)
        resp = HttpResponse(atomFeedText, content_type="application/atom+xml")
        resp.status_code = 200
    # updating an existing record
    elif request.method == 'PUT' and identifier:
        returnValidate = xmlToUpdateValidateObject(request.body)
        validateObjectXML = validateToXML(returnValidate)
        atomXML = wrapAtom(
            xml=validateObjectXML,
            id='http://%s/APP/validate/%s/' % (
                request.META['HTTP_HOST'], identifier
            ),
            title=identifier,
        )
        atomText = XML_HEADER % etree.tostring(atomXML, pretty_print=True)
        resp = HttpResponse(atomText, content_type="application/atom+xml")
        resp.status_code = 200
    elif request.method == 'GET' and identifier:
        # attempt to retrieve record -- error if unable
        try:
            validate_object = Validate.objects.get(identifier=identifier)
        except Validate.DoesNotExist:
            return HttpResponseNotFound(
                "There is no validate for identifier %s.\n" % identifier
            )
        returnValidate = validate_object
        validateObjectXML = validateToXML(returnValidate)
        atomXML = wrapAtom(
            xml=validateObjectXML,
            id='http://%s/APP/validate/%s/' % (
                request.META['HTTP_HOST'], identifier
            ),
            title=identifier,
            author=APP_AUTHOR.get('name', None),
            author_uri=APP_AUTHOR.get('uri', None)
        )
        atomText = XML_HEADER % etree.tostring(atomXML, pretty_print=True)
        resp = HttpResponse(atomText, content_type="application/atom+xml")
        resp.status_code = 200
    elif request.method == 'DELETE' and identifier:
        # attempt to retrieve record -- error if unable
        try:
            validate_object = Validate.objects.get(identifier=identifier)
        except:
            return HttpResponseNotFound(
                "Unable to Delete. There is no identifier %s.\n" % identifier)
        # grab the validate, delete it, and inform the user.
        returnValidate = validate_object
        validateObjectXML = validateToXML(returnValidate)
        validate_object.delete()
        atomXML = wrapAtom(
            xml=validateObjectXML,
            id='http://%s/APP/validate/%s/' % (
                request.META['HTTP_HOST'], identifier
            ),
            title=identifier,
        )
        atomText = XML_HEADER % etree.tostring(atomXML, pretty_print=True)
        resp = HttpResponse(atomText, content_type="application/atom+xml")
        resp.status_code = 200
    return resp


def check_json(request):
    counts = Validate.objects.last_verified_status_counts()
    return HttpResponse(json.dumps(counts), content_type='application/json')


class ValidateListView(ListView):
    model = Validate
    template_name = 'coda_validate/list.html'
    context_object_name = 'validation_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = super(ValidateListView, self).get_queryset()

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(last_verified_status=status)

        return queryset
