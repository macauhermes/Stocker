"""
Unit tests for v3.4.3 Report Search feature.

Covers:
- models.search_reports() — all 4 filter dimensions (q, category, source, ticker)
- models.count_search_results() — total count for the same filters
- Combined AND filters
- Empty/None filter handling
- Order by created_at DESC
- Limit param

v3.4.3 — P3 feature: user-facing report search.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models


# ── Fixtures (function-scope, mirrors test_alert_checker pattern) ────────


@pytest.fixture
def temp_db():
    """Create a temp SQLite DB with full Stocker schema."""
    tmp = tempfile.mkdtemp(prefix='stocker-report-search-test-')
    db_path = os.path.join(tmp, 'stocker.db')
    original = models.DB_PATH
    models.DB_PATH = db_path
    try:
        models.init_db()
        yield db_path
    finally:
        models.DB_PATH = original


@pytest.fixture
def seeded_reports(temp_db):
    """Insert a known mix of reports across categories/sources/tickers."""
    conn = models.get_db()
    rows = [
        # GLW SEC earnings
        ('GLW 10-K (2026-02-12)', 'SEC EDGAR', 'earnings',
         'Annual report for Corning Inc', '/home/x/data/files/earnings/GLW_10-K_2026-02-12.htm'),
        ('GLW 10-Q (2026-05-01)', 'SEC EDGAR', 'earnings',
         'Quarterly report', '/home/x/data/files/earnings/GLW_10-Q_2026-05-01.htm'),
        # IBM SEC earnings
        ('IBM 10-K (2026-02-24)', 'SEC EDGAR', 'earnings',
         'IBM annual report', '/home/x/data/files/earnings/IBM_10-K_2026-02-24.htm'),
        ('IBM 10-Q (2026-04-23)', 'SEC EDGAR', 'earnings',
         'IBM quarterly report', '/home/x/data/files/earnings/IBM_10-Q_2026-04-23.htm'),
        # TSLA industry news
        ('TSLA Q4 earnings preview', 'Reuters', 'industry',
         'Tesla market outlook', '/home/x/data/files/industry/TSLA_news_2026.htm'),
        ('TSLA delivery numbers', 'Bloomberg', 'industry',
         'Tesla deliveries beat estimates', '/home/x/data/files/industry/TSLA_deliveries.htm'),
        # Analyst report
        ('TSLA deep dive', 'Goldman Sachs Research', 'analyst_report',
         'Long thesis on TSLA', '/home/x/data/files/analyst_report/TSLA_goldman.htm'),
        # SPCX prospectus (no ticker prefix in path)
        ('SpaceX S-1', 'SEC EDGAR', 'sec_filing',
         'SpaceX IPO prospectus', '/home/x/data/files/sec_filing/SPCX_S1.htm'),
    ]
    for title, source, category, summary, file_path in rows:
        conn.execute(
            """INSERT INTO reports (title, source, category, summary, file_path)
               VALUES (?, ?, ?, ?, ?)""",
            (title, source, category, summary, file_path),
        )
    conn.commit()
    conn.close()
    return rows


# ── search_reports tests ────────────────────────────────────────────────


class TestSearchReports:
    def test_no_filters_returns_all(self, seeded_reports):
        results = models.search_reports(limit=100)
        assert len(results) == 8

    def test_all_none_filters_acts_like_no_filters(self, seeded_reports):
        results = models.search_reports(query=None, category=None, source=None,
                                        ticker=None, limit=100)
        assert len(results) == 8

    def test_empty_string_filters_treated_as_none(self, seeded_reports):
        results = models.search_reports(query='', category='', source='', ticker='', limit=100)
        assert len(results) == 8

    def test_query_matches_title(self, seeded_reports):
        results = models.search_reports(query='10-K')
        titles = [r['title'] for r in results]
        assert len(results) == 2
        assert all('10-K' in t for t in titles)

    def test_query_matches_summary(self, seeded_reports):
        results = models.search_reports(query='prospectus')
        assert len(results) == 1
        assert 'SpaceX' in results[0]['title']

    def test_query_is_case_insensitive(self, seeded_reports):
        upper = models.search_reports(query='IBM')
        lower = models.search_reports(query='ibm')
        assert len(upper) == len(lower) == 2

    def test_query_whitespace_stripped(self, seeded_reports):
        results = models.search_reports(query='  10-K  ')
        assert len(results) == 2

    def test_category_filter_exact_match(self, seeded_reports):
        results = models.search_reports(category='earnings')
        assert len(results) == 4
        assert all(r['category'] == 'earnings' for r in results)

    def test_category_filter_case_insensitive(self, seeded_reports):
        upper = models.search_reports(category='EARNINGS')
        lower = models.search_reports(category='earnings')
        assert len(upper) == len(lower) == 4

    def test_source_filter(self, seeded_reports):
        results = models.search_reports(source='SEC EDGAR')
        assert len(results) == 5  # 4 earnings + 1 sec_filing
        assert all(r['source'] == 'SEC EDGAR' for r in results)

    def test_ticker_filter_derives_from_file_path(self, seeded_reports):
        results = models.search_reports(ticker='GLW')
        assert len(results) == 2
        assert all('GLW' in r['file_path'] for r in results)

    def test_ticker_filter_uppercases_input(self, seeded_reports):
        upper = models.search_reports(ticker='tsla')
        lower = models.search_reports(ticker='TSLA')
        assert len(upper) == len(lower) == 3  # 2 industry + 1 analyst

    def test_combined_filters_AND(self, seeded_reports):
        results = models.search_reports(ticker='IBM', category='earnings')
        assert len(results) == 2

        results = models.search_reports(category='earnings', source='SEC EDGAR',
                                        ticker='GLW')
        assert len(results) == 2

    def test_filters_with_no_results_returns_empty(self, seeded_reports):
        results = models.search_reports(query='nonexistent_xyz_query')
        assert results == []

    def test_results_ordered_by_created_at_desc(self, seeded_reports):
        # All seeded at roughly same time, but ordering should still be DESC
        results = models.search_reports(category='earnings')
        timestamps = [r['created_at'] for r in results]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_limit_caps_results(self, seeded_reports):
        results = models.search_reports(limit=3)
        assert len(results) == 3

    def test_query_with_no_match_returns_empty(self, seeded_reports):
        results = models.search_reports(query='zzzz_no_match')
        assert len(results) == 0


# ── count_search_results tests ──────────────────────────────────────────


class TestCountSearchResults:
    def test_no_filters_returns_total(self, seeded_reports):
        assert models.count_search_results() == 8

    def test_query_count(self, seeded_reports):
        assert models.count_search_results(query='10-K') == 2
        assert models.count_search_results(query='IBM') == 2
        assert models.count_search_results(query='nope') == 0

    def test_category_count(self, seeded_reports):
        assert models.count_search_results(category='earnings') == 4
        assert models.count_search_results(category='industry') == 2

    def test_source_count(self, seeded_reports):
        assert models.count_search_results(source='SEC EDGAR') == 5

    def test_ticker_count(self, seeded_reports):
        assert models.count_search_results(ticker='GLW') == 2
        assert models.count_search_results(ticker='TSLA') == 3

    def test_combined_count(self, seeded_reports):
        assert models.count_search_results(ticker='IBM', category='earnings') == 2

    def test_count_matches_search_results_length(self, seeded_reports):
        # Without limit, count should equal len(search_results(limit=very_large))
        for combo in [
            {'query': '10-K'},
            {'category': 'earnings'},
            {'source': 'SEC EDGAR'},
            {'ticker': 'GLW'},
            {'ticker': 'IBM', 'category': 'earnings'},
            {},
        ]:
            cnt = models.count_search_results(**combo)
            results = models.search_reports(limit=1000, **combo)
            assert cnt == len(results), f"mismatch for {combo}: count={cnt}, results={len(results)}"


# ── v3.4.46 regression tests — /api/reports cap behavior ───────────────────
#
# Pre-v3.4.46, /api/reports capped at limit=500 (app.py:api_get_reports) which
# silently dropped all 23 investment_bank_report + sec_filing rows because they
# were older than the 500th-most-recent report. v3.4.46 raises the cap to 2000.
#
# These tests verify:
#   (a) The cap honors the request (limit=2000 returns up to 2000, limit=50
#       returns exactly 50).
#   (b) The cap is high enough to cover the live DB as of 2026-08-31 (1095 rows).
#
# Uses smoke-prefix pattern (Pitfall 17) — Flask test client + insert/delete
# cleanup. Cannot use temp_db here because the route imports app.py which
# wires models.DB_PATH at import time (Pitfall 17 + reload fragility).


import json
import sys

import pytest


SMOKE_PREFIX = '__REPORTS_CAP_TEST_'


@pytest.fixture(scope='module')
def flask_client():
    """Flask test client. app.py initializes DB + Prometheus on import."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def smoke_row_cleanup():
    """Clean up any smoke-test rows after each test."""
    yield
    import sqlite3
    db = sqlite3.connect('/home/ubuntu/repos/Stocker/data/stocker.db')
    try:
        db.execute("DELETE FROM reports WHERE title LIKE ?", (f'{SMOKE_PREFIX}%',))
        db.commit()
    finally:
        db.close()


def _insert_reports(n: int):
    """Insert n reports with synthetic title (marker for cleanup) + old created_at."""
    import sqlite3
    db = sqlite3.connect('/home/ubuntu/repos/Stocker/data/stocker.db')
    try:
        # Use a very old timestamp (2000-01-01) so these rows always sort to the
        # END of ORDER BY created_at DESC — exactly where the v3.4.46 bug bit.
        for i in range(n):
            db.execute(
                """INSERT INTO reports (title, source, category, summary, file_path,
                                         created_at, published_at)
                   VALUES (?, 'Test', 'earnings', 'smoke', ?, '2000-01-01 00:00:00',
                           '2000-01-01')""",
                (f'{SMOKE_PREFIX}old_{i:04d}',
                 f'/tmp/smoke/{SMOKE_PREFIX}old_{i:04d}.htm'),
            )
        db.commit()
    finally:
        db.close()


class TestReportsCap:
    """v3.4.46 regression tests for /api/reports limit cap behavior."""

    def test_limit_param_honors_request(self, flask_client):
        """limit=50 returns at most 50 results."""
        # Default test row count is small (1095 - won't matter); just verify
        # the response respects the limit.
        resp = flask_client.get('/api/reports?limit=50')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) <= 50

    def test_old_rows_not_silently_dropped(self, flask_client):
        """Insert 50 OLD rows (2000-01-01) and confirm they all appear in
        /api/reports?limit=2000 response — they would have been dropped under
        the pre-v3.4.46 LIMIT 500 if the live DB had >500 newer rows.
        """
        _insert_reports(50)

        resp = flask_client.get('/api/reports?limit=2000')
        assert resp.status_code == 200
        data = resp.get_json()

        old_smoke = [r for r in data if r['title'].startswith(SMOKE_PREFIX)]
        # All 50 smoke rows must be present (they sort to the END but cap=2000
        # is high enough to include them).
        assert len(old_smoke) == 50, (
            f"Expected 50 smoke rows in response, got {len(old_smoke)}. "
            f"Pre-v3.4.46 LIMIT 500 silently dropped rows older than the "
            f"500th-most-recent report — bug class: silent pagination truncation."
        )

    def test_cap_at_least_2000(self):
        """Static check: app.py constant must be >= 2000."""
        # Read app.py source directly (no import — keep test fast)
        with open('/home/ubuntu/repos/Stocker/app.py') as f:
            text = f.read()
        assert 'min(request.args.get(\'limit\', 50, type=int), 2000)' in text, (
            "app.py /api/reports cap must be at least 2000 to cover the "
            "current 1095-row DB with headroom. Bump it if this test fails."
        )