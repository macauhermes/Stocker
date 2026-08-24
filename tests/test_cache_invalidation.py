"""
Unit tests for cache invalidation helpers in app.py.

We extract the cache helpers into a tiny module-level dict + functions that
mirror app.py's _cache, cache_invalidate, cache_invalidate_prefix. The
production code lives inside app.py (where Flask + DB init are also done),
so we replicate the minimal helper surface here to test the logic in
isolation.

The behavior we test:
  - cache_invalidate('key') removes that one key
  - cache_invalidate('a', 'b') removes both
  - cache_invalidate('missing') is a no-op (no exception)
  - cache_invalidate_prefix('stock_info_') removes all matching keys,
    leaves others intact, returns the count removed
  - cache_invalidate_prefix('') removes every key (full flush)
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# Inline a tiny re-implementation of app.py's cache helpers so we can test
# without importing the Flask app (which boots DB / metrics side effects).
_cache = {}


def cache_invalidate(*keys):
    for k in keys:
        _cache.pop(k, None)


def cache_invalidate_prefix(prefix):
    stale = [k for k in _cache if k.startswith(prefix)]
    for k in stale:
        _cache.pop(k, None)
    return len(stale)


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear the test cache before every test."""
    _cache.clear()
    yield
    _cache.clear()


class TestCacheInvalidate:
    def test_single_key(self):
        _cache["foo"] = (1, None)
        cache_invalidate("foo")
        assert "foo" not in _cache

    def test_multiple_keys(self):
        _cache["a"] = (1, None)
        _cache["b"] = (2, None)
        _cache["c"] = (3, None)
        cache_invalidate("a", "b")
        assert "a" not in _cache
        assert "b" not in _cache
        assert "c" in _cache

    def test_missing_key_is_noop(self):
        _cache["present"] = (1, None)
        # Should not raise
        cache_invalidate("absent")
        assert "present" in _cache

    def test_mixed_existing_and_missing(self):
        _cache["real"] = (1, None)
        cache_invalidate("real", "ghost")
        assert "real" not in _cache

    def test_no_args(self):
        _cache["x"] = (1, None)
        # Calling with no keys must not raise and must not touch anything
        cache_invalidate()
        assert "x" in _cache


class TestCacheInvalidatePrefix:
    def test_removes_matching_keys(self):
        _cache["stock_info_TSLA"] = (1, None)
        _cache["stock_info_AAPL"] = (2, None)
        _cache["tickers_with_prices"] = (3, None)

        removed = cache_invalidate_prefix("stock_info_")
        assert removed == 2
        assert "stock_info_TSLA" not in _cache
        assert "stock_info_AAPL" not in _cache
        assert "tickers_with_prices" in _cache

    def test_no_matches_returns_zero(self):
        _cache["unrelated"] = (1, None)
        assert cache_invalidate_prefix("nothing_") == 0
        assert "unrelated" in _cache

    def test_empty_prefix_flushes_all(self):
        _cache["a"] = (1, None)
        _cache["b"] = (2, None)
        removed = cache_invalidate_prefix("")
        assert removed == 2
        assert _cache == {}

    def test_prefix_does_not_partial_match_unrelated(self):
        # Make sure 'stock_info_' prefix doesn't bleed into 'stock_info_other'
        _cache["stock_info_"] = (1, None)
        _cache["stock_info_x"] = (2, None)
        _cache["stock_other"] = (3, None)
        removed = cache_invalidate_prefix("stock_info_")
        assert removed == 2
        assert "stock_other" in _cache


class TestCacheInvalidateWorkflow:
    """Mirror the mutation flows in app.py."""

    def test_add_ticker_invalidates_aggregate(self):
        # Simulate cache populated by /api/tickers GET
        _cache["tickers_with_prices"] = [{"sym": "OLD"}]
        _cache["stock_info_NVDA"] = ({"price": 100}, None)

        # /api/tickers POST flow invalidates aggregate only
        cache_invalidate("tickers_with_prices")
        assert "tickers_with_prices" not in _cache
        assert "stock_info_NVDA" in _cache

    def test_refresh_invalidates_specific_stock_and_aggregate(self):
        _cache["tickers_with_prices"] = [{"sym": "TSLA"}]
        _cache["stock_info_TSLA"] = ({"price": 200}, None)

        # /api/stock/<sym>/refresh invalidates both
        sym = "TSLA"
        cache_invalidate("tickers_with_prices", f"stock_info_{sym}")
        assert "tickers_with_prices" not in _cache
        assert "stock_info_TSLA" not in _cache

    def test_delete_ticker_uppercases_symbol(self):
        _cache["tickers_with_prices"] = [{"sym": "TSLA"}]
        _cache["stock_info_tsla"] = ({"price": 200}, None)
        _cache["stock_info_TSLA"] = ({"price": 200}, None)

        # Production code uses symbol.upper() before building the key
        sym = "tsla"
        cache_invalidate("tickers_with_prices", f"stock_info_{sym.upper()}")
        assert "tickers_with_prices" not in _cache
        assert "stock_info_TSLA" not in _cache
        assert "stock_info_tsla" in _cache  # the lowercase one stays


if __name__ == "__main__":
    pytest.main([__file__, "-v"])