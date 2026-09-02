"""Pattern 5 sub-class: data-i18n on parent of inline HTML destroys children.

Bug: system.html had `<p data-i18n="system.desc">即時顯示... <code>/api/metrics/summary</code>...</p>`.
applyI18n does `el.textContent = text` which wipes ALL child elements including <code>.

Fix: move data-i18n to inner <span> wrappers around each translatable fragment.
Keep <code> elements as static siblings (path strings are language-neutral).
"""
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


SYSTEM_HTML_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'templates', 'system.html'
)
I18N_JS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'static', 'js', 'i18n.js'
)


def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


class TestSystemDescMarkup:
    """Verify the paragraph uses span fragments instead of data-i18n on parent <p>."""

    def setup_method(self):
        self.html = _read(SYSTEM_HTML_PATH)

    def test_no_data_i18n_on_outer_p(self):
        """Outer <p> must NOT have data-i18n (that would destroy <code> children)."""
        # Find the description paragraph
        m = re.search(
            r'<p[^>]*style="color:var\(--text-muted\)[^"]*"[^>]*>',
            self.html
        )
        assert m, 'Description paragraph not found in templates/system.html'
        opening_tag = m.group(0)
        assert 'data-i18n' not in opening_tag, (
            f'Outer <p> has data-i18n — applyI18n will destroy inline children. '
            f'Tag: {opening_tag}'
        )

    def test_desc_uses_span_fragments(self):
        """Inner translatable text wrapped in <span data-i18n="...">."""
        for key in ('system.desc_prefix', 'system.desc_plus', 'system.desc_suffix'):
            count = self.html.count(f'data-i18n="{key}"')
            assert count >= 1, (
                f'Expected data-i18n="{key}" wrapper span in system.html, got {count}'
            )

    def test_code_elements_are_static_siblings(self):
        """<code> elements are direct children of <p>, not inside data-i18n spans."""
        # Extract the description paragraph body
        m = re.search(
            r'<p[^>]*style="color:var\(--text-muted\)[^"]*"[^>]*>(.*?)</p>',
            self.html, re.DOTALL
        )
        assert m
        body = m.group(1)
        # Both <code> elements must be present
        code_paths = re.findall(r'<code>([^<]+)</code>', body)
        assert code_paths == ['/api/metrics/summary', '/health'], (
            f'<code> contents wrong: {code_paths}'
        )
        # For each <code>, verify no <span> is open at the point where it appears.
        # Use a depth counter that tracks open <span> tags.
        for code_match in re.finditer(r'<code>[^<]+</code>', body):
            before = body[:code_match.start()]
            span_depth = 0
            for tag_m in re.finditer(r'<(/?)span\b[^>]*>', before):
                closing = tag_m.group(1) == '/'
                if closing:
                    span_depth -= 1
                else:
                    span_depth += 1
            assert span_depth == 0, (
                f'<code> appears inside an open <span data-i18n> wrapper — '
                f'applyI18n would destroy it. span_depth={span_depth} '
                f'before {code_match.group(0)!r}'
            )

    def test_paragraph_has_exactly_two_code_elements(self):
        """Two <code> wrappers for the two API endpoints — not lost in fix."""
        m = re.search(
            r'<p[^>]*style="color:var\(--text-muted\)[^"]*"[^>]*>(.*?)</p>',
            self.html, re.DOTALL
        )
        body = m.group(1)
        assert body.count('<code>') == 2


class TestSystemDescI18nKeys:
    """3 new i18n keys (zh + en) exist for the fragments."""

    def setup_method(self):
        self.i18n = _read(I18N_JS_PATH)
        # i18n.js structure: `const I18N = { zh: {...}, en: {...} }`.
        # Find the `zh:` and `en:` section boundaries.
        zh_start = re.search(r'^\s*zh:\s*\{', self.i18n, re.MULTILINE)
        en_start = re.search(r'^\s*en:\s*\{', self.i18n, re.MULTILINE)
        assert zh_start, 'zh section not found in i18n.js'
        assert en_start, 'en section not found in i18n.js'
        # zh runs from zh_start.end() to en_start.start()
        self.zh_section = self.i18n[zh_start.end():en_start.start()]
        # en runs from en_start.end() to end of file (or next top-level `}`)
        self.en_section = self.i18n[en_start.end():]

    def test_zh_keys_exist(self):
        for key in ('system.desc_prefix', 'system.desc_plus', 'system.desc_suffix'):
            m = re.search(
                rf"['\"]?{re.escape(key)}['\"]?\s*:\s*['\"]([^'\"]+)['\"]",
                self.zh_section
            )
            assert m, f'zh key {key} not found in i18n.js (zh section)'

    def test_en_keys_exist(self):
        for key, expected_word in (
            ('system.desc_prefix', 'Live'),
            ('system.desc_plus', '+'),
            ('system.desc_suffix', '.'),
        ):
            m = re.search(
                rf"['\"]?{re.escape(key)}['\"]?\s*:\s*['\"]([^'\"]+)['\"]",
                self.en_section
            )
            assert m, f'en key {key} not found in i18n.js (en section)'
            assert expected_word in m.group(1), (
                f'en {key} does not contain expected "{expected_word}": '
                f'{m.group(1)!r}'
            )

    def test_legacy_system_desc_key_still_present(self):
        """Backwards-compat: keep `system.desc` for any external consumers."""
        assert "'system.desc':" in self.i18n, 'Legacy system.desc key removed — risk of breaking other consumers'


class TestApplyI18nPreservesChildren:
    """Verify applyI18n() does NOT destroy <code> children in our patched markup."""

    def test_simulation_code_children_survive(self):
        """Simulate what applyI18n does and verify <code> elements survive."""
        html = _read(SYSTEM_HTML_PATH)
        # Find the description paragraph
        m = re.search(
            r'<p[^>]*style="color:var\(--text-muted\)[^"]*"[^>]*>(.*?)</p>',
            html, re.DOTALL
        )
        body = m.group(1)

        # The current applyI18n implementation does:
        #   el.textContent = text
        # for each element with data-i18n. If our markup has data-i18n on
        # the outer <p>, this destroys <code> children. After our fix, data-i18n
        # is on inner <span> wrappers (which have no children), so <code> survives.
        data_i18n_outer = re.search(
            r'<p[^>]*data-i18n="[^"]+"',
            html
        )
        assert not data_i18n_outer, (
            'data-i18n on outer <p> would destroy <code> children via textContent assignment'
        )

        # The <code> elements are siblings of [data-i18n] spans, not children.
        # applyI18n only touches elements WITH data-i18n attribute.
        code_count = len(re.findall(r'<code>[^<]+</code>', body))
        assert code_count == 2, f'Expected 2 <code> elements in description paragraph, got {code_count}'


class TestE2ESmoke:
    """Live HTTP smoke test."""

    def test_system_page_200(self):
        result = subprocess.run(
            ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
             'http://localhost:5000/system', '-m', '5'],
            capture_output=True, text=True, timeout=10
        )
        assert result.stdout.strip() == '200', (
            f'/system did not return 200: {result.stdout}'
        )

    def test_served_html_has_fragment_spans(self):
        result = subprocess.run(
            ['curl', '-sS', 'http://localhost:5000/system', '-m', '5'],
            capture_output=True, text=True, timeout=10
        )
        served = result.stdout
        for key in ('system.desc_prefix', 'system.desc_plus', 'system.desc_suffix'):
            assert f'data-i18n="{key}"' in served, (
                f'Served /system HTML missing data-i18n="{key}" span'
            )
        # Both <code> elements must appear at least once in served HTML
        # (the /api/metrics/summary code is also in the footer "Data from" line)
        assert served.count('<code>/api/metrics/summary</code>') >= 1
        assert served.count('<code>/health</code>') >= 1
