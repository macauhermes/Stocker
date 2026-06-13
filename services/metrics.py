"""
Prometheus Metrics for Stocker
===============================
Exposes /metrics endpoint for Prometheus scraping.

Metrics tracked:
- http_requests_total: Counter by method, endpoint, status_code
- http_request_duration_seconds: Histogram by method, endpoint
- stocker_tickers_total: Gauge — number of active tracked tickers
- stocker_reports_total: Gauge — number of collected reports
- stocker_cache_hits_total / stocker_cache_misses_total: Counters
- stocker_data_source_requests_total: Counter by source
- stocker_sse_connections: Gauge — active SSE connections
- stocker_nightly_refresh_total: Counter by status
"""

import time
from functools import wraps
from flask import request as flask_request
from prometheus_client import (
    Counter, Histogram, Gauge, CollectorRegistry,
    generate_latest, CONTENT_TYPE_LATEST
)

# ── Request Metrics ────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ── Business Metrics ───────────────────────────────────────────────────

TICKERS_TOTAL = Gauge(
    'stocker_tickers_total',
    'Number of active tracked tickers'
)

REPORTS_TOTAL = Gauge(
    'stocker_reports_total',
    'Number of collected reports'
)

CACHE_HITS = Counter(
    'stocker_cache_hits_total',
    'Total cache hits'
)

CACHE_MISSES = Counter(
    'stocker_cache_misses_total',
    'Total cache misses'
)

DATA_SOURCE_REQUESTS = Counter(
    'stocker_data_source_requests_total',
    'Data source requests by source',
    ['source']
)

SSE_CONNECTIONS = Gauge(
    'stocker_sse_connections',
    'Active SSE connections'
)

NIGHTLY_REFRESH = Counter(
    'stocker_nightly_refresh_total',
    'Nightly refresh runs',
    ['status']
)


# ── Middleware ──────────────────────────────────────────────────────────

def init_metrics(app):
    """Register before/after request hooks for automatic HTTP metrics."""

    @app.before_request
    def _metrics_before():
        flask_request._metrics_start = time.monotonic()

    @app.after_request
    def _metrics_after(response):
        # Skip metrics endpoint itself to avoid noise
        if flask_request.path == '/metrics':
            return response

        start = getattr(flask_request, '_metrics_start', None)
        if start is not None:
            duration = time.monotonic() - start
            endpoint = _simplify_endpoint(flask_request.endpoint)
            REQUEST_LATENCY.labels(
                method=flask_request.method,
                endpoint=endpoint
            ).observe(duration)
            REQUEST_COUNT.labels(
                method=flask_request.method,
                endpoint=endpoint,
                status_code=response.status_code
            ).inc()

        return response


def _simplify_endpoint(endpoint):
    """Collapse dynamic segments to avoid cardinality explosion."""
    if not endpoint:
        return 'unknown'
    return endpoint


# ── Helpers for app.py to update gauges ────────────────────────────────

def update_ticker_count(count):
    """Set the current ticker count gauge."""
    TICKERS_TOTAL.set(count)


def update_report_count(count):
    """Set the current report count gauge."""
    REPORTS_TOTAL.set(count)


def record_cache_hit():
    """Increment cache hit counter."""
    CACHE_HITS.inc()


def record_cache_miss():
    """Increment cache miss counter."""
    CACHE_MISSES.inc()


def record_data_source(source):
    """Record which data source served a request."""
    DATA_SOURCE_REQUESTS.labels(source=source).inc()


def record_nightly_refresh(status):
    """Record a nightly refresh run (success/failure)."""
    NIGHTLY_REFRESH.labels(status=status).inc()


def sse_connect():
    """Increment SSE connection count."""
    SSE_CONNECTIONS.inc()


def sse_disconnect():
    """Decrement SSE connection count."""
    SSE_CONNECTIONS.dec()


# ── Metrics Endpoint Handler ───────────────────────────────────────────

def metrics_endpoint():
    """Return Prometheus metrics as plaintext."""
    # Update business gauges before scrape
    try:
        import models
        tickers = models.get_all_tickers()
        update_ticker_count(len(tickers))
    except Exception:
        pass

    try:
        import models
        from models import get_db
        db = get_db()
        row = db.execute('SELECT COUNT(*) as c FROM reports').fetchone()
        if row:
            update_report_count(row['c'])
    except Exception:
        pass

    from flask import Response
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )
