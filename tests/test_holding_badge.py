"""v3.4.89 — Stock card holding badge (Pattern 9b orphan field)

Tests that the dashboard stock card surfaces shares_held + cost_basis
from /api/tickers for held positions, via a new ".stock-holding" line
with a wallet icon and bilingual i18n text.
"""
import json
import os
import re
import subprocess
import sys
import unittest

REPO = '/home/ubuntu/repos/Stocker'


def _read(path):
    return open(os.path.join(REPO, path)).read()


def _extract_function_body(source, fn_name):
    """Brace-matching helper for JS function body extraction (v3.4.70 lesson)."""
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
    if depth != 0:
        return None
    return source[m.end():i - 1]


class TestHoldingBadgeApiSurface(unittest.TestCase):
    """Verify /api/tickers returns shares_held + cost_basis with populated data."""

    def test_tickers_endpoint_returns_holding_fields(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/tickers', '-m', '5'],
            capture_output=True, text=True, cwd=REPO
        )
        data = json.loads(r.stdout)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, 'No tickers returned')
        keys = sorted(data[0].keys())
        self.assertIn('shares_held', keys, 'shares_held missing from /api/tickers')
        self.assertIn('cost_basis', keys, 'cost_basis missing from /api/tickers')

    def test_held_positions_have_populated_fields(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/tickers', '-m', '5'],
            capture_output=True, text=True, cwd=REPO
        )
        data = json.loads(r.stdout)
        held = [t for t in data if float(t.get('shares_held') or 0) > 0]
        self.assertGreater(len(held), 0, 'No held positions in DB (need ≥1 for badge to render)')
        for t in held:
            self.assertGreater(float(t['shares_held']), 0,
                               f'{t["symbol"]}: shares_held should be > 0')
            self.assertGreater(float(t['cost_basis'] or 0), 0,
                               f'{t["symbol"]}: cost_basis should be > 0 for held positions')

    def test_watchlist_only_tickers_have_zero_shares(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/api/tickers', '-m', '5'],
            capture_output=True, text=True, cwd=REPO
        )
        data = json.loads(r.stdout)
        not_held = [t for t in data if float(t.get('shares_held') or 0) == 0]
        self.assertGreater(len(not_held), 0, 'All tickers are held (no watchlist-only)')
        # These should NOT render the holding badge
        for t in not_held:
            self.assertEqual(float(t['shares_held']), 0.0,
                             f'{t["symbol"]} is watchlist-only but has shares_held > 0')


class TestHoldingBadgeMarkup(unittest.TestCase):
    """Verify renderStocks() reads shares_held + cost_basis and emits the badge."""

    @classmethod
    def setUpClass(cls):
        text = _read('templates/index.html')
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        cls.script = m.group(1)

    def test_renderStocks_function_exists(self):
        body = _extract_function_body(self.script, 'renderStocks')
        self.assertIsNotNone(body, 'renderStocks() not found')

    def test_renderStocks_reads_shares_held(self):
        body = _extract_function_body(self.script, 'renderStocks')
        self.assertIn('shares_held', body, 'renderStocks does not read shares_held')

    def test_renderStocks_reads_cost_basis(self):
        body = _extract_function_body(self.script, 'renderStocks')
        self.assertIn('cost_basis', body, 'renderStocks does not read cost_basis')

    def test_renderStocks_renders_holding_class(self):
        body = _extract_function_body(self.script, 'renderStocks')
        self.assertIn('stock-holding', body,
                      'renderStocks does not emit .stock-holding class')

    def test_renderStocks_uses_holding_i18n_key(self):
        body = _extract_function_body(self.script, 'renderStocks')
        self.assertIn("t('index.holding_shares_cost'", body,
                      'renderStocks does not call t(index.holding_shares_cost)')

    def test_renderStocks_conditional_on_shares_held_positive(self):
        body = _extract_function_body(self.script, 'renderStocks')
        # Must guard with shares_held > 0 check
        self.assertRegex(body, r'holdingShares\s*>\s*0|shares_held\s*>\s*0',
                         'renderStocks does not conditionally render badge on shares_held > 0')

    def test_renderStocks_injects_holding_html_in_template(self):
        body = _extract_function_body(self.script, 'renderStocks')
        # The card template must include ${holdingHtml}
        self.assertIn('${holdingHtml}', body,
                      'card innerHTML does not include ${holdingHtml}')

    def test_renderStocks_uses_wallet_icon(self):
        body = _extract_function_body(self.script, 'renderStocks')
        self.assertIn('account_balance_wallet', body,
                      'renderStocks does not use account_balance_wallet icon')

    def test_renderStocks_data_holding_attribute(self):
        body = _extract_function_body(self.script, 'renderStocks')
        self.assertIn('data-holding=', body,
                      'renderStocks badge missing data-holding attribute for QA')


class TestHoldingBadgeCSS(unittest.TestCase):
    """Verify the .stock-holding CSS class is defined in components.css."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read('static/css/components.css')

    def test_class_defined(self):
        self.assertRegex(self.css, r'\.stock-holding\s*\{',
                         '.stock-holding class not defined in components.css')

    def test_uses_orange_color(self):
        m = re.search(r'\.stock-holding\s*\{([^}]+)\}', self.css)
        self.assertIsNotNone(m)
        body = m.group(1)
        self.assertIn('var(--orange)', body,
                      '.stock-holding should use var(--orange) for accent')

    def test_has_margin_top(self):
        m = re.search(r'\.stock-holding\s*\{([^}]+)\}', self.css)
        self.assertIsNotNone(m)
        body = m.group(1)
        self.assertIn('margin-top', body, '.stock-holding should have margin-top')

    def test_uses_font_weight_500(self):
        m = re.search(r'\.stock-holding\s*\{([^}]+)\}', self.css)
        self.assertIsNotNone(m)
        body = m.group(1)
        self.assertIn('font-weight: 500', body,
                      '.stock-holding should have font-weight: 500 for visual weight')

    def test_inner_icon_class(self):
        self.assertRegex(self.css, r'\.stock-holding\s+\.material-icons-outlined',
                         '.stock-holding .material-icons-outlined nested rule not found')


class TestHoldingBadgeI18n(unittest.TestCase):
    """Verify bilingual coverage of the new i18n keys (v3.4.61 lesson)."""

    @classmethod
    def setUpClass(cls):
        cls.i18n = _read('static/js/i18n.js')

    def test_zh_holding_shares_cost_exists(self):
        m = re.search(r"'index\.holding_shares_cost':\s*'([^']+)'", self.i18n)
        self.assertIsNotNone(m, 'index.holding_shares_cost not found in zh section')
        self.assertIn('{shares}', m.group(1), 'zh key missing {shares} placeholder')
        self.assertIn('{cost}', m.group(1), 'zh key missing {cost} placeholder')

    def test_en_holding_shares_cost_exists(self):
        matches = re.findall(r"'index\.holding_shares_cost':\s*'([^']+)'", self.i18n)
        self.assertEqual(len(matches), 2, 'index.holding_shares_cost must appear in BOTH sections')
        en_match = matches[1]
        self.assertIn('{shares}', en_match)
        self.assertIn('{cost}', en_match)

    def test_zh_holding_title_exists(self):
        m = re.search(r"'index\.holding_title':\s*'([^']+)'", self.i18n)
        self.assertIsNotNone(m, 'index.holding_title not found')

    def test_en_holding_title_exists(self):
        matches = re.findall(r"'index\.holding_title':\s*'([^']+)'", self.i18n)
        self.assertEqual(len(matches), 2, 'index.holding_title must appear in BOTH sections')

    def test_both_sections_contain_wallet_emoji_or_icon_label(self):
        """The visible text should reference 'shares' or '股' so it's clear what it shows."""
        for match in re.finditer(r"'index\.holding_shares_cost':\s*'([^']+)'", self.i18n):
            text = match.group(1)
            self.assertTrue('shares' in text.lower() or '股' in text,
                            f'i18n text missing shares/股: {text!r}')


class TestHoldingBadgeE2E(unittest.TestCase):
    """Smoke test that the page renders + served HTML contains the new markup."""

    def test_index_page_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True, cwd=REPO
        )
        self.assertEqual(r.stdout.strip(), '200')

    def test_served_html_contains_holding_references(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True, cwd=REPO
        )
        html = r.stdout
        # The CSS class is in components.css, not inline — check it's referenced in the script
        self.assertIn('stock-holding', html,
                      'served HTML should reference stock-holding class')
        # The i18n key should appear in the served HTML (inline in the script)
        self.assertIn('holding_shares_cost', html,
                      'served HTML should reference holding_shares_cost i18n key')


class TestJsSyntax(unittest.TestCase):
    """Validate JS syntax on extracted script + i18n.js."""

    def test_index_html_script_parses(self):
        text = _read('templates/index.html')
        m = re.search(r'<script>(.*?)</script>', text, re.DOTALL)
        self.assertIsNotNone(m)
        tmp_path = '/tmp/check_index.js'
        with open(tmp_path, 'w') as f:
            f.write(m.group(1))
        r = subprocess.run(['node', '--check', tmp_path],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f'index.html script syntax error: {r.stderr}')

    def test_i18n_js_parses(self):
        r = subprocess.run(['node', '--check', 'static/js/i18n.js'],
                           capture_output=True, text=True, cwd=REPO)
        self.assertEqual(r.returncode, 0, f'i18n.js syntax error: {r.stderr}')


class TestGremlinCheck(unittest.TestCase):
    """Verify no mojibake (U+FFFD/U+00AD/U+200B/U+FEFF/U+200E/U+200F) in modified files."""

    FILES = [
        'templates/index.html',
        'static/css/components.css',
        'static/js/i18n.js',
    ]

    def test_no_gremlins(self):
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
            b'\xe2\x80\x8e': 'U+200E',
            b'\xe2\x80\x8f': 'U+200F',
        }
        for f in self.FILES:
            data = open(os.path.join(REPO, f), 'rb').read()
            hits = {label: data.count(b) for b, label in gremlins.items() if data.count(b)}
            self.assertFalse(hits, f'{f} contains gremlins: {hits}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
