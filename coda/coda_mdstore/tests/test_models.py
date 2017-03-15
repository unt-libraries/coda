from coda_mdstore import factories


class TestBag:

    def test_oxum(self):
        bag = factories.BagFactory.build()
        expected = '{0}.{1}'.format(bag.size, bag.files)
        assert bag.oxum == expected

    def test_unicode(self):
        bag = factories.BagFactory.build()
        assert unicode(bag) == bag.name
