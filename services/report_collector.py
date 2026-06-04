"""
報告收集服務 — 從公開來源抓取金融報告，存入 DB 和本地檔案。
使用 yfinance 取得分析師推薦與新聞，BeautifulSoup 解析 HTML。
"""
import os
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf
from bs4 import BeautifulSoup

import models

logger = logging.getLogger(__name__)

# ── 路徑常量 ──────────────────────────────────────────────────────
DATA_DIR = Path(os.path.expanduser("~/repos/Stocker/data"))
FILES_DIR = DATA_DIR / "files"

CATEGORIES = ["earnings", "analyst_report", "news", "sec_filing"]
for cat in CATEGORIES:
    (FILES_DIR / cat).mkdir(parents=True, exist_ok=True)


# ── 輔助：從 DB 取追蹤清單 ────────────────────────────────────────
def _get_tracked_symbols() -> list[str]:
    """回傳所有追蹤中的 ticker symbol 列表。"""
    try:
        tickers = models.get_all_tickers()
        return [t["symbol"] for t in tickers] if tickers else []
    except Exception as exc:
        logger.error("取得追蹤清單失敗: %s", exc)
        return []


def _is_report_duplicate(symbol: str, title: str) -> bool:
    """檢查是否已有同標題報告（避免重複收集）。"""
    try:
        existing = models.get_reports_by_symbol(symbol) if hasattr(models, "get_reports_by_symbol") else []
        for r in existing:
            if r.get("title") == title:
                return True
    except Exception:
        pass
    return False


# ── 核心：收集單一 Ticker 的報告 ─────────────────────────────────
def collect_ticker_reports(symbol: str) -> list[dict]:
    """
    收集指定 ticker 的報告（新聞 + 分析師推薦），存入 DB 並保存檔案。
    回傳新增的報告列表。
    """
    collected = []
    ticker = yf.Ticker(symbol)

    # ── 1. 新聞 ───────────────────────────────────────────────
    try:
        news_items = ticker.news or []
        for item in news_items:
            title = item.get("title", "")
            if not title or _is_report_duplicate(symbol, title):
                continue

            # 解析內容
            content = _extract_news_content(item)
            url = item.get("link", "")
            publisher = item.get("publisher", "Unknown")
            pub_ts = item.get("providerPublishTime")
            published_at = datetime.fromtimestamp(pub_ts).isoformat() if pub_ts else datetime.now().isoformat()

            # 儲存檔案
            safe_name = re.sub(r'[^\w\-]', '_', title[:60]).strip("_")
            file_name = f"{symbol}_news_{safe_name}.txt"
            file_path = FILES_DIR / "news" / file_name
            file_path.write_text(content or title, encoding="utf-8")

            # 寫入 DB
            report_data = {
                "title": title,
                "source": publisher,
                "url": url,
                "summary": "",
                "analysis": "",
                "content": content or title,
                "file_path": str(file_path),
                "category": "news",
                "published_at": published_at,
                "created_at": datetime.now().isoformat(),
                "symbol": symbol,
            }
            try:
                report_id = models.add_report(report_data)
                report_data["id"] = report_id
                collected.append(report_data)
                logger.info("[%s] 新增新聞: %s", symbol, title[:50])
            except Exception as exc:
                logger.error("[%s] 存入報告失敗: %s — %s", symbol, title[:40], exc)

    except Exception as exc:
        logger.error("[%s] 抓取新聞失敗: %s", symbol, exc)

    # ── 2. 分析師推薦 ────────────────────────────────────────
    try:
        recs = None
        for attr in ("recommendations", "analyst_recommendations"):
            try:
                recs = getattr(ticker, attr, None)
                if recs is not None:
                    break
            except Exception:
                continue

        if recs is not None:
            # yfinance 回傳 DataFrame，轉為可讀文本
            try:
                rec_text = recs.tail(10).to_string()
            except Exception:
                rec_text = str(recs)

            title = f"{symbol} 分析師推薦摘要"
            if not _is_report_duplicate(symbol, title):
                file_name = f"{symbol}_analyst_rec.txt"
                file_path = FILES_DIR / "analyst_report" / file_name
                file_path.write_text(rec_text, encoding="utf-8")

                report_data = {
                    "title": title,
                    "source": "yfinance/analyst",
                    "url": "",
                    "summary": "",
                    "analysis": "",
                    "content": rec_text,
                    "file_path": str(file_path),
                    "category": "analyst_report",
                    "published_at": datetime.now().isoformat(),
                    "created_at": datetime.now().isoformat(),
                    "symbol": symbol,
                }
                try:
                    report_id = models.add_report(report_data)
                    report_data["id"] = report_id
                    collected.append(report_data)
                    logger.info("[%s] 新增分析師推薦報告", symbol)
                except Exception as exc:
                    logger.error("[%s] 存入分析師推薦失敗: %s", symbol, exc)
    except Exception as exc:
        logger.error("[%s] 抓取分析師推薦失敗: %s", symbol, exc)

    # ── 3. Earnings 相關 ─────────────────────────────────────
    try:
        cal = None
        for attr in ("earnings_dates", "calendar"):
            try:
                cal = getattr(ticker, attr, None)
                if cal is not None:
                    break
            except Exception:
                continue

        if cal is not None:
            try:
                cal_text = cal.to_string() if hasattr(cal, "to_string") else str(cal)
            except Exception:
                cal_text = str(cal)

            title = f"{symbol} 財報日期與數據"
            if not _is_report_duplicate(symbol, title):
                file_name = f"{symbol}_earnings.txt"
                file_path = FILES_DIR / "earnings" / file_name
                file_path.write_text(cal_text, encoding="utf-8")

                report_data = {
                    "title": title,
                    "source": "yfinance/earnings",
                    "url": "",
                    "summary": "",
                    "analysis": "",
                    "content": cal_text,
                    "file_path": str(file_path),
                    "category": "earnings",
                    "published_at": datetime.now().isoformat(),
                    "created_at": datetime.now().isoformat(),
                    "symbol": symbol,
                }
                try:
                    report_id = models.add_report(report_data)
                    report_data["id"] = report_id
                    collected.append(report_data)
                    logger.info("[%s] 新增財報資料", symbol)
                except Exception as exc:
                    logger.error("[%s] 存入財報資料失敗: %s", symbol, exc)
    except Exception as exc:
        logger.error("[%s] 抓取財報資料失敗: %s", symbol, exc)

    return collected


# ── 主收集入口 ────────────────────────────────────────────────────
def collect_reports() -> dict:
    """
    主函數：對所有追蹤中的 ticker 收集報告。
    回傳 {total_new, by_ticker: {symbol: count}, errors: [...]}。
    """
    symbols = _get_tracked_symbols()
    if not symbols:
        logger.warning("追蹤清單為空，無法收集報告")
        return {"total_new": 0, "by_ticker": {}, "errors": ["追蹤清單為空"]}

    result = {"total_new": 0, "by_ticker": {}, "errors": []}

    for sym in symbols:
        try:
            reports = collect_ticker_reports(sym)
            count = len(reports)
            result["by_ticker"][sym] = count
            result["total_new"] += count
            logger.info("[%s] 共收集 %d 份新報告", sym, count)
        except Exception as exc:
            err_msg = f"{sym}: {exc}"
            result["errors"].append(err_msg)
            logger.error("收集 %s 報告時出錯: %s", sym, exc)

    logger.info("報告收集完成，共 %d 份新報告", result["total_new"])
    return result


# ── 內部工具函數 ──────────────────────────────────────────────────
def _extract_news_content(item: dict) -> str:
    """
    從 yfinance news item 提取正文。
    嘗試從 link 抓取頁面內容（BeautifulSoup），失敗則回退到摘要。
    """
    link = item.get("link", "")
    summary = item.get("summary", "")

    if not link:
        return summary

    try:
        import requests
        resp = requests.get(link, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 移除 script / style
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        # 嘗試常見文章容器
        article = (
            soup.find("article")
            or soup.find("div", class_=re.compile(r"article|story|content|body", re.I))
            or soup.find("main")
        )
        if article:
            text = article.get_text(separator="\n", strip=True)
            # 截取合理長度
            if len(text) > 5000:
                text = text[:5000] + "..."
            return text if len(text) > 100 else summary or text

        # fallback: 取全部 <p>
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return text[:5000] if text else summary

    except Exception as exc:
        logger.debug("無法抓取 %s 內文: %s", link[:80], exc)
        return summary
