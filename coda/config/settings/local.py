from .base import *


SECRET_KEY = 'local-secret'

SITE_ID = 1

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: True
}

INSTALLED_APPS += ('debug_toolbar',)


# Database settings for the Dockerized dev environment.
# See docker-compose.yml
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': "coda_local",
        'USER': "root",
        'PASSWORD': "root",
        'HOST': "db",
    }
}
