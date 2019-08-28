# Base settings for coda
import os
import json
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured

# Absolute path to the settings module
SETTINGS_ROOT = os.path.dirname(__file__)

# Absolute path to the config app
CONFIG_ROOT = os.path.dirname(SETTINGS_ROOT)

# Absolute path to the site directory
SITE_ROOT = os.path.dirname(CONFIG_ROOT)

# Absolute path to the root of the project
PROJECT_ROOT = os.path.dirname(SITE_ROOT)


# Compose a path from the project root
def _project_path(path):
    return os.path.join(CONFIG_ROOT, path)


project_path = _project_path


# Compose path from the site root
def _site_path(path):
    return os.path.join(SITE_ROOT, path)


site_path = _site_path


# Get our secrets from a file outside of version control.
# This helps to keep the settings files generic.
with open(os.path.join(PROJECT_ROOT, "secrets.json")) as f:
    secrets = json.loads(f.read())


def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        error_msg = "The {0} setting is not set.".format(setting)
        raise ImproperlyConfigured(error_msg)


DEBUG = True

MAINTENANCE_MSG = get_secret("MAINTENANCE_MSG")

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

USE_I18N = True

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(SITE_ROOT, 'static')]


SECRET_KEY = get_secret("SECRET_KEY")

DATABASES = {
    'default': {
        'NAME': get_secret("DB_NAME"),
        'USER': get_secret("DB_USER"),
        'ENGINE': 'django.db.backends.mysql',
        'PASSWORD': get_secret("DB_PASSWORD"),
        'HOST': get_secret("DB_HOST"),
        'PORT': get_secret("DB_PORT"),
        'OPTIONS': {
            'init_command': 'SET default_storage_engine=MyISAM'
        }
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            site_path('templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'coda_mdstore.context.site_info',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
            ],
        },
    },
]

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', ]

ROOT_URLCONF = 'config.urls'

# Let the view know if we are in "proxy mode" or not.
# this uses the coda instance as a reverse proxy for the archival storage nodes
# setting to false sends requests directly to the archival servers.
CODA_PROXY_MODE = False

DJANGO_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.admindocs',
    'django.contrib.admin',
    'django.contrib.humanize', ]

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
