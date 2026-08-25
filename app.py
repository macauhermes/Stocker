"""
Stocker — 美股追蹤工具
======================
Flask web application for tracking US stocks, collecting financial reports,
and providing AI-powered analysis.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask, render_template, jsonify, request, send_file, redirect, url_for,
    Response,
)

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import models
import tsdb
from services.stock_data import (
    fetch_stock_info, fetch_historical_prices, fetch_chart_data,
    fetch_news, fetch_next_earnings, refresh_ticker_data
)
from services.report_collector import collect_reports, collect_ticker_reports
from services.ai_analyzer import analyze_report
from services import multi_source
from services import metrics
from services import portfolio_snapshot

# ── App Setup ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Prometheus Metrics ─────────────────────────────────────────────────
metrics.init_metrics(app)

DATA_DIR = Path(os.path.expanduser("~/repos/Stocker/data"))
FILES_DIR = DATA_DIR / "files"

# Simple in-memory cache with TTL
_cache = {}
_CACHE_TTL = 300  # 5 minutes

def cached(key, ttl=_CACHE_TTL):
    """Get cached value if not expired."""
    if key in _cache:
        val, ts = _cache[key]
        if (datetime.now() - ts).total_seconds() < ttl:
            metrics.record_cache_hit()
            return val
    metrics.record_cache_miss()
    return None

def cache_set(key, value):
    """Store value in cache."""
    _cache[key] = (value, datetime.now())

def cache_timestamp(key):
    """Return the datetime when a cache key was last set, or None."""
    if key in _cache:
        return _cache[key][1]
    return None

def cache_invalidate(*keys):
    """Remove one or more keys from the cache. Silently ignores missing keys.

    Use this whenever underlying data changes (ticker added/removed/restored,
    stock data refreshed, etc.) so the next request sees fresh data instead
    of stale TTL-cached values.
    """
    for k in keys:
        _cache.pop(k, None)

def cache_invalidate_prefix(prefix):
    """Remove all keys starting with `prefix` (e.g. 'stock_info_')."""
    stale = [k for k in _cache if k.startswith(prefix)]
    for k in stale:
        _cache.pop(k, None)
    return len(stale)


# ── Initialize DB on startup ──────────────────────────────────────────
models.init_db()
tsdb.init_tsdb()


# ── Page Routes ────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/stock/<symbol>')
def stock_detail(symbol):
    return render_template('stock_detail.html', symbol=symbol.upper())


@app.route('/report/<int:report_id>')
def report_detail(report_id):
    return render_template('report_detail.html', report_id=report_id)


@app.route('/files')
def files_page():
    return render_template('files.html')


@app.route('/industry')
def industry_page():
    return render_template('industry.html')


# ── API: Tickers ───────────────────────────────────────────────────────

@app.route('/api/tickers', methods=['GET'])
def api_get_tickers():
    """Return all tracked tickers with current price data."""
    # Check cache first
    cache_key = 'tickers_with_prices'
    cached_result = cached(cache_key)
    if cached_result is not None:
        return jsonify(cached_result)

    tickers = models.get_all_tickers()
    result = []
    for t in tickers:
        ticker_data = dict(t)
        # Try to get current price info from cache or yfinance
        price_cache_key = f'stock_info_{t["symbol"]}'
        info = cached(price_cache_key, ttl=60)  # 1 min cache per stock
        if info is None:
            try:
                info = fetch_stock_info(t['symbol'])
                cache_set(price_cache_key, info)
            except Exception as e:
                logger.warning(f"Failed to fetch price for {t['symbol']}: {e}")
                info = {}

        ticker_data['current_price'] = info.get('price')
        ticker_data['change_percent'] = info.get('change_pct')
        ticker_data['prev_close'] = info.get('prev_close')
        ticker_data['market_cap'] = info.get('market_cap')
        ticker_data['pe_ratio'] = info.get('pe_ratio')
        ticker_data['eps'] = info.get('eps')
        ticker_data['week52_high'] = info.get('week52_high')
        ticker_data['week52_low'] = info.get('week52_low')
        ticker_data['data_source'] = info.get('source', 'unknown')
        # Include freshness timestamp
        ts = cache_timestamp(price_cache_key)
        ticker_data['last_updated'] = ts.isoformat() if ts else None
        result.append(ticker_data)

    cache_set(cache_key, result)
    return jsonify(result)


@app.route('/api/tickers', methods=['POST'])
def api_add_ticker():
    """Add a new ticker to track."""
    data = request.get_json()
    symbol = data.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': 'Symbol is required'}), 400

    # Check if already exists
    existing = models.get_ticker(symbol)
    if existing:
        return jsonify({'error': f'{symbol} already tracked'}), 409

    try:
        # Fetch info from yfinance to get name and sector
        info = fetch_stock_info(symbol)
        if not info.get('name'):
            return jsonify({'error': f'Could not find ticker {symbol}'}), 404

        ticker = models.add_ticker(
            symbol=symbol,
            name=info.get('name', symbol),
            sector=info.get('sector', '')
        )

        # Refresh data for new ticker
        try:
            refresh_ticker_data(symbol)
        except Exception as e:
            logger.warning(f"Failed to refresh data for new ticker {symbol}: {e}")

        # Invalidate aggregate tickers cache so new ticker shows up immediately
        cache_invalidate('tickers_with_prices')

        return jsonify(dict(ticker)), 201
    except Exception as e:
        logger.error(f"Error adding ticker {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/tickers/<symbol>', methods=['PUT'])
def api_update_ticker(symbol):
    """Update ticker holdings (shares_held, cost_basis)."""
    data = request.get_json()
    allowed = {'shares_held', 'cost_basis', 'name', 'sector'}
    updates = {k: v for k, v in data.items() if k in allowed}

    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    # Convert numeric fields
    for field in ['shares_held', 'cost_basis']:
        if field in updates:
            try:
                updates[field] = float(updates[field])
            except (ValueError, TypeError):
                return jsonify({'error': f'{field} must be a number'}), 400

    ticker = models.update_ticker(symbol.upper(), updates)
    if not ticker:
        return jsonify({'error': f'Ticker {symbol} not found'}), 404

    # Holdings changes affect the dashboard aggregate view
    cache_invalidate('tickers_with_prices')

    return jsonify(dict(ticker))


@app.route('/api/tickers/<symbol>', methods=['DELETE'])
def api_delete_ticker(symbol):
    """Archive a tracked ticker (soft delete)."""
    deleted = models.archive_ticker(symbol.upper())
    if not deleted:
        return jsonify({'error': f'Ticker {symbol} not found'}), 404
    cache_invalidate('tickers_with_prices', f'stock_info_{symbol.upper()}')
    return jsonify({'success': True, 'action': 'archived'})


@app.route('/api/tickers/<symbol>/restore', methods=['POST'])
def api_restore_ticker(symbol):
    """Restore an archived ticker."""
    restored = models.restore_ticker(symbol.upper())
    if not restored:
        return jsonify({'error': f'Archived ticker {symbol} not found'}), 404
    cache_invalidate('tickers_with_prices', f'stock_info_{symbol.upper()}')
    return jsonify({'success': True, 'action': 'restored'})


@app.route('/api/tickers/archived', methods=['GET'])
def api_get_archived_tickers():
    """Return all archived tickers."""
    tickers = models.get_archived_tickers()
    return jsonify([dict(t) for t in tickers])


@app.route('/api/tickers/export.csv', methods=['GET'])
def api_export_tickers_csv():
    """Export active tickers with holdings + current price + market value + P&L as CSV.

    Columns: symbol, name, sector, shares_held, cost_basis, current_price,
    market_value, cost_value, unrealized_pl, pl_percent, change_pct,
    data_source, last_updated

    Use ?group=<id> to scope to a watchlist group, or omit for all active tickers.
    """
    import csv
    from io import StringIO

    group_id = request.args.get('group', type=int)
    if group_id:
        tickers = models.get_watchlist_group_tickers(group_id)
        export_scope = 'group'  # v3.4.9: track which scope users hit
    else:
        tickers = models.get_all_tickers()
        export_scope = 'all'

    # v3.4.9: bump the Prometheus counter BEFORE returning so the metric
    # is always visible on /metrics even if downstream yfinance calls
    # time out (Pitfall 9 — code after `return` is dead). One increment
    # per request, regardless of how many tickers the CSV contains.
    try:
        from services import metrics as _metrics
        _metrics.record_ticker_export(export_scope)
    except Exception as e:
        logger.warning(f"CSV export: failed to record metric ({export_scope}): {e}")

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'symbol', 'name', 'sector', 'shares_held', 'cost_basis',
        'current_price', 'market_value', 'cost_value',
        'unrealized_pl', 'pl_percent', 'change_pct',
        'data_source', 'last_updated',
    ])

    for t in tickers:
        symbol = t['symbol']
        info = cached(f'stock_info_{symbol}', ttl=60)
        if info is None:
            try:
                info = fetch_stock_info(symbol)
                cache_set(f'stock_info_{symbol}', info)
            except Exception as e:
                logger.warning(f"CSV export: failed to fetch {symbol}: {e}")
                info = {}

        current_price = info.get('price')
        # sqlite3.Row supports [] but not .get(); use dict.get for safety
        shares = t['shares_held'] if 'shares_held' in t.keys() and t['shares_held'] is not None else 0
        cost_basis = t['cost_basis'] if 'cost_basis' in t.keys() and t['cost_basis'] is not None else 0
        name = t['name'] if 'name' in t.keys() else ''
        sector = t['sector'] if 'sector' in t.keys() else ''
        market_value = round(current_price * shares, 2) if current_price else 0
        cost_value = round(cost_basis * shares, 2)
        unrealized_pl = round(market_value - cost_value, 2) if current_price else 0
        pl_percent = round((unrealized_pl / cost_value) * 100, 2) if cost_value > 0 else 0

        ts = cache_timestamp(f'stock_info_{symbol}')
        last_updated = ts.isoformat() if ts else ''

        writer.writerow([
            symbol,
            name,
            sector,
            shares,
            cost_basis,
            current_price if current_price is not None else '',
            market_value,
            cost_value,
            unrealized_pl,
            pl_percent,
            info.get('change_pct', ''),
            info.get('source', 'unknown'),
            last_updated,
        ])

    csv_text = buf.getvalue()
    filename = f"stocker-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    # v3.4.9: fix double-charset bug (Pitfall 16) — Flask auto-appends
    # `; charset=utf-8` to text/* mimetypes, so we drop it from the
    # string. Was producing `Content-Type: text/csv; charset=utf-8; charset=utf-8`.
    return Response(
        csv_text,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


# ── API: Portfolio Snapshots (v3.4.2) ──────────────────────────────────

@app.route('/api/portfolio/snapshots', methods=['GET'])
def api_list_portfolio_snapshots():
    """Return the last N daily portfolio snapshots (oldest first).

    Query params:
        days — how many days of history (default 30, max 365)
    """
    try:
        days = min(int(request.args.get('days', 30)), 365)
    except (TypeError, ValueError):
        days = 30
    snapshots = models.list_snapshots(days=days)
    return jsonify({'snapshots': snapshots, 'count': len(snapshots)})


@app.route('/api/portfolio/summary', methods=['GET'])
def api_portfolio_summary():
    """Return the latest snapshot + 30-day P&L delta.

    Computes `change_30d` by comparing the latest snapshot's total_value
    against the snapshot ~30 days older (or the earliest one if fewer exist).
    Returns None for the delta if there's no history to compare.
    """
    latest = models.latest_snapshot()
    if not latest:
        return jsonify({
            'latest': None,
            'change_30d_value': None,
            'change_30d_pct': None,
            'has_history': False,
        })

    # 30-day-ago snapshot for delta calc — grab everything once for efficiency
    rows = models.list_snapshots(days=60)
    change_value = None
    change_pct = None
    if len(rows) >= 2:
        # Find the snapshot closest to 30 days before `latest.snapshot_date`
        from datetime import datetime as _dt, timedelta as _td
        try:
            latest_date = _dt.strptime(latest['snapshot_date'], '%Y-%m-%d').date()
            target = latest_date - _td(days=30)
            closest = min(
                rows,
                key=lambda r: abs(
                    (_dt.strptime(r['snapshot_date'], '%Y-%m-%d').date() - target).days
                ),
            )
            closest_value = closest['total_value']
            if closest_value and closest_value > 0:
                change_value = round(latest['total_value'] - closest_value, 2)
                change_pct = round((change_value / closest_value) * 100, 2)
        except Exception as e:
            logger.debug("Portfolio summary delta calc: %s", e)

    return jsonify({
        'latest': latest,
        'change_30d_value': change_value,
        'change_30d_pct': change_pct,
        'has_history': True,
    })


@app.route('/api/portfolio/capture', methods=['POST'])
def api_capture_portfolio_snapshot():
    """Manually capture a portfolio snapshot (for testing or ad-hoc runs).

    Body (optional): {"date": "YYYY-MM-DD"} — defaults to today.
    """
    payload = request.get_json(silent=True) or {}
    date_str = payload.get('date')
    try:
        row = portfolio_snapshot.capture_snapshot(snapshot_date=date_str)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    if not row:
        return jsonify({'error': 'capture_failed'}), 500
    # Counter BEFORE return (Pitfall 9 — code after `return` is dead).
    # Distinguishes dashboard "拍攝" button traffic from the nightly cron sweep.
    try:
        metrics.record_portfolio_capture(trigger='manual')
    except Exception:
        pass  # never let metrics failures break the user-facing endpoint
    return jsonify({'success': True, 'snapshot': row}), 201


# ── API: Portfolio Per-Ticker Breakdown (v3.4.6) ──────────────────────

@app.route('/api/portfolio/breakdown', methods=['GET'])
def api_portfolio_breakdown():
    """Return live per-ticker breakdown of the user's portfolio.

    Unlike /api/portfolio/snapshots (which reads historical rows), this
    endpoint recomputes from current prices on every call — useful for
    showing "right now" holdings with unrealized P&L per position.

    Response shape:
      {
        "total_value": 15409.38,
        "total_cost": 10300.00,
        "total_pnl": 5109.38,
        "pnl_pct": 49.61,
        "holdings_count": 3,
        "holdings": [
          {
            "symbol": "TSLA",
            "shares": 10.0,
            "cost_basis": 200.0,
            "current_price": 350.0,
            "market_value": 3500.0,
            "cost_value": 2000.0,
            "unrealized_pl": 1500.0,
            "unrealized_pl_pct": 75.0,
            "share_of_portfolio": 22.71
          },
          ...
        ],
        "timestamp": "2026-08-25T..."
      }

    Holdings are sorted descending by market_value. Tickers with no
    current price or zero shares are skipped (matches snapshot policy).
    """
    try:
        total_value, total_cost, holdings_count, breakdown = (
            portfolio_snapshot.compute_totals()
        )
    except Exception as e:
        logger.error("Portfolio breakdown compute failed: %s", e)
        from services.metrics import record_portfolio_breakdown
        try:
            record_portfolio_breakdown('error')
        except Exception:
            pass  # metrics are best-effort; never break the response
        return jsonify({'error': 'breakdown_compute_failed'}), 500

    # Augment with derived fields (P&L %, share of portfolio) and sort
    enriched = []
    for h in breakdown:
        market_value = h['market_value']
        cost_value = h['cost_value']
        unrealized_pl = h['unrealized_pl']
        # Avoid div-by-zero — both as numeric guards and as None signals
        unrealized_pl_pct = (
            round((unrealized_pl / cost_value) * 100, 2) if cost_value > 0 else 0.0
        )
        share_of_portfolio = (
            round((market_value / total_value) * 100, 2) if total_value > 0 else 0.0
        )
        enriched.append({
            **h,
            'unrealized_pl_pct': unrealized_pl_pct,
            'share_of_portfolio': share_of_portfolio,
        })

    # Sort by market value desc (biggest holdings first)
    enriched.sort(key=lambda x: x['market_value'], reverse=True)

    total_pnl = round(total_value - total_cost, 2)
    pnl_pct = round((total_pnl / total_cost) * 100, 2) if total_cost > 0 else 0.0

    from services.metrics import record_portfolio_breakdown
    status = 'ok' if holdings_count > 0 else 'empty'
    try:
        record_portfolio_breakdown(status)
    except Exception:
        pass  # metrics are best-effort; never break the response

    return jsonify({
        'total_value': total_value,
        'total_cost': total_cost,
        'total_pnl': total_pnl,
        'pnl_pct': pnl_pct,
        'holdings_count': holdings_count,
        'holdings': enriched,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }), 200


# ── API: Portfolio Snapshot CSV Export (v3.4.5) ────────────────────────

@app.route('/api/portfolio/snapshots/export.csv', methods=['GET'])
def api_export_portfolio_snapshots_csv():
    """Export daily portfolio snapshots as CSV.

    Columns: snapshot_date, total_value, total_cost, total_pnl, pnl_pct,
    holdings_count, captured_at.

    Query params:
        days — how many days of history (default 365, max 3650)
        fmt  — if 'tsv', emit tab-separated values (Excel-friendly paste)

    Returns 200 with text/csv body even when empty (header-only CSV is
    still valid — easier than 404 for an export endpoint).
    """
    import csv
    from io import StringIO

    try:
        days = min(int(request.args.get('days', 365)), 3650)
    except (TypeError, ValueError):
        days = 365

    fmt = (request.args.get('fmt') or 'csv').lower()
    delimiter = '\t' if fmt == 'tsv' else ','

    snapshots = models.list_snapshots(days=days)

    buf = StringIO()
    writer = csv.writer(buf, delimiter=delimiter)
    writer.writerow([
        'snapshot_date', 'total_value', 'total_cost', 'total_pnl',
        'pnl_pct', 'holdings_count', 'captured_at',
    ])
    for s in snapshots:
        # sqlite3.Row bracket-access is safe; only the writer needs stringy values
        writer.writerow([
            s['snapshot_date'],
            s['total_value'],
            s['total_cost'],
            s['total_pnl'],
            s['pnl_pct'],
            s['holdings_count'],
            s['captured_at'],
        ])

    text = buf.getvalue()
    ext = 'tsv' if fmt == 'tsv' else 'csv'
    # Don't include `; charset=utf-8` — Flask auto-appends it for text/* mimetypes
    # (otherwise we get `text/csv; charset=utf-8; charset=utf-8` in headers).
    mime = 'text/tab-separated-values' if fmt == 'tsv' else 'text/csv'
    filename = f"stocker-portfolio-{datetime.now().strftime('%Y%m%d-%H%M')}.{ext}"
    # Record the export BEFORE returning — code after `return` is dead
    # (see flask-api-integration-pitfalls pitfall 9).
    try:
        from services.metrics import record_portfolio_export
        record_portfolio_export(ext)
    except Exception:
        pass  # metrics are best-effort; never break the export
    return Response(
        text,
        mimetype=mime,
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


# ── API: Sectors ───────────────────────────────────────────────────────

@app.route('/api/sectors', methods=['GET'])
def api_get_sectors():
    """Return distinct sectors from active tickers."""
    sectors = models.get_sectors()
    return jsonify(sectors)


@app.route('/api/sectors/<sector>/reports', methods=['GET'])
def api_sector_reports(sector):
    """Return reports relevant to tickers in a given sector."""
    tickers = models.get_tickers_by_sector(sector)
    if not tickers:
        return jsonify([])

    symbols = [t['symbol'] for t in tickers]

    # Search reports whose title or content mentions any of the sector's ticker symbols
    from models import get_db
    conn = get_db()
    try:
        # Build WHERE clauses for each symbol
        conditions = []
        params = []
        for sym in symbols:
            conditions.append("(r.title LIKE ? OR r.content LIKE ?)")
            params.extend([f'%{sym}%', f'%{sym}%'])

        where_clause = " OR ".join(conditions)
        query = f"""
            SELECT DISTINCT r.* FROM reports r
            WHERE ({where_clause})
            AND r.category IN ('news', 'analyst_report', 'earnings')
            ORDER BY r.created_at DESC
            LIMIT 50
        """
        reports = conn.execute(query, params).fetchall()
        return jsonify([dict(r) for r in reports])
    finally:
        conn.close()


@app.route('/api/industry/<sector>/news', methods=['GET'])
def api_industry_news(sector):
    """Return industry-level news for a sector. (Stub — returns empty list for now.)"""
    return jsonify([])


@app.route('/api/industry/data', methods=['GET'])
def api_industry_data():
    """Return sector summary with ticker and report counts."""
    sectors = models.get_sectors()
    result = []
    for sector in sectors:
        tickers = models.get_tickers_by_sector(sector)
        ticker_count = len(tickers)
        # Count reports mentioning any ticker in this sector
        symbols = [t['symbol'] for t in tickers]
        report_count = 0
        if symbols:
            from models import get_db
            conn = get_db()
            try:
                conditions = []
                params = []
                for sym in symbols:
                    conditions.append("(r.title LIKE ? OR r.content LIKE ?)")
                    params.extend([f'%{sym}%', f'%{sym}%'])
                where_clause = " OR ".join(conditions)
                row = conn.execute(
                    f"SELECT COUNT(DISTINCT r.id) as cnt FROM reports r WHERE ({where_clause})",
                    params
                ).fetchone()
                report_count = row['cnt'] if row else 0
            finally:
                conn.close()
        result.append({
            'name': sector,
            'ticker_count': ticker_count,
            'report_count': report_count,
        })
    return jsonify({'sectors': result})


# ── API: Stock Data ────────────────────────────────────────────────────

@app.route('/api/stock/<symbol>/detail')
def api_stock_detail(symbol):
    """Get detailed stock information."""
    symbol = symbol.upper()
    try:
        info = fetch_stock_info(symbol)
        # Track data source
        src = info.get('source')
        if src:
            metrics.record_data_source(src)
        news = fetch_news(symbol)
        earnings = fetch_next_earnings(symbol)

        # Get ticker from DB for holdings
        ticker = models.get_ticker(symbol)
        shares_held = ticker['shares_held'] if ticker else 0
        cost_basis = ticker['cost_basis'] if ticker else 0

        # Get events from DB
        events = []
        if ticker:
            evts = models.get_events_by_ticker(ticker['id'])
            events = [dict(e) for e in evts]

        # Flatten the data for the template
        return jsonify({
            'symbol': symbol,
            'name': info.get('name', symbol),
            'price': info.get('price'),
            'change_pct': info.get('change_pct'),
            'market_cap': info.get('market_cap'),
            'pe_ratio': info.get('pe_ratio'),
            'eps': info.get('eps'),
            'high_52w': info.get('week52_high'),
            'low_52w': info.get('week52_low'),
            'news': news,
            'next_earnings': earnings,
            'shares_held': shares_held,
            'cost_basis': cost_basis,
            'events': events,
        })
    except Exception as e:
        logger.error(f"Error fetching detail for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stock/<symbol>/chart-data')
def api_stock_chart(symbol):
    """Get chart data with technical indicators."""
    symbol = symbol.upper()
    range_param = request.args.get('range', '3m')

    try:
        raw = fetch_chart_data(symbol, range_param)
        # Track data source
        src = raw.get('source')
        if src:
            metrics.record_data_source(src)
        # Flatten the structure for the template
        prices_dict = raw.get('prices', {})
        indicators = raw.get('indicators', {})
        # Support both dict (from multi_source) and legacy list
        if isinstance(prices_dict, list):
            # Legacy flat list — treat as close prices
            close_prices = prices_dict
        else:
            close_prices = prices_dict.get('close', [])
        return jsonify({
            'dates': raw.get('dates', []),
            'prices': close_prices,
            'prices_full': prices_dict,  # {open, high, low, close, volume} if available
            'ma5': indicators.get('ma5', []),
            'ma20': indicators.get('ma20', []),
            'ma60': indicators.get('ma60', []),
            'rsi': indicators.get('rsi14', []),
            'macd': indicators.get('macd', []),
            'macd_signal': indicators.get('macd_signal', []),
            'macd_hist': indicators.get('macd_hist', []),
            'source': raw.get('source'),  # data source indicator
        })
    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stock/<symbol>/refresh', methods=['POST'])
def api_refresh_stock(symbol):
    """Force refresh stock data."""
    symbol = symbol.upper()
    try:
        refresh_ticker_data(symbol)
        # User-initiated refresh must show fresh data, not cached snapshot
        cache_invalidate('tickers_with_prices', f'stock_info_{symbol}')
        # v3.4 — evaluate any price alerts against the new price
        try:
            from services.alert_checker import check_alerts_for_ticker
            triggered = check_alerts_for_ticker(symbol)
            if triggered:
                metrics.record_alert_triggered(len(triggered))
        except Exception as ae:
            logger.warning(f"alert check failed for {symbol}: {ae}")
            triggered = []
        return jsonify({'success': True, 'alerts_triggered': triggered})
    except Exception as e:
        logger.error(f"Error refreshing {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


# ── API: Reports ───────────────────────────────────────────────────────

@app.route('/api/reports', methods=['GET'])
def api_get_reports():
    """Get list of reports.

    Supports filtering via query params (all optional, AND-combined):
    - q:        free-text search on title + summary (LIKE %q%, case-insensitive)
    - category: exact-match category filter (e.g. earnings, industry)
    - source:   exact-match source filter (e.g. "SEC EDGAR")
    - ticker:   filter by ticker symbol derived from file_path basename prefix
    - limit:    max results (default 50, capped at 500)
    - include_total: if '1', include total_count in response (slower)

    Response shape:
    - No filters supplied: bare JSON array (preserves pre-v3.4.3 backward compat)
    - Filters supplied: dict {results, count, filters[, total_count]}

    v3.4.3 — adds search/filter capability on top of plain list.
    """
    limit = min(request.args.get('limit', 50, type=int), 500)
    q = request.args.get('q', '').strip() or None
    category = request.args.get('category', '').strip() or None
    source = request.args.get('source', '').strip() or None
    ticker = request.args.get('ticker', '').strip() or None
    include_total = request.args.get('include_total', '') == '1'

    has_filters = any([q, category, source, ticker])

    if not has_filters:
        # Plain list — preserves the pre-v3.4.3 response shape (bare array).
        reports = models.get_reports(limit=limit)
        return jsonify([dict(r) for r in reports])

    # Filtered search — new object response shape with metadata.
    reports = models.search_reports(
        query=q, category=category, source=source, ticker=ticker, limit=limit
    )

    payload = {
        'results': [dict(r) for r in reports],
        'count': len(reports),
        'filters': {
            'q': q,
            'category': category,
            'source': source,
            'ticker': ticker,
        },
    }

    if include_total:
        payload['total_count'] = models.count_search_results(
            query=q, category=category, source=source, ticker=ticker
        )

    # Record Prometheus counter — only count filtered searches.
    try:
        from services.metrics import record_report_search
        record_report_search(has_results=len(reports) > 0)
    except Exception:
        pass

    return jsonify(payload)


@app.route('/api/reports/<int:report_id>', methods=['GET'])
def api_get_report(report_id):
    """Get a single report."""
    report = models.get_report(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    return jsonify(dict(report))


@app.route('/api/reports/collect', methods=['POST'])
def api_collect_reports():
    """Trigger report collection."""
    try:
        result = collect_reports()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error collecting reports: {e}")
        return jsonify({'error': str(e)}), 500


# ── API: Events ────────────────────────────────────────────────────────

@app.route('/api/events/active', methods=['GET'])
def api_active_events():
    """Get active (non-dismissed) events."""
    events = models.get_active_events()
    return jsonify([dict(e) for e in events])


@app.route('/api/events/<int:event_id>/dismiss', methods=['POST'])
def api_dismiss_event(event_id):
    """Dismiss an event."""
    dismissed = models.dismiss_event(event_id)
    if not dismissed:
        return jsonify({'error': 'Event not found'}), 404
    return jsonify({'success': True})


@app.route('/api/events/calendar', methods=['GET'])
def api_events_calendar():
    """Get events for a given month. ?year=2026&month=6"""
    from datetime import datetime
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    events = models.get_events_for_month(year, month)
    return jsonify([dict(e) for e in events])


@app.route('/api/events/upcoming', methods=['GET'])
def api_events_upcoming():
    """Get upcoming events within N days. ?days=90"""
    days = request.args.get('days', 90, type=int)
    events = models.get_upcoming_events(days)
    return jsonify([dict(e) for e in events])


@app.route('/api/events/sync', methods=['POST'])
def api_events_sync():
    """Sync earnings/dividend dates from yfinance for all tracked tickers."""
    import yfinance as yf
    tickers = models.get_active_tickers()
    synced = 0
    errors = []
    for t in tickers:
        sym = t['symbol']
        try:
            stock = yf.Ticker(sym)
            # Earnings dates
            cal = stock.calendar
            if cal is not None and len(cal) > 0:
                if hasattr(cal, 'index'):
                    # DataFrame format
                    for idx in cal.index:
                        row = cal.loc[idx]
                        if 'Earnings Date' in cal.columns:
                            ed = row.get('Earnings Date')
                            if ed is not None:
                                date_str = str(ed)[:10]
                                models.upsert_event(t['id'], 'earnings', date_str, f'{sym} Earnings')
                                synced += 1
                elif isinstance(cal, dict):
                    # Dict format
                    for key in ['Earnings Date', 'earningsDate']:
                        ed = cal.get(key)
                        if ed:
                            if isinstance(ed, list) and len(ed) > 0:
                                date_str = str(ed[0])[:10]
                            else:
                                date_str = str(ed)[:10]
                            models.upsert_event(t['id'], 'earnings', date_str, f'{sym} Earnings')
                            synced += 1
                            break
            # Dividends
            divs = stock.dividends
            if divs is not None and len(divs) > 0:
                last_div = divs.index[-1]
                date_str = str(last_div)[:10]
                models.upsert_event(t['id'], 'dividend', date_str, f'{sym} Dividend')
                synced += 1
        except Exception as e:
            errors.append(f'{sym}: {str(e)[:80]}')
    return jsonify({'synced': synced, 'errors': errors})


@app.route('/events')
def events_page():
    """Calendar view of earnings/dividend events."""
    return render_template('events.html')


# ── API: Files ─────────────────────────────────────────────────────────

@app.route('/api/files', methods=['GET'])
def api_get_files():
    """Get file list."""
    category = request.args.get('category')
    files = models.get_files(category if category else None)
    return jsonify([dict(f) for f in files])


@app.route('/api/files/<int:file_id>/download', methods=['GET'])
def api_download_file(file_id):
    """Download a file."""
    file_record = models.get_file(file_id)
    if not file_record:
        return jsonify({'error': 'File not found'}), 404

    file_path = file_record['file_path']
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found on disk'}), 404

    return send_file(
        file_path,
        as_attachment=True,
        download_name=file_record['filename']
    )


# ── API: System ────────────────────────────────────────────────────────

@app.route('/api/init-data', methods=['POST'])
def api_init_data():
    """Initialize default tickers (for first-time setup)."""
    default_tickers = ['TSLA', 'NVDA', 'TE', 'GLW', 'MRVU', 'IBM']
    added = []
    errors = []

    for symbol in default_tickers:
        existing = models.get_ticker(symbol)
        if existing:
            continue
        try:
            info = fetch_stock_info(symbol)
            if info.get('name'):
                models.add_ticker(
                    symbol=symbol,
                    name=info.get('name', symbol),
                    sector=info.get('sector', '')
                )
                try:
                    refresh_ticker_data(symbol)
                except Exception:
                    pass
                added.append(symbol)
            else:
                errors.append(f'{symbol}: not found')
        except Exception as e:
            errors.append(f'{symbol}: {str(e)}')

    if added:
        cache_invalidate('tickers_with_prices')

    return jsonify({'added': added, 'errors': errors})


# ── API: Investment Banks ────────────────────────────────────────────

@app.route('/api/banks', methods=['GET'])
def api_get_banks():
    """Return all investment banks."""
    banks = models.get_all_investment_banks()
    return jsonify([dict(b) for b in banks])


@app.route('/api/banks/enabled', methods=['GET'])
def api_get_enabled_banks():
    """Return enabled investment banks."""
    banks = models.get_enabled_investment_banks()
    return jsonify([dict(b) for b in banks])


@app.route('/api/banks', methods=['POST'])
def api_add_bank():
    """Add a new investment bank."""
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400

    try:
        bank = models.add_investment_bank(
            name=name,
            short_name=data.get('short_name'),
            website_url=data.get('website_url'),
            report_url=data.get('report_url'),
            logo_url=data.get('logo_url'),
        )
        return jsonify(dict(bank)), 201
    except Exception as e:
        logger.error(f"Error adding bank {name}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/banks/<int:bank_id>', methods=['PUT'])
def api_update_bank(bank_id):
    """Update an investment bank."""
    data = request.get_json()
    bank = models.update_investment_bank(bank_id, data)
    if not bank:
        return jsonify({'error': 'Bank not found'}), 404
    return jsonify(dict(bank))


@app.route('/api/banks/<int:bank_id>', methods=['DELETE'])
def api_delete_bank(bank_id):
    """Delete an investment bank."""
    deleted = models.delete_investment_bank(bank_id)
    if not deleted:
        return jsonify({'error': 'Bank not found'}), 404
    return jsonify({'success': True})


@app.route('/api/banks/<int:bank_id>/toggle', methods=['POST'])
def api_toggle_bank(bank_id):
    """Toggle investment bank enabled status."""
    data = request.get_json()
    enabled = data.get('enabled', True)
    success = models.toggle_investment_bank(bank_id, enabled)
    if not success:
        return jsonify({'error': 'Bank not found'}), 404
    return jsonify({'success': True})


@app.route('/api/banks/<int:bank_id>/reports', methods=['GET'])
def api_get_bank_reports(bank_id):
    """Return reports for a specific bank."""
    reports = models.get_bank_reports(bank_id)
    return jsonify([dict(r) for r in reports])


@app.route('/api/banks/reports/all', methods=['GET'])
def api_get_all_bank_reports():
    """Return all bank reports."""
    reports = models.get_all_bank_reports()
    return jsonify([dict(r) for r in reports])


@app.route('/api/banks/reports/<int:report_id>/download', methods=['POST'])
def api_download_bank_report(report_id):
    """Download a bank report PDF."""
    from services.bank_report_scraper import download_report_pdf
    try:
        result = download_report_pdf(report_id)
        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/banks/reports/undownloaded', methods=['GET'])
def api_get_undownloaded_reports():
    """Return undownloaded bank reports."""
    reports = models.get_undownloaded_reports()
    return jsonify([dict(r) for r in reports])


@app.route('/api/banks/<int:bank_id>/check', methods=['POST'])
def api_check_bank(bank_id):
    """Manually trigger a check for new reports from a bank."""
    from services.bank_report_scraper import check_bank_for_reports
    try:
        result = check_bank_for_reports(bank_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error checking bank {bank_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/banks/check-all', methods=['POST'])
def api_check_all_banks():
    """Check all enabled banks for new reports."""
    from services.bank_report_scraper import check_all_banks
    try:
        result = check_all_banks()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error checking banks: {e}")
        return jsonify({'error': str(e)}), 500


# ── Page Routes: Investment Banks ────────────────────────────────────

@app.route('/banks')
def banks_page():
    """Investment banks watchlist page."""
    return render_template('banks.html')


@app.route('/sources')
def sources_page():
    """Custom data sources (JSONPath) management page."""
    return render_template('sources.html')


# ── Run ────────────────────────────────────────────────────────────────

# ── Smart refresh frequency (wealthlens-style) ──────────────────────
import pytz  # lightweight tz lib; falls back if not installed
try:
    from zoneinfo import ZoneInfo
    _HAS_ZONEINFO = True
except ImportError:
    _HAS_ZONEINFO = False

def get_refresh_interval():
    """
    Return the recommended polling interval in seconds, based on whether
    US markets are currently open.

    Rules:
      - NYSE regular hours (Mon-Fri 09:30-16:00 ET) → 3s (high frequency)
      - NYSE extended hours (04:00-20:00 ET)        → 15s
      - Weekday off-hours                          → 60s
      - Weekend                                    → 300s (5 min)
    """
    now_utc = datetime.utcnow()
    # Convert to ET (handles DST via zoneinfo if available)
    if _HAS_ZONEINFO:
        try:
            et = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York"))
        except Exception:
            et = now_utc - timedelta(hours=4)  # rough fallback
    else:
        et = now_utc - timedelta(hours=4)

    weekday = et.weekday()  # 0=Mon ... 6=Sun
    hour = et.hour
    minute = et.minute
    # 9:30 = 570 minutes
    minutes_of_day = hour * 60 + minute

    if weekday >= 5:  # Sat/Sun
        return 300
    if 9 * 60 + 30 <= minutes_of_day < 16 * 60:
        return 3
    if 4 * 60 <= minutes_of_day < 20 * 60:
        return 15
    return 60


# ── API: Search (autocomplete) ────────────────────────────────────────

@app.route('/api/search')
def api_search():
    """Search tickers via multi-source (popular list + Yahoo)."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'popular': multi_source.search_popular('', limit=10)})

    # First: local popular list (instant, no network)
    popular = multi_source.search_popular(q, limit=8)
    # Then: Yahoo search (network, may return intl symbols)
    yahoo = multi_source.search_symbols(q, limit=8)
    # Dedupe by symbol
    seen = {p['symbol'] for p in popular}
    for y in yahoo:
        if y['symbol'] not in seen:
            y['market'] = _infer_market(y['symbol'])
            popular.append(y)
            seen.add(y['symbol'])
    return jsonify({'popular': popular[:15], 'query': q})


def _infer_market(symbol):
    if symbol.endswith('.HK'):
        return 'HK'
    if symbol.endswith('.SS') or symbol.endswith('.SZ'):
        return 'CN'
    if symbol.endswith('.T'):
        return 'JP'
    if symbol.endswith('.TW'):
        return 'TW'
    if symbol.endswith('-USD') or symbol.endswith('-USDT'):
        return 'CRYPTO'
    return 'US'


# ── API: Ticker preview (before adding) ───────────────────────────────

@app.route('/api/tickers/preview', methods=['POST'])
def api_ticker_preview():
    """Preview ticker info before adding (price, name, sector)."""
    data = request.get_json() or {}
    symbol = (data.get('symbol') or '').strip().upper()
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    try:
        info = multi_source.get_current_price(symbol)
        # Cross-check with yfinance for name + sector
        try:
            yinfo = fetch_stock_info(symbol)
            info['name'] = yinfo.get('name') or info.get('name')
            info['sector'] = yinfo.get('sector')
            info['pe_ratio'] = yinfo.get('pe_ratio')
            info['eps'] = yinfo.get('eps')
            info['market_cap'] = yinfo.get('market_cap')
        except Exception:
            pass
        info['market'] = _infer_market(symbol)
        return jsonify(info)
    except Exception as e:
        logger.error("preview ticker %s: %s", symbol, e)
        return jsonify({'error': str(e)}), 500


# ── API: Custom data sources CRUD ─────────────────────────────────────

@app.route('/api/sources', methods=['GET'])
def api_list_sources():
    return jsonify(multi_source._get_custom_sources())


@app.route('/api/sources', methods=['POST'])
def api_add_source():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('url') or not data.get('date_path') or not data.get('price_path'):
        return jsonify({'error': 'name, url, date_path, price_path required'}), 400
    src = models.add_custom_source(data)
    return jsonify(dict(src)), 201


@app.route('/api/sources/<int:source_id>', methods=['PUT'])
def api_update_source(source_id):
    data = request.get_json() or {}
    src = models.update_custom_source(source_id, data)
    if not src:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(src))


@app.route('/api/sources/<int:source_id>', methods=['DELETE'])
def api_delete_source(source_id):
    ok = models.delete_custom_source(source_id)
    if not ok:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'success': True})


# ── API: Refresh-interval hint ────────────────────────────────────────

@app.route('/api/refresh-interval')
def api_refresh_interval():
    """Returns the current recommended polling interval (seconds)."""
    interval = get_refresh_interval()
    # Explain why
    now_utc = datetime.utcnow()
    if _HAS_ZONEINFO:
        try:
            et = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York"))
        except Exception:
            et = now_utc - timedelta(hours=4)
    else:
        et = now_utc - timedelta(hours=4)
    weekday = et.weekday()
    minutes_of_day = et.hour * 60 + et.minute
    if weekday >= 5:
        reason = "weekend"
    elif 9*60+30 <= minutes_of_day < 16*60:
        reason = "us_market_open"
    elif 4*60 <= minutes_of_day < 20*60:
        reason = "us_extended_hours"
    else:
        reason = "us_off_hours"
    return jsonify({'interval': interval, 'reason': reason, 'et_time': et.strftime('%H:%M ET')})


# ── API: Nightly historical price refresh ──────────────────────────────

@app.route('/api/nightly-refresh', methods=['POST'])
def api_nightly_refresh():
    """Trigger 5-year historical price refresh for all tickers (manual)."""
    try:
        from services.nightly_refresher import refresh_all_tickers
        period = request.json.get('period', '5y') if request.is_json else '5y'
        result = refresh_all_tickers(period=period, sleep_between=1.0)
        metrics.record_nightly_refresh('success')
        return jsonify(result)
    except Exception as e:
        logger.error(f"Nightly refresh failed: {e}")
        metrics.record_nightly_refresh('failure')
        return jsonify({'error': str(e)}), 500


# ── API: Watchlist Groups (v3.3) ────────────────────────────────────────

@app.route('/api/watchlist-groups', methods=['GET'])
def api_get_watchlist_groups():
    """List all watchlist groups with ticker count."""
    try:
        groups = models.get_all_watchlist_groups()
        result = []
        for g in groups:
            gd = dict(g)
            gd['tickers'] = [dict(t) for t in models.get_watchlist_group_tickers(g['id'])]
            result.append(gd)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist-groups', methods=['POST'])
def api_create_watchlist_group():
    """Create a new watchlist group."""
    try:
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Name required'}), 400
        group = models.create_watchlist_group(
            name=name,
            description=data.get('description'),
            color=data.get('color', '#4fc3f7'),
            sort_order=data.get('sort_order', 0),
        )
        return jsonify(dict(group)), 201
    except Exception as e:
        if 'UNIQUE' in str(e):
            return jsonify({'error': 'Group name already exists'}), 409
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist-groups/<int:group_id>', methods=['PUT'])
def api_update_watchlist_group(group_id):
    """Update a watchlist group."""
    try:
        data = request.get_json() or {}
        group = models.update_watchlist_group(group_id, data)
        if group is None:
            return jsonify({'error': 'Group not found'}), 404
        return jsonify(dict(group))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist-groups/<int:group_id>', methods=['DELETE'])
def api_delete_watchlist_group(group_id):
    """Delete a watchlist group."""
    try:
        models.delete_watchlist_group(group_id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist-groups/<int:group_id>/tickers', methods=['GET'])
def api_get_group_tickers(group_id):
    """List tickers in a group."""
    try:
        tickers = models.get_watchlist_group_tickers(group_id)
        return jsonify([dict(t) for t in tickers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist-groups/<int:group_id>/tickers', methods=['POST'])
def api_add_ticker_to_group(group_id):
    """Add a ticker to a group."""
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', '').strip().upper()
        if not symbol:
            return jsonify({'error': 'symbol required'}), 400
        ticker = models.get_ticker(symbol)
        if ticker is None:
            return jsonify({'error': f'Ticker {symbol} not found'}), 404
        models.add_ticker_to_group(group_id, ticker['id'])
        return jsonify({'ok': True, 'symbol': symbol})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist-groups/<int:group_id>/tickers/<symbol>', methods=['DELETE'])
def api_remove_ticker_from_group(group_id, symbol):
    """Remove a ticker from a group."""
    try:
        ticker = models.get_ticker(symbol.upper())
        if ticker is None:
            return jsonify({'error': f'Ticker {symbol} not found'}), 404
        models.remove_ticker_from_group(group_id, ticker['id'])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/watchlists')
def watchlists_page():
    """Watchlist groups management page."""
    return render_template('watchlists.html')


# ── API: Price Alerts (v3.4) ───────────────────────────────────────────

@app.route('/api/alerts', methods=['GET'])
def api_list_alerts():
    """List all alerts (or just enabled if ?enabled=1)."""
    enabled_only = request.args.get('enabled', '0') == '1'
    sym_filter = request.args.get('symbol', '').strip().upper()
    if sym_filter:
        ticker = models.get_ticker(sym_filter)
        if not ticker:
            return jsonify([])
        rows = models.get_alerts(ticker_id=ticker['id'], enabled_only=enabled_only)
    else:
        rows = models.get_alerts(enabled_only=enabled_only)
    return jsonify([dict(r) for r in rows])


@app.route('/api/alerts', methods=['POST'])
def api_create_alert():
    """Create a new price alert.

    Body: {symbol, threshold_type ('high'|'low'), threshold_price, note?}
    """
    data = request.get_json(silent=True) or {}
    symbol = (data.get('symbol') or '').strip().upper()
    threshold_type = (data.get('threshold_type') or '').strip().lower()
    threshold_price = data.get('threshold_price')
    note = data.get('note')

    if not symbol:
        return jsonify({'error': 'symbol required'}), 400
    if threshold_type not in ('high', 'low'):
        return jsonify({'error': "threshold_type must be 'high' or 'low'"}), 400
    try:
        threshold_price = float(threshold_price)
    except (TypeError, ValueError):
        return jsonify({'error': 'threshold_price must be a number'}), 400
    if threshold_price <= 0:
        return jsonify({'error': 'threshold_price must be > 0'}), 400

    ticker = models.get_ticker(symbol)
    if not ticker:
        return jsonify({'error': f'symbol {symbol} not in tickers'}), 404
    if ticker['archived']:
        return jsonify({'error': f'symbol {symbol} is archived'}), 400

    try:
        row = models.add_alert(
            ticker_id=ticker['id'],
            threshold_type=threshold_type,
            threshold_price=threshold_price,
            note=note,
        )
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    return jsonify(row), 201


@app.route('/api/alerts/<int:alert_id>', methods=['PUT'])
def api_update_alert(alert_id):
    """Update alert fields (enabled, threshold_price, threshold_type, note)."""
    data = request.get_json(silent=True) or {}
    try:
        row = models.update_alert(alert_id, **data)
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    if not row:
        return jsonify({'error': 'alert not found'}), 404
    return jsonify(row)


@app.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
def api_delete_alert(alert_id):
    """Hard-delete an alert."""
    deleted = models.delete_alert(alert_id)
    if not deleted:
        return jsonify({'error': 'alert not found'}), 404
    return jsonify({'success': True})


@app.route('/api/alerts/<int:alert_id>/rearm', methods=['POST'])
def api_rearm_alert(alert_id):
    """Re-enable a triggered alert so it can fire again."""
    row = models.update_alert(alert_id, enabled=1)
    if not row:
        return jsonify({'error': 'alert not found'}), 404
    return jsonify(row)


@app.route('/api/alerts/check', methods=['POST'])
def api_check_alerts():
    """Manual sweep: re-check every enabled alert across all tickers.

    Body (optional): {symbol: 'TSLA'} to limit to one ticker.
    Returns: list of triggered alerts.
    """
    from services.alert_checker import check_alerts_for_ticker, check_alerts_all
    data = request.get_json(silent=True) or {}
    symbol = (data.get('symbol') or '').strip().upper()
    try:
        triggered = check_alerts_for_ticker(symbol) if symbol else check_alerts_all()
    except Exception as e:
        logger.error(f"manual alert check failed: {e}")
        return jsonify({'error': str(e)}), 500
    if triggered:
        metrics.record_alert_triggered(len(triggered))
    return jsonify({'triggered': triggered, 'count': len(triggered)})


@app.route('/alerts')
def alerts_page():
    """Price alerts management page."""
    return render_template('alerts.html')


# ── API: SSE stream of live prices (for future SSE client) ────────────

@app.route('/api/stream/tickers')
def api_stream_tickers():
    """Server-Sent Events stream of current prices for tracked tickers."""
    def generate():
        metrics.sse_connect()
        # Send one snapshot then yield updates
        try:
            while True:
                tickers = models.get_all_tickers()
                snapshot = []
                for t in tickers:
                    try:
                        info = multi_source.get_current_price(t['symbol'])
                        snapshot.append({
                            'symbol': t['symbol'],
                            'price': info.get('price'),
                            'change_pct': info.get('change_pct'),
                            'source': info.get('source', 'unknown'),
                            'ts': datetime.utcnow().isoformat(),
                        })
                        # Track data source usage
                        src = info.get('source', 'unknown')
                        if src:
                            metrics.record_data_source(src)
                    except Exception as exc:
                        logger.debug("SSE snapshot %s: %s", t['symbol'], exc)
                yield f"data: {json.dumps(snapshot)}\n\n"
                interval = get_refresh_interval()
                time.sleep(interval)
        except GeneratorExit:
            metrics.sse_disconnect()
            return
    return app.response_class(generate(), mimetype='text/event-stream')


@app.route('/metrics')
def prometheus_metrics():
    """Prometheus metrics endpoint."""
    return metrics.metrics_endpoint()


@app.route('/health')
def health():
    """Liveness + readiness probe for load balancers and monitoring."""
    return metrics.health_check()


@app.route('/system')
def system_page():
    """System / admin dashboard — surfaces /api/metrics/summary + /health on a page."""
    return render_template('system.html')


@app.route('/api/metrics/summary')
def api_metrics_summary():
    """Human-readable JSON summary of business metrics (for dashboards)."""
    return metrics.metrics_summary()


if __name__ == '__main__':
    # Initialize data directories
    for cat in ['earnings', 'analyst_report', 'news', 'sec_filing']:
        (FILES_DIR / cat).mkdir(parents=True, exist_ok=True)

    app.run(host='0.0.0.0', port=5000, debug=True)
