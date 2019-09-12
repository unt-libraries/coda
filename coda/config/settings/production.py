from .base import *  # noqa
from .base import get_secret  # being explicit here


SITE_ID = get_secret('SITE_ID')

SECRET_KEY = get_secret('SECRET_KEY')

DEBUG = True

ALLOWED_HOSTS = get_secret('ALLOWED_HOSTS')
ALLOWED_HOSTS += ['example.com']
ADMINS = get_secret('ADMINS')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': get_secret('DB_NAME'),
        'USER': get_secret('DB_USER'),
        'PASSWORD': get_secret('DB_PASSWORD'),
        'HOST': get_secret('DB_HOST'),
        'PORT': get_secret('DB_PORT'),
    }
}

STATIC_URL = get_secret('STATIC_URL')

STATIC_ROOT = get_secret('STATIC_ROOT')
