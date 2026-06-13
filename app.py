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
import tsdb
from services.stock_data import (
    fetch_stock_info, fetch_historical_prices, fetch_chart_data,
    fetch_news, fetch_next_earnings, refresh_ticker_data
)
from services.report_collector import collect_reports, collect_ticker_reports
from services.ai_analyzer import analyze_report
from services import multi_source

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


# ── API: SSE stream of live prices (for future SSE client) ────────────

@app.route('/api/stream/tickers')
def api_stream_tickers():
    """Server-Sent Events stream of current prices for tracked tickers."""
    def generate():
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
                    except Exception as exc:
                        logger.debug("SSE snapshot %s: %s", t['symbol'], exc)
                yield f"data: {json.dumps(snapshot)}\n\n"
                interval = get_refresh_interval()
                time.sleep(interval)
        except GeneratorExit:
            return
    return app.response_class(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    # Initialize data directories
    for cat in ['earnings', 'analyst_report', 'news', 'sec_filing']:
        (FILES_DIR / cat).mkdir(parents=True, exist_ok=True)

    app.run(host='0.0.0.0', port=5000, debug=True)
