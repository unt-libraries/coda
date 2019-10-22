# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2019-10-22 09:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coda_replication', '0002_auto_20190829_1058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queueentry',
            name='ark',
            field=models.CharField(db_index=True, help_text="The object's ARK identifier", max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='queueentry',
            name='bytes',
            field=models.BigIntegerField(db_index=True, help_text='The total size of the queued entry'),
        ),
        migrations.AlterField(
            model_name='queueentry',
            name='files',
            field=models.IntegerField(help_text='The number of files that the queued entry contains'),
        ),
        migrations.AlterField(
            model_name='queueentry',
            name='harvest_end',
            field=models.DateTimeField(blank=True, help_text='When did the harvest finish?', null=True),
        ),
        migrations.AlterField(
            model_name='queueentry',
            name='harvest_start',
            field=models.DateTimeField(blank=True, help_text='When did the harvest start?', null=True),
        ),
        migrations.AlterField(
            model_name='queueentry',
            name='queue_position',
            field=models.IntegerField(help_text="What's the priority of this particular entry?"),
        ),
        migrations.AlterField(
            model_name='queueentry',
            name='status',
            field=models.CharField(blank=True, choices=[('1', 'Ready to Harvest'), ('2', 'Currently Harvesting'), ('3', 'Completed'), ('4', 'Error: Digital Object Too Large'), ('5', 'Error: Bag Verification Failed'), ('6', 'Error: Transfer Error'), ('7', 'Error: Duplicate Entry'), ('8', 'Error: Unknown Error'), ('9', 'Held'), ('', 'None')], help_text='A message indicating the current status of the harvest', max_length=10),
        ),
        migrations.AlterField(
            model_name='queueentry',
            name='url_list',
            field=models.TextField(help_text='A link to the list of urls to download'),
        ),
    ]