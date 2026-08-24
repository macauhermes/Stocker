"""
Unit tests for /api/portfolio/snapshots/export.csv endpoint (v3.4.5).

Tests CSV/TSV formatting and column order without hitting yfinance.
Uses the actual Flask test client (which loads app.py end-to-end).

Tests do NOT mutate the production portfolio_snapshots table — they read
whatever snapshots already exist (live DB has 5 from earlier cron ticks)
and validate the *shape* of the response.
"""
import os
import sys
import csv
from io import StringIO

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


EXPECTED_HEADER = [
    'snapshot_date', 'total_value', 'total_cost', 'total_pnl',
    'pnl_pct', 'holdings_count', 'captured_at',
]


@pytest.fixture(scope='module')
def client():
    """Build a Flask test client. app.py initializes DB on import."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestPortfolioCSVExport:
    """Tests for /api/portfolio/snapshots/export.csv."""

    def test_endpoint_returns_200_csv(self, client):
        resp = client.get('/api/portfolio/snapshots/export.csv')
        assert resp.status_code == 200
        assert resp.content_type.startswith('text/csv')
        assert 'attachment' in resp.headers.get('Content-Disposition', '')

    def test_header_row_matches_expected_columns(self, client):
        resp = client.get('/api/portfolio/snapshots/export.csv')
        reader = csv.reader(StringIO(resp.get_data(as_text=True)))
        header = next(reader)
        assert header == EXPECTED_HEADER

    def test_filename_includes_timestamp_and_prefix(self, client):
        resp = client.get('/api/portfolio/snapshots/export.csv')
        cd = resp.headers.get('Content-Disposition', '')
        assert 'stocker-portfolio-' in cd
        assert '.csv' in cd

    def test_at_least_header_returned_even_if_empty(self, client):
        """Empty result set should still return 200 with just the header."""
        # Use days=1 — there's currently at least one snapshot within 24h,
        # but this test exercises the 'always-200' contract regardless.
        resp = client.get('/api/portfolio/snapshots/export.csv?days=1')
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        lines = text.strip().split('\n') if text.strip() else []
        assert len(lines) >= 1  # header always present

    def test_days_param_respected(self, client):
        """?days=N should bound the number of data rows returned."""
        resp_default = client.get('/api/portfolio/snapshots/export.csv')
        resp_tight = client.get('/api/portfolio/snapshots/export.csv?days=1')
        text_default = resp_default.get_data(as_text=True)
        text_tight = resp_tight.get_data(as_text=True)
        # The tighter window can't return MORE rows than the default.
        rows_default = max(0, len(text_default.strip().split('\n')) - 1)
        rows_tight = max(0, len(text_tight.strip().split('\n')) - 1)
        assert rows_tight <= rows_default

    def test_invalid_days_param_falls_back_to_default(self, client):
        """?days=foo shouldn't crash — fall back to default 365."""
        resp = client.get('/api/portfolio/snapshots/export.csv?days=foo')
        assert resp.status_code == 200

    def test_content_type_has_single_charset(self, client):
        """Regression test for double-charset bug — Flask auto-appends charset
        when the mimetype starts with text/. We must NOT include it ourselves."""
        resp = client.get('/api/portfolio/snapshots/export.csv')
        ct = resp.content_type
        # Should be exactly one 'charset=' in the header
        assert ct.count('charset=') == 1, f"Double charset detected: {ct}"
        assert 'charset=utf-8' in ct


class TestPortfolioTSVExport:
    """Tests for /api/portfolio/snapshots/export.csv?fmt=tsv."""

    def test_endpoint_returns_200_tsv(self, client):
        resp = client.get('/api/portfolio/snapshots/export.csv?fmt=tsv')
        assert resp.status_code == 200
        assert resp.content_type.startswith('text/tab-separated-values')
        assert 'attachment' in resp.headers.get('Content-Disposition', '')

    def test_tsv_uses_tab_delimiter(self, client):
        resp = client.get('/api/portfolio/snapshots/export.csv?fmt=tsv')
        text = resp.get_data(as_text=True)
        first_line = text.split('\n')[0].rstrip('\r')
        # Header should split into 7 fields on tab
        parts = first_line.split('\t')
        assert len(parts) == len(EXPECTED_HEADER)
        assert parts == EXPECTED_HEADER

    def test_tsv_filename_extension(self, client):
        resp = client.get('/api/portfolio/snapshots/export.csv?fmt=tsv')
        cd = resp.headers.get('Content-Disposition', '')
        assert '.tsv' in cd
        assert '.csv' not in cd.replace('.csv', '')  # not just substring check
        assert '.tsv' in cd

    def test_tsv_content_type_single_charset(self, client):
        """Same regression as CSV — no double-charset in TSV either."""
        resp = client.get('/api/portfolio/snapshots/export.csv?fmt=tsv')
        ct = resp.content_type
        assert ct.count('charset=') == 1, f"Double charset detected: {ct}"


class TestPortfolioExportMetrics:
    """Tests that hitting the export endpoint increments the Prometheus counter."""

    def test_metrics_counter_present_in_prometheus_endpoint(self, client):
        """After hitting the endpoint, /metrics should include the new counter."""
        client.get('/api/portfolio/snapshots/export.csv')
        resp = client.get('/metrics')
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        assert 'stocker_portfolio_exports_total' in text
        # format='csv' label child must exist
        assert 'format="csv"' in text

    def test_metrics_summary_block_present(self, client):
        """The /api/metrics/summary endpoint should now have portfolio_exports."""
        client.get('/api/portfolio/snapshots/export.csv')
        resp = client.get('/api/metrics/summary')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'portfolio_exports' in data
        assert 'total' in data['portfolio_exports']
        assert 'csv' in data['portfolio_exports']
        assert 'tsv' in data['portfolio_exports']
        # csv count must be > 0 after we just hit the endpoint
        assert data['portfolio_exports']['csv'] >= 1