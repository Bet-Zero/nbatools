from __future__ import annotations

import re

import pytest

import nbatools  # noqa: F401  (importing the package sizes the cache)
from nbatools.regex_cache import ENGINE_REGEX_CACHE_SIZE, ensure_regex_cache_capacity

pytestmark = pytest.mark.engine


def test_importing_the_package_raises_the_regex_cache():
    assert re._MAXCACHE >= ENGINE_REGEX_CACHE_SIZE


def test_never_shrinks_a_larger_cache(monkeypatch):
    monkeypatch.setattr(re, "_MAXCACHE", ENGINE_REGEX_CACHE_SIZE * 2)
    ensure_regex_cache_capacity()
    assert re._MAXCACHE == ENGINE_REGEX_CACHE_SIZE * 2


@pytest.mark.fixture_data
def test_a_repeated_query_compiles_no_new_patterns():
    from nbatools.query_service import execute_natural_query

    execute_natural_query("Celtics record last 10 games")
    before = len(re._cache)
    execute_natural_query("Celtics record last 10 games")
    assert len(re._cache) == before
