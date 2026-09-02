"""
v3.4.78 — Pattern 9b orphan field (file_path) surfacing on /report/<id>.

Tests:
  TestReportLocalFileAPI         (3)  /api/reports/<id> returns file_path populated
  TestReportLocalFileMarkup      (5)  templates/report_detail.html wires the new pill
  TestReportLocalFileCSS         (4)  .report-local-file class is defined in components.css
  TestReportLocalFileI18n        (3)  zh + en keys exist (Pattern 5d bilingual guard)
  TestReportLocalFileHelper      (3)  formatFileSize() handles KB/MB/GB + edge cases
  TestReportLocalFileE2ESmoke    (2)  /report/1 returns 200 + wiring markers in HTML

Total: 20 tests.
"""

import os
import re
import sys
import json
import urllib.request
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

REPO = '/home/ubuntu/repos/Stocker'


def _fetch_api(path):
    return json.loads(urllib.request.urlopen(f'http://localhost:5000{path}', timeout=5).read())


def _read_template(name):
    return open(os.path.join(REPO, 'templates', name)).read()


def _read_static(rel):
    return open(os.path.join(REPO, 'static', rel)).read()


def _extract_function_body(source, fn_name):
    """Brace-matching helper — see skill v3.4.70 lesson."""
    m = re.search(rf'function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{', source)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(source) and depth > 0:
        if source[i] == '{': depth += 1
        elif source[i] == '}': depth -= 1
        i += 1
    return source[m.end():i - 1] if depth == 0 else None


class TestReportLocalFileAPI:
    """Verify /api/reports/<id> returns populated file_path."""

    def test_report_detail_returns_file_path(self):
        data = _fetch_api('/api/reports/1')
        assert 'file_path' in data, "API must return file_path field"
        assert data['file_path'], "file_path must be populated (not null/empty)"
        assert data['file_path'].startswith('/'), \
            f"file_path should be absolute path: {data['file_path']}"

    def test_file_path_matches_actual_disk_file(self):
        """Confirm at least one report's file_path points to a real file on disk."""
        data = _fetch_api('/api/reports/1')
        assert os.path.exists(data['file_path']), \
            f"file_path points to non-existent file: {data['file_path']}"

    def test_api_files_endpoint_indexes_by_filename(self):
        """The formatFileSize helper looks up entries by filename — verify the
        filename index works against /api/files."""
        files = _fetch_api('/api/files?limit=2000')
        assert isinstance(files, list)
        assert len(files) > 0, "/api/files must return at least 1 file"
        filenames = {f['filename'] for f in files}
        assert any(f.endswith('.html') or f.endswith('.txt') or f.endswith('.pdf')
                   for f in filenames), \
            "files table should index at least one HTML/TXT/PDF"


class TestReportLocalFileMarkup:
    """Verify templates/report_detail.html wires the new pill correctly."""

    def _report_detail_js(self):
        """Extract the inline <script> block from report_detail.html."""
        html = _read_template('report_detail.html')
        m = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
        assert m, "report_detail.html must have a <script> block"
        return m.group(1)

    def test_report_local_file_div_exists(self):
        """New pill div must be in the markup."""
        html = _read_template('report_detail.html')
        assert 'id="report-local-file"' in html, \
            "Must add id='report-local-file' div to detail-header"
        assert 'display:none' in html.split('report-local-file')[1][:50], \
            "report-local-file div must start hidden (display:none)"

    def test_load_report_reads_data_file_path(self):
        """loadReport() must read data.file_path and conditionally render the pill."""
        js = self._report_detail_js()
        # Find the loadReport function body via brace-matching
        body = _extract_function_body(js, 'loadReport')
        assert body is not None, "loadReport must exist in report_detail.html"
        assert 'data.file_path' in body, \
            "loadReport must read data.file_path"
        # Must check truthy and gate the rendering
        assert re.search(r'if\s*\(\s*data\.file_path\s*\)', body), \
            "Must guard render on data.file_path truthy check"
        # Must derive filename from file_path basename via split('/')
        assert "split('/')" in body or ".split('/')" in body, \
            "Must derive filename from file_path basename via .split('/')"

    def test_pill_includes_folder_icon(self):
        """The Material Icons 'folder' icon is the visual signal that it's a local file."""
        js = self._report_detail_js()
        body = _extract_function_body(js, 'loadReport')
        assert body is not None
        # Look for folder icon — Material Icons uses 'folder' as the icon name
        assert 'folder' in body, \
            "Must render Material Icons 'folder' icon in the pill"

    def test_pill_includes_data_i18n_title(self):
        """The tooltip must use data-i18n-title so it gets translated on langchange."""
        js = self._report_detail_js()
        body = _extract_function_body(js, 'loadReport')
        assert body is not None
        assert 'data-i18n-title="report.local_file_tooltip"' in body, \
            "Pill must have data-i18n-title pointing to report.local_file_tooltip"

    def test_full_path_in_html_title_attribute(self):
        """The HTML title= attribute must contain the full file_path for native tooltip."""
        js = self._report_detail_js()
        body = _extract_function_body(js, 'loadReport')
        assert body is not None
        # Find the title="..." interpolation
        m = re.search(r'title="\$\{escapeHtml\(data\.file_path\)\}"', body)
        assert m, "Must interpolate escapeHtml(data.file_path) into title attribute"


class TestReportLocalFileCSS:
    """Verify static/css/components.css has the new .report-local-file class."""

    def test_class_defined_in_components_css(self):
        css = _read_static('css/components.css')
        assert '.report-local-file {' in css, \
            "Must add .report-local-file class to components.css"

    def test_class_has_cursor_help(self):
        """cursor:help indicates the hover-tooltip affordance (Pattern 9b convention)."""
        css = _read_static('css/components.css')
        # Find the .report-local-file block
        m = re.search(r'\.report-local-file\s*\{([^}]+)\}', css)
        assert m, ".report-local-file class must be defined"
        block = m.group(1)
        assert 'cursor: help' in block, \
            "Must set cursor:help for hover tooltip affordance"

    def test_class_uses_monospace_font(self):
        """Filenames benefit from monospace — same convention as .report-ticker-badge."""
        css = _read_static('css/components.css')
        m = re.search(r'\.report-local-file\s*\{([^}]+)\}', css)
        assert m
        block = m.group(1)
        # Either SF Mono / Monaco / Inconsolata / Fira Code — any of these count
        assert any(ff in block for ff in ['SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', 'monospace']), \
            "Must use a monospace font for filename display"

    def test_class_has_orange_or_visible_color(self):
        """Color must be readable — orange (v3.4.78 choice) or any visible foreground color."""
        css = _read_static('css/components.css')
        m = re.search(r'\.report-local-file\s*\{([^}]+)\}', css)
        assert m
        block = m.group(1)
        # Must have some color: rule
        assert re.search(r'color:\s*[^;]+', block), \
            "Must set a color value (orange / blue / etc.)"


class TestReportLocalFileI18n:
    """Verify zh + en i18n keys exist (Pattern 5d bilingual guard from v3.4.61 lesson)."""

    def _keys_in_section(self, text, section_marker):
        """Extract keys from one of the two const dicts in i18n.js (zh or en)."""
        # Each section is delimited by `const zh = {` ... `};` and `const en = {` ... `};`
        # or similar pattern. Find each dict block.
        keys = set()
        # Simpler approach: track which `const X = {` we're inside via depth counting
        # and only collect keys from the relevant block.
        return keys

    def test_zh_section_has_local_file_key(self):
        text = _read_static('js/i18n.js')
        # Find first 'report.local_file' occurrence (zh section)
        zh_block_match = re.search(r"report\.local_file':\s*'本地存檔'", text)
        assert zh_block_match, \
            "zh section must define report.local_file = '本地存檔'"

    def test_en_section_has_local_file_key(self):
        text = _read_static('js/i18n.js')
        en_block_match = re.search(r"report\.local_file':\s*'Local file'", text)
        assert en_block_match, \
            "en section must define report.local_file = 'Local file'"

    def test_tooltip_keys_bilingual(self):
        """Both zh + en must have the tooltip key (Pattern 5d v3.4.61 lesson)."""
        text = _read_static('js/i18n.js')
        zh = re.search(r"report\.local_file_tooltip':\s*'本機已存檔完整檔案於此路徑'", text)
        en = re.search(r"report\.local_file_tooltip':\s*'Complete file saved locally at this path'", text)
        assert zh, "zh section must define report.local_file_tooltip"
        assert en, "en section must define report.local_file_tooltip"


class TestReportLocalFileHelper:
    """Verify formatFileSize() handles KB/MB/GB tiers + edge cases."""

    def _helper_body(self):
        js = _read_template('report_detail.html')
        m = re.search(r'<script>(.*?)</script>', js, re.DOTALL)
        return _extract_function_body(m.group(1), 'formatFileSize')

    def test_helper_defined(self):
        body = self._helper_body()
        assert body is not None, "formatFileSize must be defined in report_detail.html"

    def test_helper_handles_tier_boundaries(self):
        """Test the 4 tier branches: <1024 = B, <1024*1024 = KB, <1024*1024*1024 = MB, else GB."""
        body = self._helper_body()
        assert body is not None
        # 1024 boundary check
        assert '< 1024' in body, "Must check <1024 for bytes tier"
        # KB tier
        assert '1024 * 1024' in body or '1048576' in body, \
            "Must check <1024*1024 for KB tier"
        # MB tier
        assert body.count('1024 * 1024') >= 2 or '1024 * 1024 * 1024' in body, \
            "Must have MB tier"
        # GB tier
        assert '1024 * 1024 * 1024' in body or '1073741824' in body, \
            "Must have GB tier"

    def test_helper_guards_against_bad_input(self):
        """Defensive guard for non-number / negative / Infinity — Pattern 5d lesson."""
        body = self._helper_body()
        assert body is not None
        # Must reject non-number / negative / non-finite values
        assert re.search(r"typeof\s+bytes\s*!==\s*['\"]number['\"]", body) or \
               'isFinite' in body, \
            "Must guard against bad input (typeof / isFinite check)"


class TestReportLocalFileE2ESmoke:
    """Verify the page renders and includes all wiring markers."""

    def test_report_detail_page_returns_200(self):
        """Sanity: page renders successfully with the new pill markup."""
        r = subprocess.run(['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
                           'http://localhost:5000/report/1', '-m', '5'],
                          capture_output=True, text=True)
        assert r.stdout == '200', \
            f"/report/1 must return 200, got {r.stdout}"

    def test_served_html_has_wiring_markers(self):
        """Verify served HTML contains all the wiring (proves template renders)."""
        r = subprocess.run(['curl', '-sS', 'http://localhost:5000/report/1', '-m', '5'],
                          capture_output=True, text=True)
        html = r.stdout
        # Markup marker
        assert 'id="report-local-file"' in html, \
            "Served HTML must include the report-local-file div"
        # JS markers (verify the inline JS still references data.file_path)
        assert 'data.file_path' in html, \
            "Served HTML must include data.file_path JS reference"
        assert 'data-i18n-title="report.local_file_tooltip"' in html, \
            "Served HTML must include the data-i18n-title attribute"
        # Helper definition
        assert 'function formatFileSize' in html, \
            "Served HTML must include formatFileSize helper"
        # CSS file is served separately — fetch and verify the class is defined there
        r2 = subprocess.run(['curl', '-sS', 'http://localhost:5000/static/css/components.css', '-m', '5'],
                           capture_output=True, text=True)
        assert '.report-local-file' in r2.stdout, \
            "Served components.css must include the .report-local-file class"