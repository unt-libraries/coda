from .. import factories


class TestValidate:

    def test_unicode(self):
        validate = factories.ValidateFactory.build()
        assert unicode(validate) == validate.identifier
