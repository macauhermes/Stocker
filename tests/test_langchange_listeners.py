"""Test that templates/watchlists.html and templates/report_detail.html
have langchange listeners (Pattern 5d sub-class: missing langchange listener).

Bug class: dynamic t() calls in JS template literals render with the
load-time language and stay frozen until page reload. Adding a langchange
listener that re-renders the affected UI fixes the bug.

Coverage:
- Both templates have at least one langchange listener
- watchlists listener re-renders group cards (renderGroups) and modal title
- report_detail listener re-renders via loadReport()
"""
import re
from pathlib import Path

TEMPLATES_DIR = Path('/home/ubuntu/repos/Stocker/templates')


def _extract_script(template_name):
    """Extract the inline <script> block from a template."""
    text = (TEMPLATES_DIR / template_name).read_text()
    m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
    return m.group(1) if m else ''


class TestWatchlistsLangchange:
    """watchlists.html had no langchange listener — renderGroups() built DOM
    via ${t('...')} but the listener was missing, leaving group cards, edit/delete
    tooltips, and add-ticker button text frozen at load-time language."""

    def test_template_has_langchange_listener(self):
        script = _extract_script('watchlists.html')
        assert "addEventListener('langchange'" in script, (
            'watchlists.html missing langchange listener — '
            'dynamic t() calls in renderGroups() stay frozen on language switch'
        )

    def test_langchange_handler_calls_renderggroups(self):
        script = _extract_script('watchlists.html')
        # Extract langchange handler body via brace matching
        m = re.search(r"addEventListener\('langchange',\s*\(?\)\s*=>\s*\{", script)
        assert m, 'langchange handler not found'
        depth = 1
        i = m.end()
        while i < len(script) and depth > 0:
            if script[i] == '{': depth += 1
            elif script[i] == '}': depth -= 1
            i += 1
        body = script[m.end():i - 1]
        assert 'renderGroups' in body, (
            'langchange handler does not re-render group cards'
        )

    def test_modal_title_also_re_rendered(self):
        """If the modal is open when langchange fires, the title text
        (watchlists.edit_title / watchlists.add_title) should refresh too."""
        script = _extract_script('watchlists.html')
        assert 'group-modal-title' in script, (
            'langchange handler should also refresh modal title'
        )

    def test_page_renders_200_ok(self):
        import urllib.request
        req = urllib.request.urlopen('http://localhost:5000/watchlists', timeout=5)
        assert req.status == 200


class TestReportDetailLangchange:
    """report_detail.html had no langchange listener — loadReport() built
    many ${t('...')} template literals (source_external, no_source,
    no_analysis, rating_summary, rating.{buy,hold,sell}, analysts,
    common.error, etc) but the listener was missing."""

    def test_template_has_langchange_listener(self):
        script = _extract_script('report_detail.html')
        assert "addEventListener('langchange'" in script, (
            'report_detail.html missing langchange listener'
        )

    def test_langchange_handler_calls_loadreport(self):
        script = _extract_script('report_detail.html')
        m = re.search(r"addEventListener\('langchange',\s*\(?\)\s*=>\s*\{", script)
        assert m, 'langchange handler not found'
        depth = 1
        i = m.end()
        while i < len(script) and depth > 0:
            if script[i] == '{': depth += 1
            elif script[i] == '}': depth -= 1
            i += 1
        body = script[m.end():i - 1]
        assert 'loadReport' in body, (
            'langchange handler does not re-call loadReport() to refresh translations'
        )

    def test_page_renders_200_ok(self):
        import urllib.request
        req = urllib.request.urlopen('http://localhost:5000/report/1', timeout=5)
        assert req.status == 200


class TestJsSyntaxValid:
    """Sanity check: extracted JS parses cleanly."""

    def test_watchlists_js_parses(self):
        import subprocess
        script = _extract_script('watchlists.html')
        Path('/tmp/test_watchlists_lang.js').write_text(script)
        r = subprocess.run(['node', '--check', '/tmp/test_watchlists_lang.js'],
                           capture_output=True, text=True)
        assert r.returncode == 0, f'JS syntax error: {r.stderr}'

    def test_report_detail_js_parses(self):
        import subprocess
        script = _extract_script('report_detail.html')
        Path('/tmp/test_report_detail_lang.js').write_text(script)
        r = subprocess.run(['node', '--check', '/tmp/test_report_detail_lang.js'],
                           capture_output=True, text=True)
        assert r.returncode == 0, f'JS syntax error: {r.stderr}'


class TestPattern5dLangchangeAudit:
    """Verify ALL templates that build dynamic DOM via t() now have a
    langchange listener. base.html is exempt (no dynamic rendering)."""

    def test_every_dynamic_template_has_listener(self):
        # Templates identified in the audit as having dynamic t() calls
        # Each must have a langchange listener
        templates_with_dynamic_t = [
            'alerts.html',
            'banks.html',
            'events.html',
            'files.html',
            'index.html',
            'industry.html',
            'report_detail.html',  # NEW: was missing
            'sources.html',
            'stock_detail.html',
            'system.html',
            'watchlists.html',  # NEW: was missing
        ]
        for tpl in templates_with_dynamic_t:
            text = (TEMPLATES_DIR / tpl).read_text()
            assert "addEventListener('langchange'" in text, (
                f'{tpl} has dynamic t() calls but no langchange listener — '
                f'page will stay frozen at load-time language on lang switch'
            )