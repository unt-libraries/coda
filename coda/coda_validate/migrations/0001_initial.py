# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Validate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(unique=True, max_length=255, editable=False)),
                ('added', models.DateTimeField(auto_now_add=True)),
                ('last_verified', models.DateTimeField(default=datetime.datetime(2000, 1, 1, 0, 0))),
                ('last_verified_status', models.CharField(default=b'Unverified', max_length=25, choices=[(b'Unverified', b'Unverified'), (b'Passed', b'Passed'), (b'Failed', b'Failed')])),
                ('priority_change_date', models.DateTimeField(default=datetime.datetime(2000, 1, 1, 0, 0))),
                ('priority', models.IntegerField(default=0)),
                ('server', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['added'],
                'verbose_name_plural': 'Validations',
            },
        ),
    ]
