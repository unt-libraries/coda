from .base import *

SECRET_KEY = 'test-secret'

SITE_ID = 1

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'coda_local',
        'USER': os.getenv('DB_MYSQL_USER', default='root'),
        'PASSWORD': os.getenv('DB_PASSWORD', default='root'),
        'HOST': os.getenv('DB_HOST', default='db'),
    }
}
