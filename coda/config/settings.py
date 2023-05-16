import os
import json
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Get our secrets from a file outside of version control.
# This helps to keep the settings files generic.
with open(os.path.join(PROJECT_ROOT, 'secrets.json')) as f:
    secrets = json.loads(f.read())


def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        error_msg = 'The {0} setting is not set.'.format(setting)
        raise ImproperlyConfigured(error_msg)


DEBUG = get_secret('DEBUG')

TEST_SITE = get_secret('TEST_SITE')

ADMINS = get_secret('ADMINS')

ALLOWED_HOSTS = get_secret('ALLOWED_HOSTS')

MAINTENANCE_MSG = get_secret('MAINTENANCE_MSG')

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

USE_I18N = True

STATIC_URL = get_secret('STATIC_URL')

STATIC_ROOT = get_secret('STATIC_ROOT')

STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, 'coda', 'static')]


SITE_ID = get_secret('SITE_ID')

SECRET_KEY = get_secret('SECRET_KEY')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(PROJECT_ROOT, 'coda', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'coda_mdstore.context.site_info',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', ]

ROOT_URLCONF = 'config.urls'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Let the view know if we are in "proxy mode" or not.
# this uses the coda instance as a reverse proxy for the archival storage nodes
# setting to false sends requests directly to the archival servers.
CODA_PROXY_MODE = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': get_secret('DB_NAME'),
        'USER': get_secret('DB_USER'),
        'PASSWORD': get_secret('DB_PASSWORD'),
        'HOST': get_secret('DB_HOST'),
        'PORT': get_secret('DB_PORT'),
        'OPTIONS': {
            'init_command': 'SET default_storage_engine=MyISAM, sql_mode="STRICT_TRANS_TABLES"'
        }
    }
}

DJANGO_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.admindocs',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django.contrib.messages',
]

THIRD_PARTY_APPS = [
    'premis_event_service',
]

LOCAL_APPS = [
    'coda_mdstore',
    'coda_replication',
    'coda_oaipmh',
    'coda_validate',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

VALIDATION_PERIOD = timedelta(days=365)

ARK_NAAN = 67531

# Optional setting to indicate if we are using a proxy server that we want to
# use to reproxy requests for a bag's static data files (via bagProxy view).
try:
    REPROXY = get_secret('REPROXY')
except ImproperlyConfigured:
    REPROXY = False

if DEBUG:
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: True
    }
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
