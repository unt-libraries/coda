from .base import *  # noqa


SECRET_KEY = 'local-secret'

SITE_ID = 1

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: True
}

try:
    INSTALLED_APPS  # noqa
except NameError:
    INSTALLED_APPS = []
INSTALLED_APPS += ['debug_toolbar']


# Database settings for the Dockerized dev environment.
# See docker-compose.yml
try:
    DATABASES  # noqa
except NameError:
    DATABASES = {'default': {}}
DATABASES['default']['NAME'] = 'coda_local'
DATABASES['default']['USER'] = 'root'
DATABASES['default']['PASSWORD'] = 'root'
DATABASES['default']['HOST'] = 'db'
