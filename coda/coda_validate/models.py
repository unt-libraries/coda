from django.db import models
from datetime import datetime

# Create your models here.
class Validate(models.Model):
    VERIFIED_STATUS_CHOICES = (
        ("Unverified", "Unverified"),
        ("Passed", "Passed"),
        ("Failed", "Failed"),
    )
    identifier = models.CharField(max_length=255, unique=True, editable=False)
    added = models.DateTimeField(auto_now_add=True)
    last_verified = models.DateTimeField(default=datetime(2000,01,01))
    last_verified_status = models.CharField(
        max_length=25, choices=VERIFIED_STATUS_CHOICES, default="Unverified"
    )
    priority_change_date = models.DateTimeField(default=datetime(2000,01,01))
    priority = models.IntegerField(max_length=1, default=0)
    server = models.CharField(max_length=255)

    def __unicode__(self):
        return '%s' % self.identifier

    class Meta:
        verbose_name_plural = "Validations"
        ordering = ['added']
