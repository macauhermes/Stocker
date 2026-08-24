"""
services/portfolio_snapshot.py
====================================

Daily portfolio value snapshot service (v3.4.2).

Walks every active ticker, multiplies (current_price × shares_held) for
market value, (cost_basis × shares_held) for cost, and stores the totals in
the `portfolio_snapshots` table keyed by date. The nightly cron (task 6)
runs this after-hours so P&L history accumulates automatically.

Failure modes handled:
- Tickers with no current_price (multi_source failure) are skipped, not zeroed
  — keeps the snapshot aligned with the rows that actually have data.
- Tickers with shares_held = 0 are skipped too (they inflate holdings_count
  without affecting totals).
- One bad ticker never kills the whole snapshot — wrapped in try/except.
"""

from __future__ import annotations

import logging
from datetime import datetime, date

import models
from services import multi_source

logger = logging.getLogger(__name__)


def _safe_get_price(symbol: str):
    """Fetch current price via multi_source, return None on any failure.

    Caller is expected to skip the ticker on None — we don't synthesize 0.0
    prices because that would silently corrupt the totals.
    """
    try:
        info = multi_source.get_current_price(symbol)
        if not info:
            return None
        return info.get('price')
    except Exception as e:
        logger.debug("Snapshot: price fetch failed for %s: %s", symbol, e)
        return None


def compute_totals() -> tuple[float, float, int, list[dict]]:
    """Walk every active ticker and return (total_value, total_cost,
    holdings_count, holdings_breakdown).

    holdings_breakdown is a list of {symbol, shares, cost_basis, current_price,
    market_value, cost_value, unrealized_pl} dicts — useful for debugging or
    surfacing in API responses.

    Tickers with no price or zero shares are skipped silently. Returns
    numeric totals rounded to 2 decimals (dollars).
    """
    tickers = models.get_all_tickers()
    total_value = 0.0
    total_cost = 0.0
    holdings_count = 0
    breakdown = []

    for t in tickers:
        # sqlite3.Row supports [] but not .get() — explicit None guards
        symbol = t['symbol']
        shares = t['shares_held'] if 'shares_held' in t.keys() and t['shares_held'] else 0
        cost_basis = t['cost_basis'] if 'cost_basis' in t.keys() and t['cost_basis'] else 0

        if shares <= 0:
            # No holdings — skip silently (don't inflate holdings_count)
            continue

        price = _safe_get_price(symbol)
        if price is None or price <= 0:
            logger.debug("Snapshot: skipping %s (no price)", symbol)
            continue

        market_value = round(price * shares, 2)
        cost_value = round(cost_basis * shares, 2)
        unrealized_pl = round(market_value - cost_value, 2)

        total_value += market_value
        total_cost += cost_value
        holdings_count += 1

        breakdown.append({
            'symbol': symbol,
            'shares': shares,
            'cost_basis': cost_basis,
            'current_price': price,
            'market_value': market_value,
            'cost_value': cost_value,
            'unrealized_pl': unrealized_pl,
        })

    return round(total_value, 2), round(total_cost, 2), holdings_count, breakdown


def capture_snapshot(snapshot_date: str | None = None) -> dict:
    """Compute today's totals and persist a snapshot row.

    snapshot_date defaults to today (UTC date as YYYY-MM-DD). Caller can pass
    an explicit date for backfilling.

    Returns the inserted row (as a dict), or None if there were no holdings
    worth snapshotting (empty portfolio — we still record a 0-valued row
    because that's accurate).

    Safe to call multiple times per day — ON CONFLICT replaces.
    """
    if snapshot_date is None:
        snapshot_date = date.today().isoformat()

    total_value, total_cost, holdings_count, breakdown = compute_totals()
    total_pnl = round(total_value - total_cost, 2)
    pnl_pct = round((total_pnl / total_cost) * 100, 2) if total_cost > 0 else 0.0

    row = models.upsert_snapshot(
        snapshot_date=snapshot_date,
        total_value=total_value,
        total_cost=total_cost,
        total_pnl=total_pnl,
        pnl_pct=pnl_pct,
        holdings_count=holdings_count,
    )

    logger.info(
        "Snapshot %s captured: value=%.2f cost=%.2f pnl=%.2f (%.2f%%) "
        "holdings=%d",
        snapshot_date, total_value, total_cost, total_pnl, pnl_pct,
        holdings_count,
    )

    if row is not None:
        row['breakdown'] = breakdown  # in-memory only; not persisted

    return row


def backfill_snapshot(date_str: str) -> dict:
    """Capture a snapshot for an explicit date string (YYYY-MM-DD).

    Mostly useful for test fixtures and one-off catch-up runs after the
    nightly cron missed a night. Production code should call capture_snapshot()
    with no args.
    """
    return capture_snapshot(snapshot_date=date_str)


def prune_old_snapshots(retention_days: int = 365) -> int:
    """Delete snapshots older than `retention_days` (default 365). Returns
    rows deleted. Kept off the hot path — only the nightly cron calls it.
    """
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=retention_days)).isoformat()
    deleted = models.delete_snapshots_before(cutoff)
    if deleted:
        logger.info("Pruned %d snapshots older than %s", deleted, cutoff)
    return deleted