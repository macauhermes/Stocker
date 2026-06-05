"""
Stocker 時序數據庫 (Time-Series Database)
==========================================
使用獨立 SQLite 存放歷史價格數據，與核心 DB 分離以提升效能。

優化策略：
1. 獨立數據庫檔案 — 避免時序寫入影響核心 DB (tickers/reports/events) 的讀寫
2. 複合索引 — (ticker_id, date) 聯合索引加速範圍查詢
3. 批量寫入 — 使用 executemany + 事務一次性插入多筆數據
4. 日期範圍查詢 — 直接用 WHERE date >= ? 避免全表掃描
5. WAL 模式 — 支援並發讀寫，寫入不阻塞讀取
6. 內聯計算 — 技術指標 (MA/RSI/MACD) 直接在查詢層計算後返回
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "timeseries.db"
)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_tsdb():
    """Return a new SQLite connection to the time-series database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")      # 平衡效能與安全
    conn.execute("PRAGMA cache_size=-64000")         # 64MB page cache
    conn.execute("PRAGMA temp_store=MEMORY")         # temp tables in RAM
    return conn


def init_tsdb():
    """Create time-series tables and indexes."""
    conn = get_tsdb()
    try:
        cur = conn.cursor()

        # ── Daily OHLCV ────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker_id INTEGER NOT NULL,
                date      TEXT    NOT NULL,
                open      REAL,
                high      REAL,
                low       REAL,
                close     REAL,
                volume    INTEGER,
                UNIQUE(ticker_id, date)
            )
        """)

        # 複合索引：加速 "某 ticker 某日期範圍" 的查詢
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_ticker_date
            ON daily_prices(ticker_id, date)
        """)

        # ── Intraday Ticks (即時價格快取) ──────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS intraday_ticks (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker_id INTEGER NOT NULL,
                timestamp TEXT    NOT NULL,
                price     REAL,
                volume    INTEGER
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticks_ticker_ts
            ON intraday_ticks(ticker_id, timestamp)
        """)

        conn.commit()
        logger.info("Timeseries DB initialized at %s", DB_PATH)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Daily Prices — 批量讀寫
# ---------------------------------------------------------------------------

def save_daily_prices(ticker_id: int, prices: list[dict]):
    """
    批量寫入日線數據。
    prices: [{"date": "2026-01-01", "open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000000}, ...]
    使用 executemany + 事務，比逐筆 INSERT 快 10-50 倍。
    """
    if not prices:
        return

    conn = get_tsdb()
    try:
        conn.executemany(
            """INSERT OR IGNORE INTO daily_prices
                   (ticker_id, date, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (ticker_id, p["date"], p["open"], p["high"], p["low"],
                 p["close"], p.get("volume", 0))
                for p in prices
            ],
        )
        conn.commit()
        logger.info("Saved %d daily bars for ticker_id=%d", len(prices), ticker_id)
    finally:
        conn.close()


def get_daily_prices(ticker_id: int, days: int = 30) -> list[dict]:
    """
    取得最近 N 天的日線數據，按日期升序 (圖表用)。
    直接用 (ticker_id, date) 複合索引，避免全表掃描。
    """
    conn = get_tsdb()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT date, open, high, low, close, volume
               FROM daily_prices
               WHERE ticker_id = ? AND date >= ?
               ORDER BY date ASC""",
            (ticker_id, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_daily_prices_as_df(ticker_id: int, days: int = 365) -> pd.DataFrame:
    """
    取得日線數據並返回 pandas DataFrame (含 DatetimeIndex)。
    直接用於 calculate_indicators() 計算技術指標。
    """
    rows = get_daily_prices(ticker_id, days)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df = df.rename(columns={"close": "close", "open": "open", "high": "high", "low": "low"})
    return df


def get_latest_price(ticker_id: int) -> dict | None:
    """取得最新的單筆日線數據。"""
    conn = get_tsdb()
    try:
        row = conn.execute(
            """SELECT date, open, high, low, close, volume
               FROM daily_prices
               WHERE ticker_id = ?
               ORDER BY date DESC LIMIT 1""",
            (ticker_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_existing_dates(ticker_id: int) -> set[str]:
    """取得已存在的日期集合 (用於去重，避免重複下載)。"""
    conn = get_tsdb()
    try:
        rows = conn.execute(
            "SELECT date FROM daily_prices WHERE ticker_id = ?",
            (ticker_id,),
        ).fetchall()
        return {r["date"] for r in rows}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Intraday Ticks — 即時價格快取
# ---------------------------------------------------------------------------

def save_tick(ticker_id: int, price: float, volume: int = None):
    """寫入一筆即時價格 tick。"""
    conn = get_tsdb()
    try:
        conn.execute(
            """INSERT INTO intraday_ticks (ticker_id, timestamp, price, volume)
               VALUES (?, ?, ?, ?)""",
            (ticker_id, datetime.now().isoformat(), price, volume),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_ticks(ticker_id: int, limit: int = 100) -> list[dict]:
    """取得最近 N 筆 tick 數據。"""
    conn = get_tsdb()
    try:
        rows = conn.execute(
            """SELECT timestamp, price, volume
               FROM intraday_ticks
               WHERE ticker_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (ticker_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_latest_tick_price(ticker_id: int) -> float | None:
    """取得最新一筆 tick 的價格。"""
    conn = get_tsdb()
    try:
        row = conn.execute(
            """SELECT price FROM intraday_ticks
               WHERE ticker_id = ?
               ORDER BY timestamp DESC LIMIT 1""",
            (ticker_id,),
        ).fetchone()
        return row["price"] if row else None
    finally:
        conn.close()


def cleanup_old_ticks(days: int = 7):
    """清除 N 天前的 tick 數據，避免數據庫無限增長。"""
    conn = get_tsdb()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur = conn.execute(
            "DELETE FROM intraday_ticks WHERE timestamp < ?", (cutoff,)
        )
        conn.commit()
        if cur.rowcount > 0:
            logger.info("Cleaned up %d old ticks", cur.rowcount)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 技術指標計算 (從 DataFrame 計算後返回)
# ---------------------------------------------------------------------------

def calculate_indicators(prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    在 DataFrame 上計算 MA5/MA20/MA60、RSI14、MACD(12/26/9)。
    輸入需要有 'close' 欄位。
    """
    df = prices_df.copy()

    # 確保欄位名稱小寫
    if "Close" in df.columns and "close" not in df.columns:
        df = df.rename(columns={
            "Close": "close", "Open": "open", "High": "high", "Low": "low"
        })

    # ── Moving Averages ────────────────────────────────────────
    df["ma5"] = df["close"].rolling(window=5).mean()
    df["ma20"] = df["close"].rolling(window=20).mean()
    df["ma60"] = df["close"].rolling(window=60).mean()

    # ── RSI 14 (Wilder's smoothing) ────────────────────────────
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["rsi14"] = 100 - (100 / (1 + rs))

    # ── MACD (12, 26, 9) ──────────────────────────────────────
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


def get_chart_data(ticker_id: int, days: int = 90, indicators: list[str] = None) -> dict:
    """
    取得圖表數據，包含價格 + 技術指標。
    直接從時序 DB 讀取 → 計算指標 → 返回 JSON-ready dict。

    indicators: 要計算的指標列表，如 ["ma5", "ma20", "rsi14", "macd"]
                None = 全部計算
    """
    df = get_daily_prices_as_df(ticker_id, days)
    if df.empty:
        return {"dates": [], "prices": {}, "indicators": {}}

    df = calculate_indicators(df)

    all_indicators = ["ma5", "ma20", "ma60", "rsi14", "macd", "macd_signal", "macd_hist"]
    if indicators is None:
        indicators = all_indicators

    def _col(col):
        return [None if pd.isna(v) else round(float(v), 2) for v in df[col]]

    dates = [idx.strftime("%Y-%m-%d") for idx in df.index]

    result = {
        "dates": dates,
        "prices": {
            "open": _col("open"),
            "high": _col("high"),
            "low": _col("low"),
            "close": _col("close"),
            "volume": [int(v) if pd.notna(v) else 0 for v in df["volume"]],
        },
        "indicators": {ind: _col(ind) for ind in indicators if ind in df.columns},
    }

    logger.info("Chart data for ticker_id=%d: %d days, indicators=%s",
                ticker_id, len(dates), indicators)
    return result
