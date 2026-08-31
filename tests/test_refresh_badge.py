"""Test /api/refresh-interval surfaces et_time, and dashboard wires the refresh badge.

v3.4.62 — Pattern 1 + Pattern 9b combo:
- Pattern 1: refresh-badge markup missing despite JS code that updates it
- Pattern 9b: et_time field returned by API but never surfaced in UI
"""
import os
import sys
import re

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope='module')
def client():
    """Build a Flask test client. app.py initializes DB + Prometheus on import."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestRefreshIntervalAPI:
    def test_returns_et_time(self, client):
        """Pattern 9b — et_time must be populated in /api/refresh-interval response."""
        resp = client.get('/api/refresh-interval')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'et_time' in data, f'et_time missing: {list(data.keys())}'
        # Format is "HH:MM ET"
        assert re.match(r'^\d{2}:\d{2} ET$', data['et_time']), f'Bad format: {data["et_time"]}'

    def test_returns_interval_and_reason(self, client):
        resp = client.get('/api/refresh-interval')
        data = resp.get_json()
        assert 'interval' in data and data['interval'] > 0
        assert 'reason' in data and data['reason']


class TestRefreshBadgeUI:
    def test_index_template_renders_refresh_badge(self, client):
        """Pattern 1 — refresh badge markup must exist so the JS update actually renders."""
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'id="refresh-badge"' in html, 'refresh-badge span missing from index.html'
        assert 'class="refresh-badge"' in html
        # Must be inside the stocks-toolbar (not hidden in some other section)
        toolbar_pos = html.find('stocks-toolbar')
        badge_pos = html.find('id="refresh-badge"')
        assert toolbar_pos != -1 and badge_pos > toolbar_pos, \
            'refresh-badge not inside stocks-toolbar'

    def test_index_template_has_rerender_function(self, client):
        """v3.4.62 — rerenderRefreshBadge must be wired into langchange listener."""
        resp = client.get('/')
        html = resp.get_data(as_text=True)
        # Function definition
        assert re.search(r'function rerenderRefreshBadge\s*\(\s*\)\s*\{', html), \
            'rerenderRefreshBadge function missing'
        # Langchange handler calls it
        langchange_block = re.search(
            r"window\.addEventListener\(['\"]langchange['\"].*?\}\s*\);",
            html, re.DOTALL
        )
        assert langchange_block, 'langchange listener missing'
        assert 'rerenderRefreshBadge()' in langchange_block.group(0), \
            'rerenderRefreshBadge not called in langchange'

    def test_refresh_badge_has_i18n_title(self, client):
        """v3.4.62 — refresh-badge uses data-i18n-title so langchange updates tooltip."""
        resp = client.get('/')
        html = resp.get_data(as_text=True)
        # Match the refresh-badge span with data-i18n-title
        assert re.search(
            r'<span\s+id="refresh-badge"[^>]*data-i18n-title="index\.refresh_badge_title"',
            html
        ), 'refresh-badge missing data-i18n-title attribute'


class TestI18nKeys:
    def test_refresh_badge_title_in_both_languages(self):
        """v3.4.62 — index.refresh_badge_title must exist in both zh + en sections."""
        text = open('static/js/i18n.js').read()
        # I18N = { zh: {...}, en: {...} } — find each section by braces
        zh_match = re.search(r'^\s*zh:\s*\{(.*?)\n\s*\}', text, re.MULTILINE | re.DOTALL)
        en_match = re.search(r'^\s*en:\s*\{(.*?)\n\s*\}', text, re.MULTILINE | re.DOTALL)
        assert zh_match, 'zh section not found'
        assert en_match, 'en section not found'
        zh_val = re.search(r"'index\.refresh_badge_title'\s*:\s*'([^']+)'", zh_match.group(1))
        en_val = re.search(r"'index\.refresh_badge_title'\s*:\s*'([^']+)'", en_match.group(1))
        assert zh_val and zh_val.group(1).strip(), 'zh value missing or empty'
        assert en_val and en_val.group(1).strip(), 'en value missing or empty'