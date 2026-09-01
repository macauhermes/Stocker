"""
v3.4.71 — Pattern 9b orphan-field surfacing for r.url on report cards.

Background: /api/reports returns 1247 reports, 1031 (82.7%) have a non-null `url`
field (external source link). Before this commit, only the dedicated /report/<id>
detail page surfaced that link (via `report-link` button). The card lists on
dashboard / stock_detail (related reports) / industry (sector news+reports) all
silently dropped `r.url` between API and DOM.

This test verifies the new open_in_new icon renders on cards that have a URL,
and is absent on cards without one. Also verifies Pattern 5c wiring
(data-i18n-title attribute set so applyI18n() rewrites the title to the current
language).
"""
import json
import os
import re
import urllib.request

import pytest

REPO = os.path.expanduser('~/repos/Stocker')


def _extract_function_body(source, fn_name):
    """Brace-matching extraction for JS function bodies.

    Regex `(.*?)` stops at the first `}` which fails for nested-brace functions
    (e.g. if/else with multi-line blocks). v3.4.70 lesson from
    test_volume_subchart.py — same fix applied here.
    """
    m = re.search(rf'function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{', source)
    if not m:
        return None
    depth = 1
    i = m.end()
    while i < len(source) and depth > 0:
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return source[m.end():i - 1]


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------

class TestReportUrlApiSurface:
    """Verify /api/reports actually returns a populated `url` field."""

    @pytest.fixture(scope='class')
    def api_reports(self):
        with urllib.request.urlopen(
            'http://localhost:5000/api/reports?limit=2000', timeout=5
        ) as resp:
            return json.loads(resp.read())

    def test_returns_url_field(self, api_reports):
        assert api_reports, 'API returned no reports'
        sample = api_reports[0]
        assert 'url' in sample, 'API response missing url field'

    def test_majority_populated(self, api_reports):
        with_url = sum(1 for r in api_reports if r.get('url'))
        ratio = with_url / len(api_reports)
        # v3.4.71 baseline: 1031/1247 = 82.7%. Threshold guards against regression
        # where someone refactors /api/reports and the URL field gets dropped.
        assert ratio >= 0.5, (
            f'Only {with_url}/{len(api_reports)} ({ratio:.1%}) reports have url. '
            f'Expected ≥50% per v3.4.71 baseline (82.7%).'
        )

    def test_urls_are_http(self, api_reports):
        """URLs must be http/https for window.open() to work."""
        for r in api_reports:
            u = r.get('url')
            if u:
                assert u.startswith(('http://', 'https://')), f'Bad URL: {u!r}'


# ---------------------------------------------------------------------------
# Generic wiring assertions — apply to all 3 card-renderer consumers
# ---------------------------------------------------------------------------

WIRING_REQUIRED = [
    # ('string pattern', 'assertion message')
    ('report-source-link', 'must include .report-source-link span'),
    (r'r\.url\s*&&', 'must guard on r.url truthy'),
    (r'\^https', 'must validate http(s) scheme via regex'),
    ('noopener,noreferrer', 'window.open() must use noopener,noreferrer'),
    ('event.preventDefault()', 'click handler must preventDefault'),
    ('event.stopPropagation()', 'click handler must stopPropagation'),
    ('data-i18n-title="report.view_source"', 'must wire data-i18n-title for hover tooltip'),
]


def _assert_wired(body, renderer_name):
    for pat, msg in WIRING_REQUIRED:
        assert re.search(pat, body), f'{renderer_name}: {msg} (pattern={pat!r})'


# ---------------------------------------------------------------------------
# Dashboard reports tab — index.html renderReports()
# ---------------------------------------------------------------------------

class TestDashboardReportUrlSurfacing:
    PAGE = os.path.join(REPO, 'templates/index.html')

    @pytest.fixture(scope='class')
    def body(self):
        text = open(self.PAGE).read()
        body = _extract_function_body(text, 'renderReports')
        assert body is not None, 'Could not extract renderReports body from index.html'
        return body

    def test_wiring_complete(self, body):
        _assert_wired(body, 'index.html renderReports')


# ---------------------------------------------------------------------------
# Stock detail related reports — stock_detail.html renderRelatedReports()
# ---------------------------------------------------------------------------

class TestRelatedReportsUrlSurfacing:
    PAGE = os.path.join(REPO, 'templates/stock_detail.html')

    @pytest.fixture(scope='class')
    def body(self):
        text = open(self.PAGE).read()
        body = _extract_function_body(text, 'renderRelatedReports')
        assert body is not None, 'Could not extract renderRelatedReports body from stock_detail.html'
        return body

    def test_wiring_complete(self, body):
        _assert_wired(body, 'stock_detail.html renderRelatedReports')


# ---------------------------------------------------------------------------
# Industry sector news + reports — industry.html renderReports() (two modes)
# ---------------------------------------------------------------------------

class TestIndustryReportUrlSurfacing:
    PAGE = os.path.join(REPO, 'templates/industry.html')

    @pytest.fixture(scope='class')
    def body(self):
        text = open(self.PAGE).read()
        # industry.html: `function renderReports(reports, listEl, opts = {})`
        body = _extract_function_body(text, 'renderReports')
        assert body is not None, 'Could not extract renderReports body from industry.html'
        return body

    def test_wiring_complete(self, body):
        _assert_wired(body, 'industry.html renderReports')


# ---------------------------------------------------------------------------
# CSS — visual styling
# ---------------------------------------------------------------------------

class TestReportSourceLinkCss:
    CSS = os.path.join(REPO, 'static/css/components.css')

    def test_class_defined(self):
        text = open(self.CSS).read()
        assert '.report-source-link {' in text, (
            'CSS missing .report-source-link styles'
        )

    def test_hover_state(self):
        text = open(self.CSS).read()
        assert '.report-source-link:hover' in text, (
            'CSS missing :hover state — visual feedback needed for clickability'
        )

    def test_focus_state_for_keyboard_a11y(self):
        text = open(self.CSS).read()
        assert '.report-source-link:focus' in text, (
            'CSS missing :focus outline — keyboard users need visible focus ring '
            'since the span has role="button" + tabindex="0"'
        )

    def test_uses_blue_var(self):
        text = open(self.CSS).read()
        # Hover color must use the project's blue var (parity with other badges)
        m = re.search(r'\.report-source-link:hover\s*\{[^}]*color:\s*var\(--blue\)', text)
        assert m, 'Hover color must use var(--blue)'

    def test_loaded_via_mobile_css_chain(self):
        """components.css is loaded via mobile.css @import (not direct HTML link)."""
        mobile = open(os.path.join(REPO, 'static/css/mobile.css')).read()
        assert 'components.css' in mobile, (
            'mobile.css must @import components.css so .report-source-link styles load'
        )


# ---------------------------------------------------------------------------
# i18n — bilingual coverage for the hover tooltip (Pattern 5d lesson)
# ---------------------------------------------------------------------------

class TestReportViewSourceI18n:
    I18N = os.path.join(REPO, 'static/js/i18n.js')

    def test_zh_key_present(self):
        text = open(self.I18N).read()
        # i18n.js uses `zh: {` (object key, not string)
        zh_section = text.split('zh:')[1].split('en:')[0] if 'zh:' in text else ''
        assert "'report.view_source':" in zh_section, (
            'report.view_source zh translation missing (Pattern 5d bilingual guard)'
        )

    def test_en_key_present(self):
        text = open(self.I18N).read()
        # i18n.js uses `en: {` (object key)
        en_section = text.split('en:')[1] if 'en:' in text else ''
        assert "'report.view_source':" in en_section, (
            'report.view_source en translation missing (Pattern 5d bilingual guard)'
        )


# ---------------------------------------------------------------------------
# E2E smoke — served pages load OK after the patch
# ---------------------------------------------------------------------------

class TestReportCardE2ESmoke:
    PAGES = ['/', '/stock/TSLA', '/industry']

    @pytest.mark.parametrize('path', PAGES)
    def test_page_loads(self, path):
        with urllib.request.urlopen(f'http://localhost:5000{path}', timeout=5) as resp:
            assert resp.status == 200, f'{path} → {resp.status}'

    def test_index_loads_i18n_and_css(self):
        """Page must include i18n.js + mobile.css (which @imports components.css)."""
        with urllib.request.urlopen('http://localhost:5000/', timeout=5) as resp:
            html = resp.read().decode()
        assert 'static/js/i18n.js' in html
        assert 'static/css/mobile.css' in html, (
            'mobile.css is the @import entry for components.css — '
            'must be linked so .report-source-link styles apply'
        )
