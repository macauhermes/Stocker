"""
投行報告抓取服務
================
從投行網站抓取 PDF 報告連結
"""
import os
import sys
import re
import logging
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path(os.path.expanduser("~/repos/Stocker/data"))
REPORTS_DIR = DATA_DIR / "files" / "bank_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# 常見投行報告頁面 URL 模式
REPORT_URL_PATTERNS = [
    "/research",
    "/insights",
    "/publications",
    "/analysis",
    "/reports",
    "/market-insights",
    "/investment-banking/research",
    "/global-research",
]


def _find_pdf_links(url: str, base_url: str = None) -> list[dict]:
    """
    從網頁中找出 PDF 連結
    返回 [{url, title, date}]
    """
    if base_url is None:
        base_url = url
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        pdf_links = []
        
        # 找出所有連結
        for a in soup.find_all("a", href=True):
            href = a["href"]
            
            # 檢查是否為 PDF 連結
            is_pdf = False
            full_url = None
            
            # 直接 PDF 連結
            if href.lower().endswith(".pdf"):
                is_pdf = True
                full_url = urljoin(base_url, href)
            
            # 連結文字包含 "pdf" 或 "download"
            link_text = a.get_text(strip=True).lower()
            if "pdf" in link_text or "download" in link_text:
                if href and not href.startswith("#"):
                    full_url = urljoin(base_url, href)
                    # 檢查目標是否為 PDF
                    try:
                        head_resp = requests.head(full_url, headers=HEADERS, timeout=10, allow_redirects=True)
                        content_type = head_resp.headers.get("Content-Type", "")
                        if "pdf" in content_type:
                            is_pdf = True
                    except:
                        pass
            
            if is_pdf and full_url:
                # 嘗試從連結文字或周圍元素獲取標題
                title = a.get_text(strip=True)
                if not title or len(title) < 5:
                    # 嘗試從父元素獲取
                    parent = a.find_parent(["div", "li", "article"])
                    if parent:
                        title = parent.get_text(strip=True)[:100]
                
                if not title:
                    title = Path(urlparse(full_url).path).stem
                
                pdf_links.append({
                    "url": full_url,
                    "title": title[:200],
                    "date": _extract_date(a),
                })
        
        return pdf_links
    
    except Exception as e:
        logger.warning("Failed to fetch PDFs from %s: %s", url, e)
        return []


def _extract_date(element) -> str:
    """從元素或其父元素中提取日期"""
    # 常見日期格式
    date_patterns = [
        r"\d{4}-\d{2}-\d{2}",
        r"\d{2}/\d{2}/\d{4}",
        r"\d{2}\.\d{2}\.\d{4}",
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}",
    ]
    
    # 檢查元素本身
    text = element.get_text(strip=True)
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    # 檢查父元素
    parent = element.find_parent(["div", "li", "article", "tr"])
    if parent:
        text = parent.get_text(strip=True)
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
    
    # 檢查 data 屬性
    for attr in ["data-date", "data-published", "datetime"]:
        date_val = element.get(attr)
        if date_val:
            return date_val
    
    return None


def check_bank_for_reports(bank_id: int) -> dict:
    """
    檢查單個投行的新報告
    返回 {bank_id, bank_name, new_reports, errors}
    """
    bank = models.get_investment_bank(bank_id)
    if not bank:
        return {"error": "Bank not found"}
    
    result = {
        "bank_id": bank_id,
        "bank_name": bank["name"],
        "new_reports": 0,
        "errors": [],
    }
    
    # 更新最後檢查時間
    models.update_investment_bank(bank_id, {"last_check": datetime.now().isoformat()})
    
    report_url = bank["report_url"]
    if not report_url:
        result["errors"].append("No report URL configured")
        return result
    
    try:
        # 找出 PDF 連結
        pdf_links = _find_pdf_links(report_url, bank["website_url"])
        
        for pdf in pdf_links:
            # 嘗試新增報告
            report = models.add_bank_report(
                bank_id=bank_id,
                title=pdf["title"],
                url=pdf["url"],
                pdf_url=pdf["url"],
                published_at=pdf["date"],
            )
            
            if report:
                result["new_reports"] += 1
                logger.info("[%s] New report found: %s", bank["name"], pdf["title"][:50])
        
        # 更新最後報告時間
        if result["new_reports"] > 0:
            models.update_investment_bank(bank_id, {"last_report": datetime.now().isoformat()})
    
    except Exception as e:
        result["errors"].append(str(e))
        logger.error("[%s] Error checking reports: %s", bank["name"], e)
    
    return result


def check_all_banks() -> dict:
    """
    檢查所有已啟用的投行
    返回 {total_new, by_bank, errors}
    """
    banks = models.get_enabled_investment_banks()
    
    result = {
        "total_new": 0,
        "by_bank": {},
        "errors": [],
    }
    
    for bank in banks:
        try:
            bank_result = check_bank_for_reports(bank["id"])
            result["by_bank"][bank["name"]] = bank_result.get("new_reports", 0)
            result["total_new"] += bank_result.get("new_reports", 0)
            if bank_result.get("errors"):
                result["errors"].extend([f"{bank['name']}: {e}" for e in bank_result["errors"]])
        except Exception as e:
            result["errors"].append(f"{bank['name']}: {str(e)}")
        
        time.sleep(2)  # Rate limiting
    
    logger.info("投行報告檢查完成: 共 %d 份新報告", result["total_new"])
    return result


def download_report_pdf(report_id: int) -> dict:
    """
    下載報告 PDF
    返回 {success, file_path, error}
    """
    conn = models.get_db()
    try:
        report = conn.execute(
            "SELECT br.*, ib.name as bank_name FROM bank_reports br JOIN investment_banks ib ON br.bank_id = ib.id WHERE br.id = ?",
            (report_id,),
        ).fetchone()
        
        if not report:
            return {"success": False, "error": "Report not found"}
        
        if report["downloaded"]:
            return {"success": True, "file_path": report["file_path"], "already_downloaded": True}
        
        pdf_url = report["pdf_url"] or report["url"]
        if not pdf_url:
            return {"success": False, "error": "No PDF URL"}
        
        # 下載 PDF
        resp = requests.get(pdf_url, headers=HEADERS, timeout=60, stream=True)
        resp.raise_for_status()
        
        # 生成檔名
        bank_name = report["bank_name"].replace(" ", "_")[:20]
        title_slug = re.sub(r'[^\w\s-]', '', report["title"][:50]).strip().replace(" ", "_")
        filename = f"{bank_name}_{title_slug}_{datetime.now().strftime('%Y%m%d')}.pdf"
        file_path = REPORTS_DIR / filename
        
        # 保存檔案
        with open(file_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        
        # 標記為已下載
        models.mark_report_downloaded(report_id, str(file_path))
        
        # 同時記錄到 files 表
        models.add_file({
            "filename": filename,
            "category": "bank_report",
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "report_id": None,
        })
        
        logger.info("Downloaded: %s", filename)
        return {"success": True, "file_path": str(file_path)}
    
    except Exception as e:
        logger.error("Failed to download report %d: %s", report_id, e)
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


if __name__ == "__main__":
    models.init_db()
    
    # 測試：檢查所有投行
    result = check_all_banks()
    print(f"\n=== 投行報告檢查完成 ===")
    print(f"新報告: {result['total_new']} 份")
    for bank, count in result["by_bank"].items():
        print(f"  {bank}: {count} 份")
    if result["errors"]:
        print(f"錯誤: {result['errors']}")
