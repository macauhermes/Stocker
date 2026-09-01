"""Tests for MACD + RSI sub-charts on stock_detail.html (v3.4.69).

Pattern: Surface orphan chart-data fields (macd, macd_signal, macd_hist, rsi)
that the API already returns but the template silently dropped. RSI + MACD
toggle checkboxes existed in markup but their onchange handlers called
updateChart() which never rendered them — pure dead controls.

This test verifies:
  1. The orphan fields ARE returned by /api/stock/<sym>/chart-data
  2. The template renders the sub-chart wrappers (initially hidden)
  3. The toggle functions exist and are wired to checkbox onchange handlers
  4. The renderer functions exist and consume the orphan fields
  5. i18n keys exist in both zh + en sections
"""
import re
import os
import sys
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestChartDataOrphanFields:
    """Verify /api/stock/<sym>/chart-data returns MACD + RSI series."""

    def test_chart_data_includes_macd_series(self):
        """API should return macd + macd_signal + macd_hist as orphan series."""
        out = subprocess.run(
            ['curl', '-sS',
             'http://localhost:5000/api/stock/TSLA/chart-data?range=3mo',
             '-m', '5'],
            capture_output=True, text=True
        ).stdout
        data = json.loads(out)
        for key in ('macd', 'macd_signal', 'macd_hist', 'rsi'):
            assert key in data, f"chart-data missing orphan field: {key}"
            assert isinstance(data[key], list), f"{key} should be a list"

    def test_chart_data_orphan_fields_have_same_length_as_prices(self):
        """All series must align with dates/prices for charting to work."""
        out = subprocess.run(
            ['curl', '-sS',
             'http://localhost:5000/api/stock/TSLA/chart-data?range=3mo',
             '-m', '5'],
            capture_output=True, text=True
        ).stdout
        data = json.loads(out)
        n = len(data.get('prices', []))
        for key in ('macd', 'macd_signal', 'macd_hist', 'rsi'):
            assert len(data[key]) == n, (
                f"{key} length {len(data[key])} != prices length {n}"
            )


class TestSubChartMarkup:
    """Verify stock_detail.html renders the sub-chart containers."""

    @classmethod
    def setup_class(cls):
        cls.html = open('templates/stock_detail.html').read()

    def test_macd_wrapper_exists(self):
        assert 'id="macd-chart-wrapper"' in self.html, (
            "Missing #macd-chart-wrapper div in stock_detail.html"
        )

    def test_rsi_wrapper_exists(self):
        assert 'id="rsi-chart-wrapper"' in self.html, (
            "Missing #rsi-chart-wrapper div in stock_detail.html"
        )

    def test_subcharts_initially_hidden(self):
        """Both wrappers must start with display:none (off by default)."""
        m1 = re.search(r'id="macd-chart-wrapper"[^>]*style="([^"]+)"', self.html)
        m2 = re.search(r'id="rsi-chart-wrapper"[^>]*style="([^"]+)"', self.html)
        assert m1 and 'display:none' in m1.group(1), (
            "macd wrapper should start hidden (display:none)"
        )
        assert m2 and 'display:none' in m2.group(1), (
            "rsi wrapper should start hidden (display:none)"
        )

    def test_toggle_macd_handler_wired(self):
        """MACD checkbox onchange must call toggleMacdSubchart (NOT updateChart)."""
        m = re.search(
            r'<input type="checkbox" data-indicator="macd"[^>]+onchange="([^"]+)"',
            self.html
        )
        assert m, "MACD checkbox not found"
        assert m.group(1) == 'toggleMacdSubchart()', (
            f"MACD checkbox should call toggleMacdSubchart, got {m.group(1)!r}"
        )

    def test_toggle_rsi_handler_wired(self):
        """RSI checkbox onchange must call toggleRsiSubchart (NOT updateChart)."""
        m = re.search(
            r'<input type="checkbox" data-indicator="rsi"[^>]+onchange="([^"]+)"',
            self.html
        )
        assert m, "RSI checkbox not found"
        assert m.group(1) == 'toggleRsiSubchart()', (
            f"RSI checkbox should call toggleRsiSubchart, got {m.group(1)!r}"
        )


class TestSubChartJSFunctions:
    """Verify the toggle + render functions are defined."""

    @classmethod
    def setup_class(cls):
        text = open('templates/stock_detail.html').read()
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        cls.js = m.group(1) if m else ''

    def test_toggle_macd_defined(self):
        assert 'function toggleMacdSubchart()' in self.js

    def test_toggle_rsi_defined(self):
        assert 'function toggleRsiSubchart()' in self.js

    def test_render_macd_defined(self):
        assert 'function renderMacdChart(data)' in self.js

    def test_render_rsi_defined(self):
        assert 'function renderRsiChart(data)' in self.js

    def test_render_macd_consumes_orphan_fields(self):
        """The renderer must read macd/macd_signal/macd_hist from data."""
        assert 'data.macd' in self.js
        assert 'data.macd_signal' in self.js
        assert 'data.macd_hist' in self.js

    def test_render_rsi_consumes_orphan_field(self):
        """The renderer must read rsi from data."""
        assert 'data.rsi' in self.js

    def test_chart_instance_vars_declared(self):
        """macdChart + rsiChart must be declared at module scope."""
        assert 'let macdChart' in self.js
        assert 'let rsiChart' in self.js

    def test_subcharts_destroyed_on_toggle_off(self):
        """Toggling off must destroy the Chart.js instance (no memory leak)."""
        # Both toggle functions should call .destroy() when unchecked
        for fn in ('toggleMacdSubchart', 'toggleRsiSubchart'):
            pattern = rf'function {fn}\(\).*?\.destroy\(\)'
            assert re.search(pattern, self.js, re.DOTALL), (
                f"{fn} should call .destroy() on the chart instance when off"
            )

    def test_render_chart_re_renders_subcharts_on_zoom(self):
        """renderChart() must re-render MACD + RSI when zoom changes."""
        assert 'renderMacdChart(data)' in self.js
        assert 'renderRsiChart(data)' in self.js


class TestSubChartI18nKeys:
    """Verify bilingual i18n coverage for new labels (Pattern 5d guard)."""

    @classmethod
    def setup_class(cls):
        cls.i18n = open('static/js/i18n.js').read()

    def test_zh_keys_present(self):
        zh_section, _ = self._split_i18n()
        for key in ('detail.macd_label', 'detail.rsi_label',
                    'detail.rsi_overbought', 'detail.rsi_oversold'):
            assert key in zh_section, f"zh section missing key {key!r}"

    def test_en_keys_present(self):
        _, en_section = self._split_i18n()
        for key in ('detail.macd_label', 'detail.rsi_label',
                    'detail.rsi_overbought', 'detail.rsi_oversold'):
            assert key in en_section, f"en section missing key {key!r}"

    def _split_i18n(self):
        """Split i18n.js into zh (first dict) + en (second dict) sections."""
        # i18n.js structure: `const I18N = { zh: {...}, en: {...} };`
        zh_start = self.i18n.find('  zh: {')
        en_start = self.i18n.find('  en: {')
        assert zh_start != -1 and en_start != -1, (
            f"Couldn't find zh: {{ or en: {{ anchors"
        )

        def find_block_end(text, start):
            i = text.find('{', start)
            depth = 1
            while i != -1 and depth > 0:
                i += 1
                if i >= len(text): break
                ch = text[i]
                if ch == '{': depth += 1
                elif ch == '}': depth -= 1
            return i

        zh_end = find_block_end(self.i18n, zh_start)
        en_end = find_block_end(self.i18n, en_start)
        return self.i18n[zh_start:zh_end], self.i18n[en_start:en_end]


class TestSubChartCSS:
    """Verify the wrapper + label CSS classes exist."""

    @classmethod
    def setup_class(cls):
        cls.css = open('static/css/components.css').read()

    def test_indicator_chart_wrapper_class(self):
        assert '.indicator-chart-wrapper' in self.css

    def test_indicator_chart_label_class(self):
        assert '.indicator-chart-label' in self.css

    def test_mobile_responsive_height(self):
        """Should have a <480px breakpoint shrinking the sub-chart height."""
        assert 'max-width: 480px' in self.css
