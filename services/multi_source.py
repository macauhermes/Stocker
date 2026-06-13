"""
Multi-source data service with fallback chain.

Borrowed design from wealthlens:
  Primary (yfinance) → Backup (Yahoo direct) → Stooq → CoinGecko → Custom JSONPath

For any given symbol, we try each source in order and return the first
that yields data. Custom JSONPath sources (registered in DB) take
precedence and are tried first.

All sources are simple HTTP — no extra Python dependencies.
"""
import os
import re
import sys
import json
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.path.expanduser("~/repos/Stocker/data"))
CUSTOM_DB = DATA_DIR / "stocker.db"

CUSTOM_HEADERS = {
    "User-Agent": "Stocker/1.0 (macauhermes@gmail.com)",
    "Accept": "application/json,text/csv",
    "Accept-Encoding": "gzip, deflate",
}

# Yahoo Finance direct query (works for stocks + .HK + .SS etc)
YAHOO_QUERY_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search?q={q}&quotesCount=10"
STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}&i=d"
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days={days}&interval=daily"

# Simple JSONPath evaluator (subset: $.a.b[*].c, ['key'], [N])
def _eval_path(data, path):
    """
    Tiny JSONPath evaluator.
    Supports:  $.a.b.c, $.a[0].b, $.a[*].b, $['key with spaces']
    """
    if not path or path in ("$", "."):
        return data
    p = path.strip().lstrip("$").lstrip(".")
    if not p:
        return data
    tokens = re.findall(r"[^.\[\]'\"']+|\[[']\s*([^']*?)\s*[']\]", p)
    tokens = [t[0] if isinstance(t, tuple) else t for t in tokens]
    cur = data
    for tok in tokens:
        if cur is None:
            return None
        m = re.match(r"^\[(\*|\d+)\]$", tok)
        if m:
            idx = m.group(1)
            if isinstance(cur, list):
                cur = cur if idx == "*" else (cur[int(idx)] if int(idx) < len(cur) else None)
            else:
                return None
        else:
            if isinstance(cur, dict):
                cur = cur.get(tok)
            elif isinstance(cur, list):
                try:
                    cur = cur[int(tok)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
    return cur


def _detect_date(s):
    """Best-effort date detection: ISO, Unix seconds, Unix ms, MM/DD/YYYY."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        # Unix timestamp
        if s > 1e12:  # ms
            return datetime.utcfromtimestamp(s / 1000).strftime("%Y-%m-%d")
        if s > 1e9:   # seconds
            return datetime.utcfromtimestamp(s).strftime("%Y-%m-%d")
        return None
    s = str(s).strip()
    # ISO
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:len(fmt) + 5 if "T" in fmt else 10], fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    # MM/DD/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(1)), int(m.group(2))).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


# ──────────────────────────────────────────────────────────────────────
# Source 1: yfinance (delegate to existing service)
# ──────────────────────────────────────────────────────────────────────

def from_yfinance(symbol, period="1y"):
    """Direct yfinance call — bypasses fetch_historical_prices to avoid recursion."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, auto_adjust=True)
        if df.empty:
            return None
        rows = []
        for idx, row in df.iterrows():
            rows.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": _round_safe(row.get("Open")),
                "high": _round_safe(row.get("High")),
                "low": _round_safe(row.get("Low")),
                "close": _round_safe(row.get("Close")),
                "volume": int(row.get("Volume", 0)) if pd.notna(row.get("Volume")) else 0,
            })
        if rows:
            return {"source": "yfinance", "rows": rows}
    except Exception as exc:
        logger.debug("yfinance source for %s failed: %s", symbol, exc)
    return None


# ──────────────────────────────────────────────────────────────────────
# Source 2: Yahoo Finance direct
# ──────────────────────────────────────────────────────────────────────

def from_yahoo_direct(symbol, range_="1y"):
    """
    Direct call to Yahoo Finance chart API.
    Works for US, .HK, .SS, .SZ, .T, .TW and crypto (-USD suffix).
    """
    try:
        url = YAHOO_QUERY_URL.format(symbol=symbol)
        params = {"range": range_, "interval": "1d", "events": "history"}
        resp = requests.get(url, params=params, headers=CUSTOM_HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        result = data.get("chart", {}).get("result")
        if not result:
            return None
        r0 = result[0]
        ts = r0.get("timestamp", [])
        quote = (r0.get("indicators", {}).get("quote") or [{}])[0]
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        vols = quote.get("volume", [])
        rows = []
        for i, t in enumerate(ts):
            if closes[i] is None:
                continue
            d = datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
            rows.append({
                "date": d,
                "open": round(opens[i], 2) if opens[i] is not None else None,
                "high": round(highs[i], 2) if highs[i] is not None else None,
                "low": round(lows[i], 2) if lows[i] is not None else None,
                "close": round(closes[i], 2),
                "volume": int(vols[i]) if vols[i] is not None else 0,
            })
        if rows:
            return {"source": "yahoo_direct", "rows": rows}
    except Exception as exc:
        logger.debug("yahoo_direct source for %s failed: %s", symbol, exc)
    return None


# ──────────────────────────────────────────────────────────────────────
# Source 3: Stooq (free, US/HK/JP, splits already adjusted)
# ──────────────────────────────────────────────────────────────────────

def from_stooq(symbol):
    """
    Stooq CSV endpoint. Symbol convention: aapl.us for US, 0700.hk for HK,
    7203.jp for JP. We translate from yfinance convention.
    """
    try:
        # Translate: AAPL → aapl.us, 0700.HK → 0700.hk, 7203.T → 7203.jp
        s = symbol.lower()
        if s.endswith(".us"):
            sym = s
        elif s.endswith(".hk"):
            sym = s
        elif s.endswith(".t"):
            sym = s.replace(".t", ".jp")
        elif s.endswith("-usd"):
            sym = s.replace("-usd", ".us")  # crypto fallback, may not work
        else:
            sym = s + ".us"
        resp = requests.get(STOOQ_URL.format(symbol=sym),
                            headers=CUSTOM_HEADERS, timeout=15)
        if resp.status_code != 200 or len(resp.text) < 50:
            return None
        lines = resp.text.strip().split("\n")
        if len(lines) < 2 or "Date" not in lines[0]:
            return None
        rows = []
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) < 6:
                continue
            try:
                rows.append({
                    "date": parts[0],
                    "open": float(parts[1]),
                    "high": float(parts[2]),
                    "low": float(parts[3]),
                    "close": float(parts[4]),
                    "volume": int(parts[5]) if parts[5] else 0,
                })
            except (ValueError, IndexError):
                continue
        if rows:
            return {"source": "stooq", "rows": rows}
    except Exception as exc:
        logger.debug("stooq source for %s failed: %s", symbol, exc)
    return None


# ──────────────────────────────────────────────────────────────────────
# Source 4: CoinGecko (crypto fallback for BTC-USD, ETH-USD etc)
# ──────────────────────────────────────────────────────────────────────

_COINGECKO_IDS = {
    "btc-usd": "bitcoin",
    "eth-usd": "ethereum",
    "sol-usd": "solana",
    "doge-usd": "dogecoin",
    "xrp-usd": "ripple",
    "ada-usd": "cardano",
}

def from_coingecko(symbol, days=365):
    try:
        s = symbol.lower()
        coin_id = _COINGECKO_IDS.get(s)
        if not coin_id:
            return None
        resp = requests.get(COINGECKO_URL.format(id=coin_id, days=days),
                            headers=CUSTOM_HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        rows = []
        for i, (ts_ms, price) in enumerate(prices):
            d = datetime.utcfromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d")
            vol = volumes[i][1] if i < len(volumes) else 0
            rows.append({
                "date": d,
                "open": round(price, 2),  # CoinGecko only gives single price
                "high": round(price, 2),
                "low": round(price, 2),
                "close": round(price, 2),
                "volume": int(vol),
            })
        if rows:
            return {"source": "coingecko", "rows": rows}
    except Exception as exc:
        logger.debug("coingecko source for %s failed: %s", symbol, exc)
    return None


# ──────────────────────────────────────────────────────────────────────
# Source 5: Custom JSONPath (DB-stored, user-defined)
# ──────────────────────────────────────────────────────────────────────

def _get_custom_sources():
    """Load user-defined data sources from the DB."""
    try:
        conn = sqlite3.connect(str(CUSTOM_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM custom_data_sources WHERE enabled=1 ORDER BY priority"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.debug("Failed to load custom sources: %s", exc)
        return []


def from_custom_source(source, symbol):
    """
    Fetch data from a user-defined JSONPath source.
    source = {url, date_path, price_path, [high_path, low_path, open_path, volume_path], symbol_match}
    """
    try:
        # Substitute {symbol} in URL
        url = source["url"].format(symbol=symbol)
        resp = requests.get(url, headers=CUSTOM_HEADERS, timeout=20)
        if resp.status_code != 200:
            return None
        data = resp.json()
        # If symbol_match is set, filter to records that match
        items = _eval_path(data, source["date_path"])
        if not isinstance(items, list):
            return None
        # Each item should have date and price
        rows = []
        for item in items:
            if not isinstance(item, dict):
                continue
            # If symbol_match path given, skip mismatches
            if source.get("symbol_match"):
                sym_val = _eval_path(item, source["symbol_match"])
                if sym_val and str(sym_val).upper() != symbol.upper():
                    continue
            d = _eval_path(item, source["date_path"].rsplit(".", 1)[0] + ".[*]." + source["date_path"].rsplit(".", 1)[1] if False else source["date_path"])
            # Simpler: re-evaluate relative to item
            # date_path was evaluated on full data; for per-item we use the LAST component
            d_simple = item.get(source["date_path"].rsplit(".", 1)[-1].strip("[]'\""))
            if not d_simple:
                d_simple = _detect_date(d) if d else None
            if not d_simple:
                d_simple = _detect_date(d)
            if not d_simple:
                continue
            close_v = _eval_path(item, source["price_path"])
            if close_v is None:
                continue
            row = {
                "date": d_simple,
                "close": round(float(close_v), 4),
                "open": round(float(_eval_path(item, source["open_path"]) or close_v), 4) if source.get("open_path") else round(float(close_v), 4),
                "high": round(float(_eval_path(item, source["high_path"]) or close_v), 4) if source.get("high_path") else round(float(close_v), 4),
                "low": round(float(_eval_path(item, source["low_path"]) or close_v), 4) if source.get("low_path") else round(float(close_v), 4),
                "volume": int(_eval_path(item, source["volume_path"]) or 0) if source.get("volume_path") else 0,
            }
            rows.append(row)
        if rows:
            return {"source": f"custom:{source['name']}", "rows": rows}
    except Exception as exc:
        logger.debug("custom source %s for %s failed: %s", source.get("name"), symbol, exc)
    return None


# ──────────────────────────────────────────────────────────────────────
# Public API: Multi-source fetch with fallback chain
# ──────────────────────────────────────────────────────────────────────

def fetch_with_fallback(symbol, period="1y"):
    """
    Try sources in priority order, return first success.
    Order: custom (if match) → yfinance → yahoo_direct → stooq → coingecko

    Returns: {"source": "yfinance", "rows": [...]} or None
    """
    # Map period to yfinance/yahoo range string
    range_map = {"1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y",
                 "5d": "5d", "1m": "1mo", "3m": "3mo", "6m": "6mo"}
    yf_period = range_map.get(period, period)
    days_map = {"5d": 7, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}
    days = days_map.get(yf_period, 365)

    # 0. Custom sources first
    for src in _get_custom_sources():
        result = from_custom_source(src, symbol)
        if result:
            logger.info("fetch_with_fallback(%s) -> custom:%s", symbol, src["name"])
            return result

    # 1. yfinance (handles most US stocks and many intl)
    result = from_yfinance(symbol, yf_period)
    if result:
        return result

    # 2. Yahoo direct (backup when yfinance lib fails)
    result = from_yahoo_direct(symbol, yf_period)
    if result:
        logger.info("fetch_with_fallback(%s) -> yahoo_direct fallback", symbol)
        return result

    # 3. Stooq (for US/HK/JP)
    result = from_stooq(symbol)
    if result:
        logger.info("fetch_with_fallback(%s) -> stooq fallback", symbol)
        return result

    # 4. CoinGecko (for crypto)
    result = from_coingecko(symbol, days)
    if result:
        logger.info("fetch_with_fallback(%s) -> coingecko fallback", symbol)
        return result

    logger.error("fetch_with_fallback(%s) — all sources failed", symbol)
    return None


def get_current_price(symbol):
    """
    Get real-time-ish price using the same fallback chain.
    """
    # Try yfinance first (has real-time via yf.Ticker)
    try:
        from services.stock_data import fetch_stock_info
        info = fetch_stock_info(symbol)
        if info.get("price"):
            return info
    except Exception:
        pass

    # Yahoo direct for last price
    try:
        url = YAHOO_QUERY_URL.format(symbol=symbol)
        resp = requests.get(url, params={"range": "1d", "interval": "1m"},
                            headers=CUSTOM_HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("chart", {}).get("result")
            if result:
                meta = result[0].get("meta", {})
                price = meta.get("regularMarketPrice")
                prev = meta.get("chartPreviousClose") or meta.get("previousClose")
                change_pct = None
                if price and prev:
                    change_pct = round((price - prev) / prev * 100, 2)
                return {
                    "symbol": symbol.upper(),
                    "price": round(price, 2) if price else None,
                    "change_pct": change_pct,
                    "name": meta.get("longName") or meta.get("shortName", symbol),
                    "source": "yahoo_direct",
                }
    except Exception as exc:
        logger.debug("yahoo_direct price for %s failed: %s", symbol, exc)

    return {"symbol": symbol.upper(), "price": None, "change_pct": None, "name": symbol}


def search_symbols(query, limit=10):
    """
    Search Yahoo Finance for matching symbols.
    Returns list of {symbol, name, exchange, type}.
    """
    try:
        url = YAHOO_SEARCH_URL.format(q=query)
        resp = requests.get(url, params={"quotesCount": limit, "newsCount": 0},
                            headers=CUSTOM_HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        results = []
        for q in data.get("quotes", []):
            results.append({
                "symbol": q.get("symbol", ""),
                "name": q.get("longname") or q.get("shortname", ""),
                "exchange": q.get("exchange", ""),
                "type": q.get("quoteType", ""),
                "currency": q.get("currency", "USD"),
            })
        return results
    except Exception as exc:
        logger.debug("search_symbols(%s) failed: %s", query, exc)
        return []


# Built-in popular list for instant autocomplete
POPULAR_TICKERS = [
    # 美股大型
    {"symbol": "AAPL", "name": "Apple Inc.", "market": "US", "currency": "USD"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "market": "US", "currency": "USD"},
    {"symbol": "GOOGL", "name": "Alphabet Inc. Class A", "market": "US", "currency": "USD"},
    {"symbol": "AMZN", "name": "Amazon.com, Inc.", "market": "US", "currency": "USD"},
    {"symbol": "META", "name": "Meta Platforms, Inc.", "market": "US", "currency": "USD"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "market": "US", "currency": "USD"},
    {"symbol": "TSLA", "name": "Tesla, Inc.", "market": "US", "currency": "USD"},
    {"symbol": "BRK.B", "name": "Berkshire Hathaway Inc.", "market": "US", "currency": "USD"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "market": "US", "currency": "USD"},
    {"symbol": "V", "name": "Visa Inc.", "market": "US", "currency": "USD"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "market": "US", "currency": "USD"},
    {"symbol": "WMT", "name": "Walmart Inc.", "market": "US", "currency": "USD"},
    {"symbol": "PG", "name": "Procter & Gamble", "market": "US", "currency": "USD"},
    {"symbol": "MA", "name": "Mastercard Incorporated", "market": "US", "currency": "USD"},
    {"symbol": "HD", "name": "Home Depot, Inc.", "market": "US", "currency": "USD"},
    {"symbol": "DIS", "name": "Walt Disney Company", "market": "US", "currency": "USD"},
    {"symbol": "BAC", "name": "Bank of America", "market": "US", "currency": "USD"},
    {"symbol": "NFLX", "name": "Netflix, Inc.", "market": "US", "currency": "USD"},
    # SpaceX
    {"symbol": "SPCX", "name": "Space Exploration Technologies Corp. (SpaceX)", "market": "US", "currency": "USD"},
    # 港股
    {"symbol": "0700.HK", "name": "騰訊控股 Tencent", "market": "HK", "currency": "HKD"},
    {"symbol": "9988.HK", "name": "阿里巴巴 Alibaba", "market": "HK", "currency": "HKD"},
    {"symbol": "3690.HK", "name": "美團 Meituan", "market": "HK", "currency": "HKD"},
    {"symbol": "1810.HK", "name": "小米 Xiaomi", "market": "HK", "currency": "HKD"},
    # A股
    {"symbol": "600519.SS", "name": "貴州茅台 Kweichow Moutai", "market": "CN", "currency": "CNY"},
    {"symbol": "000858.SZ", "name": "五糧液 Wuliangye", "market": "CN", "currency": "CNY"},
    {"symbol": "601318.SS", "name": "中國平安 Ping An", "market": "CN", "currency": "CNY"},
    # 日股
    {"symbol": "7203.T", "name": "豐田汽車 Toyota", "market": "JP", "currency": "JPY"},
    {"symbol": "6758.T", "name": "索尼 Sony", "market": "JP", "currency": "JPY"},
    # 台股
    {"symbol": "2330.TW", "name": "台積電 TSMC", "market": "TW", "currency": "TWD"},
    {"symbol": "2454.TW", "name": "聯發科 MediaTek", "market": "TW", "currency": "TWD"},
    # 加密貨幣
    {"symbol": "BTC-USD", "name": "Bitcoin 比特幣", "market": "CRYPTO", "currency": "USD"},
    {"symbol": "ETH-USD", "name": "Ethereum 以太幣", "market": "CRYPTO", "currency": "USD"},
    {"symbol": "SOL-USD", "name": "Solana", "market": "CRYPTO", "currency": "USD"},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "market": "CRYPTO", "currency": "USD"},
]


def search_popular(query, limit=8):
    """Filter POPULAR_TICKERS by query (case-insensitive, name or symbol)."""
    q = query.strip().lower()
    if not q:
        return POPULAR_TICKERS[:limit]
    matches = []
    for t in POPULAR_TICKERS:
        if q in t["symbol"].lower() or q in t["name"].lower():
            matches.append(t)
    return matches[:limit]
