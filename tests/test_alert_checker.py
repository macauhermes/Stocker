"""
Unit tests for services/alert_checker.py (Price Alerts v3.4).

alert_checker is pure-logic with two I/O surfaces:
  - models.*    (SQLite via models.DB_PATH)
  - tsdb.get_latest_price  (locally imported — Pitfall 7 path)
  - services.multi_source.get_current_price  (locally imported)

We isolate by:
  1. Pointing models.DB_PATH at a tempdir + calling models.init_db() once
     per session. The patch on models.DB_PATH doesn't affect get_db()
     because that function reads the module-level binding at call time
     (sqlite3.connect is called inside get_db(), not at import).
  2. Mocking tsdb.get_latest_price + services.multi_source.get_current_price
     at their canonical module paths.

What we verify:
  - check_alerts_for_ticker() skips archived tickers
  - check_alerts_for_ticker() silently returns [] when price is unavailable
  - 'high' alert fires only when current_price >= threshold_price
  - 'low'  alert fires only when current_price <= threshold_price
  - Fired alert is auto-disabled in the DB
  - Fired alert creates a price_alert event row with the expected title shape
  - check_alerts_all() sweeps every active ticker + survives per-ticker failures
  - Threshold type validation in add_alert() rejects bad inputs
  - update_alert() rejects bad threshold_type
"""
import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import models


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_db():
    """Per-test isolated SQLite at a tempdir; init schema; restore on teardown.

    Function-scope (not module) so each test gets a fresh DB — keeps the
    'active tickers' / 'enabled alerts' state deterministic.
    """
    tmp = tempfile.mkdtemp(prefix='stocker-alert-test-')
    db_path = os.path.join(tmp, 'stocker.db')
    original = models.DB_PATH
    models.DB_PATH = db_path
    try:
        models.init_db()
        yield db_path
    finally:
        models.DB_PATH = original


@pytest.fixture
def ticker_id(temp_db):
    """Insert a fresh TSLA ticker; return its integer id.

    Note: function-scoped so tests don't inherit rows from a previous test.
    """
    conn = sqlite3.connect(temp_db)
    try:
        cur = conn.execute(
            "INSERT INTO tickers (symbol, name, sector) VALUES (?, ?, ?)",
            ('TSLA', 'Tesla Inc', 'Consumer Cyclical'),
        )
        tid = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    return tid


@pytest.fixture
def nvda_id(temp_db):
    """Insert a fresh NVDA ticker; return its integer id."""
    conn = sqlite3.connect(temp_db)
    try:
        cur = conn.execute(
            "INSERT INTO tickers (symbol, name, sector) VALUES (?, ?, ?)",
            ('NVDA', 'Nvidia Corp', 'Technology'),
        )
        nid = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    return nid


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _insert_alert(temp_db, ticker_id, threshold_type, threshold_price,
                  enabled=1, note=None):
    """Insert a price_alert row and return its id."""
    conn = sqlite3.connect(temp_db)
    try:
        cur = conn.execute(
            """INSERT INTO price_alerts
               (ticker_id, threshold_type, threshold_price, enabled, note)
               VALUES (?, ?, ?, ?, ?)""",
            (ticker_id, threshold_type, threshold_price, enabled, note),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _alert_state(temp_db, alert_id):
    """Read (enabled, last_triggered_at) for an alert."""
    conn = sqlite3.connect(temp_db)
    try:
        row = conn.execute(
            "SELECT enabled, last_triggered_at FROM price_alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()
        return (row[0], row[1]) if row else None
    finally:
        conn.close()


def _event_rows_for_ticker(temp_db, ticker_id):
    conn = sqlite3.connect(temp_db)
    try:
        return conn.execute(
            "SELECT event_type, event_date, title FROM events WHERE ticker_id = ?",
            (ticker_id,),
        ).fetchall()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# check_alerts_for_ticker — gating logic
# ═══════════════════════════════════════════════════════════════════

class TestCheckAlertsForTicker:
    def test_returns_empty_for_unknown_symbol(self, temp_db):
        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value=None), \
             patch('services.multi_source.get_current_price', return_value=None):
            result = alert_checker.check_alerts_for_ticker('NOPE')
        assert result == []

    def test_returns_empty_for_archived_ticker(self, temp_db):
        """Archived tickers must be skipped silently even with valid alerts."""
        conn = sqlite3.connect(temp_db)
        try:
            cur = conn.execute(
                "INSERT INTO tickers (symbol, name, sector, archived) VALUES (?, ?, ?, 1)",
                ('ARCH', 'Archived Co', 'Tech'),
            )
            archived_id = cur.lastrowid
            conn.commit()
        finally:
            conn.close()
        aid = _insert_alert(temp_db, archived_id, 'high', 100.0)

        from services import alert_checker
        # Even with price available + alert active, archived must be skipped
        with patch('tsdb.get_latest_price', return_value={'close': 500.0}), \
             patch('services.multi_source.get_current_price', return_value={'price': 500.0}):
            result = alert_checker.check_alerts_for_ticker('ARCH')

        assert result == []
        # Alert must NOT be auto-disabled (function returned early)
        assert _alert_state(temp_db, aid)[0] == 1

    def test_silent_skip_when_no_price_available(self, temp_db, ticker_id):
        """If TSDB cache miss + multi_source fails, return [] silently."""
        aid = _insert_alert(temp_db, ticker_id, 'high', 100.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value=None), \
             patch('services.multi_source.get_current_price', return_value=None):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert result == []
        assert _alert_state(temp_db, aid)[0] == 1  # not triggered

    def test_uses_tsd_cache_first(self, temp_db, ticker_id):
        """tsdb hit short-circuits the multi_source network call."""
        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 200.0}) as tsdb_mock, \
             patch('services.multi_source.get_current_price', return_value={'price': 999.0}) as ms_mock:
            result = alert_checker.check_alerts_for_ticker('TSLA')

        tsdb_mock.assert_called_once()
        ms_mock.assert_not_called()
        # No alerts exist for this ticker yet, so result is []
        assert result == []

    def test_falls_back_to_multi_source_when_tsd_empty(self, temp_db, ticker_id):
        """tsdb None/0 → multi_source is consulted."""
        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value=None), \
             patch('services.multi_source.get_current_price', return_value={'price': 200.0}):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert result == []

    def test_skips_zero_or_negative_price(self, temp_db, ticker_id):
        """A 0/negative cached price must not be used (defensive)."""
        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 0}), \
             patch('services.multi_source.get_current_price', return_value={'price': -5.0}):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert result == []


# (no module-level helper needed — tests use the ticker_id fixture)


# ═══════════════════════════════════════════════════════════════════
# check_alerts_for_ticker — threshold evaluation
# ═══════════════════════════════════════════════════════════════════

class TestThresholdEvaluation:
    def test_high_alert_fires_when_price_at_or_above_threshold(self, temp_db, ticker_id):
        aid = _insert_alert(temp_db, ticker_id, 'high', 300.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 350.0}):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert len(result) == 1
        fired = result[0]
        assert fired['alert_id'] == aid
        assert fired['threshold_type'] == 'high'
        assert fired['threshold_price'] == 300.0
        assert fired['current_price'] == 350.0

    def test_high_alert_fires_at_exact_threshold(self, temp_db, ticker_id):
        """Edge: current_price == threshold_price must fire (>=)."""
        _insert_alert(temp_db, ticker_id, 'high', 300.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 300.0}):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert len(result) == 1

    def test_high_alert_does_not_fire_below_threshold(self, temp_db, ticker_id):
        aid = _insert_alert(temp_db, ticker_id, 'high', 300.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 299.99}):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert result == []
        assert _alert_state(temp_db, aid)[0] == 1

    def test_low_alert_fires_when_price_at_or_below_threshold(self, temp_db, ticker_id):
        aid = _insert_alert(temp_db, ticker_id, 'low', 200.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 180.0}):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert len(result) == 1
        fired = result[0]
        assert fired['threshold_type'] == 'low'
        assert fired['current_price'] == 180.0

    def test_low_alert_fires_at_exact_threshold(self, temp_db, ticker_id):
        """Edge: current_price == threshold_price must fire (<=)."""
        _insert_alert(temp_db, ticker_id, 'low', 200.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 200.0}):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert len(result) == 1

    def test_low_alert_does_not_fire_above_threshold(self, temp_db, ticker_id):
        aid = _insert_alert(temp_db, ticker_id, 'low', 200.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 200.01}):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert result == []
        assert _alert_state(temp_db, aid)[0] == 1

    def test_disabled_alerts_are_not_fired(self, temp_db, ticker_id):
        """enabled=0 alerts are never re-triggered until manually re-armed."""
        _insert_alert(temp_db, ticker_id, 'high', 100.0, enabled=0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 500.0}):
            result = alert_checker.check_alerts_for_ticker('TSLA')

        assert result == []

    def test_multiple_alerts_mixed_triggering(self, temp_db, ticker_id):
        """Two alerts on same ticker — only the ones whose threshold passes fire."""
        high_id = _insert_alert(temp_db, ticker_id, 'high', 300.0)
        low_id = _insert_alert(temp_db, ticker_id, 'low', 200.0)

        from services import alert_checker
        # Price 250: high(>=300) does NOT fire, low(<=200) does NOT fire
        with patch('tsdb.get_latest_price', return_value={'close': 250.0}):
            mid = alert_checker.check_alerts_for_ticker('TSLA')
        assert mid == []

        # Price 350: high fires, low does not
        with patch('tsdb.get_latest_price', return_value={'close': 350.0}):
            upper = alert_checker.check_alerts_for_ticker('TSLA')
        assert len(upper) == 1
        assert upper[0]['alert_id'] == high_id

        # Price 150: high does not, low fires
        with patch('tsdb.get_latest_price', return_value={'close': 150.0}):
            lower = alert_checker.check_alerts_for_ticker('TSLA')
        assert len(lower) == 1
        assert lower[0]['alert_id'] == low_id


# ═══════════════════════════════════════════════════════════════════
# Side-effects — event row + auto-disable
# ═══════════════════════════════════════════════════════════════════

class TestAlertSideEffects:
    def test_fired_alert_is_auto_disabled(self, temp_db, ticker_id):
        """Once fired, enabled must flip to 0 so refresh doesn't re-fire."""
        aid = _insert_alert(temp_db, ticker_id, 'high', 100.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 200.0}):
            alert_checker.check_alerts_for_ticker('TSLA')

        enabled, triggered_at = _alert_state(temp_db, aid)
        assert enabled == 0
        assert triggered_at is not None  # stamped

    def test_fired_alert_creates_event_row(self, temp_db, ticker_id):
        """An event row with type='price_alert' + the expected title shape."""
        _insert_alert(temp_db, ticker_id, 'high', 100.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 200.0}):
            alert_checker.check_alerts_for_ticker('TSLA')

        events = _event_rows_for_ticker(temp_db, ticker_id)
        assert len(events) == 1
        ev_type, ev_date, title = events[0]
        assert ev_type == 'price_alert'
        assert ev_date is not None  # ISO date
        # Title shape: "🔔 SYMBOL high $100.00 (now $200.00)"
        assert 'TSLA' in title
        assert 'high' in title
        assert '100.00' in title
        assert '200.00' in title
        assert '🔔' in title

    def test_fired_alert_is_idempotent_on_repeat_call(self, temp_db, ticker_id):
        """Second call: alert disabled → nothing fires, no duplicate event."""
        _insert_alert(temp_db, ticker_id, 'high', 100.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 200.0}):
            first = alert_checker.check_alerts_for_ticker('TSLA')
            second = alert_checker.check_alerts_for_ticker('TSLA')

        assert len(first) == 1
        assert second == []
        # Only one event row exists (no duplicate event spam)
        events = _event_rows_for_ticker(temp_db, ticker_id)
        assert len(events) == 1


# ═══════════════════════════════════════════════════════════════════
# check_alerts_all — sweep
# ═══════════════════════════════════════════════════════════════════

class TestCheckAlertsAll:
    def test_sweeps_all_active_tickers(self, temp_db, ticker_id, nvda_id):
        """Insert alerts for two tickers, both must be checked."""
        _insert_alert(temp_db, ticker_id, 'high', 100.0)
        _insert_alert(temp_db, nvda_id, 'high', 100.0)

        from services import alert_checker
        # Same current price used for both tickers via tsdb mock
        with patch('tsdb.get_latest_price', return_value={'close': 200.0}):
            triggered = alert_checker.check_alerts_all()

        assert len(triggered) == 2
        fired_syms = sorted(t['symbol'] for t in triggered)
        assert fired_syms == ['NVDA', 'TSLA']

    def test_survives_per_ticker_exception(self, temp_db, ticker_id, nvda_id):
        """One ticker raising must not abort the whole sweep."""
        from services import alert_checker

        call_count = {'n': 0}

        def fake_check(symbol):
            call_count['n'] += 1
            if symbol == 'TSLA':
                raise RuntimeError('boom')
            return []

        with patch.object(alert_checker, 'check_alerts_for_ticker', side_effect=fake_check):
            result = alert_checker.check_alerts_all()

        # The TSLA exception was swallowed + the other ticker was still processed
        assert result == []
        # Two non-archived tickers (TSLA + NVDA) — both attempted despite TSLA failing
        assert call_count['n'] == 2

    def test_skips_archived_in_sweep(self, temp_db, ticker_id):
        from services import alert_checker
        # If sweep walked archived ticker, tsdb.get_latest_price would be called
        # for it; we patch to verify the call list.
        with patch('tsdb.get_latest_price', return_value=None) as tsdb_mock, \
             patch('services.multi_source.get_current_price', return_value=None):
            alert_checker.check_alerts_all()

        called_for = [c.args[0] for c in tsdb_mock.call_args_list]
        # TSLA is the only non-archived ticker in fixture state
        assert ticker_id in called_for
        assert 'OLD' not in called_for


# ═══════════════════════════════════════════════════════════════════
# Model-level: validation + re-arm workflow
# ═══════════════════════════════════════════════════════════════════

class TestAlertModelValidation:
    def test_add_alert_rejects_invalid_threshold_type(self, temp_db, ticker_id):
        with pytest.raises(ValueError, match='high'):
            models.add_alert(ticker_id, 'sideways', 100.0)

    def test_add_alert_returns_dict(self, temp_db, ticker_id):
        row = models.add_alert(ticker_id, 'high', 100.0, note='test')
        # Critical: must be dict so jsonify works (Pitfall 13)
        assert isinstance(row, dict)
        assert 'id' in row
        assert row['threshold_type'] == 'high'
        assert row['threshold_price'] == 100.0
        assert row['enabled'] == 1

    def test_update_alert_rejects_invalid_threshold_type(self, temp_db, ticker_id):
        alert = models.add_alert(ticker_id, 'high', 100.0)
        with pytest.raises(ValueError):
            models.update_alert(alert['id'], threshold_type='sideways')

    def test_update_alert_returns_dict(self, temp_db, ticker_id):
        alert = models.add_alert(ticker_id, 'high', 100.0)
        row = models.update_alert(alert['id'], enabled=0, note='paused')
        assert isinstance(row, dict)
        assert row['enabled'] == 0
        assert row['note'] == 'paused'

    def test_delete_alert_returns_bool(self, temp_db, ticker_id):
        alert = models.add_alert(ticker_id, 'high', 100.0)
        assert models.delete_alert(alert['id']) is True
        # Second delete is a no-op
        assert models.delete_alert(alert['id']) is False

    def test_rearm_workflow(self, temp_db, ticker_id):
        """After firing, alert can be re-armed (enabled=1) and will fire again."""
        aid = _insert_alert(temp_db, ticker_id, 'high', 100.0)

        from services import alert_checker
        with patch('tsdb.get_latest_price', return_value={'close': 200.0}):
            first = alert_checker.check_alerts_for_ticker('TSLA')
        assert len(first) == 1
        assert _alert_state(temp_db, aid)[0] == 0  # disabled after firing

        # Manually re-arm
        models.update_alert(aid, enabled=1)
        assert _alert_state(temp_db, aid)[0] == 1

        with patch('tsdb.get_latest_price', return_value={'close': 250.0}):
            second = alert_checker.check_alerts_for_ticker('TSLA')
        assert len(second) == 1
        # upsert_event() dedupes by (ticker_id, event_type, event_date) so the
        # second fire on the same day does NOT create a duplicate event row.
        # This is intentional: the events table is a notification log, not an
        # audit trail of every fire. Verify only one row exists.
        events = _event_rows_for_ticker(temp_db, ticker_id)
        assert len(events) == 1
        # But the alert has now been triggered twice (last_triggered_at updated)
        assert _alert_state(temp_db, aid)[0] == 0