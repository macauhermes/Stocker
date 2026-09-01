"""
Unit tests for v3.4.75 — /api/portfolio/summary.latest.captured_at surfacing
on dashboard portfolio card.

Bug class: Pattern 9b (orphan field). /api/portfolio/summary returns
`latest.captured_at` field (10/10 snapshots populated, ISO datetime like
'2026-09-01 12:02:02') — but the dashboard `loadPortfolioSummary()` only
consumed `snapshot_date` (just the date part). User saw "今日快照：2026-09-01"
with no time-of-day context — couldn't tell whether the snapshot was
captured at noon, evening (nightly cron), or backfilled for a previous day.

Companion fields on snapshots_log table (`portfolio.snapshots_log_captured`,
`portfolio.snapshots_log_backfilled`) already use `captured_at` — but the
dashboard portfolio card silently dropped it.

This test asserts:
  - /api/portfolio/summary returns non-empty latest.captured_at (live endpoint check)
  - templates/index.html loadPortfolioSummary() now reads v.captured_at
    and uses formatDateTime() to render it
  - The portfolio-snapshot-date element receives both date + time (locale-aware)
  - formatDateTime helper exists in i18n.js (Pattern 5e guard — locale-aware)
  - portfolio.snapshot_today key exists in BOTH zh + en sections of i18n.js
    (Pattern 5d sub-class v3.4.61 lesson — bilingual coverage guard)
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


INDEX_HTML = os.path.join(
    os.path.dirname(__file__), '..', 'templates', 'index.html'
)
I18N_JS = os.path.join(
    os.path.dirname(__file__), '..', 'static', 'js', 'i18n.js'
)


@pytest.fixture(scope='module')
def client():
    """Flask test client (live DB, no inserts — read-only tests)."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestCapturedAtAPI:
    """/api/portfolio/summary must return latest.captured_at populated."""

    def test_summary_includes_captured_at(self, client):
        resp = client.get('/api/portfolio/summary')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('has_history') is True
        latest = data.get('latest', {})
        assert latest, "no latest snapshot returned"
        assert 'captured_at' in latest, (
            'summary endpoint missing captured_at field — '
            'pattern 9b bug: endpoint dropped the field between DB and JSON'
        )
        assert latest['captured_at'], (
            f'captured_at should be populated, got {latest["captured_at"]!r}'
        )
        # SQLite timestamp format: 'YYYY-MM-DD HH:MM:SS' (or ISO equivalent)
        ca = latest['captured_at']
        assert re.match(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', ca), (
            f'captured_at {ca!r} not in expected timestamp format'
        )


class TestCapturedAtMarkup:
    """index.html loadPortfolioSummary must read v.captured_at and render it."""

    def _script_block(self):
        text = open(INDEX_HTML, encoding='utf-8').read()
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        assert m, 'no <script> block in index.html'
        return m.group(1)

    def test_js_handler_reads_captured_at(self):
        script = self._script_block()
        assert 'v.captured_at' in script, (
            "loadPortfolioSummary() does not read v.captured_at — "
            "the orphan field is still silently dropped"
        )

    def test_js_handler_uses_formatdatetime_helper(self):
        """Locale-aware formatting (Pattern 5e guard)."""
        script = self._script_block()
        # Locate the loadPortfolioSummary() body via brace matching
        # (regex stops at first nested `}`, so use brace-match)
        m = re.search(r'async function loadPortfolioSummary\s*\(\)\s*\{', script)
        assert m, "loadPortfolioSummary() not found"
        depth, i = 1, m.end()
        while i < len(script) and depth > 0:
            if script[i] == '{': depth += 1
            elif script[i] == '}': depth -= 1
            i += 1
        body = script[m.end():i - 1]
        assert 'formatDateTime' in body, (
            "loadPortfolioSummary() does not call formatDateTime() — "
            "should use locale-aware datetime helper for captured_at"
        )

    def test_date_element_receives_both_date_and_time(self):
        """dateEl.textContent must include captured_at time appended after snapshot_date."""
        script = self._script_block()
        # Both should appear in the same line/region
        # Look for: dateEl.textContent = ... t('portfolio.snapshot_today' ... captured_at ...
        m = re.search(
            r'dateEl\.textContent\s*=.*?captured_at',
            script, re.DOTALL
        )
        assert m, (
            "dateEl.textContent assignment does not reference captured_at — "
            "the field is read but not actually rendered"
        )

    def test_captured_at_conditional_guard(self):
        """Defensive guard: formatDateTime('') must not produce 'Invalid Date'."""
        script = self._script_block()
        # Find a region around `v.captured_at` reference and verify truthy guard
        ctx_start = script.find('v.captured_at')
        if ctx_start == -1:
            pytest.fail('v.captured_at reference not found')
        # 200 chars around the reference should include a truthy guard
        ctx = script[max(0, ctx_start - 200):ctx_start + 200]
        # Should contain either `?` ternary or `&&` guard
        assert '?' in ctx or '&&' in ctx, (
            "v.captured_at should be guarded with a truthy check — "
            "missing captured_at would formatDateTime('') → 'Invalid Date'"
        )


class TestFormatDateTimeHelper:
    """formatDateTime() must be defined in i18n.js (locale-aware, Pattern 5e)."""

    def test_helper_defined(self):
        text = open(I18N_JS, encoding='utf-8').read()
        m = re.search(r'function formatDateTime\s*\([^)]*\)', text)
        assert m, "formatDateTime() helper not defined in i18n.js"

    def test_helper_uses_locale_variable(self):
        """Locale-aware: must read _lang to pick zh-TW vs en-US."""
        text = open(I18N_JS, encoding='utf-8').read()
        m = re.search(
            r'function formatDateTime\s*\([^)]*\)\s*\{(.*?)^\s*\}',
            text, re.DOTALL | re.MULTILINE
        )
        assert m, "formatDateTime() body not extractable"
        body = m.group(1)
        assert '_lang' in body, (
            "formatDateTime() must check _lang to pick locale — "
            "Pattern 5e guard against hardcoded 'zh-TW'"
        )


class TestSnapshotTodayI18n:
    """portfolio.snapshot_today must exist in BOTH zh + en sections."""

    def test_zh_section(self):
        text = open(I18N_JS, encoding='utf-8').read()
        m = re.search(r"'portfolio\.snapshot_today':\s*'([^']+)'", text)
        assert m, "portfolio.snapshot_today key not found in i18n.js"
        value = m.group(1)
        assert any(ord(c) > 127 for c in value), (
            f"portfolio.snapshot_today zh value '{value}' contains no CJK chars — "
            f"are you sure zh section was updated?"
        )
        assert '{date}' in value, (
            f"portfolio.snapshot_today zh value missing {{date}} placeholder: {value!r}"
        )

    def test_en_section(self):
        """Bilingual coverage guard — v3.4.61 Pattern 5d sub-class lesson."""
        text = open(I18N_JS, encoding='utf-8').read()
        matches = re.findall(r"'portfolio\.snapshot_today':\s*'([^']+)'", text)
        assert len(matches) >= 2, (
            f"portfolio.snapshot_today only found {len(matches)} time(s) — "
            f"both zh + en sections must define it (v3.4.61 Pattern 5d sub-class)"
        )
        en = [m for m in matches if all(ord(c) < 128 for c in m)]
        assert en, "No English version of portfolio.snapshot_today found"
        assert '{date}' in en[0], (
            f"portfolio.snapshot_today en value missing {{date}} placeholder: {en[0]!r}"
        )


class TestCapturedAtE2ESmoke:
    """End-to-end: page renders 200 OK + served HTML contains the binding."""

    def test_dashboard_returns_200(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_served_html_has_captured_at_binding(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        assert 'v.captured_at' in text, (
            "Served HTML missing v.captured_at binding — "
            "the field is read but template wasn't actually updated"
        )
        assert 'portfolio-snapshot-date' in text, (
            "Served HTML missing #portfolio-snapshot-date element"
        )
