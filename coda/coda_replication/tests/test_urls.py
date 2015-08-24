import pytest

from django.core.urlresolvers import resolve

from .. import views


pytestmark = pytest.mark.urls('coda_replication.urls')


def test_queue():
    assert resolve('/APP/queue/ark:/00001/codajom1/').func == views.queue


def test_queue_collection():
    assert resolve('/APP/queue/').func == views.queue


def test_queue_recent():
    assert resolve('/queue/').func == views.queue_recent


def test_queue_html():
    assert resolve('/queue/ark:/00001/codajom1/').func == views.queue_html


def test_queue_search():
    assert resolve('/queue/search/').func == views.queue_search


def test_queue_search_JSON():
    assert resolve('/queue/search.json').func == views.queue_search_JSON


def test_queue_stats():
    assert resolve('/queue/stats/').func == views.queue_stats
