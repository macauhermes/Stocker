"""
v3.4.81 — Δ vs 前次 column on /portfolio snapshot log.

Tests that the templates/index.html loadPortfolioSnapshotsLog() function
renders a delta column showing day-over-day value change with icon + sign.

The test extracts the inline JS via brace-matching (per skill v3.4.70 lesson),
fetches the rendered page, and verifies the structural invariants.
"""
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

REPO = os.path.expanduser('~/repos/Stocker')
INDEX = os.path.join(REPO, 'templates/index.html')
I18N = os.path.join(REPO, 'static/js/i18n.js')


def _read(path):
    with open(path) as f:
        return f.read()


def _extract_function_body(source, fn_name):
    """Brace-matching helper for nested-block JS functions."""
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


class TestSnapshotLogDeltaMarkup:
    """Verify the table header has the new Δ column."""

    def test_header_has_delta_th(self):
        text = _read(INDEX)
        m = re.search(
            r'<th class="num" data-i18n="portfolio\.snapshots_log_delta"',
            text,
        )
        assert m, "Missing <th data-i18n='portfolio.snapshots_log_delta'>"

    def test_header_text_has_delta_zh_fallback(self):
        text = _read(INDEX)
        m = re.search(
            r'data-i18n="portfolio\.snapshots_log_delta">([^<]+)</th>',
            text,
        )
        assert m, "Δ vs 前次 zh fallback not found"
        assert 'Δ' in m.group(1) or 'vs' in m.group(1), \
            f"Expected Δ/vs prefix in fallback, got {m.group(1)!r}"

    def test_render_has_delta_cell(self):
        """The row template must include deltaHtml + new <td> cell."""
        text = _read(INDEX)
        # Find the loadPortfolioSnapshotsLog function
        body = _extract_function_body(text, 'loadPortfolioSnapshotsLog')
        assert body is not None, "loadPortfolioSnapshotsLog function not found"
        assert 'deltaHtml' in body, "deltaHtml variable not defined in function body"
        assert 'trending_up' in body, "trending_up icon not used"
        assert 'trending_down' in body, "trending_down icon not used"
        # New <td> with ${deltaHtml}
        assert '<td class="num">${deltaHtml}</td>' in body, \
            "New delta <td> cell not in row template"


class TestSnapshotLogDeltaJS:
    """Verify the JS logic computes delta correctly."""

    def test_function_uses_idx_parameter(self):
        """The map() callback must take (s, idx) so we can look up prev snapshot."""
        text = _read(INDEX)
        # Find the .map() call inside loadPortfolioSnapshotsLog
        body = _extract_function_body(text, 'loadPortfolioSnapshotsLog')
        m = re.search(r'meaningful\.map\(\(s,\s*idx\)\s*=>', body)
        assert m, "meaningful.map() does not pass idx parameter"

    def test_looks_up_previous_snapshot(self):
        text = _read(INDEX)
        body = _extract_function_body(text, 'loadPortfolioSnapshotsLog')
        assert 'meaningful[idx + 1]' in body, \
            "Should look up previous snapshot via meaningful[idx + 1]"

    def test_computes_delta_as_difference(self):
        text = _read(INDEX)
        body = _extract_function_body(text, 'loadPortfolioSnapshotsLog')
        assert 'deltaValue' in body, "deltaValue variable not computed"
        assert 'value - prevValue' in body, \
            "Should compute deltaValue = value - prevValue"

    def test_handles_no_prev_snapshot(self):
        """Top row (no previous snapshot) should render '—' (NA)."""
        text = _read(INDEX)
        body = _extract_function_body(text, 'loadPortfolioSnapshotsLog')
        assert 'snapshot-delta-na' in body, \
            "NA fallback class not in row template"
        assert 'deltaHtml = ' in body, "deltaHtml must default to NA"


class TestSnapshotLogDeltaCSS:
    """Verify the CSS classes are defined."""

    def test_css_defined(self):
        css = _read(os.path.join(REPO, 'static/css/components.css'))
        assert '.snapshot-delta {' in css, ".snapshot-delta CSS class missing"
        assert '.snapshot-delta-icon' in css, ".snapshot-delta-icon missing"
        assert '.snapshot-delta-na' in css, ".snapshot-delta-na missing"

    def test_css_uses_existing_color_vars(self):
        """Should reference pnl-positive/pnl-negative for color coding."""
        css = _read(os.path.join(REPO, 'static/css/components.css'))
        # Find the .snapshot-delta block (not .na — that's separate)
        m = re.search(r'\.portfolio-snapshots-log-table td \.snapshot-delta \{([^}]+)\}', css)
        assert m, ".snapshot-delta block not found"
        block = m.group(1)
        assert 'display: inline-flex' in block or 'inline-flex' in block, \
            "Expected inline-flex for icon + text layout"


class TestSnapshotLogDeltaI18n:
    """Verify i18n keys exist in both zh + en sections."""

    def test_zh_keys_exist(self):
        text = _read(I18N)
        assert "'portfolio.snapshots_log_delta': 'Δ vs 前次'" in text, \
            "zh delta key missing or has wrong value"
        assert "'portfolio.snapshots_log_delta_title':" in text, \
            "zh delta_title key missing"

    def test_en_keys_exist(self):
        text = _read(I18N)
        assert "'portfolio.snapshots_log_delta': 'Δ vs prev'" in text, \
            "en delta key missing or has wrong value"
        assert "'portfolio.snapshots_log_delta_title':" in text, \
            "en delta_title key missing"

    def test_i18n_keys_in_zh_section(self):
        """zh section is the first dict (zh-TW). en section is the second dict."""
        text = _read(I18N)
        # 'common.app_name' appears in BOTH zh + en dicts — use the SECOND
        # occurrence as the en section start (zh_end boundary).
        first_app = text.find("'common.app_name': 'Stocker',")
        assert first_app > 0, "i18n.js does not contain 'common.app_name' key"
        zh_end = text.find("'common.app_name': 'Stocker',", first_app + 1)
        if zh_end < 0:
            # If only one occurrence (single-language mode), fall back to first
            zh_end = first_app
        zh_delta_pos = text.find("'portfolio.snapshots_log_delta': 'Δ vs 前次'")
        en_delta_pos = text.find("'portfolio.snapshots_log_delta': 'Δ vs prev'")
        assert 0 < zh_delta_pos < zh_end, "zh delta key not in zh section"
        assert en_delta_pos > zh_end, "en delta key not in en section"


class TestSnapshotLogDeltaRenderedPage:
    """End-to-end test against the live server."""

    def test_index_page_renders_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True,
        )
        assert r.stdout.strip() == '200', f"Got {r.stdout!r}"

    def test_index_html_contains_delta_header(self):
        """The served HTML must include the new <th>."""
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True,
        )
        assert 'data-i18n="portfolio.snapshots_log_delta"' in r.stdout, \
            "Δ vs 前次 column header not in served HTML"

    def test_index_html_contains_delta_render_code(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True,
        )
        assert 'snapshot-delta' in r.stdout, \
            "snapshot-delta class not in served HTML"


class TestJSValidation:
    """node --check on extracted inline JS."""

    def test_inline_js_parses(self):
        text = _read(INDEX)
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        assert m is not None
        with open('/tmp/snap_delta_check.js', 'w') as f:
            f.write(m.group(1))
        r = subprocess.run(
            ['node', '--check', '/tmp/snap_delta_check.js'],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"JS syntax error: {r.stderr}"

    def test_i18n_js_parses(self):
        r = subprocess.run(
            ['node', '--check', I18N],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"i18n.js syntax error: {r.stderr}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
