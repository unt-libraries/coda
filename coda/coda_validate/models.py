from django.db import models
from datetime import datetime


class ValidateManager(models.Manager):

    def last_verified_status_counts(self):
        results = self._verified_counts()
        results = self._format_count_results(results)
        return self._set_default_status_counts(results)

    def _set_default_status_counts(self, counts):
        for _, value in Validate.VERIFIED_STATUS_CHOICES:
            counts.setdefault(value, 0)
        return counts

    def _format_count_results(self, results):
        return {
            c['last_verified_status']: c['count']
            for c in results
        }

    def _verified_counts(self):
        return (self.values('last_verified_status')
                    .annotate(count=models.Count('last_verified_status')))


class Validate(models.Model):
    VERIFIED_STATUS_CHOICES = (
        ("Unverified", "Unverified"),
        ("Passed", "Passed"),
        ("Failed", "Failed"),
    )
    identifier = models.CharField(max_length=255, unique=True, editable=False)
    added = models.DateTimeField(auto_now_add=True)
    last_verified = models.DateTimeField(default=datetime(2000, 1, 1))
    last_verified_status = models.CharField(
        max_length=25, choices=VERIFIED_STATUS_CHOICES, default="Unverified"
    )
    priority_change_date = models.DateTimeField(default=datetime(2000, 1, 1))
    priority = models.IntegerField(default=0)
    server = models.CharField(max_length=255)

    objects = ValidateManager()

    def __unicode__(self):
        return '%s' % self.identifier

    class Meta:
        verbose_name_plural = "Validations"
        ordering = ['added']
