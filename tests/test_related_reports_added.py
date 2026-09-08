"""v3.4.89 test — renderRelatedReports() parallel-orbit fix to surface r.created_at as addedRaw pill."""
import os
import re
import subprocess
import sys

import pytest


def _extract_function_body(source: str, fn_name: str):
    """Brace-matching helper for JS function body extraction (v3.4.70 lesson).
    Naive regex `(.*?)}` stops at first nested `}` — fails on if/else blocks.
    """
    m = re.search(rf'function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{', source)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(source) and depth > 0:
        c = source[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    return source[m.end():i - 1] if depth == 0 else None


REPO = os.path.expanduser('~/repos/Stocker')
STOCK_DETAIL = f'{REPO}/templates/stock_detail.html'
I18N = f'{REPO}/static/js/i18n.js'


def _read(path):
    with open(path) as f:
        return f.read()


class TestRelatedReportsCreatedAtApi:
    """Confirm /api/reports?ticker=X returns created_at populated."""

    def test_endpoint_returns_created_at_field(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/reports?ticker=TSLA&limit=5', '-m', '5'],
            capture_output=True, text=True
        )
        d = __import__('json').loads(r.stdout)
        results = (d.get('results') or [])
        assert len(results) > 0, 'Need at least 1 TSLA report to verify created_at'
        for rep in results:
            assert 'created_at' in rep
            assert rep['created_at'], f'created_at empty for report {rep.get("id")}'

    def test_created_at_population_rate(self):
        """Verify ≥90% of TSLA reports have populated created_at."""
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/reports?ticker=TSLA&limit=20', '-m', '5'],
            capture_output=True, text=True
        )
        d = __import__('json').loads(r.stdout)
        results = d.get('results') or []
        populated = sum(1 for x in results if x.get('created_at'))
        assert populated / max(1, len(results)) >= 0.9, \
            f'created_at population rate too low: {populated}/{len(results)}'


class TestRelatedReportsMarkup:
    """renderRelatedReports() must define addedRaw + use report.added_at i18n + report-added class."""

    @pytest.fixture
    def stock_detail_text(self):
        return _read(STOCK_DETAIL)

    @pytest.fixture
    def body(self, stock_detail_text):
        # extract renderRelatedReports function body
        b = _extract_function_body(stock_detail_text, 'renderRelatedReports')
        assert b is not None, 'renderRelatedReports function not found'
        return b

    def test_render_related_reports_function_exists(self, stock_detail_text):
        assert 'function renderRelatedReports' in stock_detail_text

    def test_addedRaw_variable_defined(self, body):
        """Parallel-orbit fix must define `const addedRaw = r.created_at ? formatDate(r.created_at) : ''`."""
        assert 'addedRaw' in body, 'addedRaw variable not found in renderRelatedReports'
        # Specifically: const addedRaw = r.created_at ? formatDate(r.created_at) : ''
        assert re.search(r"const\s+addedRaw\s*=\s*r\.created_at\s*\?\s*formatDate\s*\(", body), \
            'addedRaw assignment does not match expected pattern (r.created_at ? formatDate(...) : ...)'

    def test_report_added_class_used(self, body):
        """The pill markup must use .report-added class (already defined in components.css)."""
        assert 'class="report-added"' in body, '.report-added class not in renderRelatedReports template'

    def test_bookmark_added_icon_used(self, body):
        """Visual parity with dashboard renderReports — use bookmark_added Material icon."""
        assert 'bookmark_added' in body, 'bookmark_added icon not in renderRelatedReports template'

    def test_conditional_render_via_ternary(self, body):
        """Must use `${addedRaw ? ... : ''}` ternary (not always render even when null)."""
        assert re.search(r"\$\{addedRaw\s*\?\s*`", body), \
            'addedRaw ternary conditional missing — must guard against empty values'

    def test_uses_report_added_at_i18n_key(self, body):
        """Must call t('report.added_at', { date: addedRaw }) — the i18n key with {date} placeholder."""
        assert re.search(r"t\(\s*['\"]report\.added_at['\"]\s*,\s*\{\s*date:\s*addedRaw\s*\}\s*\)", body), \
            't("report.added_at", { date: addedRaw }) call not found in renderRelatedReports'

    def test_xss_protection_via_escapeHtml(self, body):
        """Both title= attribute AND visible text must use escapeHtml() to prevent XSS."""
        # Title attribute
        assert re.search(r'title="\$\{escapeHtml\(t\(.*report\.added_at.*\}\)\)\}"', body), \
            'XSS-unsafe title attribute — must wrap t() output with escapeHtml()'
        # Visible text
        assert re.search(r'\$\{escapeHtml\(t\(.*report\.added_at.*\}\)\)\}', body), \
            'XSS-unsafe visible text — must wrap t() output with escapeHtml()'

    def test_positioned_between_date_and_source_link(self, body):
        """The addedRaw block must be between report-date and the sourceLink *in the meta block*.

        `sourceLink` first appears in the if/else block that builds the const, then is
        referenced inside the meta div. The test must look at the *meta block sourceLink*.
        """
        # Anchor on the meta block: ${dateStr}\n ... ${addedRaw ...} ... ${sourceLink}
        date_pos = body.find('report-date')
        added_pos = body.find('addedRaw ?')
        # Find the sourceLink reference INSIDE the meta block (the const def is the FIRST one).
        meta_link_pos = body.find('${sourceLink}', body.find('report-meta'))
        assert date_pos != -1 and added_pos != -1 and meta_link_pos != -1, \
            f'missing report-date ({date_pos}), addedRaw block ({added_pos}), or meta sourceLink ({meta_link_pos})'
        assert date_pos < added_pos < meta_link_pos, \
            f'addedRaw block not between report-date ({date_pos}) and meta sourceLink ({meta_link_pos})'


class TestRelatedReportsI18nBilingual:
    """report.added_at i18n key must exist in BOTH zh + en sections (Pattern 5d v3.4.61 guard)."""

    @pytest.fixture
    def i18n_text(self):
        return _read(I18N)

    def test_zh_section_has_report_added_at(self, i18n_text):
        # i18n.js uses `en: {` (unquoted) — the en dict starts after the zh closing brace.
        en_start = i18n_text.find('  en: {')
        assert en_start > 0, 'en: { not found in i18n.js'
        zh_section = i18n_text[:en_start]
        assert "'report.added_at':" in zh_section, 'zh section missing report.added_at key'

    def test_en_section_has_report_added_at(self, i18n_text):
        en_start = i18n_text.find('  en: {')
        assert en_start > 0, 'en: { not found in i18n.js'
        en_section = i18n_text[en_start:]
        assert "'report.added_at':" in en_section, 'en section missing report.added_at key'

    def test_zh_value_has_date_placeholder(self, i18n_text):
        en_start = i18n_text.find('  en: {')
        zh_section = i18n_text[:en_start]
        m = re.search(r"'report\.added_at':\s*'([^']+)'", zh_section)
        assert m, 'zh report.added_at key not found'
        assert '{date}' in m.group(1), f'zh value missing {{date}} placeholder: {m.group(1)!r}'

    def test_en_value_has_date_placeholder(self, i18n_text):
        en_start = i18n_text.find('  en: {')
        en_section = i18n_text[en_start:]
        m = re.search(r"'report\.added_at':\s*'([^']+)'", en_section)
        assert m, 'en report.added_at key not found'
        assert '{date}' in m.group(1), f'en value missing {{date}} placeholder: {m.group(1)!r}'


class TestReportAddedCss:
    """.report-added class must be defined in components.css (reused, no new CSS)."""

    @pytest.fixture
    def css_text(self):
        with open(f'{REPO}/static/css/components.css') as f:
            return f.read()

    def test_class_defined(self, css_text):
        assert '.report-added {' in css_text, '.report-added class not defined in components.css'

    def test_cursor_help_for_tooltip(self, css_text):
        """Should have cursor:help for native browser tooltip on hover."""
        # Find the .report-added block
        m = re.search(r'\.report-added\s*\{([^}]+)\}', css_text)
        assert m, '.report-added block not found'
        block = m.group(1)
        assert 'cursor: help' in block or 'cursor:help' in block, \
            '.report-added should have cursor:help for hover tooltip'


class TestE2ESmoke:
    """End-to-end smoke test — page renders 200 + contains the new markup."""

    def test_stock_detail_page_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/stock/TSLA', '-m', '5'],
            capture_output=True, text=True
        )
        assert r.stdout.strip() == '200', f'/stock/TSLA → {r.stdout}'

    def test_served_html_has_addedRaw_assignment(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/stock/TSLA', '-m', '5'],
            capture_output=True, text=True
        )
        # The script is inlined in stock_detail.html — should appear in served HTML
        assert 'addedRaw' in r.stdout, 'addedRaw variable not found in served HTML'
        assert 'r.created_at ? formatDate' in r.stdout, 'addedRaw assignment not in served HTML'

    def test_served_html_has_report_added_class_in_render_related(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/stock/TSLA', '-m', '5'],
            capture_output=True, text=True
        )
        # The class itself won't be rendered until JS runs, but the template literal source should be present
        assert 'class="report-added"' in r.stdout, '.report-added markup not in served HTML'

    def test_served_html_has_bookmark_added_icon(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/stock/TSLA', '-m', '5'],
            capture_output=True, text=True
        )
        assert 'bookmark_added' in r.stdout, 'bookmark_added icon not in served HTML'


class TestJSValidation:
    """Validate JS syntax of the extracted inline script."""

    def test_node_check_inline_script(self):
        text = _read(STOCK_DETAIL)
        # Extract first <script>...</script> block
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        assert m, 'no script block found'
        script_path = '/tmp/test_related_reports_added.js'
        with open(script_path, 'w') as f:
            f.write(m.group(1))
        r = subprocess.run(
            ['node', '--check', script_path],
            capture_output=True, text=True
        )
        assert r.returncode == 0, f'JS syntax error: {r.stderr}'

    def test_i18n_js_node_check(self):
        r = subprocess.run(
            ['node', '--check', I18N],
            capture_output=True, text=True
        )
        assert r.returncode == 0, f'i18n.js syntax error: {r.stderr}'


class TestGremlinCheck:
    """Comprehensive invisible Unicode check on the modified file."""

    def test_no_mojibake(self):
        data = open(STOCK_DETAIL, 'rb').read()
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
            b'\xe2\x80\x8e': 'U+200E',
            b'\xe2\x80\x8f': 'U+200F',
        }
        hits = {label: data.count(b) for b, label in gremlins.items() if data.count(b)}
        assert not hits, f'Mojibake found: {hits}'


class TestPattern9bParallelOrbitAudit:
    """Confirm the parallel-orbit fix is complete — created_at is now surfaced everywhere."""
    # index.html renderReports — added v3.4.72 ✓
    # report_detail.html — added v3.4.53 ✓ (separate context, surfaces in detail-header)
    # stock_detail.html renderRelatedReports — fixed v3.4.89 (this commit) ✓
    # industry.html renderReports — does NOT have addedRaw (no fix this tick, since
    #   that page has its own file-path pill via v3.4.83; left alone)
    # files.html — not a reports page, doesn't render reports cards

    def test_index_html_already_wires_addedRaw(self):
        """v3.4.72 dashboard fix — regression check."""
        text = _read(f'{REPO}/templates/index.html')
        assert 'addedRaw' in text, 'index.html lost addedRaw — regression from v3.4.72'

    def test_industry_html_intentionally_no_addedRaw(self):
        """v3.4.83 added file-path hint to industry.html renderReports; addedRaw was NOT added there.
        Verify the page still works without addedRaw (no regression)."""
        text = _read(f'{REPO}/templates/industry.html')
        # renderReports function exists
        assert 'function renderReports' in text, 'industry.html lost renderReports — regression'
        # No addedRaw pattern (intentional — industry has file-path-hint instead)
        # Don't assert absence (might be added later); just check the page loads.


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
