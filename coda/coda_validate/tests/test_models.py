import pytest

from coda_validate import factories
from coda_validate.models import (
    ValidateManager,
    Validate,
    VerifiedCountsResultFormatter)


class TestValidate:

    def test_str(self):
        validate = factories.ValidateFactory.build()
        assert str(validate) == validate.identifier


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


class TestLastVerifiedStatusFormatter(object):

    def test_format(self):
        results = [{'last_verified_status': 'Failed', 'count': 3}]
        formatter = VerifiedCountsResultFormatter(results)
        formatted_results = formatter.format()

        expected = {'Failed': 3, 'Passed': 0, 'Unverified': 0}

        assert formatted_results == expected

    def test_format_with_empty_result_set(self):
        results = []
        formatter = VerifiedCountsResultFormatter(results)
        formatted_results = formatter.format()

        expected = {'Failed': 0, 'Passed': 0, 'Unverified': 0}

        assert formatted_results == expected
