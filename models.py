"""
Stocker - SQLite Database Models
================================
Raw sqlite3 models for the Stocker stock tracking app.
No ORM used — direct SQL with helper functions.
"""

import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "stocker.db")


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def get_db():
    """Return a new SQLite connection with Row factory enabled."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Create all tables if they do not already exist."""
    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tickers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol      TEXT    NOT NULL UNIQUE,
                name        TEXT    NOT NULL,
                sector      TEXT,
                shares_held REAL    DEFAULT 0,
                cost_basis  REAL    DEFAULT 0,
                added_at    TEXT    DEFAULT (datetime('now'))
            )
        """)

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
                FOREIGN KEY (ticker_id) REFERENCES tickers(id) ON DELETE CASCADE,
                UNIQUE(ticker_id, date)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT,
                source        TEXT,
                url           TEXT,
                summary       TEXT,
                analysis      TEXT,
                content       TEXT,
                file_path     TEXT,
                category      TEXT,
                published_at  TEXT,
                created_at    TEXT DEFAULT (datetime('now'))
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker_id   INTEGER NOT NULL,
                event_type  TEXT,
                event_date  TEXT,
                title       TEXT,
                dismissed   INTEGER DEFAULT 0,
                dismissed_at TEXT,
                FOREIGN KEY (ticker_id) REFERENCES tickers(id) ON DELETE CASCADE
            )
        """)

        # Custom JSONPath data sources (wealthlens-inspired, allows plugging in
        # any fund / bond / crypto API for which the format isn't covered by
        # the built-in fallback chain).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS custom_data_sources (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                url           TEXT    NOT NULL,
                date_path     TEXT    NOT NULL,
                price_path    TEXT    NOT NULL,
                open_path     TEXT,
                high_path     TEXT,
                low_path      TEXT,
                volume_path   TEXT,
                symbol_match  TEXT,
                priority      INTEGER DEFAULT 100,
                enabled       INTEGER DEFAULT 1,
                notes         TEXT,
                created_at    TEXT    DEFAULT (datetime('now'))
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT    NOT NULL,
                category    TEXT,
                file_path   TEXT,
                file_size   INTEGER,
                report_id   INTEGER,
                created_at  TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL
            )
        """)

        # Watchlist groups (v3.3 — user-defined ticker groupings)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_groups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                description TEXT,
                color       TEXT    DEFAULT '#4fc3f7',
                sort_order  INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_group_tickers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id    INTEGER NOT NULL REFERENCES watchlist_groups(id) ON DELETE CASCADE,
                ticker_id   INTEGER NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
                sort_order  INTEGER DEFAULT 0,
                UNIQUE(group_id, ticker_id)
            )
        """)

        # Price alerts (v3.4 — user-defined thresholds; triggers event when price crosses)
        # threshold_type: 'high' (price >= threshold) or 'low' (price <= threshold)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker_id         INTEGER NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
                threshold_type    TEXT    NOT NULL CHECK(threshold_type IN ('high','low')),
                threshold_price   REAL    NOT NULL,
                enabled           INTEGER DEFAULT 1,
                note              TEXT,
                last_triggered_at TEXT,
                created_at        TEXT    DEFAULT (datetime('now'))
            )
        """)

        # Portfolio snapshots (v3.4.2 — daily end-of-day snapshot of total portfolio value)
        # Used for P&L history chart. snapshot_date is the day the snapshot represents
        # (YYYY-MM-DD). UNIQUE constraint guarantees one snapshot per day.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date   TEXT    NOT NULL UNIQUE,
                total_value     REAL    NOT NULL DEFAULT 0,
                total_cost      REAL    NOT NULL DEFAULT 0,
                total_pnl       REAL    NOT NULL DEFAULT 0,
                pnl_pct         REAL    NOT NULL DEFAULT 0,
                holdings_count  INTEGER NOT NULL DEFAULT 0,
                captured_at     TEXT    DEFAULT (datetime('now'))
            )
        """)

        # Investment banks (v3.3 — 投行 observation list; scrape PDFs from each bank)
        # Originally created by external migration; moved here so fresh checkouts
        # work without manual schema setup (v3.4.43).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS investment_banks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                short_name   TEXT,
                website_url  TEXT,
                report_url   TEXT,
                logo_url     TEXT,
                enabled      INTEGER DEFAULT 1,
                added_at     TEXT,
                last_check   TEXT,
                last_report  TEXT
            )
        """)

        # Bank reports (v3.3 — PDFs scraped from investment bank websites)
        # bank_id FK to investment_banks; ON DELETE CASCADE cleans up reports when
        # a bank is removed.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bank_reports (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id       INTEGER NOT NULL REFERENCES investment_banks(id) ON DELETE CASCADE,
                title         TEXT NOT NULL,
                url           TEXT,
                pdf_url       TEXT,
                published_at  TEXT,
                downloaded    INTEGER DEFAULT 0,
                file_path     TEXT,
                created_at    TEXT
            )
        """)

        # Helpful indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_ticker ON daily_prices(ticker_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_date   ON daily_prices(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_ticker ON events(ticker_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_files_report  ON files(report_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wgt_group     ON watchlist_group_tickers(group_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wgt_ticker    ON watchlist_group_tickers(ticker_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ticker ON price_alerts(ticker_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_enabled ON price_alerts(enabled)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_date ON portfolio_snapshots(snapshot_date DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bank_reports_bank ON bank_reports(bank_id)")

        # Backward-compatible migration: add archived columns if missing
        for col, ddl in [
            ("archived",    "ALTER TABLE tickers ADD COLUMN archived INTEGER DEFAULT 0"),
            ("archived_at", "ALTER TABLE tickers ADD COLUMN archived_at TEXT"),
        ]:
            cur.execute("SELECT * FROM pragma_table_info('tickers') WHERE name = ?", (col,))
            if cur.fetchone() is None:
                cur.execute(ddl)

        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tickers CRUD
# ---------------------------------------------------------------------------

def add_ticker(symbol: str, name: str, sector: str = None):
    """Insert a new ticker or restore an archived one. Returns the ticker row."""
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT * FROM tickers WHERE UPPER(symbol) = ?", (symbol.upper(),)
        ).fetchone()
        if existing and existing["archived"]:
            # Restore archived ticker, preserving shares_held and cost_basis
            conn.execute(
                "UPDATE tickers SET archived = 0, archived_at = NULL, name = ?, sector = ? WHERE UPPER(symbol) = ?",
                (name, sector, symbol.upper()),
            )
            conn.commit()
            return conn.execute(
                "SELECT * FROM tickers WHERE UPPER(symbol) = ?", (symbol.upper(),)
            ).fetchone()
        cur = conn.execute(
            "INSERT INTO tickers (symbol, name, sector) VALUES (?, ?, ?)",
            (symbol.upper(), name, sector),
        )
        conn.commit()
        return conn.execute("SELECT * FROM tickers WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_all_tickers():
    """Return every active (non-archived) ticker, ordered by symbol."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM tickers WHERE archived = 0 ORDER BY symbol"
        ).fetchall()
    finally:
        conn.close()


def get_ticker(symbol: str):
    """Return a single ticker by its symbol (case-insensitive)."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM tickers WHERE UPPER(symbol) = ?", (symbol.upper(),)
        ).fetchone()
    finally:
        conn.close()


def update_ticker(symbol: str, kwargs: dict):
    """Update arbitrary columns on a ticker identified by *symbol*.

    *kwargs* keys must be valid column names.  Returns the updated row.
    """
    allowed = {"name", "sector", "shares_held", "cost_basis"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return get_ticker(symbol)

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [symbol.upper()]

    conn = get_db()
    try:
        conn.execute(
            f"UPDATE tickers SET {set_clause} WHERE UPPER(symbol) = ?", values
        )
        conn.commit()
        return conn.execute(
            "SELECT * FROM tickers WHERE UPPER(symbol) = ?", (symbol.upper(),)
        ).fetchone()
    finally:
        conn.close()


def archive_ticker(symbol: str):
    """Soft-delete a ticker by setting archived=1. Returns True if updated."""
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE tickers SET archived = 1, archived_at = datetime('now') WHERE UPPER(symbol) = ? AND archived = 0",
            (symbol.upper(),),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def restore_ticker(symbol: str):
    """Restore an archived ticker. Returns True if updated."""
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE tickers SET archived = 0, archived_at = NULL WHERE UPPER(symbol) = ? AND archived = 1",
            (symbol.upper(),),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_archived_tickers():
    """Return every archived ticker, ordered by symbol."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM tickers WHERE archived = 1 ORDER BY symbol"
        ).fetchall()
    finally:
        conn.close()


def get_sectors():
    """Return distinct sector values from active (non-archived) tickers."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT sector FROM tickers WHERE archived = 0 AND sector IS NOT NULL ORDER BY sector"
        ).fetchall()
        return [row["sector"] for row in rows]
    finally:
        conn.close()


def get_tickers_by_sector(sector: str):
    """Return active tickers in a given sector, ordered by symbol."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM tickers WHERE archived = 0 AND UPPER(sector) = UPPER(?) ORDER BY symbol",
            (sector,),
        ).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Daily Prices
# ---------------------------------------------------------------------------

def add_daily_price(ticker_id: int, date: str, o: float, h: float,
                    l: float, c: float, vol: int):
    """Insert (or ignore duplicate) a daily price bar."""
    conn = get_db()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO daily_prices
                   (ticker_id, date, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ticker_id, date, o, h, l, c, vol),
        )
        conn.commit()
    finally:
        conn.close()


def get_prices(ticker_id: int, days: int = 30):
    """Return the last *days* of price bars for a ticker, newest first."""
    conn = get_db()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return conn.execute(
            """SELECT * FROM daily_prices
               WHERE ticker_id = ? AND date >= ?
               ORDER BY date DESC""",
            (ticker_id, cutoff),
        ).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def add_report(kwargs: dict):
    """Insert a report from a dict of field→value pairs. Returns the row."""
    allowed = {
        "title", "source", "url", "summary", "analysis",
        "content", "file_path", "category", "published_at",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))

    conn = get_db()
    try:
        cur = conn.execute(
            f"INSERT INTO reports ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )
        conn.commit()
        return conn.execute("SELECT * FROM reports WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_reports(limit: int = 50):
    """Return the most recent reports."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    finally:
        conn.close()


def get_report(id: int):
    """Return a single report by id."""
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM reports WHERE id = ?", (id,)).fetchone()
    finally:
        conn.close()


def search_reports(query: str = None, category: str = None, source: str = None,
                   ticker: str = None, limit: int = 50):
    """
    Search/filter reports by free-text + category + source + ticker.

    - `query` matches title OR summary LIKE %query% (case-insensitive)
    - `category`, `source` are exact-match filters (case-insensitive)
    - `ticker` extracts symbol from file_path prefix (e.g. 'GLW_10-Q...' → GLW)
    - All filters AND together; any None means "don't filter on this"
    - Empty `query`/category/source/ticker treated as None
    - Returns Row objects ordered by created_at DESC, capped at `limit`

    v3.4.3 — P3 feature: enables user-facing report search.
    """
    conn = get_db()
    try:
        where = []
        params = []

        # Free-text on title/summary
        if query and query.strip():
            where.append("(LOWER(title) LIKE ? OR LOWER(IFNULL(summary, '')) LIKE ?)")
            like = f"%{query.strip().lower()}%"
            params.extend([like, like])

        if category and category.strip():
            where.append("LOWER(category) = ?")
            params.append(category.strip().lower())

        if source and source.strip():
            where.append("LOWER(source) = ?")
            params.append(source.strip().lower())

        # Ticker derives from file_path basename prefix: data/files/<category>/<SYMBOL>_...
        # file_path is absolute (e.g. '/home/.../data/files/earnings/GLW_10-Q...'),
        # so use LIKE on the suffix '<SYMBOL>_' after the last '/'.
        if ticker and ticker.strip():
            t = ticker.strip().upper()
            where.append("file_path LIKE ?")
            params.append(f"%/{t}_%")

        sql = "SELECT * FROM reports"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def count_search_results(query: str = None, category: str = None, source: str = None,
                         ticker: str = None) -> int:
    """
    Count results for the same filters as search_reports, without the LIMIT.
    Used for the API response to expose total result count alongside results.
    """
    conn = get_db()
    try:
        where = []
        params = []

        if query and query.strip():
            where.append("(LOWER(title) LIKE ? OR LOWER(IFNULL(summary, '')) LIKE ?)")
            like = f"%{query.strip().lower()}%"
            params.extend([like, like])

        if category and category.strip():
            where.append("LOWER(category) = ?")
            params.append(category.strip().lower())

        if source and source.strip():
            where.append("LOWER(source) = ?")
            params.append(source.strip().lower())

        if ticker and ticker.strip():
            t = ticker.strip().upper()
            where.append("file_path LIKE ?")
            params.append(f"%/{t}_%")

        sql = "SELECT COUNT(*) as c FROM reports"
        if where:
            sql += " WHERE " + " AND ".join(where)

        row = conn.execute(sql, params).fetchone()
        return row['c'] if row else 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def add_event(kwargs: dict):
    """Insert an event from a dict. Returns the new row."""
    allowed = {"ticker_id", "event_type", "event_date", "title"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))

    conn = get_db()
    try:
        cur = conn.execute(
            f"INSERT INTO events ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )
        conn.commit()
        return conn.execute("SELECT * FROM events WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_active_events():
    """Return all non-dismissed events, soonest first."""
    conn = get_db()
    try:
        return conn.execute(
            """SELECT e.*, t.symbol FROM events e
               JOIN tickers t ON t.id = e.ticker_id
               WHERE e.dismissed = 0
               ORDER BY e.event_date ASC"""
        ).fetchall()
    finally:
        conn.close()


def dismiss_event(id: int):
    """Mark an event as dismissed. Returns True if a row was updated."""
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE events SET dismissed = 1, dismissed_at = datetime('now') WHERE id = ?",
            (id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def add_file(kwargs: dict):
    """Insert a file record from a dict. Returns the new row."""
    allowed = {"filename", "category", "file_path", "file_size", "report_id"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))

    conn = get_db()
    try:
        cur = conn.execute(
            f"INSERT INTO files ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )
        conn.commit()
        return conn.execute("SELECT * FROM files WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_files(category: str = None):
    """Return files, optionally filtered by category."""
    conn = get_db()
    try:
        if category:
            return conn.execute(
                "SELECT * FROM files WHERE category = ? ORDER BY created_at DESC",
                (category,),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM files ORDER BY created_at DESC"
        ).fetchall()
    finally:
        conn.close()


def get_file(id: int):
    """Return a single file record by id."""
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Compatibility aliases (used by services/)
# ---------------------------------------------------------------------------

def get_ticker_by_symbol(symbol: str):
    return get_ticker(symbol)

def create_ticker(symbol: str, name: str, sector: str = None):
    return add_ticker(symbol, name, sector)

def get_daily_prices(ticker_id: int, days: int = 30):
    return get_prices(ticker_id, days)

def save_daily_prices(ticker_id: int, prices: list):
    """prices = list of dicts with date/open/high/low/close/volume"""
    for p in prices:
        add_daily_price(ticker_id, p['date'], p['open'], p['high'],
                        p['low'], p['close'], p['volume'])

def get_events_by_ticker(ticker_id: int):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM events WHERE ticker_id = ? ORDER BY event_date",
            (ticker_id,),
        ).fetchall()
    finally:
        conn.close()

def create_event(kwargs: dict):
    return add_event(kwargs)


def get_events_for_month(year: int, month: int):
    """Return all events in a given month (including dismissed), with ticker symbol."""
    conn = get_db()
    try:
        start = f"{year:04d}-{month:02d}-01"
        if month == 12:
            end = f"{year + 1:04d}-01-01"
        else:
            end = f"{year:04d}-{month + 1:02d}-01"
        return conn.execute(
            """SELECT e.*, t.symbol FROM events e
               JOIN tickers t ON t.id = e.ticker_id
               WHERE e.event_date >= ? AND e.event_date < ?
               ORDER BY e.event_date ASC""",
            (start, end),
        ).fetchall()
    finally:
        conn.close()


def get_upcoming_events(days: int = 90):
    """Return upcoming events within N days from today."""
    conn = get_db()
    try:
        return conn.execute(
            """SELECT e.*, t.symbol FROM events e
               JOIN tickers t ON t.id = e.ticker_id
               WHERE e.event_date >= date('now')
                 AND e.event_date <= date('now', ? || ' days')
               ORDER BY e.event_date ASC""",
            (str(days),),
        ).fetchall()
    finally:
        conn.close()


def upsert_event(ticker_id: int, event_type: str, event_date: str, title: str):
    """Insert event only if it doesn't already exist (same ticker+type+date)."""
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM events WHERE ticker_id=? AND event_type=? AND event_date=?",
            (ticker_id, event_type, event_date),
        ).fetchone()
        if existing:
            return existing
        cur = conn.execute(
            "INSERT INTO events (ticker_id, event_type, event_date, title) VALUES (?, ?, ?, ?)",
            (ticker_id, event_type, event_date, title),
        )
        conn.commit()
        return conn.execute("SELECT * FROM events WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Custom Data Sources (JSONPath-based, wealthlens-style)
# ---------------------------------------------------------------------------

def add_custom_source(kwargs: dict):
    """Insert a new custom data source."""
    allowed = {"name", "url", "date_path", "price_path", "open_path", "high_path",
               "low_path", "volume_path", "symbol_match", "priority", "enabled", "notes"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if "enabled" not in fields:
        fields["enabled"] = 1
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    conn = get_db()
    try:
        cur = conn.execute(
            f"INSERT INTO custom_data_sources ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )
        conn.commit()
        return conn.execute("SELECT * FROM custom_data_sources WHERE id=?",
                            (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_custom_sources(enabled_only: bool = False):
    conn = get_db()
    try:
        if enabled_only:
            rows = conn.execute(
                "SELECT * FROM custom_data_sources WHERE enabled=1 ORDER BY priority"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM custom_data_sources ORDER BY priority"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_custom_source(source_id: int, kwargs: dict):
    allowed = {"name", "url", "date_path", "price_path", "open_path", "high_path",
               "low_path", "volume_path", "symbol_match", "priority", "enabled", "notes"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return None
    set_clause = ", ".join(f"{k}=?" for k in fields)
    conn = get_db()
    try:
        conn.execute(
            f"UPDATE custom_data_sources SET {set_clause} WHERE id=?",
            list(fields.values()) + [source_id],
        )
        conn.commit()
        return conn.execute(
            "SELECT * FROM custom_data_sources WHERE id=?", (source_id,)
        ).fetchone()
    finally:
        conn.close()


def delete_custom_source(source_id: int):
    conn = get_db()
    try:
        cur = conn.execute(
            "DELETE FROM custom_data_sources WHERE id=?", (source_id,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Investment Banks CRUD
# ---------------------------------------------------------------------------

def add_investment_bank(name: str, short_name: str = None, website_url: str = None, report_url: str = None, logo_url: str = None):
    """Insert a new investment bank. Returns the bank row."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO investment_banks (name, short_name, website_url, report_url, logo_url) VALUES (?, ?, ?, ?, ?)",
            (name, short_name, website_url, report_url, logo_url),
        )
        conn.commit()
        return conn.execute("SELECT * FROM investment_banks WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_all_investment_banks():
    """Return all investment banks, ordered by name."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM investment_banks ORDER BY name"
        ).fetchall()
    finally:
        conn.close()


def get_enabled_investment_banks():
    """Return only enabled investment banks."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM investment_banks WHERE enabled = 1 ORDER BY name"
        ).fetchall()
    finally:
        conn.close()


def get_investment_bank(bank_id: int):
    """Return a single investment bank by ID."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM investment_banks WHERE id = ?", (bank_id,)
        ).fetchone()
    finally:
        conn.close()


def update_investment_bank(bank_id: int, kwargs: dict):
    """Update an investment bank."""
    allowed = {"name", "short_name", "website_url", "report_url", "logo_url", "enabled", "last_check", "last_report"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return get_investment_bank(bank_id)

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [bank_id]

    conn = get_db()
    try:
        conn.execute(
            f"UPDATE investment_banks SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        return conn.execute("SELECT * FROM investment_banks WHERE id = ?", (bank_id,)).fetchone()
    finally:
        conn.close()


def delete_investment_bank(bank_id: int):
    """Delete an investment bank and its reports."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM bank_reports WHERE bank_id = ?", (bank_id,))
        cur = conn.execute("DELETE FROM investment_banks WHERE id = ?", (bank_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def toggle_investment_bank(bank_id: int, enabled: bool):
    """Enable or disable an investment bank."""
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE investment_banks SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, bank_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Bank Reports CRUD
# ---------------------------------------------------------------------------

def add_bank_report(bank_id: int, title: str, url: str = None, pdf_url: str = None, published_at: str = None):
    """Insert a new bank report. Returns the report row."""
    conn = get_db()
    try:
        # Check if report already exists
        existing = conn.execute(
            "SELECT id FROM bank_reports WHERE bank_id = ? AND (url = ? OR pdf_url = ?)",
            (bank_id, url, pdf_url),
        ).fetchone()
        if existing:
            return None
        
        cur = conn.execute(
            "INSERT INTO bank_reports (bank_id, title, url, pdf_url, published_at) VALUES (?, ?, ?, ?, ?)",
            (bank_id, title, url, pdf_url, published_at),
        )
        conn.commit()
        return conn.execute("SELECT * FROM bank_reports WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_bank_reports(bank_id: int, limit: int = 50):
    """Return reports for a specific bank."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM bank_reports WHERE bank_id = ? ORDER BY created_at DESC LIMIT ?",
            (bank_id, limit),
        ).fetchall()
    finally:
        conn.close()


def get_undownloaded_reports():
    """Return reports that haven't been downloaded yet."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT br.*, ib.name as bank_name FROM bank_reports br JOIN investment_banks ib ON br.bank_id = ib.id WHERE br.downloaded = 0 ORDER BY br.created_at"
        ).fetchall()
    finally:
        conn.close()


def mark_report_downloaded(report_id: int, file_path: str):
    """Mark a report as downloaded."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE bank_reports SET downloaded = 1, file_path = ? WHERE id = ?",
            (file_path, report_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_bank_reports(limit: int = 100):
    """Return all bank reports with bank name."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT br.*, ib.name as bank_name, ib.short_name as bank_short_name FROM bank_reports br JOIN investment_banks ib ON br.bank_id = ib.id ORDER BY br.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Watchlist Groups CRUD  (v3.3)
# ---------------------------------------------------------------------------

def create_watchlist_group(name: str, description: str = None, color: str = '#4fc3f7', sort_order: int = 0):
    """Create a new watchlist group and return it."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO watchlist_groups (name, description, color, sort_order) VALUES (?, ?, ?, ?)",
            (name, description, color, sort_order),
        )
        conn.commit()
        return conn.execute("SELECT * FROM watchlist_groups WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_all_watchlist_groups():
    """Return all watchlist groups with ticker count, ordered by sort_order."""
    conn = get_db()
    try:
        return conn.execute("""
            SELECT wg.*, COUNT(wgt.id) as ticker_count
            FROM watchlist_groups wg
            LEFT JOIN watchlist_group_tickers wgt ON wgt.group_id = wg.id
            GROUP BY wg.id
            ORDER BY wg.sort_order, wg.name
        """).fetchall()
    finally:
        conn.close()


def get_watchlist_group(group_id: int):
    """Return a single watchlist group by id."""
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM watchlist_groups WHERE id = ?", (group_id,)).fetchone()
    finally:
        conn.close()


def get_watchlist_group_tickers(group_id: int):
    """Return all tickers in a group, with ticker details, ordered by sort_order."""
    conn = get_db()
    try:
        return conn.execute("""
            SELECT t.*, wgt.sort_order, wgt.id as membership_id
            FROM watchlist_group_tickers wgt
            JOIN tickers t ON t.id = wgt.ticker_id
            WHERE wgt.group_id = ?
            ORDER BY wgt.sort_order, t.symbol
        """, (group_id,)).fetchall()
    finally:
        conn.close()


def update_watchlist_group(group_id: int, kwargs: dict):
    """Update a watchlist group's fields."""
    allowed = {'name', 'description', 'color', 'sort_order'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return get_watchlist_group(group_id)
    set_clause = ', '.join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [group_id]
    conn = get_db()
    try:
        conn.execute(f"UPDATE watchlist_groups SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return get_watchlist_group(group_id)
    finally:
        conn.close()


def delete_watchlist_group(group_id: int):
    """Delete a watchlist group (cascade removes memberships)."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM watchlist_groups WHERE id = ?", (group_id,))
        conn.commit()
    finally:
        conn.close()


def add_ticker_to_group(group_id: int, ticker_id: int, sort_order: int = 0):
    """Add a ticker to a watchlist group."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO watchlist_group_tickers (group_id, ticker_id, sort_order) VALUES (?, ?, ?)",
            (group_id, ticker_id, sort_order),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def remove_ticker_from_group(group_id: int, ticker_id: int):
    """Remove a ticker from a watchlist group."""
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM watchlist_group_tickers WHERE group_id = ? AND ticker_id = ?",
            (group_id, ticker_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_groups_for_ticker(ticker_id: int):
    """Return all groups that contain a given ticker."""
    conn = get_db()
    try:
        return conn.execute("""
            SELECT wg.* FROM watchlist_groups wg
            JOIN watchlist_group_tickers wgt ON wgt.group_id = wg.id
            WHERE wgt.ticker_id = ?
            ORDER BY wg.sort_order, wg.name
        """, (ticker_id,)).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Price Alerts (v3.4)
# ---------------------------------------------------------------------------
# A price alert fires an event (event_type='price_alert') the first time a
# ticker's price crosses its threshold.  threshold_type='high' fires when
# price >= threshold; 'low' fires when price <= threshold.  Each alert
# triggers at most once per "crossing" — the user must re-enable (or delete)
# it to re-arm.  last_triggered_at records when it last fired.

def get_alerts(ticker_id: int = None, enabled_only: bool = False):
    """List alerts. Optionally filter by ticker_id and/or enabled status.

    Joins tickers to include the symbol for client convenience.
    """
    conn = get_db()
    try:
        sql = """
            SELECT pa.*, t.symbol, t.name AS ticker_name
            FROM price_alerts pa
            JOIN tickers t ON t.id = pa.ticker_id
            WHERE 1=1
        """
        params = []
        if ticker_id is not None:
            sql += " AND pa.ticker_id = ?"
            params.append(ticker_id)
        if enabled_only:
            sql += " AND pa.enabled = 1"
        sql += " ORDER BY t.symbol, pa.threshold_type, pa.threshold_price"
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def get_alert(alert_id: int):
    """Return a single alert row by id, or None if not found."""
    conn = get_db()
    try:
        return conn.execute("""
            SELECT pa.*, t.symbol, t.name AS ticker_name
            FROM price_alerts pa
            JOIN tickers t ON t.id = pa.ticker_id
            WHERE pa.id = ?
        """, (alert_id,)).fetchone()
    finally:
        conn.close()


def add_alert(ticker_id: int, threshold_type: str, threshold_price: float,
              note: str = None) -> dict:
    """Create a new price alert.

    Returns the inserted row (as a dict so the caller can jsonify without
    touching sqlite3.Row).  Raises ValueError on bad threshold_type.
    """
    if threshold_type not in ("high", "low"):
        raise ValueError(f"threshold_type must be 'high' or 'low', got {threshold_type!r}")
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO price_alerts
               (ticker_id, threshold_type, threshold_price, note)
               VALUES (?, ?, ?, ?)""",
            (ticker_id, threshold_type, threshold_price, note),
        )
        conn.commit()
        row = conn.execute("""
            SELECT pa.*, t.symbol, t.name AS ticker_name
            FROM price_alerts pa
            JOIN tickers t ON t.id = pa.ticker_id
            WHERE pa.id = ?
        """, (cur.lastrowid,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_alert(alert_id: int, **fields):
    """Update mutable fields of an alert.  Allowed: enabled, threshold_price,
    threshold_type, note.  Returns the updated row as a dict, or None if not found.
    """
    allowed = {"enabled", "threshold_price", "threshold_type", "note"}
    sets, params = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        row = get_alert(alert_id)
        return dict(row) if row else None
    if "threshold_type" in fields and fields["threshold_type"] not in ("high", "low"):
        raise ValueError(f"threshold_type must be 'high' or 'low'")
    params.append(alert_id)
    conn = get_db()
    try:
        conn.execute(
            f"UPDATE price_alerts SET {', '.join(sets)} WHERE id = ?", params
        )
        conn.commit()
    finally:
        conn.close()
    row = get_alert(alert_id)
    return dict(row) if row else None


def delete_alert(alert_id: int) -> bool:
    """Hard-delete an alert. Returns True if a row was removed."""
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM price_alerts WHERE id = ?", (alert_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mark_alert_triggered(alert_id: int):
    """Stamp last_triggered_at + auto-disable so it doesn't re-fire on every
    subsequent refresh.  Caller is expected to have already inserted the
    matching event row.
    """
    conn = get_db()
    try:
        conn.execute(
            """UPDATE price_alerts
               SET last_triggered_at = datetime('now'), enabled = 0
               WHERE id = ?""",
            (alert_id,),
        )
        conn.commit()
    finally:
        conn.close()


def get_enabled_alerts_for_ticker(ticker_id: int):
    """Return all enabled alerts for one ticker. Used by the price check loop."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM price_alerts WHERE ticker_id = ? AND enabled = 1",
            (ticker_id,),
        ).fetchall()
    finally:
        conn.close()


def get_enabled_alerts_for_ticker_with_symbol(ticker_id: int):
    """Like get_enabled_alerts_for_ticker but joins tickers so the symbol is
    available — used by alert_checker when firing events so the title can
    name the ticker.
    """
    conn = get_db()
    try:
        return conn.execute(
            """SELECT pa.*, t.symbol, t.name AS ticker_name
               FROM price_alerts pa
               JOIN tickers t ON t.id = pa.ticker_id
               WHERE pa.ticker_id = ? AND pa.enabled = 1""",
            (ticker_id,),
        ).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Portfolio snapshots (v3.4.2 — daily P&L history)
# ---------------------------------------------------------------------------

def upsert_snapshot(snapshot_date: str, total_value: float, total_cost: float,
                    total_pnl: float, pnl_pct: float, holdings_count: int) -> dict:
    """Insert or replace today's portfolio snapshot.

    snapshot_date is YYYY-MM-DD. UNIQUE constraint guarantees one snapshot per
    day; if called twice on the same date the second call replaces the first
    (this is intentional — end-of-night refresh should overwrite an earlier
    intraday snapshot for the same date).

    Returns the row as a dict so callers can jsonify() without wrapping.
    """
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO portfolio_snapshots
                  (snapshot_date, total_value, total_cost, total_pnl,
                   pnl_pct, holdings_count, captured_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(snapshot_date) DO UPDATE SET
                  total_value = excluded.total_value,
                  total_cost = excluded.total_cost,
                  total_pnl = excluded.total_pnl,
                  pnl_pct = excluded.pnl_pct,
                  holdings_count = excluded.holdings_count,
                  captured_at = excluded.captured_at""",
            (snapshot_date, total_value, total_cost, total_pnl,
             pnl_pct, holdings_count),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM portfolio_snapshots WHERE snapshot_date = ?",
            (snapshot_date,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_snapshots(days: int = 30) -> list:
    """Return the most recent `days` snapshots, oldest first.

    Returns list of dicts (Pitfall 13 — sqlite3.Row would break jsonify()).
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT * FROM portfolio_snapshots
               ORDER BY snapshot_date DESC LIMIT ?""",
            (days,),
        ).fetchall()
        # Reverse to ascending for chart rendering
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


def latest_snapshot() -> dict | None:
    """Return the most recent snapshot row, or None if no snapshots exist."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM portfolio_snapshots ORDER BY snapshot_date DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def snapshot_count() -> int:
    """Total number of captured snapshots (for Prometheus gauge)."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM portfolio_snapshots"
        ).fetchone()
        return row['c'] if row else 0
    finally:
        conn.close()


def delete_snapshots_before(date_str: str) -> int:
    """Delete snapshots older than `date_str` (YYYY-MM-DD). Returns rows deleted."""
    conn = get_db()
    try:
        cur = conn.execute(
            "DELETE FROM portfolio_snapshots WHERE snapshot_date < ?",
            (date_str,),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
