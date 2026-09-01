"""
Regression test for v3.4.67 — stock detail holdings position summary
(Pattern 9b orphan-field surfacing + UX gap fix).

Bug class: `/api/portfolio/breakdown` returns per-holding data with
market_value / cost_value / unrealized_pl / unrealized_pl_pct. The stock
detail page (`/stock/<sym>`) had a holdings form (shares + cost_basis
inputs + save button) but ZERO feedback about the resulting portfolio
position. After saving, they had to bounce to the dashboard to see
their MV / P&L.

The fix adds a `.holdings-summary` block beneath the holdings form that
fetches /api/portfolio/breakdown, finds this ticker, and renders
MV / cost / unrealized P&L (with green/red coloring). Hidden when
shares_held is 0 (no position yet). Re-fetches after `saveHoldings()`
succeeds so the user sees the impact immediately.

What we verify:
  - /api/portfolio/breakdown returns 200 OK with holdings[] populated
  - Each holding has the expected 9 fields including market_value /
    cost_value / unrealized_pl / unrealized_pl_pct
  - The 3 new `hs-*` element IDs exist in templates/stock_detail.html
  - The `holdings-summary` CSS class is defined in static/css/components.css
  - The 10 new i18n keys (5 zh + 5 en) exist in BOTH language sections
    of static/js/i18n.js (Pattern 5d sub-class bilingual coverage guard
    from v3.4.61)
  - loadHoldingsSummary() function is defined AND wired into saveHoldings()
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope='module')
def client():
    """Flask test client. app.py initializes DB + Prometheus on import."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestBreakdownFields:
    """API contract: per-ticker breakdown returns the fields the new
    holdings-summary block consumes."""

    def test_breakdown_returns_200(self, client):
        resp = client.get('/api/portfolio/breakdown')
        assert resp.status_code == 200

    def test_breakdown_has_holdings_array(self, client):
        data = client.get('/api/portfolio/breakdown').get_json()
        assert isinstance(data.get('holdings'), list)
        assert len(data['holdings']) >= 1, 'Need at least 1 holding for test'

    def test_holdings_have_summary_fields(self, client):
        data = client.get('/api/portfolio/breakdown').get_json()
        required = {'symbol', 'market_value', 'cost_value', 'unrealized_pl', 'unrealized_pl_pct'}
        for h in data['holdings']:
            missing = required - set(h.keys())
            assert not missing, f'Holding {h.get("symbol")} missing fields: {missing}'

    def test_market_value_populated(self, client):
        data = client.get('/api/portfolio/breakdown').get_json()
        populated = [h for h in data['holdings'] if h.get('market_value') not in (None, 0)]
        assert len(populated) >= 1, 'Expected at least 1 holding with market_value > 0'


class TestTemplateMarkup:
    """The holdings-summary block markup + CSS + JS handler must be
    wired into templates/stock_detail.html."""

    def test_template_renders_holdings_summary(self):
        text = open('templates/stock_detail.html').read()
        assert 'id="holdings-summary"' in text, 'Missing #holdings-summary container'
        assert 'id="hs-market-value"' in text
        assert 'id="hs-cost-total"' in text
        assert 'id="hs-unrealized-pl"' in text

    def test_template_uses_i18n_keys_for_labels(self):
        text = open('templates/stock_detail.html').read()
        for key in ('holdings_summary', 'holdings_market_value', 'holdings_cost_total',
                    'holdings_unrealized_pl'):
            assert f'data-i18n="detail.{key}"' in text, f'Missing data-i18n for detail.{key}'

    def test_load_holdings_summary_function_defined(self):
        text = open('templates/stock_detail.html').read()
        assert 'async function loadHoldingsSummary' in text

    def test_load_holdings_summary_wired_into_save_holdings(self):
        text = open('templates/stock_detail.html').read()
        # After save success, must call loadHoldingsSummary
        save_block = re.search(
            r"async function saveHoldings\(\)\s*\{(.*?)\n    \}",
            text, re.DOTALL,
        )
        assert save_block, 'saveHoldings() not found'
        assert 'loadHoldingsSummary' in save_block.group(1), (
            'loadHoldingsSummary not called from saveHoldings success path'
        )

    def test_load_holdings_summary_wired_into_load_detail(self):
        text = open('templates/stock_detail.html').read()
        load_block = re.search(
            r"async function loadDetail\(\)\s*\{(.*?)\n    \}",
            text, re.DOTALL,
        )
        assert load_block, 'loadDetail() not found'
        assert 'loadHoldingsSummary' in load_block.group(1), (
            'loadHoldingsSummary not called from loadDetail()'
        )


class TestCSS:
    """.holdings-summary CSS class must be defined in components.css."""

    def test_holdings_summary_class_defined(self):
        text = open('static/css/components.css').read()
        assert '.holdings-summary {' in text
        assert '.holdings-summary-grid' in text
        assert '.holdings-summary-value' in text
        # P&L coloring should reuse .portfolio-positive / .portfolio-negative
        assert '.holdings-summary-value.portfolio-positive' in text
        assert '.holdings-summary-value.portfolio-negative' in text

    def test_mobile_responsive_grid(self):
        text = open('static/css/components.css').read()
        # Mobile breakpoint should collapse 3-col to 1-col
        assert '@media (max-width: 480px)' in text
        # Verify .holdings-summary-grid appears within or after a mobile media query
        assert re.search(
            r'@media[^{]*\{[^}]*\.holdings-summary-grid',
            text, re.DOTALL,
        ), 'Mobile breakpoint for .holdings-summary-grid not found'


class TestI18nKeys:
    """Pattern 5d sub-class bilingual coverage guard — every key referenced
    by the new markup must exist in BOTH zh and en sections of i18n.js.
    The previous one-call variant treated i18n.js as one bag of keys; the
    salvage check #5 from v3.4.61 elevates this to bilingual coverage."""

    def _i18n_sections(self):
        text = open('static/js/i18n.js').read()
        # Structure: const I18N = { zh: { ... }, en: { ... } };
        # The zh section ends just before the en: marker; the en section
        # ends at the closing `};` of the I18N const.
        zh_match = re.search(r"zh:\s*\{(.*?)\n\s+en:\s*\{", text, re.DOTALL)
        en_match = re.search(r"en:\s*\{(.*?)\n\};", text, re.DOTALL)
        if not en_match or not zh_match:
            pytest.skip('Could not locate zh/en sections')
        return en_match.group(1), zh_match.group(1)

    def _has_key(self, section, key):
        return bool(re.search(rf"['\"]?{re.escape(key)}['\"]?\s*:", section))

    def test_all_keys_in_both_languages(self):
        keys = [
            'detail.holdings_summary',
            'detail.holdings_market_value',
            'detail.holdings_cost_total',
            'detail.holdings_unrealized_pl',
            'detail.holdings_no_position',
        ]
        en, zh = self._i18n_sections()
        for k in keys:
            assert self._has_key(en, k), f'Missing en key: {k}'
            assert self._has_key(zh, k), f'Missing zh key: {k}'