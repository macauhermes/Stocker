"""
Nightly Refresher — 自動刷新 5 年歷史價 + 預熱 cache
====================================================
每晚由 nightly_tasks.py 觸發，為所有活躍 ticker 從 multi_source 抓取 5 年歷史數據，
存入 timeseries DB，並預熱 app.py 的 in-memory cache。

設計目標：
1. 使用 multi_source.fetch_with_fallback() — 自動 fallback
2. 只存新日期（tsdb.get_existing_dates 去重）
3. 每個 ticker 之間暫停 2s 避免 API rate limit
4. 返回每個 ticker 的摘要 + 總計
"""

import os
import sys
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import models
import tsdb

logger = logging.getLogger(__name__)


def _round_safe(value, decimals=2):
    if value is None:
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None


def refresh_all_tickers(period="5y", sleep_between=2.0):
    """
    Fetch 5-year historical prices for all active tickers and save to tsdb.

    Returns:
        {
            "started_at": "...",
            "finished_at": "...",
            "tickers": {
                "TSLA": {"total_rows": 1256, "new_rows": 42, "source": "yfinance", "error": null},
                ...
            },
            "total_new": 42,
            "errors": 0,
        }
    """
    models.init_db()
    tsdb.init_tsdb()

    results = {
        "started_at": datetime.now().isoformat(),
        "tickers": {},
        "total_new": 0,
        "errors": 0,
    }

    # Import here to avoid circular dependency at module load
    from services.multi_source import fetch_with_fallback

    tickers = models.get_all_tickers()
    logger.info("nightly_refresher: starting for %d tickers (period=%s)", len(tickers), period)

    for t in tickers:
        # sqlite3.Row supports only bracket access (Pitfall 12/14) — attribute access
        # raises AttributeError. Wrap once at top so both fields work via dict syntax.
        td = dict(t)
        symbol = td["symbol"]
        ticker_id = td["id"]

        ticker_result = {
            "total_rows": 0,
            "new_rows": 0,
            "source": None,
            "error": None,
        }

        try:
            logger.info("nightly_refresher: fetching %s ...", symbol)
            data = fetch_with_fallback(symbol, period)

            if data and data.get("rows"):
                rows = data["rows"]
                ticker_result["total_rows"] = len(rows)
                ticker_result["source"] = data.get("source", "unknown")

                # Deduplicate: only save dates not yet in tsdb
                existing = tsdb.get_existing_dates(ticker_id)
                new_rows = [r for r in rows if r["date"] not in existing]

                if new_rows:
                    tsdb.save_daily_prices(ticker_id, new_rows)
                    ticker_result["new_rows"] = len(new_rows)
                    results["total_new"] += len(new_rows)
                    logger.info(
                        "nightly_refresher: %s — %d rows fetched, %d new saved [%s]",
                        symbol, len(rows), len(new_rows), data.get("source"),
                    )
                else:
                    logger.info("nightly_refresher: %s — already up to date (%d rows)", symbol, len(rows))
            else:
                ticker_result["error"] = "all sources returned empty"
                results["errors"] += 1
                logger.warning("nightly_refresher: %s — no data from any source", symbol)

        except Exception as exc:
            ticker_result["error"] = str(exc)
            results["errors"] += 1
            logger.error("nightly_refresher: %s — exception: %s", symbol, exc)

        results["tickers"][symbol] = ticker_result

        # Rate limit: pause between tickers
        if sleep_between > 0:
            time.sleep(sleep_between)

    results["finished_at"] = datetime.now().isoformat()

    logger.info(
        "nightly_refresher: done — %d total new rows, %d errors",
        results["total_new"], results["errors"],
    )

    return results


def warm_chart_cache(symbols=None, period="5y"):
    """
    Pre-warm the chart data cache by fetching data for given symbols.
    Returns count of symbols cached.
    This is a no-op when run standalone (cache is in app.py process).
    It's meant to be called from within the Flask app context.
    """
    # This function exists for documentation; actual cache warming
    # happens when the server process calls refresh_all_tickers()
    # and the chart data endpoints read from tsdb (which is already populated).
    logger.info("warm_chart_cache: tsdb is already populated; chart endpoints read from tsdb directly.")
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    print("=" * 60)
    print("Stocker 夜間全量刷新 — 5 年歷史數據")
    print("=" * 60)

    result = refresh_all_tickers(period="5y")

    print(f"\n開始: {result['started_at']}")
    print(f"完成: {result['finished_at']}")
    print(f"總計新增: {result['total_new']} 行")
    print(f"錯誤: {result['errors']} 個\n")

    for sym, info in result["tickers"].items():
        if info["error"]:
            print(f"  ❌ {sym}: {info['error']}")
        else:
            print(f"  ✅ {sym}: {info['total_rows']} rows, {info['new_rows']} new [{info['source']}]")

    print()
