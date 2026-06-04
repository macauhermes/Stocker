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

        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tickers CRUD
# ---------------------------------------------------------------------------

def add_ticker(symbol: str, name: str, sector: str = None):
    """Insert a new ticker. Returns the ticker row as dict-like."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO tickers (symbol, name, sector) VALUES (?, ?, ?)",
            (symbol.upper(), name, sector),
        )
        conn.commit()
        return conn.execute("SELECT * FROM tickers WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_all_tickers():
    """Return every ticker, ordered by symbol."""
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM tickers ORDER BY symbol").fetchall()
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


def delete_ticker(symbol: str):
    """Delete a ticker by symbol. Returns True if a row was removed."""
    conn = get_db()
    try:
        cur = conn.execute(
            "DELETE FROM tickers WHERE UPPER(symbol) = ?", (symbol.upper(),)
        )
        conn.commit()
        return cur.rowcount > 0
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
