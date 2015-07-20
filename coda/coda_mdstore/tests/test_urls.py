from django.core.urlresolvers import resolve

from .. import views


def test_index():
    assert resolve('/').func == views.index


def test_all_bags():
    assert resolve('/bag/').func == views.all_bags


def test_app_bag_no_parameters():
    assert resolve('/APP/bag/').func == views.app_bag


def test_app_with_parameters():
    assert resolve('/APP/bag/ark:/67531/coda2/').func == views.app_bag


def test_bagHTML():
    assert resolve('/bag/ark:/67531/coda2/').func == views.bagHTML


def test_bagURLList():
    assert resolve('/bag/ark:/67531/coda2.urls').func == views.bagURLList


def test_stats():
    assert resolve('/stats/').func == views.stats


def test_json_stats():
    assert resolve('/stats.json').func == views.json_stats


def test_app_node():
    assert resolve('/APP/node/').func == views.app_node


def test_app_node_with_identifier():
    assert resolve('/APP/node/coda-123/').func == views.app_node


def test_showNodeStatus():
    assert resolve('/node/').func == views.showNodeStatus


def test_showNodeStatus_with_identifier():
    assert resolve('/node/coda-123/').func == views.showNodeStatus


def test_externalIdentifierSearch_with_identifier():
    url = resolve('/extidentifier/test_value/')
    assert url.func == views.externalIdentifierSearch


def test_externalIdentifierSearch():
    url = resolve('/extidentifier/')
    assert url.func == views.externalIdentifierSearch


def test_externalIdentifierSearchJSON():
    url = resolve('/extidentifier.json')
    assert url.func == views.externalIdentifierSearchJSON


def test_bagFullTextSearchHTML():
    url = resolve('/search/')
    assert url.func == views.bagFullTextSearchHTML


def test_about():
    url = resolve('/about/')
    assert url.func == views.about


def test_robots():
    url = resolve('/robots.txt')
    assert url.func == views.shooRobot
