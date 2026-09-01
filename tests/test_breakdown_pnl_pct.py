"""Pattern 9b orphan-field surfacing test (v3.4.71).

Surfaces `pnl_pct` from `/api/portfolio/breakdown` on the dashboard's
portfolio holdings meta line — previously silently dropped between
API and DOM, leaving users with `$+5478.06 total_pnl` but no percentage
context to know whether that's a +5% or +53% gain.

Reference: v3.4.71 — Pattern 9b orphan-field surfacing on dashboard
holdings meta line. Mirrors v3.4.58 (timestamp), v3.4.66 (dismissed_at),
v3.4.67 (position summary), v3.4.68 (total_cost) — all data the API
already returned but the UI consumed incompletely.
"""
import os
import re
import subprocess
import sys

REPO = os.path.expanduser('~/repos/Stocker')


def _extract_function_body(source, fn_name):
    """Brace-matching helper — see stocker-project skill v3.4.70."""
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


class TestBreakdownOrphanPnlPct:
    """Verify /api/portfolio/breakdown returns pnl_pct and it's surfaced on the dashboard."""

    def test_breakdown_returns_pnl_pct(self):
        """Endpoint must include the pnl_pct top-level key."""
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/portfolio/breakdown', '-m', '5'],
            capture_output=True, text=True, cwd=REPO,
        )
        assert r.returncode == 0 and r.stdout, f'breakdown endpoint failed: {r.stderr}'
        import json
        d = json.loads(r.stdout)
        assert 'pnl_pct' in d, f'pnl_pct missing from breakdown: keys={sorted(d.keys())}'
        assert d['pnl_pct'] is not None, 'pnl_pct should be populated when holdings > 0'
        assert isinstance(d['pnl_pct'], (int, float)), f'pnl_pct should be numeric, got {type(d["pnl_pct"])}'

    def test_pnl_pct_equals_total_pnl_total_cost(self):
        """pnl_pct must equal (total_pnl / total_cost) * 100 to within 0.01%."""
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/portfolio/breakdown', '-m', '5'],
            capture_output=True, text=True, cwd=REPO,
        )
        import json
        d = json.loads(r.stdout)
        if d.get('total_cost') and d['total_cost'] > 0:
            expected = (d['total_pnl'] / d['total_cost']) * 100
            assert abs(d['pnl_pct'] - expected) < 0.01, (
                f'pnl_pct {d["pnl_pct"]} != computed {expected:.2f}'
            )


class TestMetaLineMarkup:
    """Verify the meta line element exists and the JS reads pnl_pct."""

    def test_meta_element_exists(self):
        text = open(f'{REPO}/templates/index.html').read()
        assert 'id="portfolio-holdings-meta"' in text, 'meta element missing'

    def test_function_reads_pnl_pct(self):
        text = open(f'{REPO}/templates/index.html').read()
        body = _extract_function_body(text, 'loadPortfolioHoldings')
        assert body is not None, 'loadPortfolioHoldings function not found'
        # Must reference data.pnl_pct at least twice (validation + display)
        pnl_pct_count = len(re.findall(r'data\.pnl_pct\b', body))
        assert pnl_pct_count >= 2, (
            f'Expected ≥2 references to data.pnl_pct, got {pnl_pct_count}. '
            f'Function body:\n{body[:500]}'
        )

    def test_function_uses_portfolio_positive_negative_classes(self):
        """P&L coloring must reuse existing portfolio-positive/portfolio-negative classes."""
        text = open(f'{REPO}/templates/index.html').read()
        body = _extract_function_body(text, 'loadPortfolioHoldings')
        assert body is not None
        assert "'portfolio-positive'" in body, 'must apply portfolio-positive class for gains'
        assert "'portfolio-negative'" in body, 'must apply portfolio-negative class for losses'

    def test_function_uses_innerHTML_clear_for_langchange(self):
        """v3.4.71 rewrites meta via DOM children (not textContent) so colored spans
        are preserved across langchange re-renders."""
        text = open(f'{REPO}/templates/index.html').read()
        body = _extract_function_body(text, 'loadPortfolioHoldings')
        assert body is not None
        # Should clear + rebuild via appendChild (not just set textContent once)
        assert 'appendChild' in body, 'must use appendChild for multi-node meta line'
        # InnerHTML='' or similar pattern to clear previous render
        assert "innerHTML = ''" in body or "textContent = ''" in body, (
            'must clear previous metaEl children before re-rendering'
        )


class TestPnlPctI18nKeys:
    """Bilingual coverage guard — Pattern 5d v3.4.61 lesson: never ship en-only keys."""

    def test_holdings_pnl_total_in_zh_section(self):
        """zh section (first dict in i18n.js) must have holdings_pnl_total."""
        text = open(f'{REPO}/static/js/i18n.js').read()
        # Find the zh dict block (first `const X = {` ... closing `};`)
        m = re.search(r"'portfolio\.holdings_pnl_total':\s*'([^']+)'", text)
        assert m is not None, f'holdings_pnl_total key missing from i18n.js entirely'
        zh_value = m.group(1)
        assert '{pnl}' in zh_value and '{pct}' in zh_value, (
            f'zh value must use {{pnl}} + {{pct}} placeholders, got: {zh_value!r}'
        )

    def test_holdings_pnl_total_in_en_section(self):
        """en section (second dict in i18n.js) must also have holdings_pnl_total.

        Pattern 5d v3.4.61 lesson: en mode surfaces literal key string
        'portfolio.holdings_pnl_total' if the en dict is missing the key.
        """
        text = open(f'{REPO}/static/js/i18n.js').read()
        matches = list(re.finditer(r"'portfolio\.holdings_pnl_total':\s*'([^']+)'", text))
        assert len(matches) >= 2, (
            f'holdings_pnl_total must appear in BOTH zh + en sections, got {len(matches)} occurrences'
        )
        en_value = matches[1].group(1)
        assert 'P&L' in en_value or 'PnL' in en_value or 'pnl' in en_value.lower(), (
            f'en value should reference P&L concept, got: {en_value!r}'
        )
        assert '{pnl}' in en_value and '{pct}' in en_value, (
            f'en value must use {{pnl}} + {{pct}} placeholders, got: {en_value!r}'
        )


class TestE2ESmoke:
    """Smoke test: dashboard loads and rendered HTML has new elements."""

    def test_dashboard_returns_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True,
        )
        assert r.stdout.strip() == '200', f'/ returned {r.stdout}'

    def test_dashboard_html_contains_wiring(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True,
        )
        html = r.stdout
        assert 'id="portfolio-holdings-meta"' in html, 'meta element not in served HTML'
        assert 'loadPortfolioHoldings' in html, 'JS handler missing'
        assert 'pnl_pct' in html, 'pnl_pct reference missing from served HTML'
