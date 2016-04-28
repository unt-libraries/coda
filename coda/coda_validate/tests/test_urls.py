from django.core.urlresolvers import resolve

from .. import views


def test_app_validate():
    assert resolve('/APP/validate/ark:/00001/codajom1/').func == views.app_validate


def test_app_validate_collection():
    assert resolve('/APP/validate/').func == views.app_validate


def test_index():
    assert resolve('/validate/').func == views.index


def test_ValidateListView():
    assert resolve('/validate/list/').func.__name__ == views.ValidateListView.as_view().__name__


def test_check_json():
    assert resolve('/validate/check.json').func == views.check_json


def test_stats():
    assert resolve('/validate/stats/').func == views.stats


def test_prioritize():
    assert resolve('/validate/prioritize/').func == views.prioritize


def test_prioritize_json():
    assert resolve('/validate/prioritize.json').func == views.prioritize_json


def test__atom_next_feed_no_server():
    assert resolve('/validate/next/').func.__class__ == views.AtomNextFeedNoServer


def test_atom_next_feed():
    assert resolve('/validate/next/servername/').func.__class__ == views.AtomNextNewsFeed


def test_validate():
    assert resolve('/validate/ark:/00001/codajom1/').func == views.validate
