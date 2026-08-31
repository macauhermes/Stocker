"""
Regression test for v3.4.60 — surface `added_at` on stock cards (Pattern 9b
orphan field). `/api/tickers` returns 19 top-level keys including `added_at`
(SQLite `datetime('now')` stamp at ticker INSERT). Dashboard `renderStocks()`
added a 4th-line `.stock-tracking` div that reads `ticker.added_at` via
`formatDate()` (locale-aware per v3.4.34).

Bug class guard: if a future refactor drops the `added_at` field from the
serialized response, the JS still runs but the tracking line silently becomes
"—" or empty. This test catches that at the API boundary before the UI ships
a regression.

What we verify:
  - /api/tickers returns 200 OK with a list of dicts
  - Every ticker row has an `added_at` field that is non-empty + parseable
  - The added_at string matches `YYYY-MM-DD HH:MM:SS` (SQLite default format)
"""
import os
import sys
import re
import sqlite3

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


SQLITE_DATETIME_RE = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')


@pytest.fixture(scope='module')
def client():
    """Flask test client. app.py initializes DB + Prometheus on import."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestTickersAddedAt:
    def test_added_at_in_response(self, client):
        resp = client.get('/api/tickers')
        assert resp.status_code == 200, f'Expected 200 OK, got {resp.status_code}'
        data = resp.get_json()
        assert isinstance(data, list), f'Expected list, got {type(data)}'
        assert len(data) >= 1, 'No tickers in DB'

    def test_all_rows_have_populated_added_at(self, client):
        resp = client.get('/api/tickers')
        data = resp.get_json()
        for t in data:
            assert 'added_at' in t, f'Ticker {t.get("symbol")} missing added_at field'
            added = t['added_at']
            assert added is not None, f'Ticker {t.get("symbol")} added_at is None'
            assert added != '', f'Ticker {t.get("symbol")} added_at is empty'
            assert SQLITE_DATETIME_RE.match(added), (
                f'Ticker {t.get("symbol")} added_at={added!r} does not match '
                f'YYYY-MM-DD HH:MM:SS format'
            )

    def test_added_at_matches_db(self, client):
        """Cross-check that the API's added_at matches what's in the DB directly."""
        # Read DB
        db = sqlite3.connect(os.path.expanduser('~/repos/Stocker/data/stocker.db'))
        try:
            db_rows = db.execute(
                "SELECT symbol, added_at FROM tickers WHERE archived = 0"
            ).fetchall()
            db_added = {row[0]: row[1] for row in db_rows if row[1]}
        finally:
            db.close()

        # Read API
        resp = client.get('/api/tickers')
        data = resp.get_json()
        api_added = {t['symbol']: t['added_at'] for t in data}

        # Every DB entry should appear in API with matching value
        for sym, db_val in db_added.items():
            assert sym in api_added, f'{sym} in DB but missing from /api/tickers'
            assert api_added[sym] == db_val, (
                f'{sym} added_at mismatch: DB={db_val!r} API={api_added[sym]!r}'
            )
