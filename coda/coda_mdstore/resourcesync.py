from urlparse import urlparse
import warnings

from django.contrib.sitemaps import Sitemap, views
from django.contrib.sites.shortcuts import get_current_site
from django.core import urlresolvers
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from codalib.bagatom import TIME_FORMAT_STRING
from coda_mdstore.models import Bag

try:
    MOST_RECENT_BAGGING_DATE = Bag.objects.latest(
        'bagging_date'
    ).bagging_date.strftime(TIME_FORMAT_STRING)
except Exception, e:
    MOST_RECENT_BAGGING_DATE = '2012-12-12T00:00:00Z'


def index(
    request,
    sitemaps,
    template_name='sitemap_index.xml',
    content_type='application/xml',
    sitemap_url_name='django.contrib.sitemaps.views.sitemap',
    mimetype=None
):
    """
    This method is overloaded from django.contrib.sitemaps.views.
    we need this overload so that we can change the default method of
    pagination display in the sitemaps index. it's a bit hacky - but it works.
    """

    if mimetype:
        warnings.warn(
            "The mimetype keyword argument is deprecated, use "
            "content_type instead", DeprecationWarning, stacklevel=2
        )
        content_type = mimetype

    req_protocol = 'https' if request.is_secure() else 'http'
    req_site = get_current_site(request)

    sites = []
    for section, site in sitemaps.iteritems():
        if callable(site):
            site = site()
        protocol = req_protocol if site.protocol is None else site.protocol
        sitemap_url = urlresolvers.reverse(
                sitemap_url_name, kwargs={'section': section})
        absolute_url = '%s://%s%s' % (protocol, req_site.domain, sitemap_url)
        sites.append(absolute_url)
        for page in range(2, site.paginator.num_pages + 1):
            # we want to change how the pagination is displayed
            sites.append(
                '%s-%03d.xml' % (absolute_url.replace('-001.xml', ''), page)
            )

    return TemplateResponse(
        request,
        template_name,
        {
            'sitemaps': sites,
            'MOST_RECENT_BAGGING_DATE': MOST_RECENT_BAGGING_DATE,
        },
        content_type=content_type
    )


def sitemap(request, sitemaps, section=None,
            template_name='sitemap.xml', content_type='application/xml'):
    """
    This method is overloaded from django.contrib.sitemaps.views.
    we need this overload so that we can handle the urls served up by the other
    overloaded method above "index".
    """

    req_site = get_current_site(request)

    # since we no longer give ?p arguments,
    # we want the page to be the 'section'
    page = section
    # now, the 'section' is really the key of the sitemaps dict seen below
    section = '001'
    maps = [sitemaps[section]]
    urls = []
    for site in maps:
        try:
            if callable(site):
                site = site()
            u = site.get_urls(page=page, site=req_site)
            urls.extend(u)
        except EmptyPage:
            raise Http404("Page %s empty" % page)
        except PageNotAnInteger:
            raise Http404("No page \'%s\'" % page)
    for u in urls:
        bag_name = urlparse(u['location']).path.replace('/bag/', '')
        bag = get_object_or_404(Bag, name=bag_name)
        u.setdefault('oxum', '%s.%s' % (bag.size, bag.files))
    return TemplateResponse(
        request,
        template_name,
        {
            'urlset': urls,
            'MOST_RECENT_BAGGING_DATE': MOST_RECENT_BAGGING_DATE,
        },
        content_type=content_type
    )


def changelist(request, sitemaps, section=None,
               template_name='changelist.xml', content_type='application/xml'):
    most_recent_bags = Bag.objects.order_by('-bagging_date').values(
        'name',
        'size',
        'files',
        'bagging_date'
    )[:10000]
    for b in most_recent_bags:
        b['bagging_date'] = b['bagging_date'].strftime(TIME_FORMAT_STRING)
    return TemplateResponse(
        request,
        template_name,
        {
            'urlset': reversed(most_recent_bags),
            'MOST_RECENT_BAGGING_DATE': MOST_RECENT_BAGGING_DATE,
        },
        content_type=content_type
    )


def capabilitylist(
    request,
    template_name='mdstore/capabilitylist.xml',
    content_type='application/xml'
):
    return TemplateResponse(
        request,
        template_name,
        {
            'MOST_RECENT_BAGGING_DATE': MOST_RECENT_BAGGING_DATE,
        },
        content_type=content_type
    )


# overload the stock sitemap pagination stuff with our own methods
setattr(views, 'index', index)
setattr(views, 'sitemap', sitemap)
setattr(Sitemap, 'limit', 5000)


class BaseSitemap(Sitemap):
    lastmod = None
    protocol = 'http'

    def items(self):
        # return the list of all the bags sorted by bagging_date
        return Bag.objects.order_by('bagging_date').values('name')

    def location(self, obj):
        # if we just return the object it will give a unicode value tuple
        return "/bag/%s" % obj['name']


sitemaps = {
    '001': BaseSitemap,
}
