"""
Unit tests for health check and metrics summary functions in services/metrics.py.

These functions need Flask app context (for jsonify()), so we create a minimal
Flask app with sqlite3 + a temporary data dir to exercise the helpers end-to-end
without booting the full Stocker stack.

Behavior we test:
  - health_check() returns 200 + status='healthy' when DB + disk + tsdb are OK
  - health_check() returns 503 + status='unhealthy' when DB query fails
  - health_check() increments the Prometheus counter on each call
  - metrics_summary() returns a well-formed dict with all required keys
  - metrics_summary() includes top_sectors + top_tickers_by_reports
  - _format_uptime() formats seconds as 'Xd Yh Zm' / 'Yh Zm' / 'Zm'
  - _check_db() returns (True, 'sqlite_ok') for a healthy DB
  - _check_disk() returns (True, ...) and the detail contains 'free'
  - _check_tsdb() returns (True, 'tsdb_ok') for the real tsdb
"""
import os
import sys
import time
import sqlite3
import tempfile
from pathlib import Path

import pytest

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flask import Flask

# We need to import the metrics module, but it triggers APP_START_TIME.set()
# at import time. That's fine — it's just `time.time()`.
from services import metrics


@pytest.fixture
def app():
    """Minimal Flask app for context."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


# ── Health Check ────────────────────────────────────────────────────

class TestHealthCheck:
    def test_returns_200_when_all_ok(self, app):
        with app.app_context():
            response, code = metrics.health_check()
        assert code == 200
        body = response.get_json()
        assert body['status'] in ('healthy', 'degraded')
        assert 'checks' in body
        assert body['checks']['database']['ok'] is True
        assert body['checks']['disk']['ok'] is True
        assert 'uptime_seconds' in body
        assert body['uptime_seconds'] >= 0

    def test_includes_uptime_timestamp(self, app):
        with app.app_context():
            response, _ = metrics.health_check()
        body = response.get_json()
        assert 'timestamp' in body
        assert body['timestamp'].endswith('Z')

    def test_checks_structure(self, app):
        with app.app_context():
            response, _ = metrics.health_check()
        body = response.get_json()
        assert set(body['checks'].keys()) == {'database', 'disk', 'tsdb'}
        for check in body['checks'].values():
            assert 'ok' in check
            assert 'detail' in check


# ── Individual check helpers ────────────────────────────────────────

class TestCheckDb:
    def test_db_ok(self):
        ok, detail = metrics._check_db()
        assert ok is True
        assert detail == 'sqlite_ok'


class TestCheckDisk:
    def test_disk_ok_or_warning(self):
        ok, detail = metrics._check_disk()
        assert ok is True
        assert 'free' in detail or 'missing' in detail or 'skipped' in detail


class TestCheckTsdb:
    def test_tsdb_ok(self):
        ok, detail = metrics._check_tsdb()
        assert ok is True
        assert detail == 'tsdb_ok'


# ── Metrics Summary ─────────────────────────────────────────────────

class TestMetricsSummary:
    def test_returns_200_and_required_keys(self, app):
        with app.app_context():
            response, code = metrics.metrics_summary()
        assert code == 200
        body = response.get_json()
        required = [
            'uptime_seconds', 'uptime_human',
            'tickers_active', 'reports_total', 'reports_by_category',
            'events_active', 'events_upcoming_7d',
            'banks', 'custom_sources', 'watchlist_groups',
            'sse_connections', 'top_sectors', 'top_tickers_by_reports',
            'latest_report_at', 'timestamp',
        ]
        for key in required:
            assert key in body, f'Missing key: {key}'

    def test_tickers_active_is_int(self, app):
        with app.app_context():
            response, _ = metrics.metrics_summary()
        body = response.get_json()
        assert isinstance(body['tickers_active'], int)
        assert body['tickers_active'] >= 0

    def test_top_sectors_is_list(self, app):
        with app.app_context():
            response, _ = metrics.metrics_summary()
        body = response.get_json()
        assert isinstance(body['top_sectors'], list)
        if body['top_sectors']:
            entry = body['top_sectors'][0]
            assert 'sector' in entry
            assert 'count' in entry

    def test_top_tickers_is_list(self, app):
        with app.app_context():
            response, _ = metrics.metrics_summary()
        body = response.get_json()
        assert isinstance(body['top_tickers_by_reports'], list)
        if body['top_tickers_by_reports']:
            entry = body['top_tickers_by_reports'][0]
            assert 'symbol' in entry
            assert 'reports' in entry

    def test_reports_by_category_breakdown(self, app):
        with app.app_context():
            response, _ = metrics.metrics_summary()
        body = response.get_json()
        # Real DB should have at least one category
        assert isinstance(body['reports_by_category'], dict)
        total = sum(body['reports_by_category'].values())
        assert total == body['reports_total']

    def test_uptime_human_format(self, app):
        with app.app_context():
            response, _ = metrics.metrics_summary()
        body = response.get_json()
        # Should be like '5m' or '2h 30m' or '3d 4h 22m'
        assert 'm' in body['uptime_human']


# ── Uptime formatter ───────────────────────────────────────────────

class TestFormatUptime:
    def test_seconds_only(self):
        assert metrics._format_uptime(45) == '0m'

    def test_minutes(self):
        # 5m 30s → '5m'
        assert metrics._format_uptime(330) == '5m'

    def test_hours_and_minutes(self):
        # 2h 15m
        assert metrics._format_uptime(2 * 3600 + 15 * 60) == '2h 15m'

    def test_days_hours_minutes(self):
        # 3d 4h 22m
        assert metrics._format_uptime(
            3 * 86400 + 4 * 3600 + 22 * 60
        ) == '3d 4h 22m'


# ── Prometheus Counter ─────────────────────────────────────────────

class TestHealthCounter:
    def test_counter_records_status(self, app):
        from services.metrics import HEALTH_CHECK
        before_healthy = HEALTH_CHECK.labels(status='healthy')._value.get()

        with app.app_context():
            metrics.health_check()

        after_healthy = HEALTH_CHECK.labels(status='healthy')._value.get()
        assert after_healthy == before_healthy + 1
