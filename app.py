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
    Flask, render_template, jsonify, request, send_file, redirect, url_for
)

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import models
from services.stock_data import (
    fetch_stock_info, fetch_historical_prices, fetch_chart_data,
    fetch_news, fetch_next_earnings, refresh_ticker_data
)
from services.report_collector import collect_reports, collect_ticker_reports
from services.ai_analyzer import analyze_report

# ── App Setup ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            return val
    return None

def cache_set(key, value):
    """Store value in cache."""
    _cache[key] = (value, datetime.now())


# ── Initialize DB on startup ──────────────────────────────────────────
models.init_db()


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

    return jsonify(dict(ticker))


@app.route('/api/tickers/<symbol>', methods=['DELETE'])
def api_delete_ticker(symbol):
    """Archive a tracked ticker (soft delete)."""
    deleted = models.archive_ticker(symbol.upper())
    if not deleted:
        return jsonify({'error': f'Ticker {symbol} not found'}), 404
    return jsonify({'success': True, 'action': 'archived'})


@app.route('/api/tickers/<symbol>/restore', methods=['POST'])
def api_restore_ticker(symbol):
    """Restore an archived ticker."""
    restored = models.restore_ticker(symbol.upper())
    if not restored:
        return jsonify({'error': f'Archived ticker {symbol} not found'}), 404
    return jsonify({'success': True, 'action': 'restored'})


@app.route('/api/tickers/archived', methods=['GET'])
def api_get_archived_tickers():
    """Return all archived tickers."""
    tickers = models.get_archived_tickers()
    return jsonify([dict(t) for t in tickers])


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
        # Flatten the structure for the template
        prices_dict = raw.get('prices', {})
        indicators = raw.get('indicators', {})
        return jsonify({
            'dates': raw.get('dates', []),
            'prices': prices_dict.get('close', []),
            'ma5': indicators.get('ma5', []),
            'ma20': indicators.get('ma20', []),
            'ma60': indicators.get('ma60', []),
            'rsi': indicators.get('rsi14', []),
            'macd': indicators.get('macd', []),
            'macd_signal': indicators.get('macd_signal', []),
            'macd_hist': indicators.get('macd_hist', []),
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
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error refreshing {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


# ── API: Reports ───────────────────────────────────────────────────────

@app.route('/api/reports', methods=['GET'])
def api_get_reports():
    """Get list of reports."""
    limit = request.args.get('limit', 50, type=int)
    reports = models.get_reports(limit)
    return jsonify([dict(r) for r in reports])


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

    return jsonify({'added': added, 'errors': errors})


# ── Run ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Initialize data directories
    for cat in ['earnings', 'analyst_report', 'news', 'sec_filing']:
        (FILES_DIR / cat).mkdir(parents=True, exist_ok=True)

    app.run(host='0.0.0.0', port=5000, debug=True)
