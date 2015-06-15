from .base import *

SITE_ID = 1

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
