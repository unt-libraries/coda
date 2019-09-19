from django.db import models


class Bag(models.Model):
    name = models.CharField(
        max_length=255,
        primary_key=True,
        help_text='Name of Bag')

    files = models.IntegerField(
        help_text='Number of files in Bag')

    size = models.BigIntegerField(
        help_text="Size of Bag's Payload (in bytes)")

    bagit_version = models.CharField(
        max_length=10,
        help_text='BagIt version number')

    last_verified_date = models.DateField(
        help_text='Date of last Bag Verification')

    last_verified_status = models.CharField(
        max_length=25,
        help_text='Status of last bag Verification')

    bagging_date = models.DateField(
        help_text='Date of Bag Creation')

    @property
    def oxum(self):
        return '{size}.{files}'.format(**vars(self))

    def __unicode__(self):
        return self.name


class Bag_Info(models.Model):
    bag_name = models.ForeignKey(Bag, on_delete=models.CASCADE)
    field_name = models.CharField(
        max_length=255,
        help_text="Field Name",
        db_index=True
    )
    field_body = models.TextField(
        help_text="Field Body"
    )

    def __unicode__(self):
        return "%s:%s" % (self.bag_name, self.field_name)

    class Meta:
        verbose_name_plural = "Bag Info Fields"


class Node(models.Model):
    """
    This model defines a storage node for the mdstore
    """

    node_name = models.CharField(
        max_length=255,
        help_text="The name of the node",
        unique=True,
        db_index=True
    )
    node_url = models.TextField(
        help_text="The external url for the root of the node")
    node_path = models.CharField(
        max_length=255, help_text="The path on disk to the node's root")
    node_capacity = models.BigIntegerField(
        help_text="The total amount of storage (in bytes)", blank=True)
    node_size = models.BigIntegerField(
        help_text="The current size of files on disk (in bytes)", blank=True)
    last_checked = models.DateTimeField(
        help_text="Date node size last checked", blank=True)


class External_Identifier(models.Model):
    value = models.CharField(max_length=250, db_index=True)
    belong_to_bag = models.ForeignKey(Bag, on_delete=models.CASCADE)

    class Meta:
        ordering = ['value']

    def __unicode__(self):
        return self.value
