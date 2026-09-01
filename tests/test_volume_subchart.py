"""Tests for Volume sub-chart on stock_detail.html (v3.4.70).

Pattern: Surface orphan chart-data field (prices_full.volume) that the
chart-data API already returns but the template silently dropped between
API and DOM. Same Pattern 9b orphan-field surfacing that landed MACD + RSI
in v3.4.69 — the prices_full dict contains 5 keys (close, high, low, open,
volume) but only 4 were used (candlestick plugin needs OHLC, volume was
silently dropped).

This test verifies:
  1. /api/stock/<sym>/chart-data returns prices_full.volume populated
  2. The template renders the volume-chart wrapper (initially hidden)
  3. The toggle function exists and is wired to checkbox onchange handler
  4. The renderer function exists and consumes prices_full.volume
  5. i18n key 'detail.volume_label' exists in BOTH zh + en sections
  6. formatVolume() helper exists in i18n.js and is used by stock_detail
  7. Volume chart re-renders on zoom alongside MACD/RSI
"""
import re
import os
import sys
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _fetch_chart_data(symbol='TSLA'):
    """Fetch /api/stock/<sym>/chart-data and return parsed JSON."""
    out = subprocess.run(
        ['curl', '-sS', f'http://localhost:5000/api/stock/{symbol}/chart-data', '-m', '5'],
        capture_output=True, text=True, timeout=8,
    )
    return json.loads(out.stdout)


def _read_template():
    """Return stock_detail.html source."""
    with open('templates/stock_detail.html', 'r') as f:
        return f.read()


def _read_i18n():
    """Return static/js/i18n.js source."""
    with open('static/js/i18n.js', 'r') as f:
        return f.read()


def _extract_function_body(source, fn_name):
    """Extract the body of `function fn_name(...) {...}` from JS source.

    Uses brace matching to handle nested braces correctly (regex on `}` stops
    at first close-brace which fails for functions with `if/else` blocks).
    """
    m = re.search(rf'function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{', source)
    if not m:
        return None
    # Brace-match from m.end()
    depth = 1
    i = m.end()
    while i < len(source) and depth > 0:
        c = source[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return source[m.end():i - 1]


class TestChartDataVolumeOrphan:
    """Verify /api/stock/<sym>/chart-data returns prices_full.volume."""

    def test_prices_full_contains_volume(self):
        """API should return prices_full dict with volume key."""
        d = _fetch_chart_data()
        assert 'prices_full' in d, 'API missing prices_full'
        assert 'volume' in d['prices_full'], 'API prices_full missing volume (orphan field)'

    def test_volume_is_populated_for_tsla(self):
        """TSLA volume should have 65 numeric entries (range=3m default)."""
        d = _fetch_chart_data()
        vol = d['prices_full']['volume']
        assert len(vol) > 0, 'volume is empty'
        # All non-null
        assert all(v is not None for v in vol), f'volume has nulls: {vol}'
        # All numeric (int)
        assert all(isinstance(v, (int, float)) for v in vol), f'volume has non-numeric: {vol}'

    def test_volume_aligned_with_prices(self):
        """Volume array length should match prices array length."""
        d = _fetch_chart_data()
        vol = d['prices_full']['volume']
        prices = d['prices']
        assert len(vol) == len(prices), f'volume len {len(vol)} != prices len {len(prices)}'

    def test_volume_has_reasonable_values(self):
        """TSLA typical daily volume 10M-100M shares; should be in that range."""
        d = _fetch_chart_data()
        vol = d['prices_full']['volume']
        avg = sum(vol) / len(vol)
        # Allow wide range but should not be 0 (would mean yfinance returned no volume)
        assert avg > 1_000_000, f'avg volume too low: {avg} (yfinance may have lost data)'
        assert avg < 1_000_000_000, f'avg volume too high: {avg}'


class TestVolumeMarkup:
    """Verify template renders volume-chart wrapper + checkbox + label."""

    def test_volume_chart_wrapper_exists(self):
        t = _read_template()
        assert 'id="volume-chart-wrapper"' in t, 'volume-chart-wrapper div missing'

    def test_volume_wrapper_initially_hidden(self):
        t = _read_template()
        # The wrapper should have style="display:none;" inline
        m = re.search(r'<div id="volume-chart-wrapper"[^>]*>', t)
        assert m, 'volume-chart-wrapper tag not found'
        assert 'display:none' in m.group(0), 'volume wrapper should be hidden by default'

    def test_volume_canvas_id(self):
        t = _read_template()
        assert 'id="volume-chart"' in t, 'volume-chart canvas missing'

    def test_volume_checkbox_with_correct_handler(self):
        t = _read_template()
        # Should have a checkbox with data-indicator="volume" calling toggleVolumeSubchart
        m = re.search(r'<input[^>]*data-indicator="volume"[^>]*>', t)
        assert m, 'volume checkbox not found'
        assert 'onchange="toggleVolumeSubchart()"' in m.group(0), \
            'volume checkbox onchange must call toggleVolumeSubchart()'

    def test_volume_label_has_i18n(self):
        t = _read_template()
        # The volume-chart-wrapper label should have data-i18n="detail.volume_label"
        # Match the wrapper div to its closing </div>, then check for the i18n attribute
        m = re.search(r'<div id="volume-chart-wrapper".*?</div>\s*</div>', t, re.DOTALL)
        assert m, 'volume wrapper block not found'
        assert 'data-i18n="detail.volume_label"' in m.group(0), \
            'volume wrapper label missing data-i18n="detail.volume_label"'

    def test_toggle_in_indicator_toolbar(self):
        """Volume checkbox should sit in the indicator toggles row (next to MACD)."""
        t = _read_template()
        # The volume checkbox should be in the indicator toolbar (between RSI and the price-chart canvas)
        indicator_row_match = re.search(
            r'data-indicator="rsi".*?data-indicator="volume".*?data-indicator="macd"|<input[^>]*data-indicator="macd".*?<input[^>]*data-indicator="volume"|<input[^>]*data-indicator="volume"',
            t, re.DOTALL
        )
        # At minimum, all 3 checkboxes (rsi, macd, volume) should be in the same indicator toolbar
        rs_pos = t.find('data-indicator="rsi"')
        macd_pos = t.find('data-indicator="macd"')
        vol_pos = t.find('data-indicator="volume"')
        assert rs_pos > 0 and macd_pos > 0 and vol_pos > 0, \
            f'all 3 indicator checkboxes should exist (rsi={rs_pos}, macd={macd_pos}, volume={vol_pos})'


class TestVolumeJSFunctions:
    """Verify toggleVolumeSubchart + renderVolumeChart + formatVolume exist."""

    def test_toggle_volume_subchart_defined(self):
        t = _read_template()
        m = re.search(r'function\s+toggleVolumeSubchart\s*\([^)]*\)\s*\{', t)
        assert m, 'function toggleVolumeSubchart() not defined'

    def test_toggle_consumes_volume_data(self):
        """toggleVolumeSubchart should call renderVolumeChart(chartData)."""
        t = _read_template()
        body = _extract_function_body(t, 'toggleVolumeSubchart')
        assert body is not None, 'toggleVolumeSubchart body not found'
        assert 'renderVolumeChart(chartData)' in body, \
            'toggleVolumeSubchart must call renderVolumeChart(chartData) on show'
        assert 'volumeChart.destroy()' in body, \
            'toggleVolumeSubchart must destroy chart on hide to prevent memory leak'

    def test_render_volume_chart_defined(self):
        t = _read_template()
        m = re.search(r'function\s+renderVolumeChart\s*\([^)]*\)\s*\{', t)
        assert m, 'function renderVolumeChart() not defined'

    def test_render_volume_consumes_prices_full(self):
        """renderVolumeChart must read prices_full.volume (orphan field)."""
        t = _read_template()
        body = _extract_function_body(t, 'renderVolumeChart')
        assert body is not None, 'renderVolumeChart body not found'
        assert "prices_full.volume" in body or "prices_full' ].volume" in body or \
               'prices_full && data.prices_full.volume' in body, \
            'renderVolumeChart must read data.prices_full.volume (orphan field)'
        assert 'prices_full.open' in body, 'renderVolumeChart needs open for color'
        assert 'prices_full.close' in body, 'renderVolumeChart needs close for color'

    def test_render_volume_color_codes_by_direction(self):
        """Volume bars should be green when close >= open, red otherwise (bullish/bearish)."""
        t = _read_template()
        body = _extract_function_body(t, 'renderVolumeChart')
        assert body is not None
        # Should have bullish (green) + bearish (red) color references
        assert 'rgba(0,200,83' in body, 'bullish (green) color missing'
        assert 'rgba(255,23,68' in body, 'bearish (red) color missing'

    def test_render_volume_uses_format_volume(self):
        """renderVolumeChart should use formatVolume() for y-axis ticks + tooltip."""
        t = _read_template()
        body = _extract_function_body(t, 'renderVolumeChart')
        assert body is not None
        # formatVolume should be called at least once (tooltip callback + y-axis ticks)
        assert body.count('formatVolume') >= 2, \
            f'formatVolume() should be called in tooltip + y-axis ticks (count={body.count("formatVolume")})'

    def test_volume_chart_global_instance(self):
        """Volume chart instance must be tracked globally for destroy on toggle-off + zoom."""
        t = _read_template()
        assert 'let volumeChart = null' in t, 'global volumeChart instance missing'

    def test_zoom_rerenders_volume(self):
        """renderChart() zoom re-render must include volume sub-chart."""
        t = _read_template()
        # The zoom re-render block should call renderVolumeChart(data) when checkbox checked
        m = re.search(r'const\s+rsiCb.*?renderRsiChart\(data\);.*?renderVolumeChart\(data\)', t, re.DOTALL)
        assert m, 'renderChart zoom re-render must call renderVolumeChart(data)'


class TestVolumeI18nKeys:
    """Verify detail.volume_label exists in both zh + en i18n sections."""

    def test_volume_label_zh(self):
        i18n = _read_i18n()
        # zh section is the first dict literal (zh is default)
        assert "'detail.volume_label': '成交量'" in i18n or '"detail.volume_label": "成交量"' in i18n, \
            'detail.volume_label missing in zh section'

    def test_volume_label_en(self):
        i18n = _read_i18n()
        assert "'detail.volume_label': 'Volume'" in i18n or '"detail.volume_label": "Volume"' in i18n, \
            'detail.volume_label missing in en section'


class TestFormatVolumeHelper:
    """Verify formatVolume() helper exists in i18n.js."""

    def test_format_volume_defined(self):
        i18n = _read_i18n()
        m = re.search(r'function\s+formatVolume\s*\([^)]*\)\s*\{', i18n)
        assert m, 'function formatVolume() not defined in i18n.js'

    def test_format_volume_tier_coverage(self):
        """formatVolume must handle T/B/M/K ranges (similar to formatMarketCap)."""
        i18n = _read_i18n()
        body = _extract_function_body(i18n, 'formatVolume')
        assert body is not None
        for tier in ['1e12', '1e9', '1e6', '1e3']:
            assert tier in body, f'formatVolume missing tier {tier}'
        assert '—' in body, 'formatVolume must handle null/NaN → —'

    def test_format_volume_no_dollar_prefix(self):
        """Volume is unitless (share count), should NOT have $ prefix unlike market cap."""
        i18n = _read_i18n()
        body = _extract_function_body(i18n, 'formatVolume')
        assert body is not None
        # Check that return statements don't include '$' prefix
        return_stmts = re.findall(r'return\s+[^;]+', body)
        for stmt in return_stmts:
            assert "'$" not in stmt and '"$' not in stmt, \
                f'formatVolume returns have $ prefix (should be unitless): {stmt}'


class TestVolumeEndToEnd:
    """Smoke test that the rendered page contains all the new wiring."""

    def test_served_html_has_volume_wiring(self):
        """Hit /stock/TSLA, verify volume toggle + wrapper + functions + i18n all present."""
        out = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/stock/TSLA', '-m', '5'],
            capture_output=True, text=True, timeout=8,
        )
        html = out.stdout
        markers = [
            'data-indicator="volume"',
            'toggleVolumeSubchart',
            'renderVolumeChart',
            'volume-chart-wrapper',
            'detail.volume_label',
            'formatVolume',
        ]
        for m in markers:
            assert m in html, f'served HTML missing marker {m!r}'

    def test_volume_checkbox_unchecked_by_default(self):
        """Volume toggle should be OFF by default (consistent with MACD + RSI)."""
        out = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/stock/TSLA', '-m', '5'],
            capture_output=True, text=True, timeout=8,
        )
        html = out.stdout
        # The volume input should NOT have 'checked' attribute (MACD/RSI are unchecked too)
        m = re.search(r'<input[^>]*data-indicator="volume"[^>]*>', html)
        assert m
        assert 'checked' not in m.group(0), 'volume checkbox should NOT be checked by default'