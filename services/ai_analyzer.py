"""
AI 分析服務 — 使用 OpenAI API 對金融報告進行摘要與深度分析。
所有 AI 輸出使用中文。若 API Key 未設定則回退至 mock 分析。
"""
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── OpenAI 客戶端（惰性初始化） ────────────────────────────────────
_client = None


def get_openai_client():
    """
    取得 OpenAI 客戶端。
    優先使用環境變數 OPENAI_API_KEY，未設定則回傳 None（觸發 mock 分析）。
    """
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.warning("OPENAI_API_KEY 未設定，AI 分析將使用 mock 輸出")
        return None

    try:
        from openai import OpenAI
        _client = OpenAI(api_key=api_key)
        logger.info("OpenAI 客戶端初始化成功")
        return _client
    except ImportError:
        logger.error("openai 套件未安裝，請執行 pip install openai")
        return None
    except Exception as exc:
        logger.error("OpenAI 客戶端初始化失敗: %s", exc)
        return None


# ── 主分析函數 ────────────────────────────────────────────────────
def analyze_report(report_content: str, title: str = "") -> dict:
    """
    使用 OpenAI API 分析報告內容，回傳：
    {
        "summary": "約50字中文摘要",
        "analysis": "完整分析文字（含影響評級、關聯股票、關鍵數據、投資建議）"
    }

    若 API 不可用，回傳 mock 分析結果。
    """
    if not report_content or not report_content.strip():
        return _mock_analysis(title, "（內容為空）")

    client = get_openai_client()
    if client is None:
        return _mock_analysis(title, report_content)

    return _openai_analysis(client, report_content, title)


# ── OpenAI 實際分析 ──────────────────────────────────────────────
def _openai_analysis(client, content: str, title: str) -> dict:
    """呼叫 OpenAI API 進行分析。"""
    # 截取過長內容以控制 token
    truncated = content[:8000] if len(content) > 8000 else content

    system_prompt = """你是一位專業的金融分析師，擅長解讀美股相關報告和新聞。
請用繁體中文完成以下任務。

請嚴格按照以下 JSON 格式回覆，不要包含其他文字：
{
  "summary": "不超過50個中文字的摘要",
  "analysis": "完整分析，包含以下段落：\\n1. 影響評級（正面/中性/負面）及理由\\n2. 關聯股票（列出相關 ticker）\\n 3. 關鍵數據要點\\n4. 投資建議要點"
}"""

    user_prompt = f"""請分析以下金融報告：

標題：{title or '（無標題）'}

內容：
{truncated}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )

        raw = response.choices[0].message.content.strip()

        # 嘗試解析 JSON（可能帶有 markdown 包裹）
        json_str = raw
        if "```" in raw:
            # 去除 ```json ... ``` 包裹
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    json_str = part
                    break

        try:
            result = json.loads(json_str)
            summary = result.get("summary", "")[:100]
            analysis = result.get("analysis", "")
        except json.JSONDecodeError:
            # JSON 解析失敗，直接使用原始文字
            summary = raw[:50] if len(raw) >= 50 else raw
            analysis = raw
            logger.warning("OpenAI 回覆非標準 JSON，使用原始文字")

        return {"summary": summary, "analysis": analysis}

    except Exception as exc:
        logger.error("OpenAI API 呼叫失敗: %s，回退至 mock", exc)
        return _mock_analysis(title, content)


# ── Mock 分析（API 不可用時的備用方案）────────────────────────────
def _mock_analysis(title: str, content: str) -> dict:
    """當 OpenAI API 不可用時，提供基礎的本地分析。"""
    # 簡單提取可能的 ticker
    import re
    tickers = list(set(re.findall(r'\b[A-Z]{2,5}\b', content or title)))

    # 依據標題/內容的簡單情緒判斷
    positive_kw = ["up", "rise", "gain", "bullish", "upgrade", "beat", "surge", "record",
                    "上漲", "利多", "看好", "突破", "增長", "創新高"]
    negative_kw = ["down", "fall", "drop", "bearish", "downgrade", "miss", "decline", "loss",
                    "下跌", "利空", "看空", "暴跌", "虧損", "衰退"]

    text_lower = (content + " " + title).lower()
    pos_count = sum(1 for kw in positive_kw if kw.lower() in text_lower)
    neg_count = sum(1 for kw in negative_kw if kw.lower() in text_lower)

    if pos_count > neg_count:
        impact = "正面"
        suggestion = "報告傳達正面信號，可考慮適度增持相關標的。"
    elif neg_count > pos_count:
        impact = "負面"
        suggestion = "報告傳達負面信號，建議審慎評估風險，考慮減持。"
    else:
        impact = "中性"
        suggestion = "報告信號中性，建議持續觀察後續發展。"

    # 摘要（截取前50字）
    raw_summary = title or (content[:80] if content else "（無內容）")
    summary = raw_summary[:50] if len(raw_summary) <= 50 else raw_summary[:47] + "..."

    # 分析
    ticker_str = "、".join(tickers[:5]) if tickers else "待確認"
    analysis = (
        f"【AI 分析報告】（本地基礎分析 — OpenAI API 未連接）\n\n"
        f"1. 影響評級：{impact}\n"
        f"   基於關鍵詞分析判斷市場情緒偏向{'正面' if pos_count > neg_count else '負面' if neg_count > pos_count else '中性'}。\n\n"
        f"2. 關聯股票：{ticker_str}\n"
        f"   從報告內容中識別到以上可能相關的 ticker。\n\n"
        f"3. 關鍵數據要點：\n"
        f"   - 報告來源：{title[:40] or '未知'}\n"
        f"   - 內容長度：{len(content)} 字符\n\n"
        f"4. 投資建議要點：\n"
        f"   {suggestion}\n\n"
        f"（提示：設定 OPENAI_API_KEY 環境變數可啟用完整 AI 分析功能）"
    )

    return {"summary": summary, "analysis": analysis}
