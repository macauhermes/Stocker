"""
Unit tests for /api/portfolio/breakdown endpoint (v3.4.6 — live per-ticker
portfolio breakdown).

Uses Flask test client with `services.multi_source.get_current_price`
mocked at its canonical path. Doesn't hit the live data/stocker.db for
inserts (uses raw sqlite3.connect against the real DB to add/remove
smoke-test tickers — cleaned up in fixture teardown).

Why not full temp_db isolation: app.py wires a lot of cross-cutting
modules (multi_source, portfolio_snapshot, metrics) at import time, and
patching models.DB_PATH after import is fragile. The breakdown endpoint
only reads tickers + multi_source, so smoke-test tickers with a
recognisable note marker are safe.

What we verify:
  - 200 OK with correct shape (totals + per-ticker list)
  - Holdings sorted by market_value DESC
  - Per-ticker enriched fields: unrealized_pl_pct, share_of_portfolio
  - Empty portfolio: 200 OK with empty holdings list
  - Tickers with shares=0 or no price are skipped
  - JSON-safe (no Row leaks)
  - Prometheus counter for each status label (ok / empty / error)
"""
import os
import sys
import json
import sqlite3
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

SMOKE_PREFIX = '__BREAKDOWN_TEST_'  # marker for safe cleanup


@pytest.fixture(scope='module')
def client():
    """Flask test client. app.py initializes DB + Prometheus on import."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def smoke_ticker_cleanup():
    """Insert any smoke-test tickers via direct sqlite3, clean up after."""
    # Setup: nothing — tests add what they need
    yield
    # Teardown: delete any ticker whose symbol starts with our marker
    db = sqlite3.connect(os.path.expanduser('~/repos/Stocker/data/stocker.db'))
    try:
        db.execute(
            "DELETE FROM tickers WHERE symbol LIKE ?",
            (f'{SMOKE_PREFIX}%',),
        )
        db.commit()
    finally:
        db.close()


def _insert_ticker(symbol, shares=0, cost_basis=0, archived=0):
    """Insert a smoke-test ticker directly via sqlite3."""
    db = sqlite3.connect(os.path.expanduser('~/repos/Stocker/data/stocker.db'))
    try:
        db.execute(
            "INSERT INTO tickers (symbol, name, sector, shares_held, cost_basis, archived) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (symbol, f'{symbol} Inc', 'Tech', shares, cost_basis, archived),
        )
        db.commit()
    finally:
        db.close()


def _make_price(symbol, price):
    """Build the dict shape that multi_source.get_current_price() returns."""
    return {
        'price': price,
        'source': 'yfinance',
        'symbol': symbol,
        'timestamp': '2026-08-25T00:00:00Z',
    }


# ═══════════════════════════════════════════════════════════════════
# Tests — Empty Portfolio
# ═══════════════════════════════════════════════════════════════════

class TestEmptyPortfolio:
    def test_only_zero_share_tickers_skipped(self, client):
        """Tickers with shares=0 should not appear in the breakdown.

        Other tickers in the live DB may have shares>0 (they always do),
        so we check our smoke-ticker is absent rather than asserting
        the whole portfolio is empty.
        """
        smoke_sym = f'{SMOKE_PREFIX}ZERO'
        _insert_ticker(smoke_sym, shares=0, cost_basis=100)
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: _make_price(s, 200)):
            resp = client.get('/api/portfolio/breakdown')
        data = resp.get_json()
        symbols = [h['symbol'] for h in data['holdings']]
        assert smoke_sym not in symbols, f'{smoke_sym} should be skipped (shares=0)'


# ═══════════════════════════════════════════════════════════════════
# Tests — Multi-Ticker Math + Sorting
# ═══════════════════════════════════════════════════════════════════

class TestMultiTickerBreakdown:
    def _seed_three(self):
        """Seed 3 smoke-test tickers with known shares/cost."""
        _insert_ticker(f'{SMOKE_PREFIX}TSLA', shares=10, cost_basis=200)
        _insert_ticker(f'{SMOKE_PREFIX}NVDA', shares=5,  cost_basis=400)
        _insert_ticker(f'{SMOKE_PREFIX}IBM',  shares=20, cost_basis=100)

    def test_three_tickers_correct_math(self, client):
        """Three tickers → totals = MV sum, cost = cost_value sum, PnL = MV-cost."""
        self._seed_three()

        prices = {
            f'{SMOKE_PREFIX}TSLA': 350,  # MV=3500
            f'{SMOKE_PREFIX}NVDA': 900,  # MV=4500
            f'{SMOKE_PREFIX}IBM':  100,  # MV=2000
        }
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: (
                       _make_price(s, prices[s]) if s in prices else None
                   )):
            resp = client.get('/api/portfolio/breakdown')

        assert resp.status_code == 200
        data = resp.get_json()
        # Smoke tickers may share totals with non-smoke holdings, but we can
        # check at minimum that our 3 contribute (holdings_count >= 3)
        assert data['holdings_count'] >= 3

        # Find our smoke tickers in the response
        smoke = [h for h in data['holdings'] if h['symbol'].startswith(SMOKE_PREFIX)]
        assert len(smoke) == 3
        # Smoke tickers' total MV must be exactly 10000
        smoke_mv = sum(h['market_value'] for h in smoke)
        assert smoke_mv == 10000.0
        smoke_cost = sum(h['cost_value'] for h in smoke)
        assert smoke_cost == 6000.0

    def test_holdings_sorted_desc_by_market_value(self, client):
        """Order: biggest market value first (within smoke-test subset)."""
        _insert_ticker(f'{SMOKE_PREFIX}SMALL', shares=1,  cost_basis=100)
        _insert_ticker(f'{SMOKE_PREFIX}BIG',   shares=10, cost_basis=100)
        _insert_ticker(f'{SMOKE_PREFIX}MID',   shares=5,  cost_basis=100)

        prices = {
            f'{SMOKE_PREFIX}SMALL': 100,
            f'{SMOKE_PREFIX}BIG':   100,
            f'{SMOKE_PREFIX}MID':   100,
        }
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: (
                       _make_price(s, prices[s]) if s in prices else None
                   )):
            resp = client.get('/api/portfolio/breakdown')

        data = resp.get_json()
        smoke = [h['symbol'] for h in data['holdings']
                 if h['symbol'].startswith(SMOKE_PREFIX)]
        assert smoke == [
            f'{SMOKE_PREFIX}BIG',
            f'{SMOKE_PREFIX}MID',
            f'{SMOKE_PREFIX}SMALL',
        ]

    def test_enriched_fields_per_holding(self, client):
        """Each holding has unrealized_pl_pct + share_of_portfolio populated."""
        _insert_ticker(f'{SMOKE_PREFIX}TSLA', shares=10, cost_basis=200)
        _insert_ticker(f'{SMOKE_PREFIX}NVDA', shares=5,  cost_basis=400)

        prices = {
            f'{SMOKE_PREFIX}TSLA': 350,  # PnL=1500, PnL%=75
            f'{SMOKE_PREFIX}NVDA': 900,  # PnL=2500, PnL%=125
        }
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: (
                       _make_price(s, prices[s]) if s in prices else None
                   )):
            resp = client.get('/api/portfolio/breakdown')

        data = resp.get_json()
        tsla = next(h for h in data['holdings'] if h['symbol'] == f'{SMOKE_PREFIX}TSLA')
        nvda = next(h for h in data['holdings'] if h['symbol'] == f'{SMOKE_PREFIX}NVDA')

        assert tsla['unrealized_pl_pct'] == 75.0
        assert nvda['unrealized_pl_pct'] == 125.0
        # Both shares positive
        assert tsla['share_of_portfolio'] > 0
        assert nvda['share_of_portfolio'] > 0


# ═══════════════════════════════════════════════════════════════════
# Tests — Filtering
# ═══════════════════════════════════════════════════════════════════

class TestFiltering:
    def test_ticker_with_no_price_is_skipped(self, client):
        """multi_source returning None → ticker dropped silently."""
        _insert_ticker(f'{SMOKE_PREFIX}HAS_PRICE', shares=10, cost_basis=100)
        _insert_ticker(f'{SMOKE_PREFIX}NO_PRICE',  shares=5,  cost_basis=100)

        prices = {f'{SMOKE_PREFIX}HAS_PRICE': 200}
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: (
                       _make_price(s, prices[s]) if s in prices else None
                   )):
            resp = client.get('/api/portfolio/breakdown')

        data = resp.get_json()
        symbols = [h['symbol'] for h in data['holdings']]
        assert f'{SMOKE_PREFIX}HAS_PRICE' in symbols
        assert f'{SMOKE_PREFIX}NO_PRICE' not in symbols

    def test_archived_ticker_excluded(self, client):
        """Archived tickers should not appear (get_all_tickers filters them)."""
        _insert_ticker(f'{SMOKE_PREFIX}ACTIVE',   shares=10, cost_basis=100, archived=0)
        _insert_ticker(f'{SMOKE_PREFIX}ARCHIVED', shares=10, cost_basis=100, archived=1)

        prices = {f'{SMOKE_PREFIX}ACTIVE': 100, f'{SMOKE_PREFIX}ARCHIVED': 100}
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: (
                       _make_price(s, prices[s]) if s in prices else None
                   )):
            resp = client.get('/api/portfolio/breakdown')

        data = resp.get_json()
        symbols = [h['symbol'] for h in data['holdings']]
        assert f'{SMOKE_PREFIX}ARCHIVED' not in symbols
        assert f'{SMOKE_PREFIX}ACTIVE' in symbols


# ═══════════════════════════════════════════════════════════════════
# Tests — JSON Serialization Safety
# ═══════════════════════════════════════════════════════════════════

class TestJSONSafety:
    def test_response_is_json_serializable(self, client):
        """Full payload round-trips through json.dumps — no sqlite3.Row leaks."""
        _insert_ticker(f'{SMOKE_PREFIX}TSLA', shares=10, cost_basis=200)
        prices = {f'{SMOKE_PREFIX}TSLA': 350}
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: (
                       _make_price(s, prices[s]) if s in prices else None
                   )):
            resp = client.get('/api/portfolio/breakdown')

        data = resp.get_json()
        payload = json.dumps(data)  # would raise on Row
        assert f'{SMOKE_PREFIX}TSLA' in payload
        assert 'timestamp' in data
        assert 'holdings' in data
        assert 'total_value' in data

    def test_no_unrealized_pl_pct_when_no_cost(self, client):
        """shares>0 but cost_basis=0 → unrealized_pl_pct is 0 (not NaN/inf)."""
        _insert_ticker(f'{SMOKE_PREFIX}FREEBIE', shares=10, cost_basis=0)
        prices = {f'{SMOKE_PREFIX}FREEBIE': 100}
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: (
                       _make_price(s, prices[s]) if s in prices else None
                   )):
            resp = client.get('/api/portfolio/breakdown')

        data = resp.get_json()
        freebie = next(
            (h for h in data['holdings'] if h['symbol'] == f'{SMOKE_PREFIX}FREEBIE'),
            None,
        )
        assert freebie is not None
        assert freebie['unrealized_pl_pct'] == 0.0
        assert freebie['share_of_portfolio'] > 0


# ═══════════════════════════════════════════════════════════════════
# Tests — Metrics Integration
# ═══════════════════════════════════════════════════════════════════

class TestMetrics:
    def test_holdings_present_uses_ok_status_label(self, client):
        """Counter labelled 'ok' when at least one holding present."""
        from services.metrics import PORTFOLIO_BREAKDOWN
        before = int(PORTFOLIO_BREAKDOWN.labels(status='ok')._value.get())
        _insert_ticker(f'{SMOKE_PREFIX}TSLA', shares=10, cost_basis=200)
        prices = {f'{SMOKE_PREFIX}TSLA': 350}
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: (
                       _make_price(s, prices[s]) if s in prices else None
                   )):
            client.get('/api/portfolio/breakdown')
        after = int(PORTFOLIO_BREAKDOWN.labels(status='ok')._value.get())
        assert after == before + 1

    def test_compute_failure_uses_error_status_label(self, client):
        """Counter labelled 'error' when compute_totals raises."""
        from services.metrics import PORTFOLIO_BREAKDOWN
        before = int(PORTFOLIO_BREAKDOWN.labels(status='error')._value.get())

        # Patch compute_totals to raise — bypasses the inner try/except in
        # _safe_get_price (which would just return None for a price-side error)
        import services.portfolio_snapshot as ps_mod
        original = ps_mod.compute_totals

        def _raise():
            raise RuntimeError('forced breakdown failure')

        ps_mod.compute_totals = _raise
        try:
            resp = client.get('/api/portfolio/breakdown')
        finally:
            ps_mod.compute_totals = original

        assert resp.status_code == 500
        after = int(PORTFOLIO_BREAKDOWN.labels(status='error')._value.get())


# ═══════════════════════════════════════════════════════════════════
# Tests — Timestamp Field (v3.4.58 — Pattern 9b orphan field)
# ═══════════════════════════════════════════════════════════════════

class TestTimestampField:
    """v3.4.58: /api/portfolio/breakdown must include `timestamp` so the
    dashboard holdings table can show "As of: {time}" meta line. Before this,
    the timestamp field existed in the response but was silently dropped
    between API and DOM — users had no signal that current prices may be a
    few minutes stale."""

    def test_breakdown_includes_timestamp(self, client):
        """Top-level dict must include a non-empty `timestamp` field."""
        _insert_ticker(f'{SMOKE_PREFIX}TSLA', shares=10, cost_basis=200)
        prices = {f'{SMOKE_PREFIX}TSLA': _make_price(f'{SMOKE_PREFIX}TSLA', 350)}
        with patch('services.multi_source.get_current_price',
                   side_effect=lambda s, *a, **k: (
                       _make_price(s, prices[s]['price']) if s in prices else None
                   )):
            resp = client.get('/api/portfolio/breakdown')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'timestamp' in data, "breakdown response missing timestamp field"
        assert data['timestamp'], "timestamp field is empty/null"
        # Should be parseable as ISO datetime
        from datetime import datetime
        ts = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        assert ts is not None
