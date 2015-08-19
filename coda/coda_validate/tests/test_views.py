import json

from lxml import objectify
import pytest

from django.core.urlresolvers import reverse
from django import http

from .. import factories
from .. import views
from ..models import Validate

VALIDATE_XML = '{http://digital2.library.unt.edu/coda/validatexml/}validate'

pytestmark = [
    pytest.mark.urls('coda_validate.urls'),
    pytest.mark.django_db
]


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

    def test_template_used(self, client):
        response = client.get(reverse('coda_validate.views.index'))
        assert response.template[0].name == 'coda_validate/index.html'

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

    def test_template_used(self, client):
        response = client.get(reverse('coda_validate.views.stats'))
        assert response.template[0].name == 'coda_validate/stats.html'

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

    def test_template_used(self, client):
        response = client.get(reverse('coda_validate.views.prioritize'))
        assert response.template[0].name == 'coda_validate/prioritize.html'

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

    def test_returns_not_found_with_invalid_identifier(self, rf):
        request = rf.get('/', {'identifier': 'dne'})
        response = views.prioritize_json(request)
        assert response.status_code == 404
        assert response['Content-Type'] == 'application/json'

    def test_returns_bad_request_without_identifier(self, rf):
        request = rf.get('/')
        response = views.prioritize_json(request)
        assert response.status_code == 400
        assert response['Content-Type'] == 'application/json'

    def test_json_response_content_with_identifier(self, rf):
        validate = factories.ValidateFactory.create()
        request = rf.get('/', {'identifier': validate.identifier})
        response = views.prioritize_json(request)
        data = json.loads(response.content)

        updated_validate = Validate.objects.get(identifier=validate.identifier)

        assert data.get('status') == 'success'
        assert data.get('priority') == updated_validate.priority
        assert data.get('priority_change_date')
        assert data.get('atom_pub_url')

    def test_json_response_content_with_invalid_identifier(self, rf):
        request = rf.get('/', {'identifier': 'dne'})
        response = views.prioritize_json(request)
        data = json.loads(response.content)

        assert data.get('response') == 'identifier was not found'
        assert data.get('requested_identifier') == 'dne'

    def test_json_response_content_without_identifier(self, rf):
        request = rf.get('/')
        response = views.prioritize_json(request)
        data = json.loads(response.content)

        assert data.get('response') == 'missing identifier parameter'
        assert data.get('requested_identifier') == ''


class TestAppValidate:

    @pytest.fixture
    def validate_xml(self):
        return """<?xml version="1.0"?>
            <entry xmlns="http://www.w3.org/2005/Atom">
            <title>ark:/00001/codajom1</title>
            <id>http://example.com/APP/validate/ark:/00001/codajom1/</id>
            <updated>2015-08-17T17:13:07Z</updated>
            <author>
                <name>Coda</name>
                <uri>http://digital2.library.unt.edu/name/nm0004311/</uri>
            </author>
            <content type="application/xml">
                <v:validate xmlns:v="http://digital2.library.unt.edu/coda/validatexml/">
                    <v:identifier>ark:/00001/codajom1</v:identifier>
                    <v:last_verified>2015-01-01 12:11:43</v:last_verified>
                    <v:last_verified_status>Passed</v:last_verified_status>
                    <v:priority_change_date>2000-01-01 00:00:00</v:priority_change_date>
                    <v:priority>0</v:priority>
                    <v:server>arch01.example.com</v:server>
                </v:validate>
            </content>
            </entry>
        """

    def test_post_returns_created(self, validate_xml, rf):
        request = rf.post('/', validate_xml, 'application/xml', HTTP_HOST='example.com')
        response = views.app_validate(request)

        assert response.status_code == 201
        assert response['Location']
        assert response['Content-Type'] == 'application/atom+xml'

        response_xml = objectify.fromstring(response.content)
        assert len(response_xml)

    def test_post_creates_a_new_validate(self, validate_xml, rf):
        assert Validate.objects.count() == 0

        request = rf.post('/', validate_xml, 'application/xml', HTTP_HOST='example.com')
        views.app_validate(request)

        assert Validate.objects.count() == 1

    def test_head_returns_ok(self, validate_xml, rf):
        request = rf.head('/')
        response = views.app_validate(request)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

    def test_get_with_identifier_returns_ok(self, rf):
        validate = factories.ValidateFactory.create(identifier='ark:/00001/codadof3')

        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_validate(request, validate.identifier)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

        response_xml = objectify.fromstring(response.content)
        assert len(response_xml)

    def test_get_with_identifier_returns_not_found(self, rf):
        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_validate(request, 'ark:/00001/dne')
        assert response.status_code == 404

    def test_get_without_identifier_returns_ok(self, rf):
        factories.ValidateFactory.create_batch(30)

        request = rf.get('/', HTTP_HOST='example.com')
        response = views.app_validate(request)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

        response_xml = objectify.fromstring(response.content)
        assert len(response_xml.entry) == 20

    def test_put_returns_ok(self, validate_xml, rf):
        validate = factories.ValidateFactory.create(identifier='ark:/00001/codajom1')

        request = rf.put('/', validate_xml, 'application/xml', HTTP_HOST='example.com')
        response = views.app_validate(request, validate.identifier)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

        response_xml = objectify.fromstring(response.content)
        assert len(response_xml)

    def test_delete_returns_ok(self, rf):
        validate = factories.ValidateFactory.create(identifier='ark:/00001/codajom1')

        request = rf.delete('/', HTTP_HOST='example.com')
        response = views.app_validate(request, validate.identifier)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/atom+xml'

        response_xml = objectify.fromstring(response.content)
        assert len(response_xml)

    def test_delete_returns_not_found(self, rf):
        request = rf.delete('/', HTTP_HOST='example.com')
        response = views.app_validate(request, 'ark:/00001/dne')
        assert response.status_code == 404

    def test_delete_removes_validate_object(self, rf):
        validate = factories.ValidateFactory.create(identifier='ark:/00001/codajom1')
        assert Validate.objects.count() == 1

        request = rf.delete('/', HTTP_HOST='example.com')
        views.app_validate(request, validate.identifier)

        assert Validate.objects.count() == 0

    @pytest.mark.xfail(reason='Invalid request is not properly handled.')
    def test_invalid_method_and_identifier_returns_bad_request(self, rf):
        request = rf.put('/', HTTP_HOST='example.com')
        response = views.app_validate(request)
        assert response.status_code == 400
