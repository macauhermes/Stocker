"""Pattern 9b — /api/files.file_path surfacing on /files page."""
import json
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
REPO = os.path.expanduser('~/repos/Stocker')


def _extract_function_body(source, fn_name):
    """Brace-matching helper for JS function body extraction."""
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


def _curl_json(url):
    r = subprocess.run(['curl', '-sS', f'http://localhost:5000{url}', '-m', '5'],
                      capture_output=True, text=True, cwd=REPO)
    return json.loads(r.stdout)


def _files_template():
    return open(f'{REPO}/templates/files.html').read()


def _i18n():
    return open(f'{REPO}/static/js/i18n.js').read()


def _components_css():
    return open(f'{REPO}/static/css/components.css').read()


class TestFilesFilePathApiSurface:
    def test_endpoint_returns_file_path_field(self):
        d = _curl_json('/api/files?limit=10')
        assert isinstance(d, list) and len(d) > 0
        assert 'file_path' in d[0]

    def test_file_path_populated_for_most_rows(self):
        d = _curl_json('/api/files?limit=2000')
        with_path = sum(1 for f in d if f.get('file_path'))
        ratio = with_path / len(d)
        # Some rows (industry news) legitimately have no file_path — accept ≥90% coverage
        assert ratio >= 0.9, f'Only {with_path}/{len(d)} rows have file_path ({ratio:.1%})'

    def test_file_path_matches_local_disk_for_at_least_one(self):
        d = _curl_json('/api/files?limit=10')
        # find first row with file_path
        for f in d:
            if f.get('file_path'):
                # Path is on disk — should exist
                assert os.path.exists(f['file_path']), f'Path missing on disk: {f["file_path"]}'
                return
        pytest.skip('no rows with file_path in first 10')


class TestFilesTemplateMarkup:
    def test_renders_file_path_hint_class(self):
        t = _files_template()
        # Inline template literal — search the script body
        assert 'file-path-hint' in t

    def test_renders_file_path_title_on_filename(self):
        t = _files_template()
        # The renderFiles body should reference f.file_path
        body = _extract_function_body(t, 'renderFiles')
        assert body is not None, 'renderFiles not found'
        assert 'f.file_path' in body
        assert 'data-i18n-title' in body  # for langchange re-render

    def test_uses_escHtml_for_file_path(self):
        t = _files_template()
        body = _extract_function_body(t, 'renderFiles')
        assert 'escHtml(f.file_path' in body or "escHtml(f.file_path)" in body

    def test_directory_name_extraction(self):
        t = _files_template()
        body = _extract_function_body(t, 'renderFiles')
        # Uses split('/') to extract parent directory
        assert "split('/').slice(-2, -1)" in body or "split(\"/\").slice(-2, -1)" in body


class TestFilesPathHintCss:
    def test_class_defined(self):
        css = _components_css()
        assert '.file-path-hint' in css

    def test_class_has_orange_color(self):
        css = _components_css()
        # Find the .file-path-hint block
        m = re.search(r'\.file-path-hint\s*\{([^}]+)\}', css)
        assert m, '.file-path-hint block not found'
        body = m.group(1)
        # Should have orange tone (var or hex)
        assert 'orange' in body.lower() or 'ff9100' in body.lower()
        assert 'cursor: help' in body or 'cursor:help' in body

    def test_class_has_cursor_help_for_tooltip(self):
        css = _components_css()
        m = re.search(r'\.file-path-hint\s*\{([^}]+)\}', css)
        assert m
        assert 'cursor' in m.group(1)


class TestFilesPathHintI18n:
    def test_zh_key_exists(self):
        i18n = _i18n()
        # Find the zh section (first dict), check 'files.local_file_tooltip' has zh value
        m = re.search(r"^    'files\.local_file_tooltip':\s*'([^']+)'", i18n, re.MULTILINE)
        assert m, 'zh files.local_file_tooltip missing'
        assert any('\u4e00' <= c <= '\u9fff' for c in m.group(1)), f'zh value not CJK: {m.group(1)}'

    def test_en_key_exists(self):
        i18n = _i18n()
        # Must have at least 2 occurrences (zh + en)
        matches = re.findall(r"^    'files\.local_file_tooltip':\s*'([^']+)'", i18n, re.MULTILINE)
        assert len(matches) >= 2, f'Expected 2+ locales, got {len(matches)}'
        # en value should be ASCII
        assert any(all(ord(c) < 128 for c in v) for v in matches)


class TestFilesE2ESmoke:
    def test_files_page_returns_200(self):
        r = subprocess.run(['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
                          'http://localhost:5000/files', '-m', '5'],
                         capture_output=True, text=True, cwd=REPO)
        assert r.stdout == '200'

    def test_served_html_has_file_path_wiring(self):
        r = subprocess.run(['curl', '-sS', 'http://localhost:5000/files', '-m', '5'],
                         capture_output=True, text=True, cwd=REPO)
        html = r.stdout
        # file_path references in inline JS
        assert 'f.file_path' in html
        assert 'file-path-hint' in html
        assert 'data-i18n-title="files.local_file_tooltip"' in html

    def test_langchange_listener_present(self):
        r = subprocess.run(['curl', '-sS', 'http://localhost:5000/files', '-m', '5'],
                         capture_output=True, text=True, cwd=REPO)
        html = r.stdout
        # renderFiles will be called on langchange → tooltips re-translated
        assert "addEventListener('langchange'" in html or 'addEventListener("langchange"' in html


class TestFilesJsSyntax:
    def test_extracted_files_js_parses(self):
        t = _files_template()
        m = re.search(r'<script>(.*?)</script>', t, re.DOTALL)
        assert m, 'no <script> block found'
        open('/tmp/files_check.js', 'w').write(m.group(1))
        r = subprocess.run(['node', '--check', '/tmp/files_check.js'],
                          capture_output=True, text=True)
        assert r.returncode == 0, f'JS syntax error: {r.stderr}'


class TestFilesI18nSyntax:
    def test_i18n_js_parses(self):
        r = subprocess.run(['node', '--check', f'{REPO}/static/js/i18n.js'],
                          capture_output=True, text=True)
        assert r.returncode == 0, f'i18n.js syntax error: {r.stderr}'
