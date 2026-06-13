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

        # Helpful indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_ticker ON daily_prices(ticker_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_date   ON daily_prices(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_ticker ON events(ticker_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_files_report  ON files(report_id)")

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
