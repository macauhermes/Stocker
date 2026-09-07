"""
v3.4.83 — /api/watchlist-groups[].created_at surfacing on group card (Pattern 9b orphan field).

Bug class:
- /api/watchlist-groups returns 8 keys (color, created_at, description, id, name,
  sort_order, ticker_count, tickers) — `created_at` was silently dropped between
  API and DOM. User had no way to see when a watchlist group was created.
- watchlists.html renderGroups() showed: color dot, name, ticker_count, edit/delete
  buttons. Missing: created_at display.
- index.html loadGroupsDashboard() showed: color border, name + ticker_count,
  description. Missing: created_at display.

Fix scope — pure frontend 4-file surgical addition:
- templates/watchlists.html (+1): new <span class="group-created"> in renderGroups
  group header, guarded by g.created_at truthy, with data-i18n-title for tooltip.
- templates/index.html (+1/-1): new <div> in loadGroupsDashboard group card body,
  guarded by g.created_at, muted 0.7rem color, with data-i18n-title tooltip.
- static/css/components.css (+8): .group-created class — JetBrains Mono NOT used
  (regular font), 0.65rem size, var(--text-muted) color, cursor:help, white-space:nowrap.
- static/js/i18n.js (+4 keys): watchlists.created_at + watchlists.created_at_tooltip
  in BOTH zh + en sections.

0 backend / DB / schema changes — endpoint already returns created_at.
0 new tables / routes / actions — pure template + i18n wiring.
"""
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

REPO = os.path.expanduser('~/repos/Stocker')
WATCHLISTS = os.path.join(REPO, 'templates/watchlists.html')
INDEX = os.path.join(REPO, 'templates/index.html')
I18N = os.path.join(REPO, 'static/js/i18n.js')
CSS = os.path.join(REPO, 'static/css/components.css')


def _read(path):
    with open(path) as f:
        return f.read()


def _extract_function_body(source, fn_name):
    """Brace-matching helper for nested-block JS functions (per skill v3.4.70)."""
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


class TestWatchlistGroupsApiSurface:
    """Verify /api/watchlist-groups returns populated created_at for all groups."""

    def test_endpoint_returns_groups_with_created_at(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/watchlist-groups', '-m', '5'],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"curl failed: {r.stderr}"
        import json
        groups = json.loads(r.stdout)
        # Just verify structure (groups may be empty if user hasn't created any)
        for g in groups:
            assert 'created_at' in g, f"Group {g.get('name')} missing created_at"
            # Should be a SQLite datetime string or None
            assert g['created_at'] is None or re.match(r'^\d{4}-\d{2}-\d{2}', g['created_at']), \
                f"Invalid created_at format: {g['created_at']!r}"

    def test_db_returns_created_at_for_inserted_group(self):
        """Insert a test group, verify created_at populated, clean up."""
        import sqlite3
        db = sqlite3.connect(os.path.expanduser('~/repos/Stocker/data/stocker.db'))
        try:
            db.execute(
                "INSERT INTO watchlist_groups (name, description, color, sort_order, created_at) "
                "VALUES ('__TEST_GRP_CA__', 'temp test for created_at surfacing', '#4fc3f7', 99, '2026-09-07 12:00:00')"
            )
            db.commit()
            gid = db.execute("SELECT id FROM watchlist_groups WHERE name='__TEST_GRP_CA__'").fetchone()[0]

            # Hit endpoint
            r = subprocess.run(
                ['curl', '-sS', 'http://localhost:5000/api/watchlist-groups', '-m', '5'],
                capture_output=True, text=True,
            )
            import json
            groups = json.loads(r.stdout)
            test = next((g for g in groups if g['id'] == gid), None)
            assert test is not None, "Test group not in API response"
            assert test['created_at'] == '2026-09-07 12:00:00', \
                f"created_at mismatch: {test['created_at']!r}"
        finally:
            db.execute("DELETE FROM watchlist_groups WHERE name='__TEST_GRP_CA__'")
            db.commit()
            db.close()


class TestWatchlistsHTMLMarkup:
    """Verify templates/watchlists.html renderGroups() surfaces created_at."""

    def test_render_groups_reads_g_created_at(self):
        text = _read(WATCHLISTS)
        body = _extract_function_body(text, 'renderGroups')
        assert body is not None, "renderGroups function not found"
        assert 'g.created_at' in body, "renderGroups doesn't read g.created_at"

    def test_render_groups_calls_format_date(self):
        text = _read(WATCHLISTS)
        body = _extract_function_body(text, 'renderGroups')
        assert 'formatDate(g.created_at)' in body, "renderGroups doesn't call formatDate()"

    def test_render_groups_calls_created_at_i18n_keys(self):
        text = _read(WATCHLISTS)
        body = _extract_function_body(text, 'renderGroups')
        assert "t('watchlists.created_at'" in body, "watchlists.created_at key not used"
        assert "t('watchlists.created_at_tooltip'" in body, "watchlists.created_at_tooltip key not used"

    def test_render_groups_uses_data_i18n_title(self):
        text = _read(WATCHLISTS)
        body = _extract_function_body(text, 'renderGroups')
        assert 'data-i18n-title="watchlists.created_at_tooltip"' in body, \
            "data-i18n-title attribute not present on new span"

    def test_render_groups_uses_group_created_class(self):
        text = _read(WATCHLISTS)
        body = _extract_function_body(text, 'renderGroups')
        assert 'class="group-created"' in body, "group-created class not used"

    def test_render_groups_guards_against_null_created_at(self):
        """g.created_at ? ... : '' defensive guard prevents 'Invalid Date'."""
        text = _read(WATCHLISTS)
        body = _extract_function_body(text, 'renderGroups')
        # Must use g.created_at truthy guard
        assert 'g.created_at ?' in body, "Missing g.created_at truthy guard"


class TestIndexHTMLMarkup:
    """Verify templates/index.html loadGroupsDashboard() surfaces created_at."""

    def test_load_groups_dashboard_reads_g_created_at(self):
        text = _read(INDEX)
        body = _extract_function_body(text, 'loadGroupsDashboard')
        assert body is not None, "loadGroupsDashboard function not found"
        assert 'g.created_at' in body, "loadGroupsDashboard doesn't read g.created_at"

    def test_load_groups_dashboard_calls_format_date(self):
        text = _read(INDEX)
        body = _extract_function_body(text, 'loadGroupsDashboard')
        assert 'formatDate(g.created_at)' in body, "loadGroupsDashboard doesn't call formatDate()"

    def test_load_groups_dashboard_uses_created_at_i18n(self):
        text = _read(INDEX)
        body = _extract_function_body(text, 'loadGroupsDashboard')
        assert "t('watchlists.created_at'" in body, "watchlists.created_at key not used in dashboard"

    def test_load_groups_dashboard_has_tooltip(self):
        text = _read(INDEX)
        body = _extract_function_body(text, 'loadGroupsDashboard')
        assert 'data-i18n-title="watchlists.created_at_tooltip"' in body, \
            "data-i18n-title attribute not present in dashboard card"


class TestGroupCreatedCSS:
    """Verify .group-created CSS class is defined with proper styling."""

    def test_class_defined(self):
        css = _read(CSS)
        m = re.search(r'\.group-created\s*\{([^}]+)\}', css)
        assert m, ".group-created CSS class missing"

    def test_class_uses_text_muted_color(self):
        css = _read(CSS)
        m = re.search(r'\.group-created\s*\{([^}]+)\}', css)
        block = m.group(1) if m else ''
        assert 'var(--text-muted' in block, f"Expected var(--text-muted), got: {block!r}"

    def test_class_uses_cursor_help(self):
        css = _read(CSS)
        m = re.search(r'\.group-created\s*\{([^}]+)\}', css)
        block = m.group(1) if m else ''
        assert 'cursor: help' in block, f"Expected cursor: help, got: {block!r}"

    def test_class_uses_small_font_size(self):
        css = _read(CSS)
        m = re.search(r'\.group-created\s*\{([^}]+)\}', css)
        block = m.group(1) if m else ''
        # 0.6rem to 0.75rem acceptable for muted hint text
        m_size = re.search(r'font-size:\s*(\d+\.\d+)rem', block)
        assert m_size, f"No font-size in rem: {block!r}"
        size = float(m_size.group(1))
        assert 0.6 <= size <= 0.75, f"font-size {size}rem outside 0.6-0.75 range"


class TestWatchlistCreatedAtI18n:
    """Verify i18n keys exist in BOTH zh + en sections (Pattern 5d v3.4.61 lesson)."""

    def test_zh_created_at_key_exists(self):
        text = _read(I18N)
        m = re.search(r"'watchlists\.created_at':\s*'建立於 \{date\}'", text)
        assert m, "zh watchlists.created_at key missing or wrong value"

    def test_zh_created_at_tooltip_key_exists(self):
        text = _read(I18N)
        m = re.search(r"'watchlists\.created_at_tooltip':\s*'群組建立時間'", text)
        assert m, "zh watchlists.created_at_tooltip key missing or wrong value"

    def test_en_created_at_key_exists(self):
        text = _read(I18N)
        m = re.search(r"'watchlists\.created_at':\s*'Created on \{date\}'", text)
        assert m, "en watchlists.created_at key missing or wrong value"

    def test_en_created_at_tooltip_key_exists(self):
        text = _read(I18N)
        m = re.search(r"'watchlists\.created_at_tooltip':\s*'When this group was created'", text)
        assert m, "en watchlists.created_at_tooltip key missing or wrong value"

    def test_bilingual_section_split(self):
        """zh section is the first dict, en section is the second.
        Both keys must exist in BOTH sections to avoid en-mode literal-key bug."""
        text = _read(I18N)
        # 'common.app_name' appears in BOTH zh + en dicts — use the SECOND
        # occurrence as the en section start (zh_end boundary).
        first_app = text.find("'common.app_name': 'Stocker',")
        assert first_app > 0
        zh_end = text.find("'common.app_name': 'Stocker',", first_app + 1)
        if zh_end < 0:
            zh_end = first_app
        zh_ca = text.find("'watchlists.created_at': '建立於 {date}'")
        en_ca = text.find("'watchlists.created_at': 'Created on {date}'")
        assert 0 < zh_ca < zh_end, "zh created_at key not in zh section"
        assert en_ca > zh_end, "en created_at key not in en section"

    def test_date_placeholder_in_created_at_key(self):
        """The key MUST include {date} placeholder for formatDate() substitution."""
        text = _read(I18N)
        for lang in ['建立於 {date}', 'Created on {date}']:
            assert lang in text, f"Placeholder {lang!r} not in i18n.js"


class TestE2ESmoke:
    """End-to-end test against live server."""

    def test_watchlists_page_renders_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/watchlists', '-m', '5'],
            capture_output=True, text=True,
        )
        assert r.stdout.strip() == '200', f"Got {r.stdout!r}"

    def test_index_page_renders_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True,
        )
        assert r.stdout.strip() == '200', f"Got {r.stdout!r}"

    def test_served_html_contains_new_attributes(self):
        """The served /watchlists HTML must include new markup."""
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/watchlists', '-m', '5'],
            capture_output=True, text=True,
        )
        assert 'group-created' in r.stdout, "group-created class not in served HTML"
        assert 'data-i18n-title="watchlists.created_at_tooltip"' in r.stdout, \
            "tooltip attribute not in served HTML"

    def test_served_html_includes_i18n_keys(self):
        """The served /index.html must include new i18n bindings."""
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True,
        )
        assert 'watchlists.created_at_tooltip' in r.stdout, \
            "created_at_tooltip binding not in served /index.html"


class TestJSValidation:
    """Node syntax check on modified JS files."""

    def test_i18n_js_parses(self):
        r = subprocess.run(
            ['node', '--check', I18N],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"i18n.js syntax error: {r.stderr}"

    def test_watchlists_inline_js_parses(self):
        text = _read(WATCHLISTS)
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        assert m is not None
        with open('/tmp/watchlists_ca_check.js', 'w') as f:
            f.write(m.group(1))
        r = subprocess.run(
            ['node', '--check', '/tmp/watchlists_ca_check.js'],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"watchlists.html JS error: {r.stderr}"

    def test_index_inline_js_parses(self):
        text = _read(INDEX)
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        assert m is not None
        with open('/tmp/index_ca_check.js', 'w') as f:
            f.write(m.group(1))
        r = subprocess.run(
            ['node', '--check', '/tmp/index_ca_check.js'],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"index.html JS error: {r.stderr}"


class TestGremlinCheck:
    """Invisible Unicode char check across all 4 modified files."""

    def test_no_mojibake(self):
        files = [
            os.path.join(REPO, 'static/css/components.css'),
            os.path.join(REPO, 'static/js/i18n.js'),
            os.path.join(REPO, 'templates/index.html'),
            os.path.join(REPO, 'templates/watchlists.html'),
        ]
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
            b'\xe2\x80\x8e': 'U+200E',
            b'\xe2\x80\x8f': 'U+200F',
        }
        for f in files:
            data = open(f, 'rb').read()
            hits = {label: data.count(b) for b, label in gremlins.items() if data.count(b)}
            assert not hits, f"{f}: CORRUPTED {hits}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
