# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coda_mdstore', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            'CREATE FULLTEXT INDEX field_body on coda_mdstore_bag_info(field_body);',
            reverse_sql='DROP INDEX field_body on coda_mdstore_bag_info;',
        )
    ]
