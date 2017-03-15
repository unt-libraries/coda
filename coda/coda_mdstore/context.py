from django.contrib.sites.models import Site


def site_info(request,):
    # stash site title on first call
    try:
        sinfo = site_info.cached_site_info
    except AttributeError:
        sinfo = site_info.cached_site_info = Site.objects.get_current()
    return {'site_title': sinfo.name}
