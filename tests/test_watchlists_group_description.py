"""
v3.4.87 — Watchlist groups description surfacing on /watchlists (Pattern 9b).

Bug class: `/api/watchlist-groups` returns `description` (populated for all
groups that opt-in via form) — but `templates/watchlists.html renderGroups()`
silently dropped it. The dashboard's group card (`templates/index.html
loadGroupsDashboard()`) already shows description (since v3.4.x), so this is
a 1-template gap to fill for visual parity.

Fix:
  - templates/watchlists.html renderGroups() — conditional `<div class="group-description">{esc(g.description)}</div>` inside `.group-body`
  - .group-description CSS — muted 0.85rem, italic, left border accent
"""
import json
import os
import re
import sqlite3
import subprocess

import pytest

sys_path = os.path.join(os.path.dirname(__file__), '..')
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

REPO = os.path.expanduser('~/repos/Stocker')
SMOKE_PREFIX = '__DESC_TEST_'


# --- Helpers ---------------------------------------------------------------

def _extract_function_body(source: str, fn_name: str) -> str:
    """Brace-matching body extractor (v3.4.70 lesson: regex on `}` stops at first close-brace)."""
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


def _read_template(name: str) -> str:
    return open(os.path.join(REPO, 'templates', name)).read()


def _read_i18n() -> str:
    return open(os.path.join(REPO, 'static/js/i18n.js')).read()


def _read_css() -> str:
    css = ''
    for path in ['static/css/components.css', 'static/css/mobile.css']:
        try:
            css += open(os.path.join(REPO, path)).read() + '\n'
        except FileNotFoundError:
            pass
    # Also scan inline <style> blocks in templates (watchlists.html has its own)
    for tpl in ['watchlists.html', 'index.html', 'files.html']:
        try:
            text = _read_template(tpl)
            for m in re.finditer(r'<style[^>]*>(.*?)</style>', text, re.DOTALL):
                css += m.group(1) + '\n'
        except FileNotFoundError:
            pass
    return css


# --- API surface ----------------------------------------------------------

class TestWatchlistDescriptionApiSurface:
    """Verify the endpoint returns populated description field."""

    def test_endpoint_returns_description_field(self):
        # Insert smoke row directly via sqlite
        db_path = os.path.join(REPO, 'data/stocker.db')
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("""
                INSERT INTO watchlist_groups (name, description, color, sort_order, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (f'{SMOKE_PREFIX}DESC_TEST', 'Test desc text', '#4fc3f7', 0))
            conn.commit()
        finally:
            conn.close()

        try:
            r = subprocess.run(
                ['curl', '-sS', 'http://localhost:5000/api/watchlist-groups', '-m', '5'],
                capture_output=True, text=True
            )
            data = json.loads(r.stdout)
            assert isinstance(data, list)
            smoke = [g for g in data if g['name'] == f'{SMOKE_PREFIX}DESC_TEST']
            assert len(smoke) == 1, f'Expected 1 smoke group, got {len(smoke)}'
            assert smoke[0].get('description') == 'Test desc text'
        finally:
            # Cleanup
            conn = sqlite3.connect(db_path)
            try:
                conn.execute("DELETE FROM watchlist_groups WHERE name LIKE ?", (f'{SMOKE_PREFIX}%',))
                conn.commit()
            finally:
                conn.close()


# --- Template markup -------------------------------------------------------

class TestWatchlistsDescriptionMarkup:
    """Verify watchlists.html renderGroups() wires g.description."""

    def test_render_groups_function_exists(self):
        text = _read_template('watchlists.html')
        assert _extract_function_body(text, 'renderGroups') is not None

    def test_render_groups_reads_g_description(self):
        text = _read_template('watchlists.html')
        body = _extract_function_body(text, 'renderGroups')
        assert 'g.description' in body, 'renderGroups must read g.description'

    def test_render_groups_renders_group_description_div(self):
        text = _read_template('watchlists.html')
        body = _extract_function_body(text, 'renderGroups')
        assert 'group-description' in body, 'must render .group-description element'

    def test_render_groups_xss_safe_via_esc(self):
        text = _read_template('watchlists.html')
        body = _extract_function_body(text, 'renderGroups')
        # Must use esc() helper, not raw interpolation
        m = re.search(r'group-description.*?esc\(g\.description\)', body, re.DOTALL)
        assert m is not None, 'must XSS-safe via esc() helper on g.description'

    def test_render_groups_conditional_on_truthy(self):
        text = _read_template('watchlists.html')
        body = _extract_function_body(text, 'renderGroups')
        # Conditional ternary `g.description ? ... : ''` ensures empty desc doesn't render
        assert re.search(r"g\.description\s*\?\s*`", body) is not None, \
            'must conditionally render via truthy check on g.description'

    def test_render_groups_empty_groups_empty_state_intact(self):
        """Empty state should not be regressed."""
        text = _read_template('watchlists.html')
        body = _extract_function_body(text, 'renderGroups')
        assert 'empty-state' in body
        assert 'bookmark_border' in body


# --- CSS class definition --------------------------------------------------

class TestGroupDescriptionCss:
    """Verify .group-description CSS class is defined."""

    def test_class_defined(self):
        css = _read_css()
        assert '.group-description' in css, '.group-description class must be defined'

    def test_class_uses_muted_color(self):
        css = _read_css()
        m = re.search(r'\.group-description\s*\{[^}]*color:\s*var\(--text-muted', css)
        assert m is not None, '.group-description must use var(--text-muted) for color'

    def test_class_italic_style(self):
        css = _read_css()
        m = re.search(r'\.group-description\s*\{[^}]*font-style:\s*italic', css)
        assert m is not None, '.group-description must be italic'

    def test_class_has_left_border_accent(self):
        css = _read_css()
        m = re.search(r'\.group-description\s*\{[^}]*border-left:', css)
        assert m is not None, '.group-description must have border-left accent'


# --- End-to-end smoke -----------------------------------------------------

class TestE2ESmoke:
    """Verify served HTML reflects the change."""

    def test_watchlists_page_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost:5000/watchlists', '-m', '5'],
            capture_output=True, text=True
        )
        assert r.stdout == '200'

    def test_served_html_has_group_description_class(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/watchlists', '-m', '5'],
            capture_output=True, text=True
        )
        assert 'group-description' in r.stdout


# --- JS validation --------------------------------------------------------

class TestJsSyntax:
    """Verify inline JS + i18n.js still parse."""

    def test_watchlists_inline_js_valid(self):
        text = _read_template('watchlists.html')
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        assert m is not None
        open('/tmp/check.js', 'w').write(m.group(1))
        r = subprocess.run(['node', '--check', '/tmp/check.js'], capture_output=True, text=True)
        assert r.returncode == 0, f'JS invalid: {r.stderr}'

    def test_i18n_js_valid(self):
        r = subprocess.run(
            ['node', '--check', os.path.join(REPO, 'static/js/i18n.js')],
            capture_output=True, text=True
        )
        assert r.returncode == 0


# --- Gremlin check --------------------------------------------------------

class TestGremlinCheck:
    """No invisible Unicode characters in modified file."""

    def test_no_mojibake(self):
        data = open(os.path.join(REPO, 'templates/watchlists.html'), 'rb').read()
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
            b'\xe2\x80\x8e': 'U+200E',
            b'\xe2\x80\x8f': 'U+200F',
        }
        hits = {label: data.count(b) for b, label in gremlins.items() if data.count(b)}
        assert not hits, f'CORRUPTED: {hits}'