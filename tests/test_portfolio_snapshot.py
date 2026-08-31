"""
Unit tests for services/portfolio_snapshot.py + models portfolio_snapshots CRUD
(v3.4.2 — daily P&L history).

Following the same isolation pattern as test_alert_checker.py:
  1. Function-scope tempdir DB via models.DB_PATH patch + init_db()
  2. Mock `services.multi_source.get_current_price` at canonical path
     (Pitfall 7 — local import inside compute_totals())
  3. Use raw sqlite3.connect(temp_db) for assertion helpers so tests stay dumb

What we verify:
  - models.upsert_snapshot() returns dict (Pitfall 13)
  - models.upsert_snapshot() ON CONFLICT replaces (re-capturing today)
  - models.list_snapshots() returns oldest-first, capped at `days`
  - models.latest_snapshot() returns None when empty, dict otherwise
  - models.delete_snapshots_before() prunes correctly
  - portfolio_snapshot.compute_totals() skips tickers with no price
  - portfolio_snapshot.compute_totals() skips tickers with 0 shares
  - portfolio_snapshot.capture_snapshot() persists a row with correct math
  - portfolio_snapshot.prune_old_snapshots() removes only old rows
"""
import os
import sys
import sqlite3
import tempfile
from datetime import date, timedelta
from unittest.mock import patch

import pytest

# Ensure project root is on path
ROOT = Path = __import__('pathlib').Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import models


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_db():
    """Per-test isolated SQLite at a tempdir; init schema; restore on teardown.
    Function-scope so each test gets a fresh DB.
    """
    tmp = tempfile.mkdtemp(prefix='stocker-snapshot-test-')
    db_path = os.path.join(tmp, 'stocker.db')
    original = models.DB_PATH
    models.DB_PATH = db_path
    try:
        models.init_db()
        yield db_path
    finally:
        models.DB_PATH = original


def _insert_ticker(symbol, shares=0, cost_basis=0, archived=0):
    """Insert a ticker directly via sqlite3 — bypasses get_all_tickers filter
    by leaving archived=0 unless explicitly requested."""
    conn = sqlite3.connect(models.DB_PATH)
    try:
        cur = conn.execute(
            "INSERT INTO tickers (symbol, name, sector, shares_held, cost_basis, archived) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (symbol, f'{symbol} Inc', 'Tech', shares, cost_basis, archived),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _all_snapshots():
    """Read every snapshot row, ordered by date asc. Direct sqlite3 for clarity."""
    conn = sqlite3.connect(models.DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM portfolio_snapshots ORDER BY snapshot_date ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# Models CRUD — upsert_snapshot
# ═══════════════════════════════════════════════════════════════════

class TestUpsertSnapshot:
    def test_returns_dict_not_row(self, temp_db):
        """Pitfall 13: must return dict so callers can jsonify()."""
        row = models.upsert_snapshot('2026-08-25', 1000.0, 800.0, 200.0, 25.0, 5)
        assert isinstance(row, dict)
        assert row['snapshot_date'] == '2026-08-25'

    def test_insert_new_row(self, temp_db):
        models.upsert_snapshot('2026-08-25', 1000.0, 800.0, 200.0, 25.0, 5)
        rows = _all_snapshots()
        assert len(rows) == 1
        assert rows[0]['total_value'] == 1000.0
        assert rows[0]['holdings_count'] == 5

    def test_replaces_on_conflict(self, temp_db):
        """ON CONFLICT(snapshot_date) DO UPDATE — second call replaces first."""
        models.upsert_snapshot('2026-08-25', 1000.0, 800.0, 200.0, 25.0, 5)
        models.upsert_snapshot('2026-08-25', 1500.0, 800.0, 700.0, 87.5, 5)
        rows = _all_snapshots()
        assert len(rows) == 1
        assert rows[0]['total_value'] == 1500.0
        assert rows[0]['total_pnl'] == 700.0
        assert rows[0]['pnl_pct'] == 87.5

    def test_distinct_dates_coexist(self, temp_db):
        models.upsert_snapshot('2026-08-24', 900.0, 800.0, 100.0, 12.5, 5)
        models.upsert_snapshot('2026-08-25', 1000.0, 800.0, 200.0, 25.0, 5)
        assert len(_all_snapshots()) == 2

    def test_zero_values_are_stored_not_nulled(self, temp_db):
        """Empty portfolio: still record a row, not silently skip."""
        row = models.upsert_snapshot('2026-08-25', 0.0, 0.0, 0.0, 0.0, 0)
        assert row is not None
        assert row['total_value'] == 0.0


# ═══════════════════════════════════════════════════════════════════
# Models CRUD — list_snapshots
# ═══════════════════════════════════════════════════════════════════

class TestListSnapshots:
    def test_returns_empty_list_when_no_snapshots(self, temp_db):
        assert models.list_snapshots() == []

    def test_returns_oldest_first(self, temp_db):
        # Insert in scrambled order
        models.upsert_snapshot('2026-08-25', 1000.0, 800.0, 200.0, 25.0, 5)
        models.upsert_snapshot('2026-08-23', 700.0, 800.0, -100.0, -12.5, 5)
        models.upsert_snapshot('2026-08-24', 900.0, 800.0, 100.0, 12.5, 5)
        rows = models.list_snapshots()
        dates = [r['snapshot_date'] for r in rows]
        assert dates == ['2026-08-23', '2026-08-24', '2026-08-25']

    def test_caps_at_days_param(self, temp_db):
        for i in range(10):
            d = (date(2026, 8, 16) + timedelta(days=i)).isoformat()
            models.upsert_snapshot(d, 100.0 * (i + 1), 100.0, 0.0, 0.0, 1)
        rows = models.list_snapshots(days=3)
        assert len(rows) == 3
        # Should be the 3 most recent
        dates = [r['snapshot_date'] for r in rows]
        assert dates == ['2026-08-23', '2026-08-24', '2026-08-25']

    def test_returns_dicts_not_rows(self, temp_db):
        """Pitfall 13 — jsonify() needs dicts."""
        models.upsert_snapshot('2026-08-25', 1000.0, 800.0, 200.0, 25.0, 5)
        rows = models.list_snapshots()
        assert all(isinstance(r, dict) for r in rows)

    def test_captured_at_field_populated(self, temp_db):
        """v3.4.59 — list_snapshots returns captured_at alongside snapshot_date
        so the dashboard can distinguish 'this row was captured on date X'
        from 'this row represents date X but was actually captured later'
        (i.e. backfilled when nightly cron missed a day)."""
        models.upsert_snapshot('2026-08-25', 1000.0, 800.0, 200.0, 25.0, 5)
        rows = models.list_snapshots()
        assert len(rows) == 1
        s = rows[0]
        # captured_at must be present and ISO-format parseable
        assert 'captured_at' in s
        assert s['captured_at'] is not None
        # Should look like 'YYYY-MM-DD HH:MM:SS' — at minimum YYYY-MM-DD prefix
        assert s['captured_at'][:10] == s['snapshot_date'] or \
               s['captured_at'][:4].isdigit()
        # snapshot_date stays stable (still 'YYYY-MM-DD' string)
        assert s['snapshot_date'] == '2026-08-25'


# ═══════════════════════════════════════════════════════════════════
# Models CRUD — latest_snapshot
# ═══════════════════════════════════════════════════════════════════

class TestLatestSnapshot:
    def test_returns_none_when_empty(self, temp_db):
        assert models.latest_snapshot() is None

    def test_returns_most_recent(self, temp_db):
        models.upsert_snapshot('2026-08-23', 700.0, 800.0, -100.0, -12.5, 5)
        models.upsert_snapshot('2026-08-25', 1000.0, 800.0, 200.0, 25.0, 5)
        models.upsert_snapshot('2026-08-24', 900.0, 800.0, 100.0, 12.5, 5)
        latest = models.latest_snapshot()
        assert latest is not None
        assert latest['snapshot_date'] == '2026-08-25'


# ═══════════════════════════════════════════════════════════════════
# Models CRUD — snapshot_count, delete_snapshots_before
# ═══════════════════════════════════════════════════════════════════

class TestSnapshotCountAndPrune:
    def test_count_zero_when_empty(self, temp_db):
        assert models.snapshot_count() == 0

    def test_count_grows_with_inserts(self, temp_db):
        models.upsert_snapshot('2026-08-23', 1.0, 1.0, 0.0, 0.0, 1)
        models.upsert_snapshot('2026-08-24', 1.0, 1.0, 0.0, 0.0, 1)
        models.upsert_snapshot('2026-08-25', 1.0, 1.0, 0.0, 0.0, 1)
        assert models.snapshot_count() == 3

    def test_prune_deletes_old_rows(self, temp_db):
        models.upsert_snapshot('2026-01-01', 1.0, 1.0, 0.0, 0.0, 1)
        models.upsert_snapshot('2026-06-01', 1.0, 1.0, 0.0, 0.0, 1)
        models.upsert_snapshot('2026-08-25', 1.0, 1.0, 0.0, 0.0, 1)
        deleted = models.delete_snapshots_before('2026-08-01')
        assert deleted == 2
        assert models.snapshot_count() == 1

    def test_prune_keeps_recent_rows(self, temp_db):
        models.upsert_snapshot('2026-08-24', 1.0, 1.0, 0.0, 0.0, 1)
        models.upsert_snapshot('2026-08-25', 1.0, 1.0, 0.0, 0.0, 1)
        deleted = models.delete_snapshots_before('2026-08-01')
        assert deleted == 0
        assert models.snapshot_count() == 2


# ═══════════════════════════════════════════════════════════════════
# Service — compute_totals()
# ═══════════════════════════════════════════════════════════════════

class TestComputeTotals:
    def test_empty_portfolio_returns_zeros(self, temp_db):
        """No tickers at all — totals should be 0/0/0."""
        from services import portfolio_snapshot
        total_value, total_cost, holdings_count, breakdown = \
            portfolio_snapshot.compute_totals()
        assert total_value == 0.0
        assert total_cost == 0.0
        assert holdings_count == 0
        assert breakdown == []

    def test_skips_zero_share_tickers(self, temp_db):
        """Tickers with shares_held=0 must not inflate holdings_count."""
        _insert_ticker('TSLA', shares=10, cost_basis=100.0)
        _insert_ticker('NVDA', shares=0, cost_basis=0)  # zero shares
        _insert_ticker('IBM', shares=0, cost_basis=200.0)  # zero shares

        from services import portfolio_snapshot
        with patch(
            'services.multi_source.get_current_price',
            return_value={'price': 200.0, 'change_pct': 0, 'source': 'yfinance'},
        ):
            total_value, total_cost, holdings_count, breakdown = \
                portfolio_snapshot.compute_totals()
        assert holdings_count == 1
        assert total_value == 2000.0  # 10 * 200
        assert total_cost == 1000.0  # 10 * 100

    def test_skips_archived_tickers(self, temp_db):
        """get_all_tickers() filters archived=0 — verify zero archived rows appear."""
        _insert_ticker('TSLA', shares=10, cost_basis=100.0, archived=1)
        _insert_ticker('NVDA', shares=5, cost_basis=200.0)

        from services import portfolio_snapshot
        with patch(
            'services.multi_source.get_current_price',
            return_value={'price': 200.0, 'change_pct': 0, 'source': 'yfinance'},
        ):
            total_value, _, holdings_count, _ = portfolio_snapshot.compute_totals()
        # Only NVDA (not archived) should be counted
        assert holdings_count == 1
        assert total_value == 1000.0  # 5 * 200

    def test_skips_tickers_with_no_price(self, temp_db):
        """If multi_source returns None, skip — don't zero out totals."""
        _insert_ticker('TSLA', shares=10, cost_basis=100.0)
        _insert_ticker('NVDA', shares=5, cost_basis=200.0)

        from services import portfolio_snapshot

        def fake_price(symbol):
            # Only NVDA returns a price; TSLA fails
            return {'price': 200.0, 'change_pct': 0} if symbol == 'NVDA' else None

        with patch(
            'services.multi_source.get_current_price', side_effect=fake_price,
        ):
            total_value, total_cost, holdings_count, breakdown = \
                portfolio_snapshot.compute_totals()
        assert holdings_count == 1
        assert total_value == 1000.0  # only NVDA
        assert total_cost == 1000.0  # 5 * 200
        assert len(breakdown) == 1
        assert breakdown[0]['symbol'] == 'NVDA'

    def test_breakdown_contains_per_ticker_math(self, temp_db):
        _insert_ticker('TSLA', shares=10, cost_basis=100.0)

        from services import portfolio_snapshot
        with patch(
            'services.multi_source.get_current_price',
            return_value={'price': 250.0, 'change_pct': 1.5, 'source': 'yfinance'},
        ):
            _, _, _, breakdown = portfolio_snapshot.compute_totals()
        assert len(breakdown) == 1
        row = breakdown[0]
        assert row['symbol'] == 'TSLA'
        assert row['shares'] == 10
        assert row['cost_basis'] == 100.0
        assert row['current_price'] == 250.0
        assert row['market_value'] == 2500.0
        assert row['cost_value'] == 1000.0
        assert row['unrealized_pl'] == 1500.0

    def test_handles_multi_source_exception_per_ticker(self, temp_db):
        """A network exception for one ticker must not kill the whole snapshot."""
        _insert_ticker('TSLA', shares=10, cost_basis=100.0)
        _insert_ticker('NVDA', shares=5, cost_basis=200.0)

        from services import portfolio_snapshot

        def fake_price(symbol):
            if symbol == 'TSLA':
                raise RuntimeError('network down')
            return {'price': 200.0, 'change_pct': 0}

        with patch(
            'services.multi_source.get_current_price', side_effect=fake_price,
        ):
            total_value, total_cost, holdings_count, _ = \
                portfolio_snapshot.compute_totals()
        assert holdings_count == 1
        assert total_value == 1000.0


# ═══════════════════════════════════════════════════════════════════
# Service — capture_snapshot() + backfill_snapshot()
# ═══════════════════════════════════════════════════════════════════

class TestCaptureSnapshot:
    def test_captures_today_by_default(self, temp_db):
        _insert_ticker('TSLA', shares=10, cost_basis=100.0)

        from services import portfolio_snapshot
        with patch(
            'services.multi_source.get_current_price',
            return_value={'price': 250.0, 'change_pct': 1.5, 'source': 'yfinance'},
        ):
            row = portfolio_snapshot.capture_snapshot()
        assert row is not None
        assert row['snapshot_date'] == date.today().isoformat()
        assert row['total_value'] == 2500.0
        assert row['total_cost'] == 1000.0
        assert row['total_pnl'] == 1500.0
        assert row['pnl_pct'] == 150.0
        assert row['holdings_count'] == 1

    def test_accepts_explicit_date(self, temp_db):
        _insert_ticker('TSLA', shares=10, cost_basis=100.0)

        from services import portfolio_snapshot
        with patch(
            'services.multi_source.get_current_price',
            return_value={'price': 200.0, 'change_pct': 0, 'source': 'yfinance'},
        ):
            row = portfolio_snapshot.capture_snapshot(snapshot_date='2026-08-20')
        assert row['snapshot_date'] == '2026-08-20'
        assert row['total_value'] == 2000.0

    def test_replaces_existing_snapshot_for_same_date(self, temp_db):
        """Two captures on same date should produce one row, not two."""
        _insert_ticker('TSLA', shares=10, cost_basis=100.0)

        from services import portfolio_snapshot
        with patch(
            'services.multi_source.get_current_price',
            return_value={'price': 200.0, 'change_pct': 0, 'source': 'yfinance'},
        ):
            portfolio_snapshot.capture_snapshot(snapshot_date='2026-08-20')
            portfolio_snapshot.capture_snapshot(snapshot_date='2026-08-20')
        rows = _all_snapshots()
        assert len(rows) == 1

    def test_zero_pnl_pct_when_zero_cost(self, temp_db):
        """Empty portfolio: pnl_pct must be 0, not divide-by-zero."""
        from services import portfolio_snapshot
        with patch(
            'services.multi_source.get_current_price', return_value=None,
        ):
            row = portfolio_snapshot.capture_snapshot(snapshot_date='2026-08-20')
        assert row['pnl_pct'] == 0.0


# ═══════════════════════════════════════════════════════════════════
# Service — prune_old_snapshots()
# ═══════════════════════════════════════════════════════════════════

class TestPruneOldSnapshots:
    def test_deletes_only_old_rows(self, temp_db):
        _insert_ticker('TSLA', shares=10, cost_basis=100.0)
        from services import portfolio_snapshot

        with patch(
            'services.multi_source.get_current_price',
            return_value={'price': 200.0, 'change_pct': 0, 'source': 'yfinance'},
        ):
            # Old + recent snapshots — all on different dates so ON CONFLICT
            # doesn't dedupe them
            portfolio_snapshot.capture_snapshot(snapshot_date='2025-01-01')
            portfolio_snapshot.capture_snapshot(snapshot_date='2025-06-01')
            portfolio_snapshot.capture_snapshot(snapshot_date='2026-08-25')

        # cutoff = 2026-08-25 - 365 days = 2025-08-25
        # 2025-01-01 < cutoff → delete
        # 2025-06-01 < cutoff → delete
        # 2026-08-25 ≥ cutoff → keep
        deleted = portfolio_snapshot.prune_old_snapshots(retention_days=365)
        assert deleted == 2
        assert models.snapshot_count() == 1
        # The surviving row is the recent one
        assert _all_snapshots()[0]['snapshot_date'] == '2026-08-25'

    def test_returns_zero_when_nothing_to_prune(self, temp_db):
        from services import portfolio_snapshot
        portfolio_snapshot.capture_snapshot(snapshot_date='2026-08-25')
        deleted = portfolio_snapshot.prune_old_snapshots(retention_days=365)
        assert deleted == 0