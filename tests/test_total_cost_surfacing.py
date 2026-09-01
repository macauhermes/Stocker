"""
Unit tests for v3.4.68 — /api/portfolio/summary.total_cost surfacing on
dashboard portfolio card.

Bug class: Pattern 9b (orphan field). /api/portfolio/summary returns a
`latest.total_cost` field (10300.0 for 3 active holdings) — but the
portfolio-summary-card 4-tile layout only bound 4 fields
(total_value / total_pnl / change_30d / holdings_count). User saw "我
投資咗幾多" missing — P&L percentage made sense in isolation but the
"money invested" baseline was invisible.

This test asserts:
  - /api/portfolio/summary returns non-empty latest.total_cost (live endpoint check)
  - templates/index.html portfolio summary row now contains portfolio-cost tile
  - index.html JS handler binds v.total_cost to #portfolio-cost via formatCurrency
  - portfolio.total_cost key exists in BOTH zh + en sections of i18n.js
    (Pattern 5d sub-class v3.4.61 lesson — bilingual coverage guard)
  - portfolio-summary-row CSS grid is now 5-col (was 4-col pre-v3.4.68)
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


INDEX_HTML = os.path.join(
    os.path.dirname(__file__), '..', 'templates', 'index.html'
)
COMPONENTS_CSS = os.path.join(
    os.path.dirname(__file__), '..', 'static', 'css', 'components.css'
)
I18N_JS = os.path.join(
    os.path.dirname(__file__), '..', 'static', 'js', 'i18n.js'
)


@pytest.fixture(scope='module')
def client():
    """Flask test client (live DB, no inserts — read-only tests)."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestTotalCostAPI:
    """/api/portfolio/summary must return latest.total_cost populated."""

    def test_summary_includes_total_cost(self, client):
        resp = client.get('/api/portfolio/summary')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('has_history') is True
        latest = data.get('latest', {})
        assert latest, "no latest snapshot returned"
        assert 'total_cost' in latest, (
            'summary endpoint missing total_cost field — '
            'pattern 9b bug: endpoint dropped the field between DB and JSON'
        )
        assert latest['total_cost'] is not None
        assert latest['total_cost'] > 0, (
            f'total_cost should be > 0 with active holdings, got {latest["total_cost"]}'
        )


class TestTotalCostMarkup:
    """index.html portfolio card must contain the new total_cost tile + JS binding."""

    def test_index_template_renders_portfolio_cost_tile(self):
        text = open(INDEX_HTML, encoding='utf-8').read()
        assert 'id="portfolio-cost"' in text, (
            "Missing portfolio-cost tile in portfolio-summary-row"
        )
        # data-i18n attribute for langchange re-translation
        assert 'data-i18n="portfolio.total_cost"' in text, (
            "Missing data-i18n binding for portfolio.total_cost"
        )

    def test_index_template_binds_total_cost_in_js(self):
        text = open(INDEX_HTML, encoding='utf-8').read()
        # JS handler reads v.total_cost and writes to #portfolio-cost via formatCurrency
        script_match = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        assert script_match, "no <script> block in index.html"
        script = script_match.group(1)
        assert 'v.total_cost' in script, (
            "JS handler does not read v.total_cost from /api/portfolio/summary"
        )
        assert "getElementById('portfolio-cost')" in script, (
            "JS handler does not bind to #portfolio-cost DOM element"
        )
        assert 'formatCurrency' in script.split('costEl.textContent')[1].split(';')[0] if 'costEl.textContent' in script else False, \
            "JS handler does not call formatCurrency for cost display"

    def test_summary_row_now_has_5_tiles(self):
        """Pre-v3.4.68 had 4 portfolio-stat divs, post-v3.4.68 has 5."""
        text = open(INDEX_HTML, encoding='utf-8').read()
        # Find the portfolio-summary-row scope. It starts with the row opening
        # <div class="portfolio-summary-row"> and ends with the next sibling
        # <div ... portfolio-sparkline-wrapper ...> (the next portfolio block).
        row_match = re.search(
            r'<div class="portfolio-summary-row">(.*?)<div id="portfolio-sparkline-wrapper"',
            text, re.DOTALL
        )
        assert row_match, "could not locate portfolio-summary-row scope"
        row_html = row_match.group(1)
        tile_count = row_html.count('class="portfolio-stat"')
        assert tile_count == 5, (
            f"Expected 5 portfolio-stat tiles (4 pre-v3.4.68 + 1 for total_cost), "
            f"got {tile_count}"
        )


class TestTotalCostCSS:
    """components.css portfolio-summary-row must adapt to 5 tiles."""

    def test_grid_is_5_col(self):
        text = open(COMPONENTS_CSS, encoding='utf-8').read()
        # After v3.4.68: grid-template-columns: repeat(5, 1fr)
        assert re.search(
            r'\.portfolio-summary-row\s*\{[^}]*grid-template-columns:\s*repeat\(5,\s*1fr\)',
            text, re.DOTALL
        ), "portfolio-summary-row not updated to 5-column grid"


class TestTotalCostI18n:
    """portfolio.total_cost must exist in BOTH zh + en sections (Pattern 5d guard)."""

    def test_total_cost_in_zh_section(self):
        text = open(I18N_JS, encoding='utf-8').read()
        # Look for zh key with CJK value
        m = re.search(r"'portfolio\.total_cost':\s*'([^']+)'", text)
        assert m, "portfolio.total_cost key not found in i18n.js"
        value = m.group(1)
        assert any(ord(c) > 127 for c in value), (
            f"portfolio.total_cost zh value '{value}' contains no CJK chars — "
            f"are you sure zh section was updated?"
        )

    def test_total_cost_in_en_section(self):
        """Bilingual coverage guard — v3.4.61 lesson."""
        text = open(I18N_JS, encoding='utf-8').read()
        # Both zh + en keys must exist
        matches = re.findall(r"'portfolio\.total_cost':\s*'([^']+)'", text)
        assert len(matches) >= 2, (
            f"portfolio.total_cost only found {len(matches)} time(s) — "
            f"both zh + en sections must define it (v3.4.61 Pattern 5d sub-class)"
        )
        # Find English one (ASCII-only)
        en = [m for m in matches if all(ord(c) < 128 for c in m)]
        assert en, "No English version of portfolio.total_cost found"
        assert en[0] == 'Total Cost', f"Unexpected en value: {en[0]!r}"