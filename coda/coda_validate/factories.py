"""Coda Validate Model factories for test fixtures."""
from datetime import datetime, timedelta

import factory
from factory import fuzzy

from .models import Validate


SERVERS = ['arch01.example.com', 'arch02.example.com', 'arch03.example.com']


class ValidateFactory(factory.django.DjangoModelFactory):
    identifier = factory.Sequence(lambda n: 'ark:/00001/id{0}'.format(n))
    last_verified = fuzzy.FuzzyNaiveDateTime(datetime.now())
    last_verified_status = fuzzy.FuzzyChoice(i for i, v in Validate.VERIFIED_STATUS_CHOICES)
    priority_change_date = fuzzy.FuzzyNaiveDateTime(datetime.now() - timedelta(days=5))
    priority = fuzzy.FuzzyInteger(0, 9)
    server = fuzzy.FuzzyChoice(SERVERS)

    class Meta:
        model = Validate
