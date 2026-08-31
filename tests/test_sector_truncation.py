"""
Unit tests for v3.4.47 sector endpoint cap bump (Pattern 8c companion).

Covers:
- /api/industry/<sector>/news returns >50 items (was capped at Python >= 50)
- /api/sectors/<sector>/reports returns >50 items (was capped at SQL LIMIT 50)
- Old smoke rows reach the response even after cap increase

v3.4.47 — P3 fix: companion to v3.4.46 /api/reports bump. Pattern 8c (silent
pagination truncation) was hiding hundreds of industry news + sector reports.
"""

import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


SMOKE_NEWS_PREFIX = '__SECTOR_NEWS_TRUNC_TEST_'      # for /api/industry/<sector>/news
SMOKE_REPORTS_PREFIX = '__SECTOR_REPORTS_TRUNC_TEST_' # for /api/sectors/<sector>/reports


@pytest.fixture(scope='module')
def flask_client():
    """Flask test client — mirrors tests/test_report_search.py pattern."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def smoke_row_cleanup():
    """Clean up smoke rows after each test."""
    yield
    db = sqlite3.connect('/home/ubuntu/repos/Stocker/data/stocker.db')
    try:
        db.execute("DELETE FROM reports WHERE title LIKE ?",
                   (f'{SMOKE_NEWS_PREFIX}%',))
        db.execute("DELETE FROM reports WHERE title LIKE ?",
                   (f'{SMOKE_REPORTS_PREFIX}%',))
        db.commit()
    finally:
        db.close()


def _insert_industry_news(n: int, sector: str = 'Technology'):
    """Insert n industry-category rows with Technology_industry_ file_path prefix
    + VERY old timestamps so they always sort to the END of ORDER BY created_at DESC.
    """
    db = sqlite3.connect('/home/ubuntu/repos/Stocker/data/stocker.db')
    try:
        for i in range(n):
            db.execute(
                """INSERT INTO reports (title, source, category, summary, file_path,
                                         created_at, published_at)
                   VALUES (?, 'Test', 'industry', 'smoke', ?, '2000-01-01 00:00:00',
                           '2000-01-01')""",
                (f'{SMOKE_NEWS_PREFIX}{i:04d}',
                 f'/tmp/smoke/{sector}_industry_{i:04d}.txt'),
            )
        db.commit()
    finally:
        db.close()


def _insert_sector_reports(n: int, ticker: str = 'NVDA'):
    """Insert n news/analyst/earnings rows with NVDA in title (Technology sector)
    + VERY old timestamps. The endpoint searches for ticker-symbol mentions in
    title/content so we put NVDA in the title.
    """
    db = sqlite3.connect('/home/ubuntu/repos/Stocker/data/stocker.db')
    try:
        for i in range(n):
            db.execute(
                """INSERT INTO reports (title, source, category, summary, file_path,
                                         created_at, published_at)
                   VALUES (?, 'Test', 'news', 'smoke', ?, '2000-01-01 00:00:00',
                           '2000-01-01')""",
                (f'{SMOKE_REPORTS_PREFIX}{i:04d} NVDA old news',
                 f'/tmp/smoke/{SMOKE_REPORTS_PREFIX}{i:04d}.txt'),
            )
        db.commit()
    finally:
        db.close()


class TestIndustryNewsCap:
    """v3.4.47 regression tests for /api/industry/<sector>/news."""

    def test_news_returns_more_than_50(self, flask_client):
        """Pre-v3.4.47 returned exactly 50. Post-fix returns up to 200."""
        resp = flask_client.get('/api/industry/Technology/news')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 50, (
            f"Expected >50 items (DB has 191 Technology industry news), "
            f"got {len(data)}. Pre-v3.4.47 Python `if len(result) >= 50: break` "
            f"silently capped response at 50."
        )

    def test_old_smoke_news_reach_response(self, flask_client):
        """Insert 50 industry news rows with old timestamps. They must appear
        in the response (proving the SQL LIMIT is high enough)."""
        _insert_industry_news(50)

        resp = flask_client.get('/api/industry/Technology/news')
        assert resp.status_code == 200
        data = resp.get_json()

        old_smoke = [r for r in data if r['title'].startswith(SMOKE_NEWS_PREFIX)]
        # Should be at least some — the Python break is at 200 max but DB has
        # 191 real news + 50 smoke = 241; with cap=200 we get 191 + 9 = 200.
        assert len(old_smoke) > 0, (
            f"Expected smoke rows in response, got 0. Pre-v3.4.47 SQL LIMIT 500 "
            f"+ Python break at 50 was silently hiding the 50 oldest news."
        )

    def test_cap_at_least_200(self):
        """Static check: app.py Python break cap must be >= 200."""
        with open('/home/ubuntu/repos/Stocker/app.py') as f:
            text = f.read()
        assert 'if len(result) >= 200:' in text, (
            "app.py /api/industry/<sector>/news Python break must be at least 200. "
            "Bump it if this test fails — DB has 191 Technology news."
        )


class TestSectorReportsCap:
    """v3.4.47 regression tests for /api/sectors/<sector>/reports."""

    def test_reports_returns_more_than_50(self, flask_client):
        """Pre-v3.4.47 returned exactly 50. Post-fix returns up to 2000."""
        resp = flask_client.get('/api/sectors/Technology/reports')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        # DB has 184 Technology sector reports — was truncated to 50, now 184
        assert len(data) > 50, (
            f"Expected >50 items (DB has 184 Technology sector reports), "
            f"got {len(data)}. Pre-v3.4.47 SQL `LIMIT 50` silently capped."
        )

    def test_old_smoke_reports_reach_response(self, flask_client):
        """Insert 50 sector-report rows with old timestamps + NVDA in title.
        They must appear in the Technology sector response."""
        _insert_sector_reports(50)

        resp = flask_client.get('/api/sectors/Technology/reports')
        assert resp.status_code == 200
        data = resp.get_json()

        old_smoke = [r for r in data if r['title'].startswith(SMOKE_REPORTS_PREFIX)]
        assert len(old_smoke) > 0, (
            f"Expected smoke rows in response, got 0. Pre-v3.4.47 SQL LIMIT 50 "
            f"silently hid all 50 oldest sector reports (DB had 184 > 50)."
        )

    def test_sql_limit_at_least_2000(self):
        """Static check: app.py SQL LIMIT must be >= 2000."""
        with open('/home/ubuntu/repos/Stocker/app.py') as f:
            text = f.read()
        # Find the LIMIT clause inside api_sectors_reports (the one with
        # news/analyst_report/earnings category filter, not /api/reports).
        assert 'AND r.category IN (\'news\', \'analyst_report\', \'earnings\')' in text
        assert 'LIMIT 2000' in text, (
            "app.py /api/sectors/<sector>/reports SQL LIMIT must be >= 2000. "
            "Bump it if this test fails — DB has 316 Industrials reports."
        )
