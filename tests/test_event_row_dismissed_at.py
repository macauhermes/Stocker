"""
v3.4.74 — Pattern 9b orphan-field surfacing for events[].dismissed_at on
stock_detail.html renderEvents().

Background: /api/stock/<sym>/detail returns events[] with 7 keys including
`dismissed_at` (set when event is dismissed, NULL when not). The events.html
upcoming list already surfaced this field in v3.4.66, but stock_detail.html's
renderEvents() — which renders the same data shape for the same events —
silently dropped the field between API and DOM.

User would see "[dismissed tag]" but no idea when they dismissed it. This
commit adds inline muted timestamp ("Dismissed on 09/01") next to the tag,
matching the events.html pattern.
"""
import json
import os
import re
import urllib.request

import pytest

REPO = os.path.expanduser('~/repos/Stocker')


def _extract_function_body(source, fn_name):
    """Brace-matching extraction (v3.4.70 lesson)."""
    m = re.search(rf'function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{', source)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(source) and depth > 0:
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
        i += 1
    return source[m.end():i - 1] if depth == 0 else None


# ---------------------------------------------------------------------------
# API surface — confirm `dismissed_at` is returned by the detail endpoint
# ---------------------------------------------------------------------------

class TestStockDetailEventsApiSurface:
    """Verify /api/stock/<sym>/detail actually returns `dismissed_at`."""

    @pytest.fixture(scope='class')
    def detail(self):
        # TSLA has 1 dismissed event with timestamp (from v3.4.66 salvage work)
        with urllib.request.urlopen(
            'http://localhost:5000/api/stock/TSLA/detail', timeout=5
        ) as resp:
            return json.loads(resp.read())

    def test_returns_events_array(self, detail):
        assert 'events' in detail
        assert isinstance(detail['events'], list)

    def test_events_have_dismissed_at_field(self, detail):
        if detail['events']:
            sample = detail['events'][0]
            assert 'dismissed_at' in sample, (
                'API response missing dismissed_at on events[] items'
            )

    def test_at_least_one_dismissed_with_timestamp(self, detail):
        """TSLA's TSLA Earnings event should be dismissed with a timestamp."""
        dismissed_with_ts = [
            e for e in detail['events']
            if e.get('dismissed') and e.get('dismissed_at')
        ]
        assert dismissed_with_ts, (
            'Expected ≥1 dismissed event with dismissed_at timestamp. '
            f'Got events: {detail["events"]}'
        )


# ---------------------------------------------------------------------------
# Markup wiring — renderEvents() must consume dismissed_at
# ---------------------------------------------------------------------------

class TestStockDetailRenderEventsWiring:
    PAGE = os.path.join(REPO, 'templates/stock_detail.html')

    @pytest.fixture(scope='class')
    def body(self):
        text = open(self.PAGE).read()
        body = _extract_function_body(text, 'renderEvents')
        assert body is not None, 'Could not extract renderEvents body'
        return body

    def test_reads_dismissed_at(self, body):
        assert 'e.dismissed_at' in body, (
            'renderEvents must read e.dismissed_at'
        )

    def test_guards_on_dismissed_and_timestamp(self, body):
        # Must check both isDismissed AND truthy dismissed_at
        assert re.search(r'isDismissed\s*&&\s*e\.dismissed_at', body), (
            'renderEvents must guard on both isDismissed AND e.dismissed_at truthy'
        )

    def test_uses_format_date_helper(self, body):
        assert 'formatDate(e.dismissed_at)' in body, (
            'renderEvents must format dismissed_at via formatDate()'
        )

    def test_uses_dismissed_at_i18n_key(self, body):
        assert "t('events.dismissed_at'" in body, (
            'renderEvents must call t("events.dismissed_at") for i18n'
        )

    def test_uses_tooltip_i18n_key(self, body):
        assert "t('events.dismissed_at_tooltip'" in body, (
            'renderEvents must wire tooltip via t("events.dismissed_at_tooltip")'
        )

    def test_appends_to_event_row_title(self, body):
        # The dismissedAtHtml should be appended after dismissedTag in the title span
        assert 'dismissedTag}${dismissedAtHtml}' in body, (
            'dismissedAtHtml must be appended after dismissedTag in the title span'
        )


# ---------------------------------------------------------------------------
# CSS — visual styling for the new dismissed-at timestamp
# ---------------------------------------------------------------------------

class TestEventRowDismissedAtCss:
    CSS = os.path.join(REPO, 'static/css/components.css')

    def test_class_defined(self):
        text = open(self.CSS).read()
        assert '.event-row-dismissed-at {' in text, (
            'CSS missing .event-row-dismissed-at styles'
        )

    def test_uses_text_muted_color(self):
        """Parity with events.html's dismissed_at inline span (var(--text-muted))."""
        text = open(self.CSS).read()
        m = re.search(
            r'\.event-row-dismissed-at\s*\{[^}]*color:\s*var\(--text-muted\)',
            text,
        )
        assert m, '.event-row-dismissed-at must use var(--text-muted)'

    def test_has_cursor_help_for_tooltip(self):
        """Since title= attribute is wired, cursor:help signals hover tooltip."""
        text = open(self.CSS).read()
        m = re.search(
            r'\.event-row-dismissed-at\s*\{[^}]*cursor:\s*help',
            text,
        )
        assert m, '.event-row-dismissed-at must have cursor:help'

    def test_loaded_via_mobile_css_chain(self):
        """components.css is loaded via mobile.css @import (not direct HTML link)."""
        mobile = open(os.path.join(REPO, 'static/css/mobile.css')).read()
        assert 'components.css' in mobile


# ---------------------------------------------------------------------------
# i18n — bilingual coverage guard (Pattern 5d lesson)
# ---------------------------------------------------------------------------

class TestDismissedAtI18nBilingual:
    I18N = os.path.join(REPO, 'static/js/i18n.js')

    def test_zh_key_has_time_placeholder(self):
        text = open(self.I18N).read()
        zh_section = text.split('zh:')[1].split('en:')[0] if 'zh:' in text else ''
        assert "'events.dismissed_at':" in zh_section
        # Extract the zh key value
        m = re.search(r"'events\.dismissed_at':\s*'([^']+)'", zh_section)
        assert m, 'zh events.dismissed_at key value not found'
        assert '{time}' in m.group(1), (
            f'zh events.dismissed_at must use {{time}} placeholder, got: {m.group(1)!r}'
        )

    def test_en_key_has_time_placeholder(self):
        text = open(self.I18N).read()
        en_section = text.split('en:')[1] if 'en:' in text else ''
        assert "'events.dismissed_at':" in en_section
        m = re.search(r"'events\.dismissed_at':\s*'([^']+)'", en_section)
        assert m, 'en events.dismissed_at key value not found'
        assert '{time}' in m.group(1), (
            f'en events.dismissed_at must use {{time}} placeholder, got: {m.group(1)!r}'
        )

    def test_zh_tooltip_key_present(self):
        text = open(self.I18N).read()
        zh_section = text.split('zh:')[1].split('en:')[0] if 'zh:' in text else ''
        assert "'events.dismissed_at_tooltip':" in zh_section

    def test_en_tooltip_key_present(self):
        text = open(self.I18N).read()
        en_section = text.split('en:')[1] if 'en:' in text else ''
        assert "'events.dismissed_at_tooltip':" in en_section


# ---------------------------------------------------------------------------
# E2E smoke — pages still load after patch
# ---------------------------------------------------------------------------

class TestStockDetailEventRowE2ESmoke:
    @pytest.mark.parametrize('path', ['/', '/stock/TSLA', '/events'])
    def test_page_loads(self, path):
        with urllib.request.urlopen(f'http://localhost:5000{path}', timeout=5) as resp:
            assert resp.status == 200, f'{path} → {resp.status}'

    def test_stock_detail_includes_wired_render(self):
        with urllib.request.urlopen('http://localhost:5000/stock/TSLA', timeout=5) as resp:
            html = resp.read().decode()
        # Page references renderEvents + i18n.js + mobile.css
        assert 'renderEvents' in html
        assert 'static/js/i18n.js' in html
        assert 'static/css/mobile.css' in html
