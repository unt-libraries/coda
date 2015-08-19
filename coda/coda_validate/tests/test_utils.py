import pytest

from .. import views


@pytest.mark.parametrize('month, expected', [
    (1, 31),
    (2, 28),
    (3, 31),
    (4, 30),
    (5, 31),
    (6, 30),
    (7, 31),
    (8, 31),
    (9, 30),
    (10, 31),
    (11, 30),
    (12, 31)
])
def test_last_day_of_month(month, expected):
    assert views.last_day_of_month(2015, month) == expected


@pytest.mark.xfail
def test_xmlToValidateObject():
    assert 0


@pytest.mark.xfail
def test_xmlToUpdateValidateObject():
    assert 0


@pytest.mark.xfail
def test_validateToXML():
    assert 0
