import factory

from datetime import datetime

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


class NodeFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Node

    node_name = factory.Sequence(lambda n: 'coda-{0}'.format(n))
    node_url = factory.Sequence(
        lambda n: 'http://example.com/node/{0}'.format(n))
    node_path = factory.Sequence(lambda n: '/foo/bar/node/{0}'.format(n))
    node_capacity = 1024 * 1000
    node_size = 512 * 900
    last_checked = datetime.now()
