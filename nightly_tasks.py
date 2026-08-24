#!/usr/bin/env python3
"""
Stocker 每晚排程任務
====================
每晚 20:00 自動執行以下三項任務：
1. SEC 財報下載 (earnings_downloader)
2. 行業新聞收集 (industry_collector)
3. 金融機構分析報告 (analyst_collector)
"""
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import models

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)


def run_nightly():
    """Execute all three collection tasks sequentially."""
    models.init_db()

    results = {
        "started_at": datetime.now().isoformat(),
        "tasks": {}
    }

    # ── Task 1: SEC Earnings PDF Download ──────────────────────
    logger.info("=" * 50)
    logger.info("[1/3] 開始下載 SEC 財報 PDF...")
    logger.info("=" * 50)
    try:
        from services.earnings_downloader import download_all_earnings
        r1 = download_all_earnings()
        results["tasks"]["earnings"] = r1
        logger.info("[1/3] 財報下載完成: %d 份新報告", r1.get("total", 0))
    except Exception as e:
        results["tasks"]["earnings"] = {"error": str(e)}
        logger.error("[1/3] 財報下載失敗: %s", e)

    # ── Task 2: Industry News Collection ───────────────────────
    logger.info("=" * 50)
    logger.info("[2/3] 開始收集行業新聞...")
    logger.info("=" * 50)
    try:
        from services.industry_collector import collect_industry_news
        r2 = collect_industry_news()
        results["tasks"]["industry"] = r2
        logger.info("[2/3] 行業新聞完成: %d 份新報告", r2.get("total_new", 0))
    except Exception as e:
        results["tasks"]["industry"] = {"error": str(e)}
        logger.error("[2/3] 行業新聞收集失敗: %s", e)

    # ── Task 3: Institutional Analyst Reports ──────────────────
    logger.info("=" * 50)
    logger.info("[3/3] 開始收集金融機構分析報告...")
    logger.info("=" * 50)
    try:
        from services.analyst_collector import collect_institutional_reports
        r3 = collect_institutional_reports()
        results["tasks"]["analyst"] = r3
        logger.info("[3/3] 分析報告完成: %d 份新報告", r3.get("total_new", 0))
    except Exception as e:
        results["tasks"]["analyst"] = {"error": str(e)}
        logger.error("[3/3] 分析報告收集失敗: %s", e)

    # ── Task 4: Nightly Historical Price Refresh (5y) ────────────
    logger.info("=" * 50)
    logger.info("[4/4] 開始刷新 5 年歷史價格...")
    logger.info("=" * 50)
    try:
        from services.nightly_refresher import refresh_all_tickers
        r4 = refresh_all_tickers(period="5y", sleep_between=2.0)
        results["tasks"]["refresher"] = r4
        logger.info("[4/4] 歷史價格刷新完成: %d 行新增, %d 錯誤", r4.get("total_new", 0), r4.get("errors", 0))
    except Exception as e:
        results["tasks"]["refresher"] = {"error": str(e)}
        logger.error("[4/4] 歷史價格刷新失敗: %s", e)

    # ── Task 5: Price Alert Sweep (v3.4) ─────────────────────────
    logger.info("=" * 50)
    logger.info("[5/5] 開始檢查價格提醒...")
    logger.info("=" * 50)
    try:
        from services.alert_checker import check_alerts_all
        triggered = check_alerts_all()
        results["tasks"]["alerts"] = {"triggered": len(triggered)}
        # Record to Prometheus counter when running in-process. When this
        # script is invoked via cron (separate process from app.py), the
        # counter file isn't shared — call only when we're in the Flask process.
        try:
            from services.metrics import record_alert_triggered
            record_alert_triggered(len(triggered))
        except Exception:
            pass  # metrics module may not be importable standalone
        logger.info("[5/5] 價格提醒檢查完成: %d 個觸發", len(triggered))
    except Exception as e:
        results["tasks"]["alerts"] = {"error": str(e)}
        logger.error("[5/5] 價格提醒檢查失敗: %s", e)

    # ── Summary ────────────────────────────────────────────────
    results["finished_at"] = datetime.now().isoformat()

    total = 0
    for task_name, task_result in results["tasks"].items():
        if isinstance(task_result, dict):
            count = task_result.get("total", 0) or task_result.get("total_new", 0)
            total += count

    logger.info("=" * 50)
    logger.info("全部完成! 共收集 %d 份新報告", total)
    logger.info("=" * 50)

    return results


if __name__ == "__main__":
    results = run_nightly()

    # Print summary
    print(f"\n{'='*50}")
    print(f"Stocker 每晚排程完成 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    for task_name, task_result in results["tasks"].items():
        if isinstance(task_result, dict) and "error" not in task_result:
            count = task_result.get("total", 0) or task_result.get("total_new", 0)
            by = task_result.get("by_ticker", {}) or task_result.get("by_sector", {})
            print(f"\n✅ {task_name}: {count} 份新報告")
            for k, v in by.items():
                if v > 0:
                    print(f"   {k}: {v}")
        else:
            err = task_result.get("error", "Unknown error") if isinstance(task_result, dict) else str(task_result)
            print(f"\n❌ {task_name}: {err}")

    print()
