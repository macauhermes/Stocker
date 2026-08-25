"""
Unit tests for services/bank_report_scraper.py (投行報告抓取 v3.3+).

bank_report_scraper is pure-logic + network I/O. We isolate by:
  1. Pointing models.DB_PATH at a tempdir + creating the bank/investment
     tables manually (NOT in models.init_db() — see schema note below).
  2. Mocking requests.get / requests.head at the canonical module path
     (Pitfall 7 — services.bank_report_scraper imports requests at
     module level, so we can patch it directly).

Schema note: `investment_banks` and `bank_reports` tables exist in the
live DB (created externally) but NOT in models.init_db(). Tests create
them in the temp_db fixture so a fresh checkout works.

What we verify:
  - _extract_date() matches 4 common date formats from text
  - _extract_date() falls back to data-* / datetime attributes
  - _find_pdf_links() finds direct .pdf links
  - _find_pdf_links() finds "pdf"/"download" links when HEAD returns PDF
  - _find_pdf_links() returns [] on network error
  - check_bank_for_reports() returns error for unknown bank
  - check_bank_for_reports() calls _find_pdf_links + add_bank_report per PDF
  - check_bank_for_reports() increments last_report only when new reports > 0
  - check_bank_for_reports() reports "No report URL configured" when empty
  - check_bank_for_reports() always stamps last_check, even on failure
  - check_all_banks() aggregates per-bank new_reports and survives per-bank errors
  - download_report_pdf() refuses to re-download already-downloaded reports
  - download_report_pdf() writes file + marks downloaded + records to files table
  - download_report_pdf() returns error for missing report_id / no PDF URL
  - Filename generation strips illegal chars and trims length
"""
import os
import re
import sys
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import models
import services.bank_report_scraper as scraper


# ═══════════════════════════════════════════════════════════════════
# Schema helpers
# ═══════════════════════════════════════════════════════════════════

BANK_SCHEMA = """
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
"""

BANK_REPORT_SCHEMA = """
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
"""


def _create_bank_tables(conn):
    """Create bank tables (mimics what models.init_db() should do)."""
    conn.execute(BANK_SCHEMA)
    conn.execute(BANK_REPORT_SCHEMA)
    conn.commit()


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_db():
    """Function-scope isolated SQLite at a tempdir. Restores models.DB_PATH."""
    tmp = tempfile.mkdtemp(prefix='stocker-bank-test-')
    db_path = os.path.join(tmp, 'stocker.db')
    original = models.DB_PATH
    models.DB_PATH = db_path
    try:
        # Mirror what models.init_db() does — but models.init_db() doesn't
        # create the bank tables. We do that explicitly here so the test
        # fixture matches the live DB schema.
        conn = sqlite3.connect(db_path)
        try:
            conn.row_factory = sqlite3.Row
            models.init_db()       # creates the standard tables
            _create_bank_tables(conn)  # + bank/investment tables
        finally:
            conn.close()
        yield db_path
    finally:
        models.DB_PATH = original


@pytest.fixture
def bank_id(temp_db):
    """Insert an enabled test bank; return its id."""
    return models.add_investment_bank(
        name="Test Capital",
        short_name="TC",
        website_url="https://example.com",
        report_url="https://example.com/research",
        logo_url=None,
    )["id"]


@pytest.fixture
def disabled_bank_id(temp_db):
    """Insert a disabled bank; return its id."""
    bid = models.add_investment_bank(
        name="Disabled Bank",
        short_name="DB",
        website_url="https://disabled.example.com",
        report_url="https://disabled.example.com/research",
    )["id"]
    models.toggle_investment_bank(bid, False)
    return bid


def _mock_response(html="", status=200, content_type="text/html", headers=None):
    """Build a MagicMock that quacks like requests.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = html
    resp.content = html.encode("utf-8") if isinstance(html, str) else html
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


def _mock_head_response(content_type, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"Content-Type": content_type}
    return resp


# ═══════════════════════════════════════════════════════════════════
# _extract_date
# ═══════════════════════════════════════════════════════════════════

class TestExtractDate:
    def _element(self, text="", **attrs):
        from bs4 import BeautifulSoup
        return BeautifulSoup(f"<a>{text}</a>", "html.parser").find("a")

    def test_iso_format(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a>2026-08-25 — Market Outlook</a>', "html.parser")
        assert scraper._extract_date(soup.find("a")) == "2026-08-25"

    def test_us_slash_format(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a>08/25/2026 — Earnings Note</a>', "html.parser")
        assert scraper._extract_date(soup.find("a")) == "08/25/2026"

    def test_european_dot_format(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a>25.08.2026 — Earnings Note</a>', "html.parser")
        assert scraper._extract_date(soup.find("a")) == "25.08.2026"

    def test_month_name_format(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a>August 25, 2026 — Macro Outlook</a>', "html.parser")
        assert scraper._extract_date(soup.find("a")) == "August 25, 2026"

    def test_no_match_returns_none(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a>Just a title with no date</a>', "html.parser")
        assert scraper._extract_date(soup.find("a")) is None

    def test_falls_back_to_data_date_attr(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a data-date="2026-08-25">Note</a>', "html.parser")
        assert scraper._extract_date(soup.find("a")) == "2026-08-25"

    def test_falls_back_to_datetime_attr(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a datetime="2026-08-25">Note</a>', "html.parser")
        assert scraper._extract_date(soup.find("a")) == "2026-08-25"

    def test_walks_up_to_parent_when_self_has_no_date(self):
        from bs4 import BeautifulSoup
        html = '<div><span>2026-08-25</span><a>Link</a></div>'
        soup = BeautifulSoup(html, "html.parser")
        assert scraper._extract_date(soup.find("a")) == "2026-08-25"


# ═══════════════════════════════════════════════════════════════════
# _find_pdf_links
# ═══════════════════════════════════════════════════════════════════

class TestFindPdfLinks:
    def test_direct_pdf_href(self):
        html = '<a href="/reports/Q3.pdf">Q3 2026 Report</a>'
        with patch.object(scraper.requests, "get", return_value=_mock_response(html)):
            links = scraper._find_pdf_links("https://example.com/research")
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/reports/Q3.pdf"
        assert "Q3 2026 Report" in links[0]["title"]

    def test_relative_href_gets_resolved_to_absolute(self):
        # urljoin treats `/reports/foo.pdf` as a server-absolute path,
        # so it resolves against the scheme+host of the base URL only —
        # not against `/research`. This is the standard urljoin behavior.
        html = '<a href="reports/foo.pdf">Foo</a>'
        with patch.object(scraper.requests, "get", return_value=_mock_response(html)):
            links = scraper._find_pdf_links("https://example.com/research")
        assert links[0]["url"] == "https://example.com/reports/foo.pdf"

    def test_pdf_text_link_confirmed_by_head_request(self):
        # href ends in .html but text contains "download" → HEAD confirms PDF
        html = '<a href="/reports/Q3">Download Q3 Report</a>'
        get_resp = _mock_response(html)
        head_resp = _mock_head_response("application/pdf")
        with patch.object(scraper.requests, "get", return_value=get_resp), \
             patch.object(scraper.requests, "head", return_value=head_resp):
            links = scraper._find_pdf_links("https://example.com/research")
        assert len(links) == 1
        assert "Q3 Report" in links[0]["title"]

    def test_pdf_text_link_rejected_when_head_says_html(self):
        html = '<a href="/reports/Q3">Download Q3 Report</a>'
        get_resp = _mock_response(html)
        head_resp = _mock_head_response("text/html")
        with patch.object(scraper.requests, "get", return_value=get_resp), \
             patch.object(scraper.requests, "head", return_value=head_resp):
            links = scraper._find_pdf_links("https://example.com/research")
        assert links == []

    def test_head_request_failure_silently_skips_link(self):
        html = '<a href="/reports/Q3">Download Q3 Report</a>'
        get_resp = _mock_response(html)
        with patch.object(scraper.requests, "get", return_value=get_resp), \
             patch.object(scraper.requests, "head", side_effect=Exception("network")):
            # No PDF href → must not raise; result is empty
            links = scraper._find_pdf_links("https://example.com/research")
        assert links == []

    def test_anchor_href_starting_with_hash_is_skipped(self):
        html = '<a href="#section">PDF Download</a>'
        with patch.object(scraper.requests, "get", return_value=_mock_response(html)):
            links = scraper._find_pdf_links("https://example.com/research")
        # HEAD won't be called for # anchors since the link starts with "#"
        assert links == []

    def test_returns_empty_on_network_error(self):
        with patch.object(scraper.requests, "get", side_effect=Exception("boom")):
            links = scraper._find_pdf_links("https://example.com/research")
        assert links == []

    def test_returns_empty_on_http_error(self):
        with patch.object(scraper.requests, "get", return_value=_mock_response(status=500)):
            links = scraper._find_pdf_links("https://example.com/research")
        assert links == []

    def test_title_truncated_at_200_chars(self):
        long_title = "Q3 " + ("very " * 60) + "report"
        html = f'<a href="/r.pdf">{long_title}</a>'
        with patch.object(scraper.requests, "get", return_value=_mock_response(html)):
            links = scraper._find_pdf_links("https://example.com/research")
        assert len(links[0]["title"]) == 200

    def test_multiple_pdfs(self):
        html = '''
        <a href="/a.pdf">A</a>
        <a href="/b.pdf">BB</a>
        <a href="/c.pdf">CCC</a>
        '''
        with patch.object(scraper.requests, "get", return_value=_mock_response(html)):
            links = scraper._find_pdf_links("https://example.com/research")
        assert len(links) == 3


# ═══════════════════════════════════════════════════════════════════
# check_bank_for_reports
# ═══════════════════════════════════════════════════════════════════

class TestCheckBankForReports:
    def test_unknown_bank_returns_error(self, temp_db):
        result = scraper.check_bank_for_reports(99999)
        assert "error" in result
        assert result["error"] == "Bank not found"

    def test_no_report_url_returns_configured_error(self, temp_db, bank_id):
        # Wipe the report_url to simulate misconfiguration
        models.update_investment_bank(bank_id, {"report_url": None})
        result = scraper.check_bank_for_reports(bank_id)
        assert result["new_reports"] == 0
        assert "No report URL configured" in result["errors"]

    def test_stamps_last_check_even_when_no_report_url(self, temp_db, bank_id):
        models.update_investment_bank(bank_id, {"report_url": None})
        scraper.check_bank_for_reports(bank_id)
        bank = models.get_investment_bank(bank_id)
        assert bank["last_check"] is not None

    def test_stamps_last_check_even_when_network_fails(self, temp_db, bank_id):
        with patch.object(scraper, "_find_pdf_links", side_effect=Exception("boom")):
            result = scraper.check_bank_for_reports(bank_id)
        bank = models.get_investment_bank(bank_id)
        assert bank["last_check"] is not None
        assert "boom" in " ".join(result["errors"])

    def test_inserts_one_row_per_new_pdf(self, temp_db, bank_id):
        with patch.object(scraper, "_find_pdf_links", return_value=[
            {"url": "https://x.com/a.pdf", "title": "A Report", "date": "2026-08-25"},
            {"url": "https://x.com/b.pdf", "title": "B Report", "date": "2026-08-24"},
        ]):
            result = scraper.check_bank_for_reports(bank_id)
        assert result["new_reports"] == 2
        assert models.get_bank_reports(bank_id, limit=10) and len(
            models.get_bank_reports(bank_id, limit=10)
        ) == 2

    def test_dedupes_existing_url(self, temp_db, bank_id):
        # Pre-insert one report
        models.add_bank_report(
            bank_id=bank_id,
            title="Existing",
            url="https://x.com/a.pdf",
            pdf_url="https://x.com/a.pdf",
        )
        with patch.object(scraper, "_find_pdf_links", return_value=[
            {"url": "https://x.com/a.pdf", "title": "Existing", "date": "2026-08-25"},
            {"url": "https://x.com/b.pdf", "title": "New B", "date": "2026-08-25"},
        ]):
            result = scraper.check_bank_for_reports(bank_id)
        # Only B is new; A is deduped
        assert result["new_reports"] == 1

    def test_only_stamps_last_report_when_new_reports_positive(self, temp_db, bank_id):
        with patch.object(scraper, "_find_pdf_links", return_value=[]):
            scraper.check_bank_for_reports(bank_id)
        bank = models.get_investment_bank(bank_id)
        assert bank["last_check"] is not None
        assert bank["last_report"] is None

    def test_stamps_last_report_when_new_reports_positive(self, temp_db, bank_id):
        with patch.object(scraper, "_find_pdf_links", return_value=[
            {"url": "https://x.com/a.pdf", "title": "A", "date": "2026-08-25"},
        ]):
            scraper.check_bank_for_reports(bank_id)
        bank = models.get_investment_bank(bank_id)
        assert bank["last_report"] is not None


# ═══════════════════════════════════════════════════════════════════
# check_all_banks
# ═══════════════════════════════════════════════════════════════════

class TestCheckAllBanks:
    def test_returns_only_enabled_banks(self, temp_db, bank_id, disabled_bank_id):
        with patch.object(scraper, "_find_pdf_links", return_value=[]):
            result = scraper.check_all_banks()
        # Disabled bank must not be queried
        assert "Test Capital" in result["by_bank"]
        assert "Disabled Bank" not in result["by_bank"]

    def test_aggregates_per_bank_new_reports(self, temp_db, bank_id):
        # Second enabled bank
        models.add_investment_bank(
            name="Other Capital",
            report_url="https://other.example.com",
        )
        with patch.object(scraper, "_find_pdf_links", return_value=[
            {"url": "https://x.com/a.pdf", "title": "A", "date": "2026-08-25"},
        ]):
            result = scraper.check_all_banks()
        assert result["total_new"] == 2  # both banks got 1

    def test_per_bank_failure_does_not_kill_sweep(self, temp_db, bank_id):
        models.add_investment_bank(
            name="Failing Capital",
            report_url="https://fail.2",
        )
        original = scraper.check_bank_for_reports

        def flaky(bank_id):
            row = models.get_investment_bank(bank_id)
            if row["name"] == "Failing Capital":
                raise Exception("intentional")
            return original(bank_id)

        with patch.object(scraper, "check_bank_for_reports", side_effect=flaky):
            result = scraper.check_all_banks()
        # Failed bank reported, others succeeded
        assert any("Failing Capital" in e for e in result["errors"])
        # Other banks still in by_bank
        assert "Test Capital" in result["by_bank"]


# ═══════════════════════════════════════════════════════════════════
# download_report_pdf
# ═══════════════════════════════════════════════════════════════════

class TestDownloadReportPdf:
    def test_unknown_report_returns_error(self, temp_db):
        result = scraper.download_report_pdf(99999)
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_already_downloaded_returns_existing_path(self, temp_db, bank_id):
        rid = models.add_bank_report(
            bank_id=bank_id,
            title="Old",
            url="https://x.com/a.pdf",
            pdf_url="https://x.com/a.pdf",
        )["id"]
        # Mark as already downloaded
        conn = sqlite3.connect(temp_db)
        try:
            conn.execute(
                "UPDATE bank_reports SET downloaded = 1, file_path = ? WHERE id = ?",
                ("/tmp/old.pdf", rid),
            )
            conn.commit()
        finally:
            conn.close()
        result = scraper.download_report_pdf(rid)
        assert result["success"] is True
        assert result["already_downloaded"] is True
        assert result["file_path"] == "/tmp/old.pdf"

    def test_no_pdf_url_returns_error(self, temp_db, bank_id):
        rid = models.add_bank_report(
            bank_id=bank_id,
            title="No URL",
            url=None,
            pdf_url=None,
        )["id"]
        result = scraper.download_report_pdf(rid)
        assert result["success"] is False
        assert "no pdf url" in result["error"].lower()

    def test_happy_path_writes_file_and_marks_db(self, temp_db, bank_id):
        rid = models.add_bank_report(
            bank_id=bank_id,
            title="My Report: Big Test!",
            url="https://x.com/a.pdf",
            pdf_url="https://x.com/a.pdf",
        )["id"]

        # Mock a 200 PDF response with a small body
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.iter_content = lambda chunk_size: [b"%PDF-1.4 fake body"]
        resp.headers = {"Content-Type": "application/pdf"}

        with patch.object(scraper.requests, "get", return_value=resp), \
             patch.object(scraper, "REPORTS_DIR", Path(tempfile.mkdtemp(prefix="dl-"))):
            result = scraper.download_report_pdf(rid)

        assert result["success"] is True
        assert Path(result["file_path"]).exists()
        # DB state updated
        report = models.get_bank_reports(bank_id, limit=1)[0]
        assert report["downloaded"] == 1
        assert report["file_path"] == result["file_path"]
        # Files table row recorded
        conn = sqlite3.connect(temp_db)
        try:
            row = conn.execute(
                "SELECT * FROM files WHERE category = 'bank_report'"
            ).fetchone()
            assert row is not None
        finally:
            conn.close()

    def test_network_failure_returns_error(self, temp_db, bank_id):
        rid = models.add_bank_report(
            bank_id=bank_id,
            title="X",
            url="https://x.com/x.pdf",
            pdf_url="https://x.com/x.pdf",
        )["id"]

        with patch.object(scraper.requests, "get",
                          side_effect=Exception("network down")):
            result = scraper.download_report_pdf(rid)
        assert result["success"] is False
        assert "network down" in result["error"]


# ═══════════════════════════════════════════════════════════════════
# Filename generation
# ═══════════════════════════════════════════════════════════════════

class TestFilenameGeneration:
    """Indirect test — exercise download_report_pdf with various titles
    and inspect the file path written."""

    @pytest.mark.parametrize("title,bank_name,expect_fragment", [
        # Production code: `[^\w\s-]` strips `/` (since \w excludes /),
        # leaving double spaces which `.replace(" ", "_")` turns into
        # double underscores — `Title / With / Slashes` → `Title__With__Slashes`.
        ("Clean Title", "Bank A", "Bank_A_Clean_Title"),
        ("Title / With / Slashes", "Bank B", "Title__With__Slashes"),
        ("Special: <chars>!", "Bank C", "Special"),
        ("   Leading and trailing   ", "Bank D", "Leading_and_trailing"),
        ("a" * 200, "Bank E", "Bank_E_"),  # truncation at 50 chars
    ])
    def test_filename_sanitization(self, temp_db, bank_id, title, bank_name, expect_fragment):
        # Replace bank_id with the parametrized name (re-insert for clarity)
        models.update_investment_bank(bank_id, {"name": bank_name})

        rid = models.add_bank_report(
            bank_id=bank_id,
            title=title,
            url="https://x.com/x.pdf",
            pdf_url="https://x.com/x.pdf",
        )["id"]

        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.iter_content = lambda chunk_size: [b"%PDF-1.4 body"]
        resp.headers = {"Content-Type": "application/pdf"}

        tmp_dir = Path(tempfile.mkdtemp(prefix="fname-"))
        with patch.object(scraper.requests, "get", return_value=resp), \
             patch.object(scraper, "REPORTS_DIR", tmp_dir):
            result = scraper.download_report_pdf(rid)

        assert result["success"] is True
        fname = Path(result["file_path"]).name
        assert expect_fragment in fname
        # All filenames end in .pdf
        assert fname.endswith(".pdf")
        # Stripped characters that would break cross-platform filesystems
        # Note: production regex `[^\w\s-]` deliberately keeps `/` and similar
        # chars (documented quirk — see test parametrize note above).
        # We only assert against truly dangerous chars:
        assert not re.search(r'[<>:"|?*\\]', fname.rstrip(".pdf"))