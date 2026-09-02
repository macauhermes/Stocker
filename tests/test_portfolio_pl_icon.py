"""v3.4.80 — Portfolio holdings table trend icon (UX polish).

Adds trending_up / trending_down Material icons next to per-holding P&L
cells in the dashboard portfolio holdings table. Icons are color-coded
via portfolio-positive/negative classes (same green/red palette as the
P&L cell). This is pure UX scannability — the dollar amount and
percentage already render; the icon just makes the row's direction
visible at a glance.
"""
import re
import subprocess


def _index_html():
    return open('/home/ubuntu/repos/Stocker/templates/index.html').read()


def _components_css():
    return open('/home/ubuntu/repos/Stocker/static/css/components.css').read()


class TestPortfolioPlIconMarkup:
    """Verify the holdings table row template includes the trend icon span."""

    def test_holdings_row_has_portfolio_pl_icon_span(self):
        html = _index_html()
        # The class .portfolio-pl-icon must appear in the holdings row template
        assert 'portfolio-pl-icon' in html, \
            'Expected .portfolio-pl-icon class in portfolio holdings row template'

    def test_trending_icon_ternary_uses_three_states(self):
        html = _index_html()
        # The icon picker uses pl > 0 / pl < 0 / trending_flat fallback
        # Make sure both up and down states are present in the row template
        assert "trending_up" in html
        assert "trending_down" in html

    def test_icon_inside_pl_cell(self):
        html = _index_html()
        # The icon span should be inside the P&L cell (the one with plClass)
        # Find the row template by searching for the P&L cell context
        pl_cell_match = re.search(
            r'<td class="num \$\{plClass\}">.*?</td>',
            html, re.DOTALL
        )
        assert pl_cell_match is not None, 'P&L cell template not found'
        assert 'portfolio-pl-icon' in pl_cell_match.group(0), \
            'portfolio-pl-icon span must be inside the P&L cell'

    def test_icon_inherits_plclass_color(self):
        html = _index_html()
        # The icon span must carry the plClass for color coding
        pl_cell_match = re.search(
            r'<td class="num \$\{plClass\}">.*?</td>',
            html, re.DOTALL
        )
        assert pl_cell_match is not None
        # Look for the icon span with plClass
        assert re.search(
            r'<span class="material-icons-outlined portfolio-pl-icon \$\{plClass\}',
            pl_cell_match.group(0)
        ), 'icon span must include ${plClass} for color parity'


class TestPortfolioPlIconCss:
    """Verify the .portfolio-pl-icon CSS classes are defined and color-coded."""

    def test_base_class_defined(self):
        css = _components_css()
        m = re.search(r'\.portfolio-pl-icon\s*\{[^}]+\}', css)
        assert m is not None, '.portfolio-pl-icon base class must be defined'
        # Should set font-size + vertical-align + display inline-block
        body = m.group(0)
        assert 'font-size' in body
        assert 'vertical-align' in body

    def test_positive_color_green(self):
        css = _components_css()
        m = re.search(r'\.portfolio-pl-icon\.portfolio-positive\s*\{[^}]+\}', css)
        assert m is not None
        assert '#4caf50' in m.group(0), 'positive icon should be green (#4caf50)'

    def test_negative_color_red(self):
        css = _components_css()
        m = re.search(r'\.portfolio-pl-icon\.portfolio-negative\s*\{[^}]+\}', css)
        assert m is not None
        assert '#ef5350' in m.group(0), 'negative icon should be red (#ef5350)'


class TestPortfolioPlIconE2E:
    """Smoke test the rendered dashboard contains the icon markup + CSS classes."""

    def test_index_page_200(self):
        r = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True
        )
        assert r.stdout.strip() == '200'

    def test_served_html_has_icon_markup(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/', '-m', '5'],
            capture_output=True, text=True
        )
        html = r.stdout
        assert 'portfolio-pl-icon' in html

    def test_served_css_has_icon_class(self):
        r = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/static/css/components.css',
             '-m', '5'],
            capture_output=True, text=True
        )
        css = r.stdout
        assert '.portfolio-pl-icon' in css


class TestPortfolioPlIconJsSyntax:
    """Make sure the inline JS in index.html still parses after the patch."""

    def test_inline_js_parses(self):
        html = _index_html()
        m = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
        assert m is not None
        open('/tmp/check_v3480.js', 'w').write(m.group(1))
        result = subprocess.run(
            ['node', '--check', '/tmp/check_v3480.js'],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f'JS syntax error: {result.stderr}'


class TestPortfolioPlIconGremlin:
    """No invisible Unicode corruption from the patch tool."""

    def test_index_html_clean(self):
        data = _index_html().encode('utf-8')
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
        }
        hits = {label: data.count(g) for g, label in gremlins.items() if data.count(g)}
        assert not hits, f'Gremlin chars in index.html: {hits}'

    def test_components_css_clean(self):
        data = _components_css().encode('utf-8')
        gremlins = {
            b'\xef\xbf\xbd': 'U+FFFD',
            b'\xc2\xad': 'U+00AD',
            b'\xe2\x80\x8b': 'U+200B',
            b'\xef\xbb\xbf': 'U+FEFF',
        }
        hits = {label: data.count(g) for g, label in gremlins.items() if data.count(g)}
        assert not hits, f'Gremlin chars in components.css: {hits}'