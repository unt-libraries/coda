from django.db import models

STATUS_CHOICES = [
    ('1', "Ready to Harvest"),
    ('2', "Currently Harvesting"),
    ('3', "Completed"),
    ('4', "Error: Digital Object Too Large"),
    ('5', "Error: Bag Verification Failed"),
    ('6', "Error: Transfer Error"),
    ('7', "Error: Duplicate Entry"),
    ('8', "Error: Unknown Error"),
    ('9', "Held"),
]


class QueueEntry(models.Model):
    """
    This defines an enqueued digital object to be "harvested"
    """

    ark = models.CharField(
        max_length=255,
        help_text="The object's ARK identifier",
        unique=True,
        db_index=True,
    )
    # let's change this storage method to a less oblique approach
    # oxum = models.CharField(
    #     max_length=128,
    #     help_text="The calculated oxum. format: <# bytes>.<# files>",
    # )
    # like this, so we can access for statistics.
    bytes = models.BigIntegerField(
        db_index=True,
        help_text="The total size of the queued entry"
    )
    files = models.IntegerField(
        help_text="The number of files that the queued entry contains",
    )
    url_list = models.TextField(
        help_text="A link to the list of urls to download",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        help_text="A message indicating the current status of the harvest",
        blank=True,
    )
    harvest_start = models.DateTimeField(
        help_text="When did the harvest start?",
        blank=True,
        null=True,
    )
    harvest_end = models.DateTimeField(
        help_text="When did the harvest finish?",
        blank=True,
        null=True,
    )
    queue_position = models.IntegerField(
        help_text="What's the priority of this particular entry?",
    )

    # and we can still have our cake like we want it.
    def oxum(self):
        return '%s.%s' % (self.bytes, self.files)
    oxum = property(oxum)

    class Meta:
        verbose_name_plural = "queue entries"
