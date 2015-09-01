import pytest

from .. import views

pytestmark = pytest.mark.django_db()


def test_index_returns_ok(rf):
    request = rf.get('/')
    response = views.index(request)
    assert response.status_code == 200
