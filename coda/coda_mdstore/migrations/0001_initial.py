# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bag',
            fields=[
                ('name', models.CharField(help_text=b'Name of Bag', max_length=255, serialize=False, primary_key=True)),
                ('files', models.IntegerField(help_text=b'Number of files in Bag')),
                ('size', models.BigIntegerField(help_text=b"Size of Bag's Payload (in bytes)")),
                ('bagit_version', models.CharField(help_text=b'BagIt version number', max_length=10)),
                ('last_verified_date', models.DateField(help_text=b'Date of last Bag Verification')),
                ('last_verified_status', models.CharField(help_text=b'Status of last bag Verification', max_length=25)),
                ('bagging_date', models.DateField(help_text=b'Date of Bag Creation')),
            ],
        ),
        migrations.CreateModel(
            name='Bag_Info',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field_name', models.CharField(help_text=b'Field Name', max_length=255, db_index=True)),
                ('field_body', models.TextField(help_text=b'Field Body')),
                ('bag_name', models.ForeignKey(to='coda_mdstore.Bag')),
            ],
            options={
                'verbose_name_plural': 'Bag Info Fields',
            },
        ),
        migrations.CreateModel(
            name='External_Identifier',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=250, db_index=True)),
                ('belong_to_bag', models.ForeignKey(to='coda_mdstore.Bag')),
            ],
            options={
                'ordering': ['value'],
            },
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('node_name', models.CharField(help_text=b'The name of the node', unique=True, max_length=255, db_index=True)),
                ('node_url', models.TextField(help_text=b'The external url for the root of the node')),
                ('node_path', models.CharField(help_text=b"The path on disk to the node's root", max_length=255)),
                ('node_capacity', models.BigIntegerField(help_text=b'The total amount of storage (in bytes)', blank=True)),
                ('node_size', models.BigIntegerField(help_text=b'The current size of files on disk (in bytes)', blank=True)),
                ('last_checked', models.DateTimeField(help_text=b'Date node size last checked', blank=True)),
            ],
        ),
    ]
