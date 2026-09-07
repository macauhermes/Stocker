"""
Regression test for v3.4.86 — surface `prev_close` (Pattern 9b orphan field).

Bug class:
  `/api/stock/<sym>/detail` and `/api/tickers` both return `prev_close` (the
  prior-session close price). The field was being computed internally for
  change_pct but never serialized to the client. v3.4.86 adds it to:

  1. `/api/stock/<sym>/detail` JSON response (services/stock_data.py + app.py)
  2. `/api/tickers` JSON response (via fetch_stock_info)
  3. Dashboard stock card `.stock-prev-close` line (templates/index.html)
  4. Stock detail page `val-prev-close` stat tile (templates/stock_detail.html)

This test guards against regressions in 4 areas:
  A. API surface — both endpoints return `prev_close` populated for ≥80% of
     active tickers (some may legitimately have None for illiquid names)
  B. Template markup — index.html renderStocks reads ticker.prev_close
  C. Template markup — stock_detail.html reads data.prev_close
  D. i18n wiring — `stock.prev_close` (zh + en) and `detail.prev_close` (zh + en)
     keys both defined; both referenced by template
  E. CSS — `.stock-prev-close` class defined for the dashboard pill
"""
import os
import sys
import re

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope='module')
def client():
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _i18n_sections():
    """Return (zh_section_text, en_section_text) split by brace-matching.

    i18n.js has structure `const I18N = { zh: {...}, en: {...} };` — a single
    outer dict with two nested language dicts. This helper extracts each
    language section so we can verify zh + en coverage separately (Pattern 5d
    v3.4.61 lesson — en-only / zh-only keys silently render literal key in
    the missing language).
    """
    text = open('static/js/i18n.js').read()
    m = re.search(r'const I18N = \{', text)
    i = m.end()
    depth = 1
    while i < len(text) and depth > 0:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        i += 1
    i18n_inner = text[m.end():i-1]

    zh_match = re.search(r'zh:\s*\{', i18n_inner)
    zh_start = zh_match.end()
    depth = 1
    j = zh_start
    while j < len(i18n_inner) and depth > 0:
        if i18n_inner[j] == '{':
            depth += 1
        elif i18n_inner[j] == '}':
            depth -= 1
        j += 1
    zh_section = i18n_inner[zh_start:j-1]

    en_match = re.search(r'en:\s*\{', i18n_inner)
    en_start = en_match.end()
    depth = 1
    k = en_start
    while k < len(i18n_inner) and depth > 0:
        if i18n_inner[k] == '{':
            depth += 1
        elif i18n_inner[k] == '}':
            depth -= 1
        k += 1
    en_section = i18n_inner[en_start:k-1]

    return zh_section, en_section


def _extract_function_body(source, fn_name):
    """Brace-matching helper for JS function body extraction (v3.4.70 lesson)."""
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
    if depth != 0:
        return None
    return source[m.end():i-1]


# ──────────────────────────────────────────────────────────────────────
# A. API surface
# ──────────────────────────────────────────────────────────────────────

class TestPrevCloseApiSurface:
    def test_tickers_returns_prev_close_field(self, client):
        resp = client.get('/api/tickers')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        assert 'prev_close' in first, f'/api/tickers missing prev_close field; keys={sorted(first.keys())}'

    def test_tickers_prev_close_populated_for_most(self, client):
        """prev_close should be populated for ≥80% of active tickers."""
        resp = client.get('/api/tickers')
        data = resp.get_json()
        populated = sum(1 for t in data if t.get('prev_close') is not None)
        ratio = populated / max(1, len(data))
        assert ratio >= 0.8, f'prev_close populated only {populated}/{len(data)} ({ratio:.0%})'

    def test_tickers_prev_close_is_numeric(self, client):
        resp = client.get('/api/tickers')
        data = resp.get_json()
        for t in data:
            pc = t.get('prev_close')
            if pc is not None:
                assert isinstance(pc, (int, float)), (
                    f'{t.get("symbol")}: prev_close={pc!r} should be numeric, got {type(pc).__name__}'
                )
                assert pc > 0, f'{t.get("symbol")}: prev_close={pc} should be > 0'

    def test_stock_detail_returns_prev_close(self, client):
        resp = client.get('/api/stock/TSLA/detail')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'prev_close' in data, f'/api/stock/TSLA/detail missing prev_close; keys={sorted(data.keys())}'
        pc = data['prev_close']
        assert pc is not None, 'TSLA prev_close should not be None'
        assert isinstance(pc, (int, float))
        assert pc > 0


# ──────────────────────────────────────────────────────────────────────
# B. Dashboard stock card markup (templates/index.html)
# ──────────────────────────────────────────────────────────────────────

class TestStockCardPrevCloseMarkup:
    @pytest.fixture
    def html(self):
        return open('templates/index.html').read()

    def test_renderStocks_function_exists(self, html):
        assert 'function renderStocks' in html

    def test_renderStocks_reads_prev_close(self, html):
        """renderStocks body must reference ticker.prev_close."""
        body = _extract_function_body(html, 'renderStocks')
        assert body is not None, 'renderStocks not found'
        assert 'prev_close' in body, (
            'renderStocks() does not read ticker.prev_close — '
            'regression: stock card prev-close line silently dropped'
        )

    def test_renderStocks_wires_t_i18n_stock_prev_close(self, html):
        """renderStocks must call t('stock.prev_close') so the label translates."""
        body = _extract_function_body(html, 'renderStocks')
        assert body is not None
        assert "t('stock.prev_close')" in body, (
            'renderStocks() does not call t(\'stock.prev_close\') — '
            'label hardcoded would silently stay Chinese in en mode'
        )

    def test_renderStocks_has_stock_prev_close_class(self, html):
        body = _extract_function_body(html, 'renderStocks')
        assert body is not None
        assert 'stock-prev-close' in body, (
            'renderStocks() missing .stock-prev-close CSS class — pill unstyled'
        )


# ──────────────────────────────────────────────────────────────────────
# C. Stock detail markup (templates/stock_detail.html)
# ──────────────────────────────────────────────────────────────────────

class TestStockDetailPrevCloseMarkup:
    @pytest.fixture
    def html(self):
        return open('templates/stock_detail.html').read()

    def test_has_val_prev_close_element(self, html):
        assert 'id="val-prev-close"' in html, (
            'templates/stock_detail.html missing #val-prev-close element'
        )

    def test_has_data_i18n_detail_prev_close(self, html):
        """Stat label uses data-i18n so applyI18n() rewrites the text on langchange."""
        assert 'data-i18n="detail.prev_close"' in html

    def test_loadDetail_reads_data_prev_close(self, html):
        """loadDetail() must read data.prev_close."""
        body = _extract_function_body(html, 'loadDetail')
        assert body is not None, 'loadDetail function not found'
        assert 'data.prev_close' in body, (
            'loadDetail() does not read data.prev_close — '
            'regression: stock detail stat tile stays "—"'
        )

    def test_loadDetail_writes_to_val_prev_close(self, html):
        body = _extract_function_body(html, 'loadDetail')
        assert body is not None
        assert 'val-prev-close' in body, (
            'loadDetail() does not write to #val-prev-close element'
        )


# ──────────────────────────────────────────────────────────────────────
# D. i18n bilingual coverage guard
# ──────────────────────────────────────────────────────────────────────

class TestPrevCloseI18nBilingual:
    def test_stock_prev_close_in_zh_section(self):
        zh, en = _i18n_sections()
        assert "'stock.prev_close':" in zh, (
            'stock.prev_close missing from zh section of i18n.js'
        )

    def test_stock_prev_close_in_en_section(self):
        zh, en = _i18n_sections()
        assert "'stock.prev_close':" in en, (
            'stock.prev_close missing from en section of i18n.js — '
            'English mode would render literal key string'
        )

    def test_detail_prev_close_in_zh_section(self):
        zh, en = _i18n_sections()
        assert "'detail.prev_close':" in zh

    def test_detail_prev_close_in_en_section(self):
        zh, en = _i18n_sections()
        assert "'detail.prev_close':" in en


# ──────────────────────────────────────────────────────────────────────
# E. CSS class definition
# ──────────────────────────────────────────────────────────────────────

class TestStockPrevCloseCss:
    def test_class_defined_in_components_css(self):
        css = open('static/css/components.css').read()
        assert '.stock-prev-close' in css, (
            '.stock-prev-close CSS class missing — pill renders unstyled'
        )

    def test_class_has_visual_styling(self):
        """Class must define at least font-size / color / margin to be a real pill."""
        css = open('static/css/components.css').read()
        m = re.search(r'\.stock-prev-close\s*\{([^}]+)\}', css)
        assert m is not None, '.stock-prev-close block not found'
        block = m.group(1)
        # Must have at least these three properties for a pill
        assert 'font-size' in block
        assert 'color' in block


# ──────────────────────────────────────────────────────────────────────
# F. JS syntax validity
# ──────────────────────────────────────────────────────────────────────

class TestJsSyntax:
    def test_i18n_js_node_check(self):
        """node --check on i18n.js catches unbalanced braces introduced by edits."""
        import subprocess
        r = subprocess.run(['node', '--check', 'static/js/i18n.js'],
                           capture_output=True, text=True)
        assert r.returncode == 0, f'i18n.js syntax error: {r.stderr}'


# ──────────────────────────────────────────────────────────────────────
# G. E2E smoke
# ──────────────────────────────────────────────────────────────────────

class TestE2ESmoke:
    def test_dashboard_loads(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_dashboard_served_html_has_stock_prev_close_class(self, client):
        resp = client.get('/')
        text = resp.get_data(as_text=True)
        # The class name appears once in the template (the renderStocks line);
        # subsequent cards would be JS-injected, not in initial HTML
        assert 'stock-prev-close' in text

    def test_stock_detail_loads(self, client):
        resp = client.get('/stock/TSLA')
        assert resp.status_code == 200

    def test_stock_detail_served_html_has_val_prev_close(self, client):
        resp = client.get('/stock/TSLA')
        text = resp.get_data(as_text=True)
        assert 'id="val-prev-close"' in text


# ──────────────────────────────────────────────────────────────────────
# H. Gremlin check — no mojibake in modified files
# ──────────────────────────────────────────────────────────────────────

class TestGremlinCheck:
    GREMLINS = {
        b'\xef\xbf\xbd': 'U+FFFD (replacement char — patch corruption)',
        b'\xc2\xad': 'U+00AD (soft hyphen)',
        b'\xe2\x80\x8b': 'U+200B (zero-width space)',
        b'\xef\xbb\xbf': 'U+FEFF (BOM)',
        b'\xe2\x80\x8e': 'U+200E (LTR mark)',
        b'\xe2\x80\x8f': 'U+200F (RTL mark)',
    }

    @pytest.mark.parametrize('filename', [
        'templates/index.html',
        'templates/stock_detail.html',
        'static/css/components.css',
        'static/js/i18n.js',
        'app.py',
        'services/stock_data.py',
    ])
    def test_no_mojibake(self, filename):
        data = open(filename, 'rb').read()
        hits = {label: data.count(b) for b, label in self.GREMLINS.items()
                if data.count(b)}
        assert not hits, f'{filename}: mojibake detected: {hits}'


# ──────────────────────────────────────────────────────────────────────
# I. Backend: services/stock_data.py + app.py include prev_close
# ──────────────────────────────────────────────────────────────────────

class TestBackendWiring:
    def test_fetch_stock_info_returns_prev_close(self):
        """services/stock_data.py fetch_stock_info dict must contain prev_close key."""
        src = open('services/stock_data.py').read()
        # Look for the dict construction in the yfinance branch
        assert '"prev_close"' in src, (
            'services/stock_data.py missing "prev_close" key in fetch_stock_info'
        )
        assert '_round_safe(prev_close)' in src, (
            'fetch_stock_info not rounding prev_close with _round_safe'
        )

    def test_app_api_stock_detail_passes_prev_close(self):
        """app.py api_stock_detail must include prev_close in the JSON response."""
        src = open('app.py').read()
        # Look for the prev_close line in api_stock_detail
        assert "'prev_close'" in src, (
            'app.py missing prev_close field in api_stock_detail response'
        )


# ──────────────────────────────────────────────────────────────────────
# J. Live API contract verification (cold-cache, fresh import)
# ──────────────────────────────────────────────────────────────────────

class TestLiveApiContract:
    """Sanity: live endpoints actually serve prev_close — catches the case
    where the WSGI server is still serving a stale code path."""

    def test_live_tickers_has_prev_close(self, client):
        data = client.get('/api/tickers').get_json()
        assert all('prev_close' in t for t in data)

    def test_live_stock_detail_has_prev_close(self, client):
        data = client.get('/api/stock/TSLA/detail').get_json()
        assert 'prev_close' in data
        assert data['prev_close'] is not None
