"""
Unit tests for the portfolio_captures Prometheus counter (v3.4.8).

These tests exercise the helpers + summary endpoint surface that the
dashboard "拍攝快照" / cron "nightly sweep" trigger paths rely on.

What we test:
  - record_portfolio_capture('manual') increments manual counter
  - record_portfolio_capture('nightly') increments nightly counter
  - invalid trigger label coerces to 'manual' (fail-safe — never drop)
  - /api/metrics/summary includes portfolio_captures block with manual + nightly + total
  - total = sum of manual + nightly children (Pitfall 15 from
    flask-api-integration-pitfalls — labelled Counter parent has no _value)
"""
import os
import sys
from pathlib import Path

import pytest

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services import metrics  # noqa: E402


class TestRecordPortfolioCapture:
    """Test the counter helper directly. No Flask context needed —
    Prometheus counters are global module state."""

    def test_manual_trigger_increments_manual_counter(self):
        from services.metrics import PORTFOLIO_CAPTURES, record_portfolio_capture
        before = PORTFOLIO_CAPTURES.labels(trigger='manual')._value.get()
        record_portfolio_capture(trigger='manual')
        after = PORTFOLIO_CAPTURES.labels(trigger='manual')._value.get()
        assert after == before + 1

    def test_nightly_trigger_increments_nightly_counter(self):
        from services.metrics import PORTFOLIO_CAPTURES, record_portfolio_capture
        before = PORTFOLIO_CAPTURES.labels(trigger='nightly')._value.get()
        record_portfolio_capture(trigger='nightly')
        after = PORTFOLIO_CAPTURES.labels(trigger='nightly')._value.get()
        assert after == before + 1

    def test_invalid_trigger_coerces_to_manual(self):
        """Fail-safe: unknown trigger labels coerce to 'manual' rather than
        dropping the event silently. This matters because Prometheus labelled
        Counters auto-create child metrics for any label value seen."""
        from services.metrics import PORTFOLIO_CAPTURES, record_portfolio_capture
        before = PORTFOLIO_CAPTURES.labels(trigger='manual')._value.get()
        record_portfolio_capture(trigger='something_weird')
        after = PORTFOLIO_CAPTURES.labels(trigger='manual')._value.get()
        assert after == before + 1
        # The weird label should NOT exist — only the valid ones
        # (this prevents polluting the metric with garbage label values)
        assert 'something_weird' not in PORTFOLIO_CAPTURES._metrics

    def test_manual_and_nightly_are_independent(self):
        """Each trigger label has its own counter — incrementing manual
        must not bump nightly."""
        from services.metrics import PORTFOLIO_CAPTURES, record_portfolio_capture
        m_before = PORTFOLIO_CAPTURES.labels(trigger='manual')._value.get()
        n_before = PORTFOLIO_CAPTURES.labels(trigger='nightly')._value.get()
        record_portfolio_capture(trigger='manual')
        m_after = PORTFOLIO_CAPTURES.labels(trigger='manual')._value.get()
        n_after = PORTFOLIO_CAPTURES.labels(trigger='nightly')._value.get()
        assert m_after == m_before + 1
        assert n_after == n_before


class TestMetricsSummary:
    """Test that metrics_summary() surfaces the portfolio_captures block."""

    @pytest.fixture(scope='class')
    def app(self):
        """Minimal Flask app — needed because metrics_summary uses jsonify()."""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    def test_summary_has_portfolio_captures_block(self, app):
        with app.app_context():
            response, _ = metrics.metrics_summary()
        body = response.get_json()
        assert 'portfolio_captures' in body
        pc = body['portfolio_captures']
        assert 'total' in pc
        assert 'manual' in pc
        assert 'nightly' in pc

    def test_summary_block_is_numeric(self, app):
        """All values must be ints/0.0, not None — a missing label would
        AttributeError on ._value.get(), so this also guards against
        future regressions where a label is renamed but not pre-created."""
        with app.app_context():
            response, _ = metrics.metrics_summary()
        pc = response.get_json()['portfolio_captures']
        for key in ('total', 'manual', 'nightly'):
            assert isinstance(pc[key], (int, float)), f"{key} is {type(pc[key])}"
            assert pc[key] >= 0

    def test_total_equals_sum_of_children(self, app):
        """Pitfall 15: parent Counter has no _value. We sum the children
        via _metrics.values(). This test verifies the math holds."""
        from services.metrics import PORTFOLIO_CAPTURES, record_portfolio_capture
        # Bump both labels once each so totals are deterministic
        record_portfolio_capture(trigger='manual')
        record_portfolio_capture(trigger='nightly')

        with app.app_context():
            response, _ = metrics.metrics_summary()
        pc = response.get_json()['portfolio_captures']
        assert pc['total'] == pc['manual'] + pc['nightly']
        # Also verify the raw Prometheus math agrees
        child_total = sum(c._value.get() for c in PORTFOLIO_CAPTURES._metrics.values())
        assert pc['total'] == child_total
