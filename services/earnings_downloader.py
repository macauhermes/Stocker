#!/usr/bin/env python3
"""
財報 PDF 下載服務 — 從 SEC EDGAR 下載最新的 10-K / 10-Q 財報 PDF
"""
import os
import sys
import re
import logging
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path(os.path.expanduser("~/repos/Stocker/data"))
EARNINGS_DIR = DATA_DIR / "files" / "earnings"
EARNINGS_DIR.mkdir(parents=True, exist_ok=True)

# SEC EDGAR requires a User-Agent with contact info
HEADERS = {
    "User-Agent": "Stocker/1.0 (macauhermes@gmail.com)",
    "Accept-Encoding": "gzip, deflate",
}

# SEC EDGAR company tickers JSON (maps ticker → CIK)
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FILINGS_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{cik}%22&dateRange=custom&startdt={start}&enddt={end}&forms=10-K,10-Q"
FILING_DETAIL_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}&dateb=&owner=include&count=5&search_text=&action=getcompany"


def _get_cik_map() -> dict:
    """從 SEC EDGAR 取得 ticker → CIK 映射表。"""
    cache_path = DATA_DIR / "cik_cache.json"
    # Use cache if less than 7 days old
    if cache_path.exists():
        import json
        age = time.time() - cache_path.stat().st_mtime
        if age < 7 * 86400:
            return json.loads(cache_path.read_text())

    try:
        resp = requests.get(TICKERS_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # data = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
        mapping = {}
        for entry in data.values():
            mapping[entry["ticker"].upper()] = str(entry["cik_str"]).zfill(10)
        # Save cache
        import json
        cache_path.write_text(json.dumps(mapping))
        return mapping
    except Exception as e:
        logger.error("Failed to fetch CIK map: %s", e)
        return {}


def _get_latest_filings(cik: str, form_types=("10-K", "10-Q"), count=3) -> list[dict]:
    """
    從 SEC EDGAR 取得指定 CIK 的最新財報 filing 列表。
    回傳 [{form_type, filing_date, accession, primary_doc_url}]
    """
    results = []
    for ft in form_types:
        try:
            url = f"https://efts.sec.gov/LATEST/search-index?q=%22{cik}%22&forms={ft}"
            # Use the EDGAR full-text search API
            search_url = f"https://efts.sec.gov/LATEST/search-index?q=&forms={ft}&dateRange=custom&startdt=2024-01-01&enddt=2026-12-31"
            
            # Simpler approach: use the company filings JSON endpoint
            filings_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            resp = requests.get(filings_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])
            
            for i in range(len(forms)):
                if forms[i] in form_types:
                    acc_no_dash = accessions[i].replace("-", "")
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc_no_dash}/{primary_docs[i]}"
                    results.append({
                        "form_type": forms[i],
                        "filing_date": dates[i],
                        "accession": accessions[i],
                        "doc_url": doc_url,
                        "primary_doc": primary_docs[i],
                    })
                    if len(results) >= count:
                        break
            
            if len(results) >= count:
                break
                
        except Exception as e:
            logger.error("Failed to fetch filings for CIK %s form %s: %s", cik, ft, e)
    
    # Sort by date descending
    results.sort(key=lambda x: x["filing_date"], reverse=True)
    return results[:count]


def _download_filing_pdf(cik: str, accession: str, primary_doc: str, symbol: str, form_type: str, filing_date: str) -> str | None:
    """
    下載 filing 的主要文件。如果是 HTML 則直接保存（SEC 大部分 10-K/10-Q 是 HTML）。
    回傳本地檔案路徑。
    """
    acc_no_dash = accession.replace("-", "")
    
    # Try to find the actual document (could be .htm, .html, or .pdf)
    base_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc_no_dash}"
    
    # Build filename
    safe_type = form_type.replace("/", "-")
    filename = f"{symbol}_{safe_type}_{filing_date}.htm"
    local_path = EARNINGS_DIR / filename
    
    if local_path.exists():
        logger.info("[%s] 已存在: %s", symbol, filename)
        return str(local_path)
    
    doc_url = f"{base_url}/{primary_doc}"
    try:
        resp = requests.get(doc_url, headers=HEADERS, timeout=60, stream=True)
        resp.raise_for_status()
        
        content_type = resp.headers.get("Content-Type", "")
        
        # If it's a PDF, save with .pdf extension
        if "pdf" in content_type or primary_doc.endswith(".pdf"):
            filename = f"{symbol}_{safe_type}_{filing_date}.pdf"
            local_path = EARNINGS_DIR / filename
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
        else:
            # Save as HTML (SEC filings are typically HTML)
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
        
        file_size = local_path.stat().st_size
        logger.info("[%s] 下載完成: %s (%d bytes)", symbol, filename, file_size)
        return str(local_path)
        
    except Exception as e:
        logger.error("[%s] 下載失敗 %s: %s", symbol, doc_url, e)
        return None


def download_earnings_for_ticker(symbol: str) -> list[dict]:
    """
    為指定 ticker 下載最新的 10-K / 10-Q 財報。
    回傳新增的報告列表。
    """
    cik_map = _get_cik_map()
    cik = cik_map.get(symbol.upper())
    if not cik:
        logger.warning("[%s] 找不到 CIK，跳過", symbol)
        return []
    
    filings = _get_latest_filings(cik, form_types=("10-K", "10-Q"), count=3)
    if not filings:
        logger.warning("[%s] 找不到財報 filing", symbol)
        return []
    
    collected = []
    for f in filings:
        # Check if already in DB
        title = f"{symbol} {f['form_type']} ({f['filing_date']})"
        existing = models.get_reports(100)
        already_exists = any(r["title"] == title for r in existing)
        if already_exists:
            logger.info("[%s] 已存在: %s", symbol, title)
            continue
        
        # Download the filing
        local_path = _download_filing_pdf(
            cik, f["accession"], f["primary_doc"],
            symbol, f["form_type"], f["filing_date"]
        )
        
        if not local_path:
            continue
        
        file_size = Path(local_path).stat().st_size
        
        # Save to DB
        report_data = {
            "title": title,
            "source": "SEC EDGAR",
            "url": f["doc_url"],
            "summary": f"{symbol} {f['form_type']} 年度/季度財報，提交日期 {f['filing_date']}",
            "analysis": "",
            "content": f"SEC EDGAR filing: {f['form_type']}\nFiling date: {f['filing_date']}\nURL: {f['doc_url']}",
            "file_path": local_path,
            "category": "earnings",
            "published_at": f["filing_date"],
        }
        
        report = models.add_report(report_data)
        
        # Also record as file
        models.add_file({
            "filename": Path(local_path).name,
            "category": "earnings",
            "file_path": local_path,
            "file_size": file_size,
            "report_id": report["id"] if report else None,
        })
        
        collected.append({
            "symbol": symbol,
            "form_type": f["form_type"],
            "filing_date": f["filing_date"],
            "file_path": local_path,
        })
        logger.info("[%s] 已下載: %s", symbol, title)
        
        # Be polite to SEC
        time.sleep(0.5)
    
    return collected


def download_all_earnings() -> dict:
    """為所有追蹤中的 ticker 下載最新財報。"""
    tickers = models.get_all_tickers()
    symbols = [t["symbol"] for t in tickers]
    
    result = {"total": 0, "by_ticker": {}, "errors": []}
    
    for sym in symbols:
        try:
            collected = download_earnings_for_ticker(sym)
            result["by_ticker"][sym] = len(collected)
            result["total"] += len(collected)
        except Exception as e:
            result["errors"].append(f"{sym}: {e}")
            logger.error("[%s] 下載財報失敗: %s", sym, e)
        
        time.sleep(1)  # Rate limit between tickers
    
    logger.info("財報下載完成: 共 %d 份新報告", result["total"])
    return result


if __name__ == "__main__":
    models.init_db()
    result = download_all_earnings()
    print(f"\n=== 財報下載完成 ===")
    print(f"新報告: {result['total']} 份")
    for sym, count in result["by_ticker"].items():
        print(f"  {sym}: {count} 份")
    if result["errors"]:
        print(f"錯誤: {result['errors']}")
