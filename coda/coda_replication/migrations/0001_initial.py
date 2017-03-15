# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='QueueEntry',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID',
                        serialize=False,
                        auto_created=True,
                        primary_key=True
                    )
                ),
                (
                    'ark',
                    models.CharField(
                        help_text=b"The object's ARK identifier",
                        unique=True,
                        max_length=255,
                        db_index=True
                    )
                ),
                (
                    'bytes',
                    models.BigIntegerField(
                        help_text=b'The total size of the queued entry',
                        db_index=True
                    )
                ),
                (
                    'files',
                    models.IntegerField(
                        help_text=b'The number of files that the queued entry ' +
                                  'contains'
                    )
                ),
                (
                    'url_list',
                    models.TextField(
                        help_text=b'A link to the list of urls to download'
                    )
                ),
                (
                    'status',
                    models.CharField(
                        blank=True,
                        help_text=b'A message indicating the current status ' +
                                  'of the harvest',
                        max_length=10,
                        choices=[
                            (b'1', b'Ready to Harvest'),
                            (b'2', b'Currently Harvesting'),
                            (b'3', b'Completed'),
                            (b'4', b'Error: Digital Object Too Large'),
                            (b'5', b'Error: Bag Verification Failed'),
                            (b'6', b'Error: Transfer Error'),
                            (b'7', b'Error: Duplicate Entry'),
                            (b'8', b'Error: Unknown Error'),
                            (b'9', b'Held'),
                            (b'', b'None')
                        ]
                    )
                ),
                (
                    'harvest_start',
                    models.DateTimeField(
                        help_text=b'When did the harvest start?',
                        null=True, blank=True
                    )
                ),
                (
                    'harvest_end',
                    models.DateTimeField(
                        help_text=b'When did the harvest finish?',
                        null=True, blank=True
                    )
                ),
                (
                    'queue_position',
                    models.IntegerField(
                        help_text=b"What's the priority of this particular entry?"
                    )
                ),
            ],
        ),
    ]
