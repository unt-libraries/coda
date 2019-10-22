"""
WSGI config for coda project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os
import sys
import site


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV = os.path.join(BASE_DIR, 'env')
SITE_PACKAGES = os.path.join(ENV, '/lib/python3.7/site-packages')

site.addsitedir(SITE_PACKAGES)
sys.path.append(os.path.join(BASE_DIR, 'coda/'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

activate_env = os.path.join(ENV, 'bin/activate_this.py')
exec(compile(open(activate_env).read(), activate_env, 'exec'), dict(__file__=activate_env))

from django.core.wsgi import get_wsgi_application  # noqa
application = get_wsgi_application()
