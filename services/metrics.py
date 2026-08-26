"""
Prometheus Metrics + Health Check for Stocker
==============================================
Exposes /metrics endpoint for Prometheus scraping and /health for liveness checks.

Metrics tracked:
- http_requests_total: Counter by method, endpoint, status_code
- http_request_duration_seconds: Histogram by method, endpoint
- stocker_tickers_total: Gauge — number of active tracked tickers
- stocker_reports_total: Gauge — number of collected reports (overall + by category)
- stocker_events_total: Gauge — events count (active + upcoming 7d)
- stocker_banks_total: Gauge — investment banks count (enabled + total)
- stocker_custom_sources_total: Gauge — custom JSONPath sources count
- stocker_watchlist_groups_total: Gauge — watchlist groups count
- stocker_alerts_total: Gauge — price alerts count (enabled + disabled)
- stocker_alerts_triggered_total: Counter — alerts triggered events
- stocker_cache_hits_total / stocker_cache_misses_total: Counters
- stocker_data_source_requests_total: Counter by source
- stocker_sse_connections: Gauge — active SSE connections
- stocker_nightly_refresh_total: Counter by status
- stocker_health_check_total: Counter by status
"""

import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from flask import request as flask_request, jsonify
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

REPORTS_BY_CATEGORY = Gauge(
    'stocker_reports_by_category',
    'Reports grouped by category',
    ['category']
)

EVENTS_ACTIVE = Gauge(
    'stocker_events_active',
    'Number of active (un-dismissed) events'
)

EVENTS_UPCOMING_7D = Gauge(
    'stocker_events_upcoming_7d',
    'Number of upcoming events in next 7 days'
)

BANKS_TOTAL = Gauge(
    'stocker_banks_total',
    'Total investment banks',
    ['enabled']  # 'true' / 'false'
)

CUSTOM_SOURCES_TOTAL = Gauge(
    'stocker_custom_sources_total',
    'Custom JSONPath data sources count',
    ['enabled']
)

WATCHLIST_GROUPS_TOTAL = Gauge(
    'stocker_watchlist_groups_total',
    'Watchlist groups count'
)

# ── Price Alerts (v3.4) ─────────────────────────────────────────────────

ALERTS_TOTAL = Gauge(
    'stocker_alerts_total',
    'Price alerts count',
    ['enabled']  # 'true' / 'false'
)

ALERTS_TRIGGERED = Counter(
    'stocker_alerts_triggered_total',
    'Total price alerts that have fired (across all check paths)'
)

# ── Portfolio Snapshots (v3.4.2) ──────────────────────────────────────────

SNAPSHOTS_TOTAL = Gauge(
    'stocker_portfolio_snapshots_total',
    'Number of portfolio snapshots stored in the database'
)

PORTFOLIO_VALUE_LATEST = Gauge(
    'stocker_portfolio_value_dollars_latest',
    'Latest portfolio market value in dollars'
)

PORTFOLIO_PNL_LATEST = Gauge(
    'stocker_portfolio_pnl_dollars_latest',
    'Latest portfolio unrealized P&L in dollars'
)

APP_START_TIME = Gauge(
    'stocker_app_start_time_seconds',
    'Unix timestamp when Stocker started'
)

# ── Industry News (v3.4.16) ──────────────────────────────────────────────

INDUSTRY_NEWS_REQUESTS = Counter(
    'stocker_industry_news_requests_total',
    'Industry news endpoint requests per sector (split by result status)',
    ['status']  # 'ok' | 'empty' — tracks whether the sector had any news
)


def record_industry_news_request(sector: str, status: str):
    """Increment the industry news request counter for a sector.

    Called from app.py:api_industry_news. status is 'ok' (≥1 result)
    or 'empty' (no industry-category rows matched the sector prefix).
    The sector itself is intentionally NOT a label — too many sectors
    would explode cardinality. Status split lets dashboards spot
    sectors that have never been collected.
    """
    INDUSTRY_NEWS_REQUESTS.labels(status=status).inc()

# Set start time on import
APP_START_TIME.set(time.time())

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

HEALTH_CHECK = Counter(
    'stocker_health_check_total',
    'Health check calls',
    ['status']  # 'healthy' / 'degraded' / 'unhealthy'
)

# Report search (v3.4.3) — track search queries by whether they returned results
REPORT_SEARCH = Counter(
    'stocker_report_searches_total',
    'Filtered report searches via /api/reports (filters supplied)',
    ['has_results']  # 'true' / 'false'
)

# Portfolio CSV export (v3.4.5) — track export calls by format
PORTFOLIO_EXPORT = Counter(
    'stocker_portfolio_exports_total',
    'Portfolio snapshot CSV/TSV export calls via /api/portfolio/snapshots/export.csv',
    ['format']  # 'csv' / 'tsv'
)

# Portfolio per-ticker breakdown (v3.4.6) — track live breakdown endpoint usage
PORTFOLIO_BREAKDOWN = Counter(
    'stocker_portfolio_breakdown_requests_total',
    'Live portfolio per-ticker breakdown requests via /api/portfolio/breakdown',
    ['status']  # 'ok' / 'empty' / 'error'
)

# Portfolio snapshot capture (v3.4.8) — track both manual (dashboard button)
# and nightly (cron) trigger paths. Lets dashboards see whether users are
# actively curating their history vs. relying purely on the 20:00 sweep.
PORTFOLIO_CAPTURES = Counter(
    'stocker_portfolio_captures_total',
    'Portfolio snapshot captures via /api/portfolio/capture (manual) or nightly_tasks.py (cron)',
    ['trigger']  # 'manual' / 'nightly'
)

# Tickers CSV export (v3.4.9) — track the dashboard "匯出持倉 CSV" button
# (and any other consumers of /api/tickers/export.csv). Helps spot whether
# users actually use the export vs. relying on the in-app portfolio view.
# Two scopes: 'all' = full active tickers list, 'group' = filtered to a watchlist group.
TICKER_EXPORT = Counter(
    'stocker_ticker_exports_total',
    'Ticker holdings CSV export calls via /api/tickers/export.csv',
    ['scope']  # 'all' / 'group'
)

# Pre-create label children so /metrics and /api/metrics/summary show 0 (not absent)
# before any traffic. Mirrors the report_searches pattern (Pitfall 15).
TICKER_EXPORT.labels(scope='all')
TICKER_EXPORT.labels(scope='group')


# Manual admin triggers (v3.4.24) — track button presses on /system page.
# 'action' is one of: 'nightly_refresh', 'check_banks', 'collect_reports'.
# Helps spot whether users actually use the admin triggers vs. waiting for
# the nightly cron sweep.
MANUAL_TRIGGERS = Counter(
    'stocker_manual_triggers_total',
    'Manual admin trigger button presses on /system page',
    ['action']  # 'nightly_refresh' / 'check_banks' / 'collect_reports'
)

# Pre-create label children so /metrics shows 0 (not absent) before any traffic.
MANUAL_TRIGGERS.labels(action='nightly_refresh')
MANUAL_TRIGGERS.labels(action='check_banks')
MANUAL_TRIGGERS.labels(action='collect_reports')


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


def record_alert_triggered(count: int = 1):
    """Record that `count` price alerts fired.

    Called by app.py / nightly_tasks.py whenever check_alerts_*() produces output.
    """
    if count > 0:
        ALERTS_TRIGGERED.inc(count)


def record_health(status):
    """Record a health check outcome (healthy/degraded/unhealthy)."""
    HEALTH_CHECK.labels(status=status).inc()


def record_report_search(has_results: bool):
    """Record a filtered report search via /api/reports.

    Called from app.py's api_get_reports only when filters were supplied.
    Tracks zero-result searches separately so dashboard can spot dead queries.
    """
    REPORT_SEARCH.labels(has_results='true' if has_results else 'false').inc()


def record_portfolio_export(fmt: str):
    """Record a portfolio snapshot CSV/TSV export via /api/portfolio/snapshots/export.csv.

    Tracks format separately (csv vs tsv) so dashboards can spot which
    format users actually consume — useful before adding new formats
    like JSON or XLSX.
    """
    PORTFOLIO_EXPORT.labels(format=fmt).inc()


def record_portfolio_breakdown(status: str):
    """Record a per-ticker portfolio breakdown request.

    `status` is 'ok' (had at least one holding), 'empty' (no holdings
    worth breaking down — shares=0 or no prices), or 'error' (exception).
    Label lets dashboards spot empty-portfolio users separately from
    genuine errors.
    """
    PORTFOLIO_BREAKDOWN.labels(status=status).inc()


def record_portfolio_capture(trigger: str):
    """Record a portfolio snapshot capture.

    `trigger` is 'manual' (dashboard "拍攝" button → POST /api/portfolio/capture)
    or 'nightly' (cron sweep in nightly_tasks.py). Splits the two paths
    so dashboards can chart daily activity vs. user-driven curation.
    """
    if trigger not in ('manual', 'nightly'):
        trigger = 'manual'  # fail safe — never silently drop an event
    PORTFOLIO_CAPTURES.labels(trigger=trigger).inc()


def record_ticker_export(scope: str):
    """Record a tickers CSV export call (v3.4.9 dashboard "📤 匯出持倉 CSV" button).

    `scope` is 'all' (no ?group filter — full active tickers) or 'group'
    (filter scoped to a watchlist group_id). Splits the two paths so
    dashboards can see whether group-aware exports are ever used.
    """
    TICKER_EXPORT.labels(scope=scope).inc()


def record_manual_trigger(action: str):
    """Record a manual admin trigger button press (v3.4.24 /system page).

    `action` is one of: 'nightly_refresh' (POST /api/nightly-refresh),
    'check_banks' (POST /api/banks/check-all), or 'collect_reports'
    (POST /api/reports/collect). Splits so dashboards can spot which
    admin actions users actually use vs. waiting for nightly cron.
    """
    if action not in ('nightly_refresh', 'check_banks', 'collect_reports'):
        action = 'nightly_refresh'  # fail safe — never silently drop an event
    MANUAL_TRIGGERS.labels(action=action).inc()




# ── Metrics Endpoint Handler ───────────────────────────────────────────

def _update_business_gauges():
    """Refresh all business gauges from DB before scrape.
    Called by metrics_endpoint and JSON summary endpoint.
    Each block is wrapped in try/except so a single failure doesn't kill the others.
    """
    import models

    # Tickers
    try:
        tickers = models.get_all_tickers()
        update_ticker_count(len(tickers) if tickers else 0)
    except Exception:
        pass

    # Reports overall + by category
    try:
        from models import get_db
        db = get_db()
        row = db.execute('SELECT COUNT(*) as c FROM reports').fetchone()
        if row:
            update_report_count(row['c'])
        # By category
        rows = db.execute(
            'SELECT category, COUNT(*) as c FROM reports GROUP BY category'
        ).fetchall()
        for r in rows:
            REPORTS_BY_CATEGORY.labels(category=r['category'] or 'unknown').set(r['c'])
    except Exception:
        pass

    # Events
    try:
        from models import get_db
        db = get_db()
        row = db.execute(
            "SELECT COUNT(*) as c FROM events WHERE dismissed = 0"
        ).fetchone()
        if row:
            EVENTS_ACTIVE.set(row['c'])
        # event_date stored as YYYY-MM-DD; use date() for consistent comparison
        row = db.execute(
            "SELECT COUNT(*) as c FROM events WHERE dismissed = 0 "
            "AND event_date >= date('now') AND event_date <= date('now', '+7 days')"
        ).fetchone()
        if row:
            EVENTS_UPCOMING_7D.set(row['c'])
    except Exception:
        pass

    # Banks (enabled vs total)
    try:
        from models import get_db
        db = get_db()
        for enabled_val in ('true', 'false'):
            row = db.execute(
                'SELECT COUNT(*) as c FROM investment_banks WHERE enabled = ?',
                (1 if enabled_val == 'true' else 0,)
            ).fetchone()
            if row:
                BANKS_TOTAL.labels(enabled=enabled_val).set(row['c'])
    except Exception:
        pass

    # Custom sources
    try:
        from models import get_db
        db = get_db()
        for enabled_val in ('true', 'false'):
            row = db.execute(
                'SELECT COUNT(*) as c FROM custom_data_sources WHERE enabled = ?',
                (1 if enabled_val == 'true' else 0,)
            ).fetchone()
            if row:
                CUSTOM_SOURCES_TOTAL.labels(enabled=enabled_val).set(row['c'])
    except Exception:
        pass

    # Watchlist groups
    try:
        from models import get_db
        db = get_db()
        row = db.execute('SELECT COUNT(*) as c FROM watchlist_groups').fetchone()
        if row:
            WATCHLIST_GROUPS_TOTAL.set(row['c'])
    except Exception:
        pass

    # Price alerts (v3.4) — split by enabled flag
    try:
        from models import get_db
        db = get_db()
        for enabled_val in ('true', 'false'):
            row = db.execute(
                'SELECT COUNT(*) as c FROM price_alerts WHERE enabled = ?',
                (1 if enabled_val == 'true' else 0,)
            ).fetchone()
            if row:
                ALERTS_TOTAL.labels(enabled=enabled_val).set(row['c'])
    except Exception:
        pass

    # Portfolio snapshots (v3.4.2) — count + latest value/pnl
    try:
        from models import get_db
        db = get_db()
        row = db.execute('SELECT COUNT(*) as c FROM portfolio_snapshots').fetchone()
        if row:
            SNAPSHOTS_TOTAL.set(row['c'])
        latest = db.execute(
            "SELECT total_value, total_pnl FROM portfolio_snapshots "
            "ORDER BY snapshot_date DESC LIMIT 1"
        ).fetchone()
        if latest:
            PORTFOLIO_VALUE_LATEST.set(latest['total_value'] or 0)
            PORTFOLIO_PNL_LATEST.set(latest['total_pnl'] or 0)
    except Exception:
        pass


def metrics_endpoint():
    """Return Prometheus metrics as plaintext."""
    _update_business_gauges()
    from flask import Response
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )


# ── Health Check ──────────────────────────────────────────────────────

def _check_db():
    """Verify SQLite is readable. Returns (ok, detail)."""
    try:
        import models
        db = models.get_db()
        row = db.execute('SELECT 1 as ok').fetchone()
        if row and row['ok'] == 1:
            return True, 'sqlite_ok'
        return False, 'sqlite_query_failed'
    except Exception as e:
        return False, f'sqlite_error: {type(e).__name__}'


def _check_disk():
    """Check free disk space on data dir. Warn if <500MB."""
    try:
        from pathlib import Path
        data_dir = Path.home() / 'repos' / 'Stocker' / 'data'
        if not data_dir.exists():
            return True, 'data_dir_missing_skipped'
        usage = shutil.disk_usage(data_dir)
        free_mb = usage.free / (1024 * 1024)
        if free_mb < 100:
            return False, f'critical_low_disk: {free_mb:.0f}MB free'
        if free_mb < 500:
            return True, f'low_disk_warning: {free_mb:.0f}MB free'
        return True, f'ok_{free_mb:.0f}MB_free'
    except Exception as e:
        return True, f'disk_check_skipped: {type(e).__name__}'


def _check_tsdb():
    """Verify timeseries DB is readable. Returns (ok, detail)."""
    try:
        import tsdb
        # Try a trivial query
        df = tsdb.get_daily_prices('TSLA', days=1)
        return True, 'tsdb_ok'
    except Exception as e:
        return False, f'tsdb_error: {type(e).__name__}: {str(e)[:80]}'


def health_check():
    """
    Liveness + readiness probe.
    Returns 200 if healthy/degraded, 503 if unhealthy.
    Records outcome in Prometheus counter.
    """
    checks = {}
    overall_ok = True

    db_ok, db_detail = _check_db()
    checks['database'] = {'ok': db_ok, 'detail': db_detail}
    if not db_ok:
        overall_ok = False

    disk_ok, disk_detail = _check_disk()
    checks['disk'] = {'ok': disk_ok, 'detail': disk_detail}
    if not disk_ok:
        overall_ok = False

    tsdb_ok, tsdb_detail = _check_tsdb()
    checks['tsdb'] = {'ok': tsdb_ok, 'detail': tsdb_detail}
    if not tsdb_ok:
        # TSDB failure is degraded, not unhealthy — app can still serve from primary DB
        pass

    uptime_seconds = time.time() - APP_START_TIME._value.get()

    # Determine status
    if not overall_ok:
        status = 'unhealthy'
        http_code = 503
    elif not tsdb_ok:
        status = 'degraded'
        http_code = 200
    else:
        status = 'healthy'
        http_code = 200

    record_health(status)

    payload = {
        'status': status,
        'uptime_seconds': round(uptime_seconds, 1),
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    return jsonify(payload), http_code


# ── JSON Metrics Summary (for human-readable dashboards) ──────────────

def metrics_summary():
    """
    Human-readable JSON summary of key Stocker business metrics.
    Designed for monitoring dashboards (not Prometheus).
    """
    _update_business_gauges()

    try:
        from models import get_db
        db = get_db()

        # Reports by category breakdown
        cat_rows = db.execute(
            'SELECT category, COUNT(*) as c FROM reports GROUP BY category ORDER BY c DESC'
        ).fetchall()
        reports_by_category = {r['category']: r['c'] for r in cat_rows}

        # Top sectors
        sector_rows = db.execute(
            '''SELECT sector, COUNT(*) as c FROM tickers
               WHERE archived = 0 AND sector IS NOT NULL
               GROUP BY sector ORDER BY c DESC LIMIT 10'''
        ).fetchall()
        sectors = [{'sector': r['sector'], 'count': r['c']} for r in sector_rows]

        # Banks status
        bank_rows = db.execute(
            '''SELECT enabled, COUNT(*) as c FROM investment_banks GROUP BY enabled'''
        ).fetchall()
        banks = {'enabled': 0, 'disabled': 0}
        for r in bank_rows:
            if r['enabled']:
                banks['enabled'] = r['c']
            else:
                banks['disabled'] = r['c']

        # Latest report timestamp
        latest = db.execute(
            'SELECT MAX(created_at) as ts FROM reports'
        ).fetchone()
        latest_report_ts = latest['ts'] if latest else None

        # Tickers with most reports (top 5) — derive symbol from file_path prefix
        # file_path format: data/files/<category>/<SYMBOL>_
        top_rows = db.execute(
            '''SELECT file_path, COUNT(*) as c FROM reports
               WHERE file_path IS NOT NULL AND file_path != ''
               GROUP BY file_path ORDER BY c DESC LIMIT 50'''
        ).fetchall()

        # Count by extracted symbol
        from collections import Counter
        symbol_counter = Counter()
        for r in top_rows:
            fp = r['file_path'] or ''
            # filename like "GLW_10-Q_2026-05-01.htm" — take part before first '_'
            fname = fp.split('/')[-1] if '/' in fp else fp.split('\\')[-1]
            sym = fname.split('_')[0].split('.')[0].upper()
            if sym.isalpha() and len(sym) <= 5:
                symbol_counter[sym] += r['c']
        top_tickers = [
            {'symbol': sym, 'reports': cnt}
            for sym, cnt in symbol_counter.most_common(5)
        ]

    except Exception as e:
        return jsonify({'error': f'db_query_failed: {type(e).__name__}', 'detail': str(e)[:200]}), 500

    uptime_seconds = time.time() - APP_START_TIME._value.get()

    return jsonify({
        'uptime_seconds': round(uptime_seconds, 1),
        'uptime_human': _format_uptime(uptime_seconds),
        'tickers_active': int(TICKERS_TOTAL._value.get()),
        'reports_total': int(REPORTS_TOTAL._value.get()),
        'reports_by_category': reports_by_category,
        'events_active': int(EVENTS_ACTIVE._value.get()),
        'events_upcoming_7d': int(EVENTS_UPCOMING_7D._value.get()),
        'banks': banks,
        'custom_sources': {
            'enabled': int(CUSTOM_SOURCES_TOTAL.labels(enabled='true')._value.get()),
            'disabled': int(CUSTOM_SOURCES_TOTAL.labels(enabled='false')._value.get()),
        },
        'watchlist_groups': int(WATCHLIST_GROUPS_TOTAL._value.get()),
        'sse_connections': int(SSE_CONNECTIONS._value.get()),
        'alerts': {
            'enabled': int(ALERTS_TOTAL.labels(enabled='true')._value.get()),
            'disabled': int(ALERTS_TOTAL.labels(enabled='false')._value.get()),
            'triggered_total': int(ALERTS_TRIGGERED._value.get()),
        },
        # report_searches: sum across label values for total; read each label
        # for zero_result vs with_results breakdown. Use children (._metrics)
        # rather than trying to read the parent Counter.
        'report_searches': {
            'total': sum(c._value.get() for c in REPORT_SEARCH._metrics.values()),
            'with_results': int(REPORT_SEARCH.labels(has_results='true')._value.get()),
            'zero_results': int(REPORT_SEARCH.labels(has_results='false')._value.get()),
        },
        'portfolio': {
            'snapshots_count': int(SNAPSHOTS_TOTAL._value.get()),
            'latest_value': round(PORTFOLIO_VALUE_LATEST._value.get(), 2),
            'latest_pnl': round(PORTFOLIO_PNL_LATEST._value.get(), 2),
        },
        # portfolio_exports: sum across format label values for total;
        # split by format for dashboards. Mirrors report_searches pattern.
        'portfolio_exports': {
            'total': sum(c._value.get() for c in PORTFOLIO_EXPORT._metrics.values()),
            'csv': int(PORTFOLIO_EXPORT.labels(format='csv')._value.get()),
            'tsv': int(PORTFOLIO_EXPORT.labels(format='tsv')._value.get()),
        },
        # portfolio_breakdowns: sum across status label values for total;
        # split by status (ok / empty / error) so dashboards can spot
        # users who have no holdings vs genuine errors.
        'portfolio_breakdowns': {
            'total': sum(c._value.get() for c in PORTFOLIO_BREAKDOWN._metrics.values()),
            'ok': int(PORTFOLIO_BREAKDOWN.labels(status='ok')._value.get()),
            'empty': int(PORTFOLIO_BREAKDOWN.labels(status='empty')._value.get()),
            'error': int(PORTFOLIO_BREAKDOWN.labels(status='error')._value.get()),
        },
        # portfolio_captures (v3.4.8): track how the history was built —
        # nightly sweep vs. user pressing the dashboard "拍攝" button.
        # Empty/missing label keys are coerced to 0 via labels(...)._value.get().
        'portfolio_captures': {
            'total': sum(c._value.get() for c in PORTFOLIO_CAPTURES._metrics.values()),
            'manual': int(PORTFOLIO_CAPTURES.labels(trigger='manual')._value.get()),
            'nightly': int(PORTFOLIO_CAPTURES.labels(trigger='nightly')._value.get()),
        },
        # ticker_exports (v3.4.9): track dashboard "📤 匯出持倉 CSV" button
        # usage. Two scopes — 'all' (full active list) vs 'group'
        # (filtered by watchlist group_id). Pre-created labels at import
        # ensure these counters always appear (Pitfall 15).
        'ticker_exports': {
            'total': sum(c._value.get() for c in TICKER_EXPORT._metrics.values()),
            'all': int(TICKER_EXPORT.labels(scope='all')._value.get()),
            'group': int(TICKER_EXPORT.labels(scope='group')._value.get()),
        },
        # industry_news (v3.4.16): /api/industry/<sector>/news requests.
        # Sum across status labels for total; split by ok/empty so we
        # can spot sectors that have never been collected.
        'industry_news': {
            'total': sum(c._value.get() for c in INDUSTRY_NEWS_REQUESTS._metrics.values()),
            'ok': int(INDUSTRY_NEWS_REQUESTS.labels(status='ok')._value.get()),
            'empty': int(INDUSTRY_NEWS_REQUESTS.labels(status='empty')._value.get()),
        },
        # manual_triggers (v3.4.24): /system page admin button presses.
        # Three actions: nightly_refresh / check_banks / collect_reports.
        # Pre-created labels at import ensure these counters always appear.
        'manual_triggers': {
            'total': sum(c._value.get() for c in MANUAL_TRIGGERS._metrics.values()),
            'nightly_refresh': int(MANUAL_TRIGGERS.labels(action='nightly_refresh')._value.get()),
            'check_banks': int(MANUAL_TRIGGERS.labels(action='check_banks')._value.get()),
            'collect_reports': int(MANUAL_TRIGGERS.labels(action='collect_reports')._value.get()),
        },
        'top_sectors': sectors,
        'top_tickers_by_reports': top_tickers,
        'latest_report_at': latest_report_ts,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


def _format_uptime(seconds):
    """Format uptime in human-readable form (e.g. '3d 4h 22m')."""
    td = timedelta(seconds=int(seconds))
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes = remainder // 60
    if days > 0:
        return f'{days}d {hours}h {minutes}m'
    if hours > 0:
        return f'{hours}h {minutes}m'
    return f'{minutes}m'
