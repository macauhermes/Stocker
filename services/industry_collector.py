"""
Industry Collector — collects industry-level news and reports for each
sector represented in the tracked tickers.

Sources: Yahoo Finance sector pages, MarketWatch, and public financial news.
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

# Ensure project root on sys.path so `models` can be imported
sys.path.insert(0, os.path.expanduser("~/repos/Stocker"))

import models

logger = logging.getLogger(__name__)

# ── Path constants ──────────────────────────────────────────────────
DATA_DIR = Path(os.path.expanduser("~/repos/Stocker/data"))
FILES_DIR = DATA_DIR / "files"
NEWS_DIR = FILES_DIR / "news"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ── Sector → Yahoo Finance URL mapping ──────────────────────────────
_SECTOR_URL_MAP = {
    "Technology": "https://finance.yahoo.com/sectors/technology/",
    "Healthcare": "https://finance.yahoo.com/sectors/healthcare/",
    "Health Care": "https://finance.yahoo.com/sectors/healthcare/",
    "Consumer Cyclical": "https://finance.yahoo.com/sectors/consumer-cyclical/",
    "Consumer Defensive": "https://finance.yahoo.com/sectors/consumer-defensive/",
    "Financial Services": "https://finance.yahoo.com/sectors/financial-services/",
    "Financial": "https://finance.yahoo.com/sectors/financial-services/",
    "Financials": "https://finance.yahoo.com/sectors/financial-services/",
    "Energy": "https://finance.yahoo.com/sectors/energy/",
    "Industrials": "https://finance.yahoo.com/sectors/industrials/",
    "Basic Materials": "https://finance.yahoo.com/sectors/basic-materials/",
    "Communication Services": "https://finance.yahoo.com/sectors/communication-services/",
    "Utilities": "https://finance.yahoo.com/sectors/utilities/",
    "Real Estate": "https://finance.yahoo.com/sectors/real-estate/",
}


# ── Helper: map sector name to URL ─────────────────────────────────
def _get_sector_url(sector: str) -> str:
    """Return Yahoo Finance sector page URL for a sector name.

    Tries an exact match first, then a case-insensitive partial match.
    Falls back to a generic search URL.
    """
    if not sector:
        return ""

    # Exact match
    if sector in _SECTOR_URL_MAP:
        return _SECTOR_URL_MAP[sector]

    # Case-insensitive match
    sector_lower = sector.lower().strip()
    for key, url in _SECTOR_URL_MAP.items():
        if key.lower() == sector_lower:
            return url

    # Partial match
    for key, url in _SECTOR_URL_MAP.items():
        if sector_lower in key.lower() or key.lower() in sector_lower:
            return url

    # Fallback: construct a search-style URL with the raw sector name
    slug = sector_lower.replace(" ", "-")
    return f"https://finance.yahoo.com/sectors/{slug}/"


# ── Deduplication helper ────────────────────────────────────────────
def _is_duplicate(title: str, sector: str) -> bool:
    """Check if a report with the same title already exists for this sector."""
    safe_sector = re.sub(r"[^\w\-]", "_", sector[:40]).strip("_")
    pattern = f"{safe_sector}_industry_"
    existing_files = list(NEWS_DIR.glob(f"{pattern}*.txt"))
    for f in existing_files:
        # Read the first line which stores the title
        try:
            first_line = f.read_text(encoding="utf-8").split("\n", 1)[0]
            if first_line.strip() == title.strip():
                return True
        except Exception:
            continue
    return False


# ── Collect news for a specific sector ──────────────────────────────
def collect_sector_news(sector: str) -> list[dict]:
    """Scrape industry news for a single sector from Yahoo Finance.

    Returns a list of newly-saved report dicts.
    """
    collected: list[dict] = []
    url = _get_sector_url(sector)

    if not url:
        logger.warning("[%s] No URL mapping found, skipping", sector)
        return collected

    logger.info("[%s] Fetching industry news from %s", sector, url)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("[%s] Failed to fetch sector page: %s", sector, exc)
        raise

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove boilerplate
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    articles: list[dict] = []

    # Strategy 1: look for news items in common Yahoo Finance layouts
    #   - <li> items inside containers with "news" or "stream" in class/id
    #   - Each item usually has an <a> with href and text for the headline
    news_containers = soup.find_all(
        ["div", "ul", "section"],
        class_=re.compile(r"news|stream|feed|stories", re.I),
    )
    for container in news_containers:
        for li in container.find_all("li"):
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
            headline = a_tag.get_text(strip=True)
            if not headline or len(headline) < 10:
                continue
            link = a_tag["href"]
            if link.startswith("/"):
                link = "https://finance.yahoo.com" + link

            # Try to get a summary paragraph near the link
            p_tag = li.find("p")
            summary = p_tag.get_text(strip=True) if p_tag else ""

            articles.append({
                "title": headline,
                "url": link,
                "summary": summary,
            })

    # Strategy 2: fallback — grab all <a> tags that look like news headlines
    if not articles:
        for a_tag in soup.find_all("a", href=True):
            text = a_tag.get_text(strip=True)
            href = a_tag["href"]
            # Heuristic: headlines are usually 20-200 chars and link to articles
            if (
                20 <= len(text) <= 200
                and ("finance.yahoo.com" in href or href.startswith("/news/"))
            ):
                if href.startswith("/"):
                    href = "https://finance.yahoo.com" + href
                articles.append({"title": text, "url": href, "summary": ""})

    # Strategy 3: try MarketWatch as secondary source
    if not articles:
        try:
            mw_slug = sector.lower().replace(" ", "-")
            mw_url = f"https://www.marketwatch.com/investing/sector/{mw_slug}"
            logger.info("[%s] Trying MarketWatch fallback: %s", sector, mw_url)
            time.sleep(0.5)
            resp2 = requests.get(mw_url, headers=HEADERS, timeout=15)
            resp2.raise_for_status()
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            for tag in soup2(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            for a_tag in soup2.find_all("a", href=True):
                text = a_tag.get_text(strip=True)
                href = a_tag["href"]
                if 20 <= len(text) <= 200 and "marketwatch.com" in href:
                    articles.append({"title": text, "url": href, "summary": ""})
        except Exception as exc:
            logger.debug("[%s] MarketWatch fallback failed: %s", sector, exc)

    # Deduplicate and save
    seen_titles: set[str] = set()
    for article in articles:
        title = article["title"]
        if not title or title in seen_titles:
            continue
        if _is_duplicate(title, sector):
            logger.debug("[%s] Skipping duplicate: %s", sector, title[:50])
            continue
        seen_titles.add(title)

        safe_sector = re.sub(r"[^\w\-]", "_", sector[:40]).strip("_")
        safe_title = re.sub(r"[^\w\-]", "_", title[:60]).strip("_")
        file_name = f"{safe_sector}_industry_{safe_title}.txt"
        file_path = NEWS_DIR / file_name

        content = article.get("summary") or title
        file_path.write_text(
            f"{title}\n\n{content}\n\nSource: {article.get('url', '')}",
            encoding="utf-8",
        )

        report_data = {
            "title": title,
            "source": "Industry News",
            "url": article.get("url", ""),
            "summary": article.get("summary", ""),
            "analysis": "",
            "content": content,
            "file_path": str(file_path),
            "category": "industry",
            "published_at": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "symbol": sector,  # sector-level, not a single ticker
        }

        try:
            if hasattr(models, "add_report"):
                report_id = models.add_report(report_data)
                report_data["id"] = report_id
        except Exception as exc:
            logger.error("[%s] Failed to save report to DB: %s", sector, exc)

        collected.append(report_data)
        logger.info("[%s] Saved industry news: %s", sector, title[:60])

    logger.info("[%s] Collected %d new industry reports", sector, len(collected))
    return collected


# ── Main entry point ────────────────────────────────────────────────
def collect_industry_news() -> dict:
    """Collect industry-level news for every sector represented in tracked tickers.

    Returns:
        {
            "total_new": int,
            "by_sector": {sector_name: count},
            "errors": [str],
        }
    """
    result: dict = {"total_new": 0, "by_sector": {}, "errors": []}

    # Get all sectors
    try:
        sectors = models.get_sectors() if hasattr(models, "get_sectors") else []
    except Exception as exc:
        msg = f"Failed to get sectors: {exc}"
        logger.error(msg)
        result["errors"].append(msg)
        return result

    if not sectors:
        logger.warning("No sectors found in database")
        result["errors"].append("No sectors found")
        return result

    logger.info("Starting industry news collection for %d sectors", len(sectors))

    for sector_info in sectors:
        # sectors may be a list of strings or dicts with a 'sector' key
        if isinstance(sector_info, dict):
            sector_name = (
                sector_info.get("sector")
                or sector_info.get("name")
                or sector_info.get("sector_name", "")
            )
        else:
            sector_name = str(sector_info)

        if not sector_name:
            continue

        try:
            reports = collect_sector_news(sector_name)
            count = len(reports)
            result["by_sector"][sector_name] = count
            result["total_new"] += count

            # Rate limiting: 0.5 s between requests
            time.sleep(0.5)

        except Exception as exc:
            err_msg = f"{sector_name}: {exc}"
            result["errors"].append(err_msg)
            logger.error("Error collecting sector '%s': %s", sector_name, exc)

    logger.info(
        "Industry news collection complete — %d new reports across %d sectors",
        result["total_new"],
        len(result["by_sector"]),
    )
    return result


# ── CLI convenience ─────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    summary = collect_industry_news()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
