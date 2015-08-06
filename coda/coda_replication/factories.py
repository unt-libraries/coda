"""
Coda Replication Model factories for test fixtures.
"""
from datetime import datetime

import factory
from factory import fuzzy

from . import models


class QueueEntryFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.QueueEntry

    ark = factory.Sequence(lambda n: 'ark:/00001/id{0}'.format(n))
    bytes = fuzzy.FuzzyInteger(100000000)
    files = fuzzy.FuzzyInteger(50, 500)
    url_list = fuzzy.FuzzyText(length=500)
    status = fuzzy.FuzzyChoice(str(i) for i in range(1, 10))
    harvest_start = fuzzy.FuzzyNaiveDateTime(datetime(2015, 01, 01))
    harvest_end = fuzzy.FuzzyNaiveDateTime(datetime(2015, 06, 01))
    queue_position = fuzzy.FuzzyInteger(1, 100)
