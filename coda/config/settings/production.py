from .base import *  # noqa


SECRET_KEY = get_secret('SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = get_secret('ALLOWED_HOSTS')

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
