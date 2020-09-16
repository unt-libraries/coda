"""
Coda MDStore Model factories for test fixtures.
"""
from datetime import datetime

import factory
from factory import fuzzy

from . import models


class BagFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Bag

    name = factory.Sequence(lambda n: 'ark:/00001/id{0}'.format(n))
    files = 10
    size = 139023
    bagit_version = '3.4'
    last_verified_date = datetime.now()
    last_verified_status = 'fake status'
    bagging_date = datetime.now()


class Bag_InfoFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Bag_Info


class ExternalIdentifierFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.External_Identifier

    value = factory.Sequence(lambda n: 'value {0}'.format(n))


class FullBagFactory(BagFactory):
    """
    Factory to create a Bag object with two related Bag_Info objects, and
    two related External_Identifier objects.
    """
    info1 = factory.RelatedFactory(
        Bag_InfoFactory,
        'bag_name',
        field_name='Payload-Oxum',
        field_body='3.1400'
    )

    info2 = factory.RelatedFactory(
        Bag_InfoFactory,
        'bag_name',
        field_name='Bagging-Date',
        field_body='2015-01-01'
    )

    ext_id1 = factory.RelatedFactory(
        ExternalIdentifierFactory,
        'belong_to_bag',
    )

    ext_id2 = factory.RelatedFactory(
        ExternalIdentifierFactory,
        'belong_to_bag',
    )


class OAIBagFactory(BagFactory):
    """
    Factory for creating Bag objects with related Bag_Info objects
    that are expected from the md_store_oai module.
    """
    info1 = factory.RelatedFactory(
        Bag_InfoFactory,
        'bag_name',
        field_name='External-Description',
        field_body='Fake description'
    )

    info2 = factory.RelatedFactory(
        Bag_InfoFactory,
        'bag_name',
        field_name='Bagging-Date',
        field_body='2015-01-01'
    )

    info3 = factory.RelatedFactory(
        Bag_InfoFactory,
        'bag_name',
        field_name='Contact-Name',
        field_body='John Doe'
    )

    info4 = factory.RelatedFactory(
        Bag_InfoFactory,
        'bag_name',
        field_name='External-Identifier',
        field_body='http://example.com/bag/0001/'
    )


class NodeFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Node

    node_name = factory.Sequence(lambda n: 'coda-{0}'.format(n))
    node_url = factory.Sequence(
        lambda n: 'http://example.com/node/{0}'.format(n))
    node_path = factory.Sequence(lambda n: '/foo/bar/node/{0}'.format(n))
    node_capacity = 1024 * 1000
    node_size = 512 * 900
    status = fuzzy.FuzzyChoice(str(i) for i in range(1, 3))
    last_checked = datetime.now()
