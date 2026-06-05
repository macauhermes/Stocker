"""
金融機構分析報告收集服務
========================
從公開來源收集各大銀行及投行的分析報告：
- yfinance analyst recommendations
- Yahoo Finance analyst opinion pages
- MarketWatch analyst ratings
- 存入 DB 並保存檔案
"""
import os
import sys
import re
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path(os.path.expanduser("~/repos/Stocker/data"))
REPORTS_DIR = DATA_DIR / "files" / "analyst_report"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Major investment banks / research firms to track
INSTITUTIONS = [
    "Goldman Sachs", "Morgan Stanley", "JPMorgan", "Bank of America",
    "Citigroup", "Barclays", "UBS", "Deutsche Bank", "Wells Fargo",
    "HSBC", "Credit Suisse", "Jefferies", "Piper Sandler",
    "Raymond James", "Oppenheimer", "Stifel", "BMO Capital",
    "RBC Capital", "TD Cowen", "Bernstein", "Rosenblatt",
    "Wedbush", "Needham", "Loop Capital", "Argus Research",
]


def _is_duplicate(title: str) -> bool:
    """Check if a report with same title already exists."""
    try:
        existing = models.get_reports(200)
        return any(r["title"] == title for r in existing)
    except Exception:
        return False


def collect_analyst_ratings(symbol: str) -> list[dict]:
    """
    Collect analyst ratings and recommendations for a ticker from yfinance.
    Returns list of collected reports.
    """
    collected = []
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)

        # Get analyst recommendations
        recs = None
        for attr in ("recommendations", "analyst_recommendations"):
            try:
                recs = getattr(ticker, attr, None)
                if recs is not None and not (hasattr(recs, 'empty') and recs.empty):
                    break
            except Exception:
                continue

        if recs is not None:
            try:
                df = recs.tail(20)
                rec_text = f"=== {symbol} Analyst Recommendations ===\n"
                rec_text += f"Collected: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                rec_text += df.to_string()

                title = f"{symbol} 分析師評級摘要 ({datetime.now().strftime('%Y-%m')})"
                if not _is_duplicate(title):
                    file_name = f"{symbol}_analyst_ratings_{datetime.now().strftime('%Y%m%d')}.txt"
                    file_path = REPORTS_DIR / file_name
                    file_path.write_text(rec_text, encoding="utf-8")

                    report = models.add_report({
                        "title": title,
                        "source": "Analyst Consensus",
                        "url": f"https://finance.yahoo.com/quote/{symbol}/analysis/",
                        "summary": f"{symbol} 分析師評級匯總，包含近期機構評級變動及目標價",
                        "analysis": "",
                        "content": rec_text,
                        "file_path": str(file_path),
                        "category": "analyst_report",
                        "published_at": datetime.now().isoformat(),
                    })
                    if report:
                        models.add_file({
                            "filename": file_name,
                            "category": "analyst_report",
                            "file_path": str(file_path),
                            "file_size": file_path.stat().st_size,
                            "report_id": report["id"],
                        })
                    collected.append({"symbol": symbol, "title": title, "type": "ratings"})
                    logger.info("[%s] 分析師評級已收集", symbol)
            except Exception as e:
                logger.warning("[%s] 處理分析師評級失敗: %s", symbol, e)

    except Exception as e:
        logger.error("[%s] 收集分析師評級失敗: %s", symbol, e)

    return collected


def collect_analyst_opinions(symbol: str) -> list[dict]:
    """
    Scrape analyst opinions from Yahoo Finance analysis page.
    """
    collected = []
    url = f"https://finance.yahoo.com/quote/{symbol}/analysis/"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract earnings estimates table
        tables = soup.find_all("table")
        content_parts = [f"=== {symbol} Analyst Opinions ===", f"Source: Yahoo Finance", f"Date: {datetime.now().strftime('%Y-%m-%d')}", ""]

        for table in tables[:3]:  # First 3 tables usually most relevant
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            rows = []
            for tr in table.find_all("tr")[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if cells:
                    rows.append(cells)
            if headers and rows:
                content_parts.append(" | ".join(headers))
                for row in rows[:5]:
                    content_parts.append(" | ".join(row))
                content_parts.append("")

        if len(content_parts) > 4:
            content = "\n".join(content_parts)
            title = f"{symbol} 分析師預測 ({datetime.now().strftime('%Y-%m-%d')})"

            if not _is_duplicate(title):
                file_name = f"{symbol}_analyst_opinions_{datetime.now().strftime('%Y%m%d')}.html"
                file_path = REPORTS_DIR / file_name
                file_path.write_text(content, encoding="utf-8")

                report = models.add_report({
                    "title": title,
                    "source": "Yahoo Finance Analysis",
                    "url": url,
                    "summary": f"{symbol} 分析師盈利預測及收入預估",
                    "analysis": "",
                    "content": content,
                    "file_path": str(file_path),
                    "category": "analyst_report",
                    "published_at": datetime.now().isoformat(),
                })
                if report:
                    models.add_file({
                        "filename": file_name,
                        "category": "analyst_report",
                        "file_path": str(file_path),
                        "file_size": file_path.stat().st_size,
                        "report_id": report["id"],
                    })
                collected.append({"symbol": symbol, "title": title, "type": "opinions"})
                logger.info("[%s] 分析師預測已收集", symbol)

    except Exception as e:
        logger.debug("[%s] Yahoo Finance analysis scrape failed: %s", symbol, e)

    return collected


def collect_institutional_reports() -> dict:
    """
    Main function: collect analyst/institutional reports for all tracked tickers.
    Includes:
    1. Analyst ratings (yfinance)
    2. Analyst opinions (Yahoo Finance scrape)
    
    Returns {total_new, by_ticker, errors}.
    """
    tickers = models.get_all_tickers()
    symbols = [t["symbol"] for t in tickers]

    if not symbols:
        logger.warning("追蹤清單為空，無法收集分析報告")
        return {"total_new": 0, "by_ticker": {}, "errors": ["追蹤清單為空"]}

    result = {"total_new": 0, "by_ticker": {}, "errors": []}

    for sym in symbols:
        count = 0
        try:
            # 1. Analyst ratings from yfinance
            ratings = collect_analyst_ratings(sym)
            count += len(ratings)
        except Exception as e:
            result["errors"].append(f"{sym} ratings: {e}")

        try:
            # 2. Analyst opinions from Yahoo Finance
            opinions = collect_analyst_opinions(sym)
            count += len(opinions)
        except Exception as e:
            result["errors"].append(f"{sym} opinions: {e}")

        result["by_ticker"][sym] = count
        result["total_new"] += count

        time.sleep(1)  # Rate limit

    logger.info("分析報告收集完成: 共 %d 份新報告", result["total_new"])
    return result


if __name__ == "__main__":
    models.init_db()
    result = collect_institutional_reports()
    print(f"\n=== 分析報告收集完成 ===")
    print(f"新報告: {result['total_new']} 份")
    for sym, count in result["by_ticker"].items():
        print(f"  {sym}: {count} 份")
    if result["errors"]:
        print(f"錯誤: {result['errors']}")
