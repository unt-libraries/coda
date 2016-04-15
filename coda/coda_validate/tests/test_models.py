import pytest

from .. import factories
from ..models import ValidateManager, Validate


class TestValidate:

    def test_unicode(self):
        validate = factories.ValidateFactory.build()
        assert unicode(validate) == validate.identifier


@pytest.mark.django_db
class TestValidateManager(object):

    def test_last_verified_status_counts(self):
        factories.ValidateFactory.create_batch(3, last_verified_status='Passed')
        factories.ValidateFactory.create_batch(5, last_verified_status='Failed')
        factories.ValidateFactory.create_batch(7, last_verified_status='Unverified')

        manager = ValidateManager()
        manager.model = Validate

        counts = manager.last_verified_status_counts()
        assert counts['Passed'] == 3
        assert counts['Failed'] == 5
        assert counts['Unverified'] == 7

    def test_last_verified_status_counts_are_zero(self):
        manager = ValidateManager()
        manager.model = Validate

        counts = manager.last_verified_status_counts()
        assert counts['Passed'] == 0
        assert counts['Failed'] == 0
        assert counts['Unverified'] == 0
