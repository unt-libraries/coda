# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-08-31 14:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('coda_mdstore', '0001_initial'), ('coda_mdstore', '0002_add_fulltext_index'), ('coda_mdstore', '0003_auto_20191022_0935')]

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bag',
            fields=[
                ('name', models.CharField(help_text=b'Name of Bag', max_length=255, primary_key=True, serialize=False)),
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
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(db_index=True, help_text=b'Field Name', max_length=255)),
                ('field_body', models.TextField(help_text=b'Field Body')),
                ('bag_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='coda_mdstore.Bag')),
            ],
            options={
                'verbose_name_plural': 'Bag Info Fields',
            },
        ),
        migrations.CreateModel(
            name='External_Identifier',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(db_index=True, max_length=250)),
                ('belong_to_bag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='coda_mdstore.Bag')),
            ],
            options={
                'ordering': ['value'],
            },
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_name', models.CharField(db_index=True, help_text=b'The name of the node', max_length=255, unique=True)),
                ('node_url', models.TextField(help_text=b'The external url for the root of the node')),
                ('node_path', models.CharField(help_text=b"The path on disk to the node's root", max_length=255)),
                ('node_capacity', models.BigIntegerField(blank=True, help_text=b'The total amount of storage (in bytes)')),
                ('node_size', models.BigIntegerField(blank=True, help_text=b'The current size of files on disk (in bytes)')),
                ('last_checked', models.DateTimeField(blank=True, help_text=b'Date node size last checked')),
            ],
        ),
        migrations.RunSQL(
            sql='CREATE FULLTEXT INDEX field_body on coda_mdstore_bag_info(field_body);',
            reverse_sql='DROP INDEX field_body on coda_mdstore_bag_info;',
        ),
        migrations.AlterField(
            model_name='bag',
            name='bagging_date',
            field=models.DateField(help_text='Date of Bag Creation'),
        ),
        migrations.AlterField(
            model_name='bag',
            name='bagit_version',
            field=models.CharField(help_text='BagIt version number', max_length=10),
        ),
        migrations.AlterField(
            model_name='bag',
            name='files',
            field=models.IntegerField(help_text='Number of files in Bag'),
        ),
        migrations.AlterField(
            model_name='bag',
            name='last_verified_date',
            field=models.DateField(help_text='Date of last Bag Verification'),
        ),
        migrations.AlterField(
            model_name='bag',
            name='last_verified_status',
            field=models.CharField(help_text='Status of last bag Verification', max_length=25),
        ),
        migrations.AlterField(
            model_name='bag',
            name='name',
            field=models.CharField(help_text='Name of Bag', max_length=255, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='bag',
            name='size',
            field=models.BigIntegerField(help_text="Size of Bag's Payload (in bytes)"),
        ),
        migrations.AlterField(
            model_name='bag_info',
            name='field_body',
            field=models.TextField(help_text='Field Body'),
        ),
        migrations.AlterField(
            model_name='bag_info',
            name='field_name',
            field=models.CharField(db_index=True, help_text='Field Name', max_length=255),
        ),
        migrations.AlterField(
            model_name='node',
            name='last_checked',
            field=models.DateTimeField(blank=True, help_text='Date node size last checked'),
        ),
        migrations.AlterField(
            model_name='node',
            name='node_capacity',
            field=models.BigIntegerField(blank=True, help_text='The total amount of storage (in bytes)'),
        ),
        migrations.AlterField(
            model_name='node',
            name='node_name',
            field=models.CharField(db_index=True, help_text='The name of the node', max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='node',
            name='node_path',
            field=models.CharField(help_text="The path on disk to the node's root", max_length=255),
        ),
        migrations.AlterField(
            model_name='node',
            name='node_size',
            field=models.BigIntegerField(blank=True, help_text='The current size of files on disk (in bytes)'),
        ),
        migrations.AlterField(
            model_name='node',
            name='node_url',
            field=models.TextField(help_text='The external url for the root of the node'),
        ),
    ]