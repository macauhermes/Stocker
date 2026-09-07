"""Tests for events.html search input (v3.4.85).

The /events page has an upcoming events list. v3.4.85 adds a debounced
client-side search input that filters by symbol OR title substring.
"""
import json
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.expanduser('~/repos/Stocker')


def _read(p):
    with open(p) as f:
        return f.read()


def _extract_function_body(source, fn_name):
    """Brace-matching helper for nested if/else bodies (see skill)."""
    m = re.search(rf'function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{', source)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(source) and depth > 0:
        c = source[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    return source[m.end():i - 1] if depth == 0 else None


# ----- API surface ----------------------------------------------------------

class TestEventsSearchApiSurface:
    """Verify the data the search filter runs against."""

    @pytest.fixture
    def events_data(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/events/upcoming?days=365&include_past=true', '-m', '5'],
            capture_output=True, text=True
        )
        return json.loads(r.stdout)

    def test_endpoint_returns_symbol_field(self, events_data):
        assert len(events_data) > 0, 'no events to test against'
        for ev in events_data:
            assert 'symbol' in ev
            assert 'title' in ev

    def test_endpoint_returns_enough_distinct_symbols(self, events_data):
        """Search filter needs at least 3 distinct symbols to be useful."""
        symbols = {e['symbol'] for e in events_data}
        assert len(symbols) >= 3, f'only {len(symbols)} symbols — search would be dead-on-arrival'


# ----- Markup ---------------------------------------------------------------

class TestEventsSearchMarkup:
    @pytest.fixture
    def t(self):
        return _read(os.path.join(REPO, 'templates/events.html'))

    def test_search_input_present(self, t):
        assert 'id="events-search"' in t
        assert 'data-i18n-placeholder="events.search_placeholder"' in t
        assert 'type="search"' in t

    def test_search_input_in_filter_row(self, t):
        """Search input must be inside the events-filter-row, not orphaned."""
        # find filter row block
        m = re.search(r'<div class="events-filter-row">(.*?)</div>\s*<div id="upcoming-list">',
                      t, re.DOTALL)
        assert m, 'events-filter-row not found'
        block = m.group(1)
        assert 'events-search' in block

    def test_uses_reports_search_input_css_class(self, t):
        """Reuse the existing .reports-search-input class for visual parity."""
        assert 'class="reports-search-input"' in t


# ----- JS logic -------------------------------------------------------------

class TestEventsSearchJs:
    @pytest.fixture
    def script(self):
        t = _read(os.path.join(REPO, 'templates/events.html'))
        m = re.search(r'<script>(.*?)</script>', t, re.DOTALL)
        return m.group(1)

    def test_search_query_state_var(self, script):
        assert "let eventSearchQuery = '';" in script

    def test_renderUpcoming_applies_search_filter(self, script):
        body = _extract_function_body(script, 'renderUpcoming')
        assert body is not None
        assert 'eventSearchQuery' in body
        assert "typeFiltered.filter" in body or ".filter(" in body

    def test_search_is_case_insensitive(self, script):
        """Filter uses .toLowerCase() on both sides for case-insensitive match."""
        body = _extract_function_body(script, 'renderUpcoming')
        assert '.toLowerCase()' in body

    def test_search_matches_symbol_or_title(self, script):
        body = _extract_function_body(script, 'renderUpcoming')
        # either e.symbol.includes or e.title.includes
        assert 'sym.includes' in body or 'e.symbol.includes' in body or 'symbol.includes' in body
        assert 'ttl.includes' in body or 'e.title.includes' in body or 'title.includes' in body

    def test_search_input_event_listener(self, script):
        """Wires DOMContentLoaded listener that reads e.target.value."""
        # Look for the DOMContentLoaded block
        assert "addEventListener('input'" in script or 'addEventListener("input"' in script
        assert 'eventSearchQuery = e.target.value' in script
        # debounced via setTimeout
        assert 'setTimeout' in script

    def test_count_badge_hides_when_no_filters_active(self, script):
        """When type=all AND hideDismissed=true AND q is empty → no count badge."""
        body = _extract_function_body(script, 'renderUpcoming')
        # the conditional should include the q check now
        assert '!q' in body

    def test_empty_state_distinguishes_search_no_match(self, script):
        body = _extract_function_body(script, 'renderUpcoming')
        assert 'events.search_no_match' in body
        assert 'events.search_no_match_hint' in body

    def test_langchange_re_translates_placeholder(self, script):
        """Placeholder must be re-translated when language switches."""
        assert "events.search_placeholder" in script
        # the langchange listener should setAttribute placeholder
        assert "setAttribute('placeholder'" in script


# ----- CSS (reuse of existing class) ---------------------------------------

class TestEventsSearchCss:
    @pytest.fixture
    def css(self):
        css_path = os.path.join(REPO, 'static/css/components.css')
        if not os.path.exists(css_path):
            return ''
        return _read(css_path)

    def test_reports_search_input_class_exists(self, css):
        """The shared class must be defined somewhere."""
        assert '.reports-search-input' in css


# ----- i18n -----------------------------------------------------------------

class TestEventsSearchI18n:
    @pytest.fixture
    def i18n(self):
        return _read(os.path.join(REPO, 'static/js/i18n.js'))

    def test_zh_search_placeholder(self, i18n):
        assert "'events.search_placeholder':" in i18n
        assert '搜尋代碼或事件' in i18n

    def test_en_search_placeholder(self, i18n):
        assert "'events.search_placeholder':" in i18n
        assert 'Search ticker or event' in i18n

    def test_zh_search_no_match(self, i18n):
        assert "'events.search_no_match':" in i18n
        # CJK content for zh
        assert '冇符合' in i18n or '無符合' in i18n

    def test_en_search_no_match(self, i18n):
        assert "'events.search_no_match':" in i18n
        assert 'No matching events' in i18n

    def test_zh_search_no_match_hint(self, i18n):
        assert "'events.search_no_match_hint':" in i18n

    def test_en_search_no_match_hint(self, i18n):
        assert "'events.search_no_match_hint':" in i18n
        assert 'Try a different ticker' in i18n

    def test_bilingual_section_split(self, i18n):
        """All 3 search keys must exist in BOTH zh and en sections."""
        en_start = i18n.find('en:')
        zh_keys = set(re.findall(r"^\s+'([a-z][a-z0-9._]+)':",
                                 i18n[:en_start], re.MULTILINE))
        en_keys = set(re.findall(r"^\s+'([a-z][a-z0-9._]+)':",
                                 i18n[en_start:], re.MULTILINE))
        for k in ['events.search_placeholder', 'events.search_no_match', 'events.search_no_match_hint']:
            assert k in zh_keys, f'{k} missing from zh section'
            assert k in en_keys, f'{k} missing from en section'


# ----- E2E smoke ------------------------------------------------------------

class TestEventsSearchE2E:
    def test_events_page_loads_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/events', '-m', '5'],
            capture_output=True, text=True
        )
        assert r.stdout == '200', f'/events returned {r.stdout}'

    def test_served_html_has_search_input(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/events', '-m', '5'],
            capture_output=True, text=True
        )
        assert 'events-search' in r.stdout
        assert 'events.search_placeholder' in r.stdout


# ----- JS syntax & gremlin --------------------------------------------------

class TestEventsSearchJsSyntax:
    def test_extracted_js_parses(self):
        t = _read(os.path.join(REPO, 'templates/events.html'))
        m = re.search(r'<script>(.*?)</script>', t, re.DOTALL)
        with open('/tmp/_events_search.js', 'w') as f:
            f.write(m.group(1))
        r = subprocess.run(['node', '--check', '/tmp/_events_search.js'],
                           capture_output=True, text=True)
        assert r.returncode == 0, f'JS syntax error: {r.stderr}'

    def test_i18n_js_parses(self):
        r = subprocess.run(['node', '--check',
                           os.path.join(REPO, 'static/js/i18n.js')],
                          capture_output=True, text=True)
        assert r.returncode == 0, f'i18n.js syntax error: {r.stderr}'


class TestEventsSearchGremlin:
    """Invisible Unicode trap (U+FFFD / U+00AD / U+200B etc.)"""

    @pytest.mark.parametrize('fname', ['templates/events.html', 'static/js/i18n.js'])
    def test_no_mojibake(self, fname):
        path = os.path.join(REPO, fname)
        data = open(path, 'rb').read()
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
        }
        hits = {gremlins[b]: data.count(b) for b in gremlins if data.count(b)}
        assert not hits, f'mojibake in {fname}: {hits}'
