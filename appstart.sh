#!/bin/bash
/wait-for-mysqld.sh
echo "Migrate..."
python manage.py migrate --settings=coda.config.settings
echo "Start app..."
python manage.py runserver 0.0.0.0:8787 --settings=coda.config.settings

