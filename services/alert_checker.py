"""
Price alert checker (v3.4) — evaluates enabled alerts against current price.

Used by:
- app.py  → /api/stock/<sym>/refresh  (manual refresh)
- app.py  → /api/tickers  (polling fetch path)
- nightly_tasks.py → scheduled sweep across all tickers

Public API:
    check_alerts_for_ticker(symbol)  → list of triggered alerts (dicts)
    check_alerts_all()              → list of triggered alerts (dicts)

Each triggered alert is:
1. Recorded in the `events` table as event_type='price_alert' (dismissed=0)
2. Marked triggered in the price_alerts table (auto-disabled)

Returns: list of {"alert_id", "ticker_id", "symbol", "threshold_type",
                  "threshold_price", "current_price", "event_id"}
"""
from datetime import date

import models


def _fire(alert_row, current_price):
    """Create the matching event row + auto-disable the alert. Returns dict."""
    alert = dict(alert_row)
    symbol = alert.get("symbol") or "?"
    title = (
        f"🔔 {symbol} {alert['threshold_type']} "
        f"${alert['threshold_price']:.2f} (now ${current_price:.2f})"
    )
    # Use SQLite's date('now') — matches existing events convention
    event_row = models.upsert_event(
        ticker_id=alert["ticker_id"],
        event_type="price_alert",
        event_date=date.today().isoformat(),
        title=title,
    )
    event_id = event_row["id"] if event_row else None
    models.mark_alert_triggered(alert["id"])
    return {
        "alert_id": alert["id"],
        "ticker_id": alert["ticker_id"],
        "symbol": symbol,
        "threshold_type": alert["threshold_type"],
        "threshold_price": alert["threshold_price"],
        "current_price": current_price,
        "event_id": event_id,
    }


def check_alerts_for_ticker(symbol: str):
    """Check all enabled alerts for `symbol`. Returns list of fired alerts.

    `symbol` may be passed in any case. Uses get_current_price() for the
    latest price, falling back to the daily_prices table if the price service
    is unavailable (e.g. when the market is closed and yfinance returns NaN).
    """
    sym = symbol.upper()
    ticker = models.get_ticker(sym)
    if not ticker or ticker["archived"]:
        return []

    # Pull the latest price. Avoid forcing a network call by trying the
    # TSDB cache first; fall back to multi_source only if no cache hit.
    from tsdb import get_latest_price
    cached = get_latest_price(ticker["id"])
    current_price = None
    if cached and cached.get("close") is not None:
        try:
            current_price = float(cached["close"])
        except (TypeError, ValueError):
            current_price = None

    if current_price is None or current_price <= 0:
        try:
            from services.multi_source import get_current_price
            data = get_current_price(sym)
            current_price = data.get("price") if data else None
        except Exception:
            current_price = None

    if current_price is None:
        # No price available — silently skip; nothing to compare against
        return []

    alerts = models.get_enabled_alerts_for_ticker_with_symbol(ticker["id"])
    fired = []
    for alert in alerts:
        threshold = float(alert["threshold_price"])
        if alert["threshold_type"] == "high" and current_price >= threshold:
            fired.append(_fire(alert, current_price))
        elif alert["threshold_type"] == "low" and current_price <= threshold:
            fired.append(_fire(alert, current_price))
    return fired


def check_alerts_all():
    """Sweep every active ticker. Used by nightly_tasks.py."""
    triggered = []
    for ticker in models.get_all_tickers():
        try:
            triggered.extend(check_alerts_for_ticker(ticker["symbol"]))
        except Exception:
            # Never let one ticker break the sweep
            continue
    return triggered