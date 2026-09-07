"""Tests for industry.html news filter row (v3.4.88, salvage sibling WIP).

The /industry page has a news panel per sector. v3.4.88 (sibling WIP) adds a
debounced client-side search input + sort dropdown + count badge — mirrors
the v3.4.85 events search and v3.4.20 reports search patterns.

Sibling subagent implemented zh i18n keys but missed the en section (v3.4.61
Pattern 5d bilingual coverage gap). This tick completes the bilingual fix
and adds comprehensive tests.
"""
import json
import os
import re
import subprocess

import pytest

REPO = os.path.expanduser('~/repos/Stocker')


def _read(p):
    with open(p) as f:
        return f.read()


def _extract_function_body(source, fn_name):
    """Brace-matching helper for nested if/else bodies (see skill v3.4.70)."""
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

class TestIndustryNewsApiSurface:
    """Verify the data the search filter runs against."""

    @pytest.fixture
    def news_data(self):
        # Use a sector that has populated news (Technology is the largest)
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/industry/Technology/news', '-m', '5'],
            capture_output=True, text=True
        )
        return json.loads(r.stdout)

    def test_endpoint_returns_news_array(self, news_data):
        assert isinstance(news_data, list)
        assert len(news_data) > 0, 'no news to test against'

    def test_news_items_have_searchable_fields(self, news_data):
        for n in news_data:
            assert 'title' in n, 'news missing title (search filter needs it)'

    def test_endpoint_returns_enough_items_for_search(self, news_data):
        """Search filter needs at least 10 items to be useful."""
        assert len(news_data) >= 10, (
            f'only {len(news_data)} news items — search would be dead-on-arrival'
        )

    def test_titles_have_distinct_substrings(self, news_data):
        """Titles must contain varied substrings for search to demonstrate value."""
        # Sample first word of each title — must have ≥3 distinct words
        first_words = {n['title'].split()[0] for n in news_data[:30] if n.get('title')}
        assert len(first_words) >= 3, (
            f'only {len(first_words)} distinct first words — search would be dead-on-arrival'
        )


# ----- Markup ---------------------------------------------------------------

class TestIndustryNewsFilterMarkup:
    @pytest.fixture
    def t(self):
        return _read(os.path.join(REPO, 'templates/industry.html'))

    def test_filter_row_present(self, t):
        assert 'id="news-filter-row"' in t

    def test_search_input_present(self, t):
        assert 'id="news-search-input"' in t
        assert 'data-i18n-placeholder="industry.news_search_placeholder"' in t
        assert 'type="text"' in t or 'type="search"' in t

    def test_sort_select_present(self, t):
        assert 'id="news-sort-select"' in t
        # Both desc + asc options must be present
        assert 'value="desc"' in t
        assert 'value="asc"' in t
        assert 'data-i18n="industry.sort_newest"' in t
        assert 'data-i18n="industry.sort_oldest"' in t

    def test_count_badge_present(self, t):
        assert 'id="news-filter-count"' in t
        assert 'events-filter-count' in t  # reuse v3.4.19 CSS class

    def test_filter_row_hidden_by_default(self, t):
        """Filter row should be hidden until first data load."""
        assert 'id="news-filter-row"' in t
        # The inline style="display:none;" should be on the filter row
        m = re.search(r'<div id="news-filter-row"[^>]*style="([^"]+)"', t)
        assert m and 'display:none' in m.group(1), 'filter row should start hidden'


# ----- JS -------------------------------------------------------------------

class TestIndustryNewsFilterJs:
    @pytest.fixture
    def script(self):
        t = _read(os.path.join(REPO, 'templates/industry.html'))
        m = re.search(r'<script>(.*?)</script>', t, re.DOTALL)
        assert m, 'no inline script found'
        return m.group(1)

    def test_state_vars_declared(self, script):
        assert 'let allNews = []' in script
        assert 'let newsSearchQuery' in script
        assert 'let newsSort' in script

    def test_render_news_function_exists(self, script):
        body = _extract_function_body(script, 'renderNews')
        assert body is not None, 'renderNews function not found'

    def test_render_news_caches_data(self, script):
        """renderNews should read from module-scope cache (not re-fetch)."""
        body = _extract_function_body(script, 'renderNews')
        assert 'allNews' in body

    def test_render_news_applies_search_filter(self, script):
        body = _extract_function_body(script, 'renderNews')
        # Substring match (case-insensitive) on title
        assert 'newsSearchQuery' in body
        assert '.toLowerCase()' in body
        assert '.includes(' in body
        assert '.title' in body or 'title' in body

    def test_render_news_applies_sort(self, script):
        body = _extract_function_body(script, 'renderNews')
        assert 'newsSort' in body
        assert '.sort(' in body
        # Sort key must be a date field
        assert 'published_at' in body or 'created_at' in body

    def test_render_news_count_badge_only_when_searching(self, script):
        """Count badge should show filtered count only when search is active."""
        body = _extract_function_body(script, 'renderNews')
        assert 'count_filtered' in body
        assert 'news-filter-count' in body

    def test_render_news_search_empty_state(self, script):
        """When search excludes all items, show distinct empty state."""
        body = _extract_function_body(script, 'renderNews')
        assert 'news_search_no_match' in body
        assert 'news_search_no_match_hint' in body
        assert 'filter_alt_off' in body

    def test_render_news_calls_render_reports(self, script):
        """Filtered news must be delegated to existing renderReports()."""
        body = _extract_function_body(script, 'renderNews')
        assert 'renderReports(' in body
        assert 'isNews: true' in body

    def test_init_news_filter_row_wires_search(self, script):
        """initNewsFilterRow should attach debounced input listener."""
        body = _extract_function_body(script, 'initNewsFilterRow')
        assert body is not None, 'initNewsFilterRow function not found'
        assert 'addEventListener' in body
        assert 'setTimeout' in body  # debounce
        assert 'newsSearchQuery' in body

    def test_init_news_filter_row_wires_sort(self, script):
        body = _extract_function_body(script, 'initNewsFilterRow')
        assert 'addEventListener' in body
        assert "'change'" in body or '"change"' in body
        assert 'newsSort' in body

    def test_search_listener_uses_200ms_debounce(self, script):
        """Debounce window must be 200ms (matches v3.4.20 reports search)."""
        body = _extract_function_body(script, 'initNewsFilterRow')
        assert '200' in body

    def test_data_load_assigns_all_news_cache(self, script):
        """The selectSector() handler must populate allNews cache before renderNews()."""
        body = _extract_function_body(script, 'selectSector')
        assert body is not None, 'selectSector function not found'
        assert 'allNews' in body
        assert 'initNewsFilterRow()' in body
        assert 'renderNews()' in body

    def test_filter_row_hidden_when_news_unavailable(self, script):
        """When fetch fails, allNews is [] and filter row stays hidden."""
        body = _extract_function_body(script, 'renderNews')
        assert 'allNews.length === 0' in body or '!allNews' in body


# ----- CSS ------------------------------------------------------------------

class TestIndustryNewsFilterCss:
    @pytest.fixture
    def css(self):
        # Reuse from v3.4.19 events-filter-row, v3.4.20 reports-search-input,
        # and v3.4.14 stocks-control-select. No new CSS needed.
        text = ''
        for path in ['components.css', 'mobile.css', 'variables.css', 'responsive.css']:
            full = os.path.join(REPO, 'static/css', path)
            if os.path.exists(full):
                text += _read(full)
        return text

    def test_events_filter_row_class_defined(self, css):
        assert '.events-filter-row' in css, 'reuses events-filter-row from v3.4.19'

    def test_reports_search_input_class_defined(self, css):
        assert '.reports-search-input' in css, 'reuses reports-search-input from v3.4.20'

    def test_stocks_control_select_class_defined(self, css):
        assert '.stocks-control-select' in css, 'reuses stocks-control-select from v3.4.14'

    def test_events_filter_count_class_defined(self, css):
        assert '.events-filter-count' in css


# ----- i18n -----------------------------------------------------------------

class TestIndustryNewsFilterI18n:
    @pytest.fixture
    def i18n(self):
        return _read(os.path.join(REPO, 'static/js/i18n.js'))

    def test_zh_keys_exist(self, i18n):
        """All 3 new zh keys must exist (sibling WIP already added these)."""
        assert "'industry.news_search_placeholder': '搜尋新聞標題...'" in i18n
        assert "'industry.news_search_no_match': '冇符合搜尋嘅新聞'" in i18n
        assert "'industry.news_search_no_match_hint': '試下其他關鍵字'" in i18n

    def test_en_keys_exist(self, i18n):
        """All 3 new en keys must exist (added by this tick — v3.4.61 fix)."""
        assert "'industry.news_search_placeholder': 'Search news title" in i18n
        assert "'industry.news_search_no_match': 'No news matches the search'" in i18n
        assert "'industry.news_search_no_match_hint': 'Try a different keyword'" in i18n

    def test_bilingual_coverage(self, i18n):
        """Each key must exist exactly twice (zh + en)."""
        for k in ['industry.news_search_placeholder',
                  'industry.news_search_no_match',
                  'industry.news_search_no_match_hint']:
            count = len(re.findall(rf"^\s+'{re.escape(k)}':", i18n, re.MULTILINE))
            assert count == 2, f'{k}: {count} occurrences (expect 2 — zh + en)'

    def test_reused_keys_exist_bilingual(self, i18n):
        """Sort + count keys reused from v3.4.22 must exist in both sections."""
        for k in ['industry.sort_newest', 'industry.sort_oldest', 'industry.count_filtered']:
            count = len(re.findall(rf"^\s+'{re.escape(k)}':", i18n, re.MULTILINE))
            assert count == 2, f'{k}: {count} occurrences (expect 2 — zh + en)'


# ----- E2E ------------------------------------------------------------------

class TestIndustryNewsFilterE2E:
    def test_industry_page_returns_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/industry', '-m', '5'],
            capture_output=True, text=True
        )
        assert r.stdout.strip() == '200'

    def test_served_html_contains_filter_row(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/industry', '-m', '5'],
            capture_output=True, text=True
        )
        text = r.stdout
        assert 'id="news-filter-row"' in text
        assert 'id="news-search-input"' in text
        assert 'id="news-sort-select"' in text
        assert 'id="news-filter-count"' in text

    def test_served_html_contains_wired_i18n_keys(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/industry', '-m', '5'],
            capture_output=True, text=True
        )
        text = r.stdout
        assert 'industry.news_search_placeholder' in text
        assert 'industry.sort_newest' in text
        assert 'industry.sort_oldest' in text

    def test_news_endpoint_returns_data(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/industry/Technology/news', '-m', '5'],
            capture_output=True, text=True
        )
        data = json.loads(r.stdout)
        assert len(data) > 0


# ----- JS validation --------------------------------------------------------

class TestIndustryNewsFilterJsSyntax:
    def test_node_check_inline_script(self):
        t = _read(os.path.join(REPO, 'templates/industry.html'))
        m = re.search(r'<script>(.*?)</script>', t, re.DOTALL)
        assert m, 'no inline script found'
        open('/tmp/check_industry_filter.js', 'w').write(m.group(1))
        r = subprocess.run(['node', '--check', '/tmp/check_industry_filter.js'],
                          capture_output=True, text=True)
        assert r.returncode == 0, f'JS syntax error: {r.stderr}'

    def test_node_check_i18n_js(self):
        i18n_path = os.path.join(REPO, 'static/js/i18n.js')
        r = subprocess.run(['node', '--check', i18n_path],
                          capture_output=True, text=True)
        assert r.returncode == 0, f'i18n.js syntax error: {r.stderr}'


# ----- Gremlin check --------------------------------------------------------

class TestIndustryNewsFilterGremlin:
    """Catch invisible Unicode corruption (patch tool pitfall)."""

    def test_no_mojibake_in_modified_files(self):
        targets = [
            os.path.join(REPO, 'templates/industry.html'),
            os.path.join(REPO, 'static/js/i18n.js'),
        ]
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD (patch corruption)',
            b'\xc2\xad': 'U+00AD (soft hyphen)',
            b'\xe2\x80\x8b': 'U+200B (zero-width space)',
            b'\xef\xbb\xbf': 'U+FEFF (BOM)',
            b'\xe2\x80\x8e': 'U+200E (LTR mark)',
            b'\xe2\x80\x8f': 'U+200F (RTL mark)',
        }
        for path in targets:
            data = open(path, 'rb').read()
            for b, label in gremlins.items():
                cnt = data.count(b)
                assert cnt == 0, f'{path}: {cnt}× {label} detected'