"""
v3.4.72 — Dashboard report cards added_at pill (Pattern 9b orphan field).

Tests that /api/reports returns created_at (it does, since v3.3 ships) and that
the dashboard renderReports() now reads it via formatDate() + report.added_at
i18n key — same key already used by /report/<id> since v3.4.53.

Bilingual coverage guard mirrors v3.4.61 lesson: report.added_at must exist in
BOTH zh + en sections of i18n.js, otherwise English mode would surface the
literal key string 'report.added_at' as UI text.
"""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope='module')
def client():
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestReportsCreatedAtAPI:
    """Verify /api/reports returns created_at (sanity check before UI test)."""

    def test_endpoint_returns_created_at(self, client):
        resp = client.get('/api/reports?limit=10')
        data = resp.get_json()
        assert resp.status_code == 200
        rows = data if isinstance(data, list) else data.get('results', [])
        assert len(rows) > 0, 'No reports in DB to test against'
        # Every row must have a non-empty created_at
        missing = [r for r in rows if not r.get('created_at')]
        assert not missing, f'{len(missing)}/{len(rows)} rows missing created_at'

    def test_created_at_matches_iso_or_sqlite_pattern(self, client):
        """created_at can be either 'YYYY-MM-DD HH:MM:SS' (SQLite default) or
        ISO with T separator. formatDate() handles both via new Date()."""
        resp = client.get('/api/reports?limit=10')
        data = resp.get_json()
        rows = data if isinstance(data, list) else data.get('results', [])
        pat = re.compile(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}')
        for r in rows:
            assert pat.match(r['created_at']), f"Bad format: {r['created_at']!r}"


class TestReportsAddedAtMarkup:
    """Verify dashboard template renders the new added pill."""

    def _extract_render_reports(self):
        text = open(os.path.join(
            os.path.dirname(__file__), '..', 'templates', 'index.html'
        )).read()
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        return text, m.group(1) if m else ''

    def test_index_template_reports_added_class(self):
        text, _ = self._extract_render_reports()
        assert 'report-added' in text, 'report-added CSS class missing from index.html'

    def test_render_reports_reads_created_at(self):
        _, script = self._extract_render_reports()
        # Must read r.created_at in the renderReports function body
        assert 'r.created_at' in script or 'created_at' in script, \
            'renderReports() never reads created_at — orphan field regression'

    def test_render_reports_calls_formatDate_on_created_at(self):
        _, script = self._extract_render_reports()
        # The addedRaw computation must use formatDate (locale-aware)
        pat = re.compile(r'created_at\)?\s*\?\s*formatDate')
        assert pat.search(script), \
            'created_at is not passed through formatDate() — locale regression'

    def test_render_reports_wires_t_added_at(self):
        _, script = self._extract_render_reports()
        # Must call t('report.added_at', ...) for the i18n translation
        assert "t('report.added_at'" in script, \
            'renderReports() never calls t(report.added_at) — i18n not wired'


class TestReportsAddedAtCSS:
    """Verify CSS rules for the new pill."""

    def test_css_defines_report_added(self):
        css = open(os.path.join(
            os.path.dirname(__file__), '..', 'static', 'css', 'components.css'
        )).read()
        assert '.report-added' in css, '.report-added class missing from components.css'
        # flex-wrap + gap on .report-meta is the layout fix for 4-child overflow
        assert 'flex-wrap' in css, \
            '.report-meta lacks flex-wrap — narrow widths will overflow'

    def test_css_added_has_cursor_help(self):
        css = open(os.path.join(
            os.path.dirname(__file__), '..', 'static', 'css', 'components.css'
        )).read()
        m = re.search(r'\.report-added\s*\{([^}]+)\}', css, re.DOTALL)
        assert m is not None, '.report-added block not found in components.css'
        body = m.group(1)
        assert 'cursor: help' in body, \
            'report-added should have cursor:help for hover tooltip affordance'


class TestReportsAddedAtI18n:
    """Bilingual coverage guard — v3.4.61 lesson (zh-only keys surface literal)."""

    def _section_keys(self, lang_marker):
        text = open(os.path.join(
            os.path.dirname(__file__), '..', 'static', 'js', 'i18n.js'
        )).read()
        sections = re.split(r'^\s*(zh|en):\s*\{', text, flags=re.MULTILINE)
        if lang_marker == 'zh':
            body = sections[2]
        else:
            body = sections[4].split('function')[0]
        return set(re.findall(r"^\s+'([a-z][a-z0-9._]+)':", body, re.MULTILINE))

    def test_report_added_at_in_zh_section(self):
        keys = self._section_keys('zh')
        assert 'report.added_at' in keys, 'zh section missing report.added_at key'

    def test_report_added_at_in_en_section(self):
        keys = self._section_keys('en')
        assert 'report.added_at' in keys, \
            'en section MISSING report.added_at — English mode would surface literal key string'

    def test_report_added_at_uses_date_placeholder(self):
        text = open(os.path.join(
            os.path.dirname(__file__), '..', 'static', 'js', 'i18n.js'
        )).read()
        # Both zh + en must use {date} placeholder so formatDate output substitutes
        for m in re.finditer(r"'report\.added_at':\s*'([^']+)'", text):
            val = m.group(1)
            assert '{date}' in val, \
                f'report.added_at missing {{date}} placeholder: {val!r}'


class TestE2ESmoke:
    """End-to-end: page loads, served HTML contains wiring."""

    def test_dashboard_returns_200(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_served_html_has_report_added_class(self, client):
        resp = client.get('/')
        body = resp.get_data(as_text=True)
        assert 'report-added' in body, \
            'Served HTML missing report-added markup'

    def test_served_html_has_report_added_at_i18n_binding(self, client):
        resp = client.get('/')
        body = resp.get_data(as_text=True)
        assert 'report.added_at' in body, \
            "Served HTML missing 'report.added_at' i18n binding reference"