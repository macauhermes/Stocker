"""
Stock data service — pulls data from yfinance, caches to SQLite via models.
"""

import sys
import os
import logging
from datetime import datetime, date, timedelta

import pandas as pd
import yfinance as yf

# ── Ensure we can import models.py from the project root ──────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import (
    get_db,
    get_ticker_by_symbol,
    create_ticker,
    get_events_by_ticker,
    create_event,
)
import tsdb

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _round_safe(value, decimals=2):
    """Round a value if it's numeric, otherwise return None."""
    if value is None:
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


# ──────────────────────────────────────────────────────────────────────
# Technical indicator helpers
# ──────────────────────────────────────────────────────────────────────

def calculate_indicators(prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute MA5, MA20, MA60, RSI14, MACD (12/26/9) on a DataFrame
    that must contain a 'Close' column with a DatetimeIndex.

    Returns the same DataFrame with indicator columns appended.
    """
    df = prices_df.copy()

    # Ensure column name is lowercase for consistency
    if 'Close' in df.columns and 'close' not in df.columns:
        df = df.rename(columns={'Close': 'close', 'Open': 'open', 'High': 'high', 'Low': 'low'})

    # ── Moving Averages ───────────────────────────────────────────────
    df["ma5"] = df["close"].rolling(window=5).mean()
    df["ma20"] = df["close"].rolling(window=20).mean()
    df["ma60"] = df["close"].rolling(window=60).mean()

    # ── RSI 14 ────────────────────────────────────────────────────────
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Wilder's smoothing (EMA-like) for RSI
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

    rs = avg_gain / avg_loss
    df["rsi14"] = 100 - (100 / (1 + rs))

    # ── MACD (12, 26, 9) ──────────────────────────────────────────────
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


# ──────────────────────────────────────────────────────────────────────
# 1. fetch_stock_info
# ──────────────────────────────────────────────────────────────────────

def fetch_stock_info(symbol: str) -> dict:
    """
    Return current snapshot for *symbol*:
      price, change%, name, sector, market_cap, pe_ratio, eps,
      week52_high, week52_low
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change_pct = None
        if price and prev_close and prev_close != 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        result = {
            "symbol": symbol.upper(),
            "price": _round_safe(price),
            "change_pct": change_pct,
            "name": info.get("shortName") or info.get("longName", symbol),
            "sector": info.get("sector", "N/A"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": _round_safe(info.get("trailingPE")),
            "eps": _round_safe(info.get("trailingEps")),
            "week52_high": _round_safe(info.get("fiftyTwoWeekHigh")),
            "week52_low": _round_safe(info.get("fiftyTwoWeekLow")),
        }
        logger.info("fetch_stock_info(%s) -> price=%s", symbol, result["price"])
        return result

    except Exception as exc:
        logger.error("fetch_stock_info(%s) failed: %s", symbol, exc)
        return {
            "symbol": symbol.upper(),
            "price": None,
            "change_pct": None,
            "name": symbol,
            "sector": "N/A",
            "market_cap": None,
            "pe_ratio": None,
            "eps": None,
            "week52_high": None,
            "week52_low": None,
            "error": str(exc),
        }


# ──────────────────────────────────────────────────────────────────────
# 2. fetch_historical_prices
# ──────────────────────────────────────────────────────────────────────

def fetch_historical_prices(symbol: str, period: str = "1mo") -> list[dict]:
    """
    Return a list of dicts with keys:
      date, open, high, low, close, volume
    Uses multi-source fallback chain (yfinance → Yahoo → Stooq → CoinGecko → custom).
    """
    from services.multi_source import fetch_with_fallback
    try:
        result = fetch_with_fallback(symbol, period)
        if result and result.get("rows"):
            logger.info("fetch_historical_prices(%s, %s) -> %d rows [%s]",
                        symbol, period, len(result["rows"]), result.get("source", "?"))
            return result["rows"]
        logger.warning("fetch_historical_prices(%s, %s) — all sources returned empty", symbol, period)
        return []
    except Exception as exc:
        logger.error("fetch_historical_prices(%s) failed: %s", symbol, exc)
        return []


# ──────────────────────────────────────────────────────────────────────
# 3. fetch_chart_data
# ──────────────────────────────────────────────────────────────────────

# Map friendly range strings to yfinance period strings
_RANGE_MAP = {
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y",
    "5d": "5d",
}


def fetch_chart_data(symbol: str, range: str = "3m") -> dict:
    """
    Return a dict suitable for charting:
      {
        "dates": [...],
        "prices": {"open":[], "high":[], "low":[], "close":[], "volume":[]},
        "indicators": {"ma5":[], "ma20":[], "ma60":[], "rsi14":[], "macd":[], "macd_signal":[], "macd_hist":[]},
        "source": "yfinance|yahoo_direct|stooq|coingecko|custom:..."
      }
    """
    try:
        period = _RANGE_MAP.get(range, range)
        # Use multi-source fallback instead of direct yfinance call
        from services.multi_source import fetch_with_fallback
        result = fetch_with_fallback(symbol, period)
        if not result or not result.get("rows"):
            logger.warning("fetch_chart_data(%s) — all sources empty", symbol)
            return {"dates": [], "prices": {}, "indicators": {}, "source": None}

        rows = result["rows"]
        source = result.get("source", "unknown")

        # Build DataFrame for technical indicators
        df = pd.DataFrame(rows)
        # Ensure correct column order
        for col in ("open", "high", "low", "close"):
            if col not in df.columns:
                df[col] = df.get("close")  # fallback
        df["Volume"] = df.get("volume", 0)
        df = df.sort_values("date").reset_index(drop=True)
        df.index = pd.to_datetime(df["date"])

        df = calculate_indicators(df)

        dates = df["date"].tolist() if "date" in df.columns else [d.strftime("%Y-%m-%d") for d in df.index]

        def _col(col):
            if col not in df.columns:
                return [None] * len(df)
            return [None if pd.isna(v) else _round_safe(v) for v in df[col]]

        prices = {
            "open": _col("open"),
            "high": _col("high"),
            "low": _col("low"),
            "close": _col("close"),
            "volume": [int(v) if pd.notna(v) else 0 for v in df["Volume"]],
        }

        indicators = {
            "ma5": _col("ma5"),
            "ma20": _col("ma20"),
            "ma60": _col("ma60"),
            "rsi14": _col("rsi14"),
            "macd": _col("macd"),
            "macd_signal": _col("macd_signal"),
            "macd_hist": _col("macd_hist"),
        }

        logger.info("fetch_chart_data(%s, %s) -> %d data points", symbol, range, len(dates))
        return {"dates": dates, "prices": prices, "indicators": indicators}

    except Exception as exc:
        logger.error("fetch_chart_data(%s) failed: %s", symbol, exc)
        return {"dates": [], "prices": {}, "indicators": {}, "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────
# 4. fetch_news
# ──────────────────────────────────────────────────────────────────────

def fetch_news(symbol: str) -> list[dict]:
    """
    Return recent news items from yfinance.
    Each item: {title, publisher, link, published_at}
    """
    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news or []

        articles = []
        for item in raw_news:
            content = item.get("content", {})
            pub_ts = content.get("pubDate") or item.get("providerPublishTime")
            published = None
            if pub_ts:
                try:
                    if isinstance(pub_ts, (int, float)):
                        published = datetime.utcfromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M")
                    else:
                        published = str(pub_ts)[:19]
                except Exception:
                    published = str(pub_ts)

            articles.append(
                {
                    "title": content.get("title") or item.get("title", ""),
                    "publisher": content.get("provider", {}).get("displayName", "")
                                 or item.get("publisher", ""),
                    "link": content.get("canonicalUrl", {}).get("url", "")
                            or item.get("link", ""),
                    "published_at": published,
                }
            )

        logger.info("fetch_news(%s) -> %d articles", symbol, len(articles))
        return articles

    except Exception as exc:
        logger.error("fetch_news(%s) failed: %s", symbol, exc)
        return []


# ──────────────────────────────────────────────────────────────────────
# 5. fetch_next_earnings
# ──────────────────────────────────────────────────────────────────────

def fetch_next_earnings(symbol: str) -> dict | None:
    """
    Return the next upcoming earnings date as
    {date: 'YYYY-MM-DD', title: 'Earnings - <symbol>'} or None.
    """
    try:
        ticker = yf.Ticker(symbol)

        # Try .earnings_dates first (most reliable)
        earnings_dates = None
        try:
            earnings_dates = ticker.earnings_dates
        except Exception:
            pass

        if earnings_dates is not None and not earnings_dates.empty:
            today = pd.Timestamp.now(tz=earnings_dates.index.tz).normalize()
            future = earnings_dates[earnings_dates.index >= today]
            if not future.empty:
                next_date = future.index[0].strftime("%Y-%m-%d")
                logger.info("fetch_next_earnings(%s) -> %s (via earnings_dates)", symbol, next_date)
                return {"date": next_date, "title": f"Earnings — {symbol.upper()}"}

        # Fallback: .calendar
        try:
            cal = ticker.calendar
            if cal is not None:
                # calendar can be a dict or DataFrame
                if isinstance(cal, dict):
                    ed = cal.get("Earnings Date")
                    if ed:
                        if isinstance(ed, list) and len(ed) > 0:
                            next_date = ed[0].strftime("%Y-%m-%d")
                        elif hasattr(ed, "strftime"):
                            next_date = ed.strftime("%Y-%m-%d")
                        else:
                            next_date = str(ed)[:10]
                        logger.info("fetch_next_earnings(%s) -> %s (via calendar)", symbol, next_date)
                        return {"date": next_date, "title": f"Earnings — {symbol.upper()}"}
                elif hasattr(cal, "index"):
                    if "Earnings Date" in cal.index:
                        val = cal.loc["Earnings Date"].iloc[0] if hasattr(cal.loc["Earnings Date"], "iloc") else cal.loc["Earnings Date"]
                        next_date = pd.Timestamp(val).strftime("%Y-%m-%d")
                        logger.info("fetch_next_earnings(%s) -> %s (via calendar df)", symbol, next_date)
                        return {"date": next_date, "title": f"Earnings — {symbol.upper()}"}
        except Exception as cal_exc:
            logger.debug("Calendar fallback for %s failed: %s", symbol, cal_exc)

        logger.warning("fetch_next_earnings(%s) — no earnings date found", symbol)
        return None

    except Exception as exc:
        logger.error("fetch_next_earnings(%s) failed: %s", symbol, exc)
        return None


# ──────────────────────────────────────────────────────────────────────
# 6. refresh_ticker_data
# ──────────────────────────────────────────────────────────────────────

def refresh_ticker_data(symbol: str) -> dict:
    """
    Full refresh for a ticker:
      1. Fetch 1-year historical prices from yfinance.
      2. Upsert rows into the daily_prices table (skip dates already stored).
      3. Fetch next earnings date and upsert into the events table.
      4. Return summary info.

    Caching logic: if today's date already exists in daily_prices for this
    ticker, we still re-fetch to ensure freshness on explicit refresh.
    """
    summary = {"symbol": symbol.upper(), "prices_saved": 0, "earnings": None}
    try:
        # ── Ensure ticker exists in DB ────────────────────────────────
        ticker_row = get_ticker_by_symbol(symbol)
        if ticker_row is None:
            logger.info("refresh_ticker_data: ticker %s not in DB, creating stub", symbol)
            info = fetch_stock_info(symbol)
            ticker_row = create_ticker(
                symbol=symbol.upper(),
                name=info.get("name", symbol),
                sector=info.get("sector", "N/A"),
            )

        ticker_id = ticker_row["id"] if isinstance(ticker_row, dict) else ticker_row.id

        # ── Fetch & save daily prices (1 year) ────────────────────────
        historical = fetch_historical_prices(symbol, period="1y")
        if historical:
            existing_dates = tsdb.get_existing_dates(ticker_id)

            new_rows = [r for r in historical if r["date"] not in existing_dates]
            if new_rows:
                tsdb.save_daily_prices(ticker_id, new_rows)
                summary["prices_saved"] = len(new_rows)
                logger.info(
                    "refresh_ticker_data(%s): saved %d new price rows", symbol, len(new_rows)
                )
            else:
                logger.info("refresh_ticker_data(%s): prices already up to date", symbol)

        # ── Fetch & save next earnings date ────────────────────────────
        earnings = fetch_next_earnings(symbol)
        if earnings:
            # Check if an earnings event for this date already exists
            existing_events = get_events_by_ticker(ticker_id) or []
            already_tracked = False
            for ev in existing_events:
                ev_type = ev["event_type"] if isinstance(ev, dict) else ev.event_type
                ev_date = ev["event_date"] if isinstance(ev, dict) else ev.event_date
                if ev_type == "earnings" and str(ev_date) == earnings["date"]:
                    already_tracked = True
                    break

            if not already_tracked:
                create_event(
                    ticker_id=ticker_id,
                    event_type="earnings",
                    event_date=earnings["date"],
                    title=earnings["title"],
                )
                logger.info("refresh_ticker_data(%s): created earnings event %s", symbol, earnings["date"])
            else:
                logger.info("refresh_ticker_data(%s): earnings event already tracked", symbol)

            summary["earnings"] = earnings

        return summary

    except Exception as exc:
        logger.error("refresh_ticker_data(%s) failed: %s", symbol, exc)
        summary["error"] = str(exc)
        return summary
