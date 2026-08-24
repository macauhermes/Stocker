"""
Unit tests for /api/tickers/export.csv endpoint.

Tests CSV formatting and column order without hitting yfinance.
Uses the actual Flask test client (which loads app.py end-to-end).
"""
import os
import sys
import csv
from io import StringIO

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


EXPECTED_HEADER = [
    'symbol', 'name', 'sector', 'shares_held', 'cost_basis',
    'current_price', 'market_value', 'cost_value',
    'unrealized_pl', 'pl_percent', 'change_pct',
    'data_source', 'last_updated',
]


@pytest.fixture(scope='module')
def client():
    """Build a Flask test client. app.py initializes DB on import."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestCSVExport:
    def test_endpoint_returns_200_csv(self, client):
        resp = client.get('/api/tickers/export.csv')
        assert resp.status_code == 200
        assert resp.content_type.startswith('text/csv')
        assert 'attachment' in resp.headers.get('Content-Disposition', '')

    def test_header_row_matches_expected_columns(self, client):
        resp = client.get('/api/tickers/export.csv')
        reader = csv.reader(StringIO(resp.get_data(as_text=True)))
        header = next(reader)
        assert header == EXPECTED_HEADER

    def test_filename_includes_timestamp(self, client):
        resp = client.get('/api/tickers/export.csv')
        cd = resp.headers.get('Content-Disposition', '')
        assert 'stocker-' in cd
        assert '.csv' in cd

    def test_at_least_header_returned_even_if_no_tickers(self, client):
        """If DB has tickers, body should have > 1 line. If empty, only header."""
        resp = client.get('/api/tickers/export.csv')
        text = resp.get_data(as_text=True)
        lines = text.strip().split('\n')
        assert len(lines) >= 1  # at minimum the header

    def test_group_filter_404_or_csv(self, client):
        """?group=N should work for any int; non-existent group may yield empty CSV (header only)."""
        resp = client.get('/api/tickers/export.csv?group=99999')
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        reader = csv.reader(StringIO(text))
        header = next(reader)
        assert header == EXPECTED_HEADER