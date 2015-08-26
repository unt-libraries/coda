from datetime import datetime

import pytest

from django.conf import settings

from .. import views, factories


pytestmark = [
    pytest.mark.urls('coda_validate.urls'),
    pytest.mark.django_db()
]


class TestAtomNextNewsFeed:

    def test_items_filters_by_server(self):
        validate = factories.ValidateFactory.create()

        feed = views.AtomNextNewsFeed()
        feed.items(validate.server)
        assert 'This selection was filtered' in feed.reason

    def test_items_chooses_oldest_validate(self):
        factories.ValidateFactory.create_batch(30, priority=1)

        feed = views.AtomNextNewsFeed()
        feed.items('')
        assert 'Item was chosen because it is the oldest' in feed.reason

    def test_items_chooses_a_random_validate(self):
        last_verified = datetime.now() - settings.VALIDATION_PERIOD
        factories.ValidateFactory.create_batch(30, priority=0, last_verified=last_verified)

        feed = views.AtomNextNewsFeed()
        feed.items('')
        assert 'randomly selected and within the past year' in feed.reason

    def test_items_chooses_unprioritized_validate(self):
        last_verified = datetime.now() + settings.VALIDATION_PERIOD
        factories.ValidateFactory.create_batch(30, priority=0, last_verified=last_verified)

        feed = views.AtomNextNewsFeed()
        feed.items('')
        assert 'there is no prioritized record and it had not been validated' in feed.reason

    def test_item_title(self):
        validate = factories.ValidateFactory.create()
        feed = views.AtomNextNewsFeed()
        title = feed.item_title(validate)
        assert title == validate.identifier

    def test_item_description(self):
        validate = factories.ValidateFactory.create()
        feed = views.AtomNextNewsFeed()
        description = feed.item_description(validate)
        assert description == feed.reason

    def test_item_link(self):
        validate = factories.ValidateFactory.create()
        feed = views.AtomNextNewsFeed()
        link = feed.item_link(validate)
        assert link == '/APP/validate/{0}/'.format(validate.identifier)
