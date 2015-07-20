from django.core.paginator import Paginator
import pytest

from .. import views
from . import factories


class Test_prepare_graph_date_range:

    @pytest.mark.xfail
    def test_smoke():
        assert 0


class Test_calc_total_by_month:

    @pytest.mark.xfail
    def test_smoke():
        assert 0


class TestBagFullTextSearch:

    @pytest.mark.xfail(reason='FULLTEXT index is required.')
    def test_returns_paginator_object(self):
        factories.FullBagFactory.create_batch(15)
        paginator = views.bagFullTextSearch('test search')

        assert isinstance(paginator, Paginator)
