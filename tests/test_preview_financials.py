"""
v3.4.81 — Test add-ticker preview card financial-stats row (Pattern 9b orphan-field surfacing).

Bug class: /api/tickers/preview returns pe_ratio (9/10 profitable), eps (9/10), market_cap (9/10)
but templates/index.html loadPreview() only consumed name + price + change_pct + sector + market.
The 3 financial-stat fields were silently dropped between API and DOM since the preview card
shipped in v3.2.

Fix scope (3-file surgical addition):
  - templates/index.html: new financial-row with P/E + EPS + Cap, using formatCurrency()/
    formatMarketCap() helpers instead of raw '$' + toLocaleString() (Pattern 5e consistency)
  - static/css/variables.css: new .preview-financials + .preview-fin + .preview-fin-label
  - static/js/i18n.js: new index.eps_label key (zh+en); pe_label/cap_label already existed
"""
import os
import json
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


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
    return source[m.end():i - 1] if depth == 0 else None


class TestPreviewFinancialFields:
    """Verify /api/tickers/preview returns the 3 financial-stat fields used by the new row."""

    def _preview(self, symbol: str) -> dict:
        import urllib.request

        req = urllib.request.Request(
            'http://localhost:5000/api/tickers/preview',
            data=json.dumps({'symbol': symbol}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())

    def test_preview_returns_pe_ratio_for_profitable(self):
        """TSLA is profitable — pe_ratio populated."""
        data = self._preview('TSLA')
        assert 'pe_ratio' in data
        assert data['pe_ratio'] is not None
        assert isinstance(data['pe_ratio'], (int, float))
        assert data['pe_ratio'] > 0

    def test_preview_returns_eps_for_profitable(self):
        data = self._preview('TSLA')
        assert 'eps' in data
        assert data['eps'] is not None
        assert isinstance(data['eps'], (int, float))

    def test_preview_returns_market_cap(self):
        data = self._preview('TSLA')
        assert 'market_cap' in data
        assert data['market_cap'] is not None
        assert data['market_cap'] > 0

    def test_preview_negative_eps_returns_null_pe_ratio(self):
        """TE has negative EPS — pe_ratio should be None (P/E meaningless with negative earnings)."""
        data = self._preview('TE')
        assert data['eps'] is not None
        assert data['eps'] < 0  # negative EPS
        assert data['pe_ratio'] is None  # pe_ratio null when negative


class TestPreviewFinancialsMarkup:
    """Verify the JS reads the new fields and renders them in the preview card."""

    def test_load_preview_function_exists(self):
        text = open('templates/index.html').read()
        body = _extract_function_body(text, 'loadPreview')
        assert body is not None, 'loadPreview function not found'

    def test_load_preview_reads_pe_ratio(self):
        text = open('templates/index.html').read()
        body = _extract_function_body(text, 'loadPreview')
        assert 'd.pe_ratio' in body, 'loadPreview must read d.pe_ratio'

    def test_load_preview_reads_eps(self):
        text = open('templates/index.html').read()
        body = _extract_function_body(text, 'loadPreview')
        assert 'd.eps' in body, 'loadPreview must read d.eps'

    def test_load_preview_reads_market_cap(self):
        text = open('templates/index.html').read()
        body = _extract_function_body(text, 'loadPreview')
        assert 'd.market_cap' in body, 'loadPreview must read d.market_cap'

    def test_load_preview_uses_format_currency_for_price(self):
        """v3.4.81 fix — uses formatCurrency() instead of raw '$' + toLocaleString()."""
        text = open('templates/index.html').read()
        body = _extract_function_body(text, 'loadPreview')
        assert 'formatCurrency(d.price)' in body, (
            "loadPreview should use formatCurrency(d.price) for locale-aware rendering"
        )
        # Old broken pattern should NOT be present
        assert "'$' + d.price.toLocaleString()" not in body, (
            "Old '$' + d.price.toLocaleString() pattern should be replaced"
        )

    def test_load_preview_uses_format_market_cap(self):
        text = open('templates/index.html').read()
        body = _extract_function_body(text, 'loadPreview')
        assert 'formatMarketCap(d.market_cap)' in body, (
            "loadPreview should use formatMarketCap() helper (v3.4.65)"
        )

    def test_load_preview_handles_null_pe_ratio(self):
        """Defensive guard: pe_ratio null/NaN/negative should not break rendering."""
        text = open('templates/index.html').read()
        body = _extract_function_body(text, 'loadPreview')
        # Must guard with isFinite() — covers null, NaN, Infinity
        assert 'isFinite(d.pe_ratio)' in body, (
            "Defensive isFinite(d.pe_ratio) check required (covers null/NaN/Infinity)"
        )

    def test_load_preview_renders_financial_row(self):
        """Conditional <div class="preview-row preview-financials"> block."""
        text = open('templates/index.html').read()
        body = _extract_function_body(text, 'loadPreview')
        assert 'preview-financials' in body, (
            "loadPreview must include preview-financials row class"
        )

    def test_load_preview_calls_apply_translations_after_innerHTML(self):
        """v3.4.81 Pattern 5d fix — re-translate data-i18n attrs injected via innerHTML."""
        text = open('templates/index.html').read()
        body = _extract_function_body(text, 'loadPreview')
        assert 'applyTranslations' in body, (
            "loadPreview must call applyTranslations() after innerHTML to translate "
            "data-i18n attrs on the new DOM nodes"
        )


class TestPreviewFinancialsCSS:
    """Verify CSS classes are defined for the new financial row."""

    def test_css_has_preview_financials(self):
        css = open('static/css/variables.css').read()
        assert '.preview-financials' in css

    def test_css_has_preview_fin(self):
        css = open('static/css/variables.css').read()
        assert '.preview-fin' in css

    def test_css_has_preview_fin_label(self):
        css = open('static/css/variables.css').read()
        assert '.preview-fin-label' in css

    def test_preview_fin_label_uses_text_muted(self):
        css = open('static/css/variables.css').read()
        # The label should use the muted color for visual hierarchy
        m = re.search(r'\.preview-fin-label\s*\{([^}]+)\}', css)
        assert m is not None
        assert 'var(--text-muted)' in m.group(1)


class TestPreviewFinancialsI18n:
    """Verify i18n keys exist in BOTH zh + en sections (Pattern 5d v3.4.61 lesson)."""

    @staticmethod
    def _sections():
        """Return (zh_section, en_section) from i18n.js by finding `zh: {` and `en: {` blocks."""
        text = open('static/js/i18n.js').read()
        # Find the start positions of zh: and en: dicts
        zh_start = text.find('zh: {')
        en_start = text.find('en: {')
        # Find the matching closing } for each (next standalone })
        # Simpler: use the `,` that separates zh and en
        # zh: { ... }, en: { ... }
        # We find the first top-level }, after zh_start
        depth = 0
        zh_end = None
        i = zh_start + len('zh: {')
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                if depth == 0:
                    zh_end = i
                    break
                depth -= 1
            i += 1
        return text[zh_start:zh_end + 1], text[en_start:]

    def test_eps_label_zh(self):
        zh, _ = self._sections()
        assert "'index.eps_label': 'EPS'" in zh

    def test_eps_label_en(self):
        _, en = self._sections()
        assert "'index.eps_label': 'EPS'" in en

    def test_pe_label_zh_already_existed(self):
        zh, _ = self._sections()
        assert "'index.pe_label': '本益比'" in zh

    def test_pe_label_en_already_existed(self):
        _, en = self._sections()
        assert "'index.pe_label': 'P/E'" in en

    def test_cap_label_zh_already_existed(self):
        zh, _ = self._sections()
        assert "'index.cap_label': '市值'" in zh

    def test_cap_label_en_already_existed(self):
        _, en = self._sections()
        assert "'index.cap_label': 'Cap'" in en


class TestPreviewFinancialsE2ESmoke:
    """End-to-end smoke tests against the running server."""

    def test_root_returns_200(self):
        import urllib.request
        with urllib.request.urlopen('http://localhost:5000/', timeout=5) as r:
            assert r.status == 200

    def test_served_html_has_preview_financials_class(self):
        import urllib.request
        with urllib.request.urlopen('http://localhost:5000/', timeout=5) as r:
            html = r.read().decode('utf-8')
        assert 'preview-financials' in html
        assert 'data-i18n="index.eps_label"' in html
        assert 'data-i18n="index.pe_label"' in html
        assert 'data-i18n="index.cap_label"' in html

    def test_served_html_has_load_preview_function(self):
        import urllib.request
        with urllib.request.urlopen('http://localhost:5000/', timeout=5) as r:
            html = r.read().decode('utf-8')
        assert 'function loadPreview(' in html
        assert 'formatCurrency(d.price)' in html  # v3.4.81 fix
        assert 'formatMarketCap(d.market_cap)' in html  # v3.4.81 new

    def test_served_css_has_preview_financials(self):
        import urllib.request
        with urllib.request.urlopen(
            'http://localhost:5000/static/css/variables.css', timeout=5
        ) as r:
            css = r.read().decode('utf-8')
        assert '.preview-financials' in css
        assert '.preview-fin' in css
        assert '.preview-fin-label' in css

    def test_served_i18n_has_eps_label(self):
        import urllib.request
        with urllib.request.urlopen(
            'http://localhost:5000/static/js/i18n.js', timeout=5
        ) as r:
            js = r.read().decode('utf-8')
        # 2 occurrences — once in zh, once in en
        assert js.count("'index.eps_label'") == 2


class TestPreviewFinancialsJsSyntax:
    """Validate JS syntax via node --check."""

    def test_i18n_js_syntax(self):
        import subprocess
        result = subprocess.run(
            ['node', '--check', 'static/js/i18n.js'],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f'i18n.js syntax error: {result.stderr}'

    def test_index_html_script_syntax(self):
        import re
        import subprocess
        text = open('templates/index.html').read()
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        assert m is not None
        open('/tmp/_check_preview.js', 'w').write(m.group(1))
        result = subprocess.run(
            ['node', '--check', '/tmp/_check_preview.js'],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f'index.html script syntax error: {result.stderr}'


class TestPreviewFinancialsGremlin:
    """Detect invisible Unicode corruption across modified files."""

    def test_index_html_no_mojibake(self):
        data = open('templates/index.html', 'rb').read()
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
            b'\xe2\x80\x8e': 'U+200E',
            b'\xe2\x80\x8f': 'U+200F',
        }
        hits = {label: data.count(b) for b, label in gremlins.items() if data.count(b)}
        assert not hits, f'Mojibake in index.html: {hits}'

    def test_i18n_js_no_mojibake(self):
        data = open('static/js/i18n.js', 'rb').read()
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
            b'\xe2\x80\x8e': 'U+200E',
            b'\xe2\x80\x8f': 'U+200F',
        }
        hits = {label: data.count(b) for b, label in gremlins.items() if data.count(b)}
        assert not hits, f'Mojibake in i18n.js: {hits}'

    def test_variables_css_no_mojibake(self):
        data = open('static/css/variables.css', 'rb').read()
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
            b'\xe2\x80\x8e': 'U+200E',
            b'\xe2\x80\x8f': 'U+200F',
        }
        hits = {label: data.count(b) for b, label in gremlins.items() if data.count(b)}
        assert not hits, f'Mojibake in variables.css: {hits}'