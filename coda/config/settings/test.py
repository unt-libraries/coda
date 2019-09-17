from .base import *  # noqa
import os
ALLOWED_HOSTS = ['example.com']
SECRET_KEY = 'test-secret'

SITE_ID = 1

try:
    DATABASES  # noqa
except NameError:
    DATABASES = {'default': {}}
DATABASES['default']['NAME'] = 'coda_local'
DATABASES['default']['USER'] = os.getenv('DB_MYSQL_USER', default='root')
DATABASES['default']['PASSWORD'] = os.getenv('DB_PASSWORD', default='root')
DATABASES['default']['HOST'] = os.getenv('DB_HOST', default='db')
