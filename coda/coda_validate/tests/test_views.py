import json

import pytest

from django.core.urlresolvers import reverse
from django import http

from .. import factories
from .. import views
from ..models import Validate

pytestmark = pytest.mark.django_db


class TestIndex:
    """
    Tests for coda_validate.views.index.
    """

    def test_status_ok(self, rf):
        factories.ValidateFactory.create_batch(30)
        request = rf.get('/')
        response = views.index(request)
        assert response.status_code == 200

    def test_status_ok_without_validate_objects(self, rf):
        request = rf.get('/')
        response = views.index(request)
        assert response.status_code == 200

    def test_context(self, client):
        factories.ValidateFactory.create_batch(30)
        response = client.get(reverse('coda_validate.views.index'))
        context = response.context[-1]
        assert len(context['recently_prioritized']) == 20
        assert len(context['recently_verified']) == 20

    def test_context_without_validate_objects(self, client):
        response = client.get(reverse('coda_validate.views.index'))
        context = response.context[-1]
        assert len(context['recently_prioritized']) == 0
        assert len(context['recently_verified']) == 0


class TestStats:
    """
    Tests for coda_validate.views.stats.
    """

    def test_status_ok(self, rf):
        factories.ValidateFactory.create_batch(30)
        request = rf.get('/')
        response = views.stats(request)
        assert response.status_code == 200

    def test_status_ok_without_validate_objects(self, rf):
        request = rf.get('/')
        response = views.stats(request)
        assert response.status_code == 200

    def test_context(self, client):
        factories.ValidateFactory.create_batch(30)
        response = client.get(reverse('coda_validate.views.stats'))
        context = response.context[-1]

        # Test the context variables for truthiness.
        # TODO: Many of these values are dependent on datetimes and complex
        # queries. Testing them within the view is not practical.
        assert context['sums_by_date']
        assert context['validations']
        assert context['this_month']
        assert context['last_24h']
        assert context['last_vp']
        assert context['unverified']
        assert context['passed']
        assert context['failed']

    def test_context_without_validate_objects(self, client):
        response = client.get(reverse('coda_validate.views.stats'))
        context = response.context[-1]

        assert not context['sums_by_date']
        assert not context['validations']
        assert not context['this_month']
        assert not context['last_24h']
        assert not context['last_vp']
        assert not context['unverified']
        assert not context['passed']
        assert not context['failed']


class TestPrioritize:
    """
    Tests for coda_validate.views.prioritize.
    """

    def test_raises_http404(self, rf):
        request = rf.get('/', {'identifier': 'dne'})

        with pytest.raises(http.Http404):
            views.prioritize(request)

    def test_returns_ok_with_identifier(self, rf):
        validate = factories.ValidateFactory.create()
        request = rf.get('/', {'identifier': validate.identifier})
        response = views.prioritize(request)
        assert response.status_code == 200

    def test_returns_ok_without_identifier(request, rf):
        request = rf.get('/')
        response = views.prioritize(request)
        assert response.status_code == 200

    def test_updates_validate_priority(request, rf):
        validate = factories.ValidateFactory.create(priority=3)
        request = rf.get('/', {'identifier': validate.identifier})
        views.prioritize(request)

        updated_validate = Validate.objects.get(identifier=validate.identifier)
        assert updated_validate.priority_change_date > validate.priority_change_date
        assert updated_validate.priority == 1

    def test_context_with_identifier(self, client):
        validate = factories.ValidateFactory.create()
        response = client.get(
            reverse('coda_validate.views.prioritize'),
            {'identifier': validate.identifier})

        context = response.context[-1]
        assert context['prioritized'] is True
        assert context['identifier'] == validate.identifier

    def test_context_without_identifier(self, client):
        response = client.get(reverse('coda_validate.views.prioritize'))
        context = response.context[-1]
        assert context['prioritized'] is False
        assert context['identifier'] is None


class TestValidate:
    """
    Tests for coda_validate.views.validate.
    """

    def test_raises_http404(self, rf):
        request = rf.get('/')

        with pytest.raises(http.Http404):
            views.validate(request, 'dne')

    def test_returns_ok(self, rf):
        validate = factories.ValidateFactory.create()
        request = rf.get('/')
        response = views.validate(request, validate.identifier)
        assert response.status_code == 200

    def test_context(self, client):
        validate = factories.ValidateFactory.create()
        response = client.get(
            reverse('coda_validate.views.validate', args=[validate.identifier]))

        context = response.context[-1]
        assert context.get('validate').identifier == validate.identifier

    def test_priority_was_updated(self, client):
        validate = factories.ValidateFactory.create(priority=3)
        client.get(
            reverse('coda_validate.views.validate', args=[validate.identifier]),
            {'priority': 1})

        updated_validate = Validate.objects.get(identifier=validate.identifier)
        assert updated_validate.priority == 1

    def test_priority_was_not_updated(self, client):
        validate = factories.ValidateFactory.create(priority=3)
        client.get(
            reverse('coda_validate.views.validate', args=[validate.identifier]),
            {'priority': 2})

        updated_validate = Validate.objects.get(identifier=validate.identifier)
        assert updated_validate.priority == validate.priority


class TestPrioritizeJson:
    """
    Tests for coda_validate.views.prioritize_json.
    """

    def test_returns_ok_with_identifier(self, rf):
        validate = factories.ValidateFactory.create()
        request = rf.get('/', {'identifier': validate.identifier})
        response = views.prioritize_json(request)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    def test_returns_ok_with_invalid_identifier(self, rf):
        request = rf.get('/', {'identifier': 'dne'})
        response = views.prioritize_json(request)
        assert response.status_code == 404
        assert response['Content-Type'] == 'application/json'

    def test_returns_ok_without_identifier(self, rf):
        request = rf.get('/')
        response = views.prioritize_json(request)
        assert response.status_code == 400
        assert response['Content-Type'] == 'application/json'

    def test_json_response_with_identifier(self, rf):
        validate = factories.ValidateFactory.create()
        request = rf.get('/', {'identifier': validate.identifier})
        response = views.prioritize_json(request)
        data = json.loads(response.content)

        updated_validate = Validate.objects.get(identifier=validate.identifier)

        assert data.get('status') == 'success'
        assert data.get('priority') == updated_validate.priority
        assert data.get('priority_change_date')
        assert data.get('atom_pub_url')

    def test_json_response_with_invalid_identifier(self, rf):
        request = rf.get('/', {'identifier': 'dne'})
        response = views.prioritize_json(request)
        data = json.loads(response.content)

        assert data.get('response') == 'identifier was not found'
        assert data.get('requested_identifier') == 'dne'

    def test_json_response_without_identifier(self, rf):
        request = rf.get('/')
        response = views.prioritize_json(request)
        data = json.loads(response.content)

        assert data.get('response') == 'missing identifier parameter'
        assert data.get('requested_identifier') == ''
