"""
v3.4.82 — Industry page report-card file_path hint (Pattern 9b parallel-orbit).

Tests that templates/industry.html renderReports() function renders an inline
file_path hint pill on report/news cards (matching the v3.4.79 files.html +
v3.4.78 report_detail.html parallel-orbit pattern).

Bug class:
- /api/industry/<sector>/news and /api/sectors/<sector>/reports both return
  populated file_path field (200/200 industry news, 200/200 sector reports).
  v3.4.78 wired file_path on report_detail.html (single report detail page).
  v3.4.79 wired file_path on files.html (file list page). Industry page was
  the only rich report-listing endpoint where file_path was silently dropped
  between API and DOM. User on /industry could see the report title/source/date
  but had no signal that the full file was also saved locally on disk.

Implementation:
- templates/industry.html (+1): new inline <span class="file-path-hint"> added
  to renderReports() report-meta div after date span. Conditional on
  r.file_path truthy (industry news files legitimately NULL some cases).
  Reuses .file-path-hint CSS class from v3.4.79 + files.local_file_tooltip
  i18n key (already bilingual). Zero new i18n keys, zero new CSS rules.

The test extracts the inline JS via brace-matching (v3.4.70 recipe), fetches
the rendered page, and verifies the structural invariants.
"""
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

REPO = os.path.expanduser('~/repos/Stocker')
TPL = os.path.join(REPO, 'templates/industry.html')
CSS = os.path.join(REPO, 'static/css/components.css')
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


class TestIndustryFilePathMarkup:
    """Verify the renderReports() function includes the file_path hint span."""

    def test_render_has_file_path_hint(self):
        text = _read(TPL)
        body = _extract_function_body(text, 'renderReports')
        assert body is not None, "renderReports function not found"
        assert 'file-path-hint' in body, \
            ".file-path-hint class not in renderReports() body"
        assert 'r.file_path' in body, \
            "r.file_path field not referenced in renderReports()"
        # Path extraction: take parent dir via split + slice(-2, -1)
        assert "split('/')" in body, \
            "Path split not in renderReports()"
        assert 'slice(-2, -1)' in body, \
            "Parent dir slice not in renderReports()"

    def test_conditional_on_truthy(self):
        """The hint should be conditional on r.file_path being populated."""
        text = _read(TPL)
        body = _extract_function_body(text, 'renderReports')
        # Look for `${r.file_path ?` ternary
        assert 'r.file_path ?' in body or 'r.file_path?' in body, \
            "file_path hint not wrapped in conditional ternary"

    def test_uses_correct_i18n_key(self):
        """Tooltip should use files.local_file_tooltip (bilingual, already exists)."""
        text = _read(TPL)
        body = _extract_function_body(text, 'renderReports')
        assert 'files.local_file_tooltip' in body, \
            "files.local_file_tooltip i18n key not used in renderReports()"

    def test_uses_escHtml_for_xss_safety(self):
        """Path strings from disk must be escaped before innerHTML injection."""
        text = _read(TPL)
        body = _extract_function_body(text, 'renderReports')
        # Find the file_path hint span and verify escHtml wraps the path
        m = re.search(r'r\.file_path \? `[^`]*file_path[^`]*`', body)
        assert m, "file_path hint template literal not found"
        hint_template = m.group(0)
        assert 'escHtml(r.file_path)' in hint_template, \
            "file_path not wrapped in escHtml() — XSS risk"


class TestIndustryFilePathCSS:
    """Verify the .file-path-hint CSS class is defined (from v3.4.79)."""

    def test_css_class_defined(self):
        css = _read(CSS)
        assert '.file-path-hint {' in css, \
            ".file-path-hint CSS class missing"

    def test_css_has_mono_font(self):
        css = _read(CSS)
        m = re.search(r'\.file-path-hint\s*\{([^}]+)\}', css)
        assert m, ".file-path-hint block not found"
        block = m.group(1)
        assert 'monospace' in block or 'JetBrains' in block, \
            "Expected monospace font in .file-path-hint"


class TestIndustryFilePathI18n:
    """Verify files.local_file_tooltip exists in BOTH zh + en sections."""

    def test_zh_key_exists(self):
        text = _read(I18N)
        assert "'files.local_file_tooltip': '本機已存檔完整檔案於此路徑'" in text, \
            "zh files.local_file_tooltip missing or has wrong value"

    def test_en_key_exists(self):
        text = _read(I18N)
        assert "'files.local_file_tooltip': 'Complete file saved locally at this path'" in text, \
            "en files.local_file_tooltip missing or has wrong value"

    def test_keys_in_both_sections(self):
        """zh key in first dict, en key in second dict."""
        text = _read(I18N)
        first_app = text.find("'common.app_name': 'Stocker',")
        assert first_app > 0, "i18n.js does not contain 'common.app_name'"
        zh_end = text.find("'common.app_name': 'Stocker',", first_app + 1)
        if zh_end < 0:
            zh_end = first_app
        zh_pos = text.find("'files.local_file_tooltip': '本機已存檔完整檔案於此路徑'")
        en_pos = text.find("'files.local_file_tooltip': 'Complete file saved locally at this path'")
        assert 0 < zh_pos < zh_end, "zh key not in zh section"
        assert en_pos > zh_end, "en key not in en section"


class TestIndustryFilePathApiSurface:
    """Verify the underlying endpoint actually returns populated file_path."""

    def test_industry_news_returns_file_path(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/industry/Technology/news', '-m', '5'],
            capture_output=True, text=True,
        )
        data = __import__('json').loads(r.stdout)
        assert isinstance(data, list) and data, "Industry news empty"
        populated = sum(1 for r in data if r.get('file_path'))
        assert populated == len(data), \
            f"file_path not 100% populated: {populated}/{len(data)}"

    def test_sectors_reports_returns_file_path(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/sectors/Technology/reports', '-m', '5'],
            capture_output=True, text=True,
        )
        data = __import__('json').loads(r.stdout)
        if isinstance(data, list) and data:
            populated = sum(1 for r in data if r.get('file_path'))
            assert populated == len(data), \
                f"file_path not 100% populated in sector reports: {populated}/{len(data)}"
        else:
            pytest.skip("sector reports empty for Technology")


class TestIndustryFilePathRenderedPage:
    """End-to-end test against the live server."""

    def test_industry_page_renders_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/industry', '-m', '5'],
            capture_output=True, text=True,
        )
        assert r.stdout.strip() == '200', f"Got {r.stdout!r}"

    def test_served_html_has_file_path_hint_code(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/industry', '-m', '5'],
            capture_output=True, text=True,
        )
        assert 'file-path-hint' in r.stdout, \
            ".file-path-hint not in served /industry HTML"


class TestJSValidation:
    """node --check on extracted inline JS."""

    def test_inline_js_parses(self):
        text = _read(TPL)
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        assert m is not None
        with open('/tmp/industry_fpath_check.js', 'w') as f:
            f.write(m.group(1))
        r = subprocess.run(
            ['node', '--check', '/tmp/industry_fpath_check.js'],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"JS syntax error: {r.stderr}"

    def test_i18n_js_parses(self):
        r = subprocess.run(
            ['node', '--check', I18N],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"i18n.js syntax error: {r.stderr}"


class TestGremlinCheck:
    """Verify no invisible Unicode corruption in modified files."""

    def test_industry_html_clean(self):
        data = open(TPL, 'rb').read()
        gremlins = {b'\xef\xbf\xbd': 'U+FFFD', b'\xc2\xad': 'U+00AD',
                    b'\xe2\x80\x8b': 'U+200B', b'\xef\xbb\xbf': 'U+FEFF'}
        hits = {k: v for k, v in gremlins.items() if data.count(k)}
        assert not hits, f"Corrupted: {hits}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
