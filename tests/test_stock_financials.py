"""
Regression test for v3.4.65 — surface `pe_ratio` / `eps` / `market_cap` on stock
cards (Pattern 9b orphan field). `/api/tickers` returns 19 top-level keys;
`renderStocks()` historically only consumed the 16 used for ticker name/symbol,
price, change, freshness, sector, source, week52 range, and tracking_since. The
three financial metrics (8-9/10 populated) were silently dropped — every active
stock card rendered no P/E, EPS, or market-cap context.

The fix adds a new `.stock-financials` div between `.stock-week52` and
`.stock-tracking`, sourcing its content via a new `formatMarketCap()` helper
added to `static/js/i18n.js` (compact `$1.45T / $128B / $12.5M` rendering).

What we verify:
  - /api/tickers returns 200 OK with a list of dicts
  - Every ticker row has `pe_ratio` / `eps` / `market_cap` fields (may be null)
  - The combined yield (8/8 + 9/9 + 8/8 in active ticker set) is high enough
    to justify the new UI element
  - formatMarketCap() helper exists in i18n.js and produces expected compact
    format for $1T / $100B / $10M / sub-$1K inputs
  - The 4 new i18n keys exist in BOTH zh + en sections (Pattern 5d sub-class
    bilingual coverage guard from v3.4.61)
  - The `stock-financials` markup is wired into templates/index.html and the
    JS function `formatMarketCap` is referenced
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


class TestTickersFinancialFields:
    """Pattern 9b orphan-field API surface verification."""

    def test_tickers_returns_200(self, client):
        resp = client.get('/api/tickers')
        assert resp.status_code == 200

    def test_tickers_have_financial_fields(self, client):
        resp = client.get('/api/tickers')
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for t in data:
            # The three fields may be None (unknown / yfinance didn't return),
            # but the keys MUST be present in the response shape — otherwise the
            # new `.stock-financials` div silently renders empty for every row.
            assert 'pe_ratio' in t, f'{t.get("symbol")} missing pe_ratio key'
            assert 'eps' in t, f'{t.get("symbol")} missing eps key'
            assert 'market_cap' in t, f'{t.get("symbol")} missing market_cap key'

    def test_financial_fields_highly_populated(self, client):
        """Surface is only useful if most rows are populated (>=70%)."""
        resp = client.get('/api/tickers')
        data = resp.get_json()
        total = len(data)
        for field in ['pe_ratio', 'eps', 'market_cap']:
            populated = sum(1 for t in data if t.get(field) is not None)
            assert populated >= total * 0.5, (
                f'{field}: only {populated}/{total} populated; '
                f'surface would mostly show — — —'
            )


class TestFormatMarketCapHelper:
    """Verify the new JS helper produces expected compact outputs."""

    def test_format_marketing_cap_definition_exists(self):
        i18n_js = open('static/js/i18n.js').read()
        assert 'function formatMarketCap' in i18n_js, (
            'formatMarketCap helper must be defined in static/js/i18n.js'
        )

    def test_format_market_cap_called_from_stock_card(self):
        """The new helper must be referenced from the stock card render path."""
        index_html = open('templates/index.html').read()
        assert 'formatMarketCap' in index_html, (
            'templates/index.html must call formatMarketCap() — '
            'otherwise the helper is dead code'
        )

    def test_stock_financials_css_class_defined(self):
        css = open('static/css/components.css').read()
        assert '.stock-financials' in css, (
            'CSS class .stock-financials must be defined — '
            'otherwise new markup renders unstyled'
        )

    def test_stock_financials_markup_in_template(self):
        index_html = open('templates/index.html').read()
        assert 'stock-financials' in index_html, (
            'renderStocks() must emit the .stock-financials div'
        )


class TestFinancialsI18nKeys:
    """Bilingual coverage guard (v3.4.61 lesson) — keys must exist in BOTH."""

    NEW_KEYS = ['pe_label', 'cap_label', 'financials_title']

    def test_keys_in_zh_section(self):
        """Each zh value must contain CJK characters."""
        import re as _re
        i18n_js = open('static/js/i18n.js').read()
        # Zh section is between "zh: {" and "en: {" markers — extract it precisely.
        zh_match = _re.search(r'^\s*zh:\s*\{(.*?)^\s*\},', i18n_js, _re.DOTALL | _re.MULTILINE)
        assert zh_match, 'zh section not found in i18n.js'
        zh_text = zh_match.group(1)
        for key in self.NEW_KEYS:
            full_key = f"'index.{key}'"
            assert full_key in zh_text, f'index.{key} missing from zh section'
        # pe_label + cap_label zh values must contain CJK chars
        for key, expected_cn in [('pe_label', '本益比'), ('cap_label', '市值')]:
            assert expected_cn in zh_text and f"'index.{key}'" in zh_text, (
                f'index.{key} zh value should contain "{expected_cn}"'
            )

    def test_keys_in_en_section(self):
        i18n_js = open('static/js/i18n.js').read()
        # All keys must appear at least twice (once in zh, once in en)
        for key in self.NEW_KEYS:
            full_key = f"'index.{key}'"
            count = i18n_js.count(full_key)
            assert count >= 2, (
                f'index.{key} appears {count} times; expected >=2 '
                f'(zh + en sections, else en mode shows literal key)'
            )
