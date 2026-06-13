"""
Unit tests for services/multi_source.py

Tests pure functions directly and network-dependent functions with mocks.
No real HTTP calls — safe for CI/cron.
"""
import os
import sys
import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.multi_source import (
    _round_safe,
    _eval_path,
    _detect_date,
    search_popular,
    from_yfinance,
    from_yahoo_direct,
    from_stooq,
    from_coingecko,
    get_current_price,
    search_symbols,
    fetch_with_fallback,
    POPULAR_TICKERS,
    _COINGECKO_IDS,
)


# ═══════════════════════════════════════════════════════════════════
# _round_safe
# ═══════════════════════════════════════════════════════════════════

class TestRoundSafe:
    def test_normal_float(self):
        assert _round_safe(3.14159) == 3.14

    def test_integer(self):
        assert _round_safe(5) == 5.0

    def test_none_returns_none(self):
        assert _round_safe(None) is None

    def test_string_numeric(self):
        assert _round_safe("3.14159") == 3.14

    def test_non_numeric_string(self):
        assert _round_safe("abc") is None

    def test_custom_decimals(self):
        assert _round_safe(3.14159, 4) == 3.1416

    def test_zero(self):
        assert _round_safe(0) == 0.0

    def test_negative(self):
        assert _round_safe(-2.567) == -2.57

    def test_very_small(self):
        assert _round_safe(0.001) == 0.0

    def test_very_large(self):
        assert _round_safe(1e15) == 1e15


# ═══════════════════════════════════════════════════════════════════
# _eval_path (JSONPath evaluator)
# ═══════════════════════════════════════════════════════════════════

class TestEvalPath:
    SAMPLE = {
        "a": {
            "b": {"c": 42},
            "list": [10, 20, 30],
            "items": [
                {"name": "x", "val": 1},
                {"name": "y", "val": 2},
            ],
        },
        "key with spaces": "hello",
    }

    def test_simple_dot_path(self):
        assert _eval_path(self.SAMPLE, "$.a.b.c") == 42

    def test_root_path(self):
        assert _eval_path(self.SAMPLE, "$") == self.SAMPLE

    def test_empty_path(self):
        assert _eval_path(self.SAMPLE, "") == self.SAMPLE

    def test_dot_only(self):
        assert _eval_path(self.SAMPLE, ".") == self.SAMPLE

    def test_array_index(self):
        assert _eval_path(self.SAMPLE, "$.a.list[1]") == 20

    def test_array_wildcard(self):
        result = _eval_path(self.SAMPLE, "$.a.list[*]")
        assert result == [10, 20, 30]

    def test_bracket_notation(self):
        assert _eval_path(self.SAMPLE, "$['key with spaces']") == "hello"

    def test_nonexistent_key(self):
        assert _eval_path(self.SAMPLE, "$.a.nonexistent") is None

    def test_deep_nonexistent(self):
        assert _eval_path(self.SAMPLE, "$.a.b.c.d.e") is None

    def test_none_data(self):
        assert _eval_path(None, "$.a.b") is None

    def test_index_out_of_bounds(self):
        assert _eval_path(self.SAMPLE, "$.a.list[99]") is None

    def test_array_on_non_list(self):
        assert _eval_path(self.SAMPLE, "$.a.b[0]") is None

    def test_nested_array_objects(self):
        assert _eval_path(self.SAMPLE, "$.a.items[0].name") == "x"
        assert _eval_path(self.SAMPLE, "$.a.items[1].val") == 2


# ═══════════════════════════════════════════════════════════════════
# _detect_date
# ═══════════════════════════════════════════════════════════════════

class TestDetectDate:
    def test_iso_date(self):
        assert _detect_date("2024-01-15") == "2024-01-15"

    def test_iso_datetime(self):
        assert _detect_date("2024-01-15T10:30:00") == "2024-01-15"

    def test_iso_datetime_z(self):
        assert _detect_date("2024-01-15T10:30:00Z") == "2024-01-15"

    def test_slash_date(self):
        assert _detect_date("2024/01/15") == "2024-01-15"

    def test_us_date_format(self):
        assert _detect_date("1/15/2024") == "2024-01-15"

    def test_us_date_padded(self):
        assert _detect_date("12/25/2024") == "2024-12-25"

    def test_unix_seconds(self):
        # 2024-01-15 00:00:00 UTC ≈ 1705276800
        result = _detect_date(1705276800)
        assert result == "2024-01-15"

    def test_unix_milliseconds(self):
        result = _detect_date(1705276800000)
        assert result == "2024-01-15"

    def test_none(self):
        assert _detect_date(None) is None

    def test_invalid_string(self):
        assert _detect_date("not-a-date") is None

    def test_small_number(self):
        """Numbers < 1e9 are not timestamps."""
        assert _detect_date(42) is None

    def test_float_unix(self):
        result = _detect_date(1705276800.0)
        assert result == "2024-01-15"


# ═══════════════════════════════════════════════════════════════════
# search_popular (pure function, no network)
# ═══════════════════════════════════════════════════════════════════

class TestSearchPopular:
    def test_by_symbol(self):
        results = search_popular("TSLA")
        assert any(r["symbol"] == "TSLA" for r in results)

    def test_by_name(self):
        results = search_popular("Tesla")
        assert any(r["symbol"] == "TSLA" for r in results)

    def test_case_insensitive(self):
        results = search_popular("tsla")
        assert any(r["symbol"] == "TSLA" for r in results)

    def test_partial_match(self):
        results = search_popular("BTC")
        assert any("BTC" in r["symbol"] for r in results)

    def test_empty_query_returns_all(self):
        results = search_popular("")
        assert len(results) == 8  # default limit

    def test_custom_limit(self):
        results = search_popular("", limit=3)
        assert len(results) == 3

    def test_no_match(self):
        results = search_popular("ZZZZZNONEXISTENT")
        assert len(results) == 0

    def test_chinese_name_search(self):
        results = search_popular("騰訊")
        assert any(r["symbol"] == "0700.HK" for r in results)

    def test_hk_stock(self):
        results = search_popular("9988")
        assert any(r["symbol"] == "9988.HK" for r in results)


# ═══════════════════════════════════════════════════════════════════
# Stooq symbol translation (internal logic test)
# ═══════════════════════════════════════════════════════════════════

class TestStooqSymbolTranslation:
    """Test that from_stooq translates symbols correctly before HTTP call."""

    @patch("services.multi_source.requests.get")
    def test_us_stock_appends_us(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text="Date,Open,High,Low,Close,Volume\n2024-01-15,100,105,99,103,1000")
        from_stooq("AAPL")
        call_url = mock_get.call_args[0][0]
        assert "aapl.us" in call_url

    @patch("services.multi_source.requests.get")
    def test_hk_stock_keeps_hk(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text="Date,Open,High,Low,Close,Volume\n2024-01-15,100,105,99,103,1000")
        from_stooq("0700.HK")
        call_url = mock_get.call_args[0][0]
        assert "0700.hk" in call_url

    @patch("services.multi_source.requests.get")
    def test_jp_stock_converts_t_to_jp(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text="Date,Open,High,Low,Close,Volume\n2024-01-15,100,105,99,103,1000")
        from_stooq("7203.T")
        call_url = mock_get.call_args[0][0]
        assert "7203.jp" in call_url

    @patch("services.multi_source.requests.get")
    def test_crypto_usd_converts_to_us(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text="Date,Open,High,Low,Close,Volume\n2024-01-15,100,105,99,103,1000")
        from_stooq("BTC-USD")
        call_url = mock_get.call_args[0][0]
        assert "btc.us" in call_url


# ═══════════════════════════════════════════════════════════════════
# from_yfinance (mock yfinance)
# ═══════════════════════════════════════════════════════════════════

class TestFromYfinance:
    @patch("yfinance.Ticker")
    def test_returns_rows_on_success(self, mock_ticker):
        import pandas as pd
        dates = pd.to_datetime(["2024-01-15", "2024-01-16"])
        df = pd.DataFrame(
            {"Open": [100.0, 101.0], "High": [105.0, 106.0],
             "Low": [99.0, 100.0], "Close": [103.0, 104.0],
             "Volume": [1000, 2000]},
            index=dates,
        )
        mock_ticker.return_value.history.return_value = df
        result = from_yfinance("AAPL")
        assert result is not None
        assert result["source"] == "yfinance"
        assert len(result["rows"]) == 2
        assert result["rows"][0]["close"] == 103.0

    @patch("yfinance.Ticker")
    def test_returns_none_on_empty(self, mock_ticker):
        import pandas as pd
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        result = from_yfinance("INVALID")
        assert result is None

    @patch("yfinance.Ticker")
    def test_returns_none_on_exception(self, mock_ticker):
        mock_ticker.side_effect = Exception("no network")
        result = from_yfinance("AAPL")
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# from_yahoo_direct (mock requests)
# ═══════════════════════════════════════════════════════════════════

class TestFromYahooDirect:
    def _make_response(self, data, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = data
        return resp

    @patch("services.multi_source.requests.get")
    def test_returns_rows_on_success(self, mock_get):
        import time
        ts = int(time.time()) - 86400
        data = {
            "chart": {"result": [{
                "timestamp": [ts, ts + 86400],
                "indicators": {"quote": [{
                    "open": [100.0, 101.0],
                    "high": [105.0, 106.0],
                    "low": [99.0, 100.0],
                    "close": [103.0, 104.0],
                    "volume": [1000, 2000],
                }]},
            }]}
        }
        mock_get.return_value = self._make_response(data)
        result = from_yahoo_direct("AAPL")
        assert result is not None
        assert result["source"] == "yahoo_direct"
        assert len(result["rows"]) == 2

    @patch("services.multi_source.requests.get")
    def test_returns_none_on_non_200(self, mock_get):
        mock_get.return_value = self._make_response({}, status=403)
        result = from_yahoo_direct("AAPL")
        assert result is None

    @patch("services.multi_source.requests.get")
    def test_returns_none_on_empty_result(self, mock_get):
        data = {"chart": {"result": []}}
        mock_get.return_value = self._make_response(data)
        result = from_yahoo_direct("AAPL")
        assert result is None

    @patch("services.multi_source.requests.get")
    def test_skips_none_closes(self, mock_get):
        import time
        ts = int(time.time()) - 86400
        data = {
            "chart": {"result": [{
                "timestamp": [ts],
                "indicators": {"quote": [{
                    "open": [100.0], "high": [105.0],
                    "low": [99.0], "close": [None], "volume": [1000],
                }]},
            }]}
        }
        mock_get.return_value = self._make_response(data)
        result = from_yahoo_direct("AAPL")
        assert result is None  # all closes are None


# ═══════════════════════════════════════════════════════════════════
# from_stooq (mock requests)
# ═══════════════════════════════════════════════════════════════════

class TestFromStooq:
    def _make_csv(self, n=5):
        lines = ["Date,Open,High,Low,Close,Volume"]
        for i in range(n):
            d = f"2024-01-{15+i:02d}"
            lines.append(f"{d},{100+i},{105+i},{99+i},{103+i},{1000+i*100}")
        return "\n".join(lines)

    @patch("services.multi_source.requests.get")
    def test_returns_rows_on_valid_csv(self, mock_get):
        resp = MagicMock(status_code=200, text=self._make_csv())
        mock_get.return_value = resp
        result = from_stooq("AAPL")
        assert result is not None
        assert result["source"] == "stooq"
        assert len(result["rows"]) == 5

    @patch("services.multi_source.requests.get")
    def test_returns_none_on_short_response(self, mock_get):
        resp = MagicMock(status_code=200, text="short")
        mock_get.return_value = resp
        result = from_stooq("AAPL")
        assert result is None

    @patch("services.multi_source.requests.get")
    def test_returns_none_on_non_200(self, mock_get):
        resp = MagicMock(status_code=500, text="")
        mock_get.return_value = resp
        result = from_stooq("AAPL")
        assert result is None

    @patch("services.multi_source.requests.get")
    def test_parses_volume_correctly(self, mock_get):
        csv = "Date,Open,High,Low,Close,Volume\n2024-01-15,100,105,99,103,50000"
        resp = MagicMock(status_code=200, text=csv)
        mock_get.return_value = resp
        result = from_stooq("AAPL")
        assert result["rows"][0]["volume"] == 50000


# ═══════════════════════════════════════════════════════════════════
# from_coingecko (mock requests)
# ═══════════════════════════════════════════════════════════════════

class TestFromCoingecko:
    @patch("services.multi_source.requests.get")
    def test_returns_rows_for_btc(self, mock_get):
        import time
        now_ms = int(time.time() * 1000)
        data = {
            "prices": [[now_ms - 86400000, 42000.5], [now_ms, 43000.3]],
            "total_volumes": [[now_ms - 86400000, 25000000000], [now_ms, 30000000000]],
        }
        resp = MagicMock(status_code=200)
        resp.json.return_value = data
        mock_get.return_value = resp
        result = from_coingecko("BTC-USD")
        assert result is not None
        assert result["source"] == "coingecko"
        assert len(result["rows"]) == 2
        assert result["rows"][0]["close"] == 42000.5

    @patch("services.multi_source.requests.get")
    def test_returns_none_for_unknown_crypto(self, mock_get):
        result = from_coingecko("FAKECOIN-USD")
        assert result is None

    @patch("services.multi_source.requests.get")
    def test_returns_none_for_stock(self, mock_get):
        result = from_coingecko("AAPL")
        assert result is None

    @patch("services.multi_source.requests.get")
    def test_returns_none_on_non_200(self, mock_get):
        resp = MagicMock(status_code=429)
        mock_get.return_value = resp
        result = from_coingecko("BTC-USD")
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# get_current_price (mock requests + yfinance)
# ═══════════════════════════════════════════════════════════════════

class TestGetCurrentPrice:
    @patch("services.multi_source.requests.get")
    def test_yahoo_direct_success(self, mock_get):
        data = {
            "chart": {"result": [{
                "meta": {
                    "regularMarketPrice": 150.0,
                    "chartPreviousClose": 148.0,
                    "longName": "Apple Inc.",
                },
            }]}
        }
        resp = MagicMock(status_code=200)
        resp.json.return_value = data
        mock_get.return_value = resp
        result = get_current_price("AAPL")
        assert result["price"] == 150.0
        assert result["source"] == "yahoo_direct"
        assert result["name"] == "Apple Inc."
        assert result["change_pct"] is not None

    @patch("services.multi_source.requests.get")
    @patch("yfinance.Ticker")
    def test_falls_back_to_yfinance(self, mock_ticker, mock_get):
        # Yahoo direct fails
        mock_get.return_value = MagicMock(status_code=403)
        # yfinance succeeds
        mock_ticker.return_value.info = {
            "currentPrice": 150.0,
            "previousClose": 148.0,
            "shortName": "Apple",
            "sector": "Technology",
            "marketCap": 3000000000000,
            "trailingPE": 25.5,
            "trailingEps": 5.88,
        }
        result = get_current_price("AAPL")
        assert result["price"] == 150.0
        assert result["source"] == "yfinance"
        assert result["sector"] == "Technology"

    @patch("services.multi_source.requests.get")
    @patch("yfinance.Ticker")
    def test_returns_none_price_when_all_fail(self, mock_ticker, mock_get):
        mock_get.return_value = MagicMock(status_code=403)
        mock_ticker.side_effect = Exception("no network")
        result = get_current_price("AAPL")
        assert result["price"] is None
        assert result["source"] is None

    @patch("services.multi_source.requests.get")
    def test_change_pct_calculation(self, mock_get):
        data = {
            "chart": {"result": [{
                "meta": {
                    "regularMarketPrice": 110.0,
                    "chartPreviousClose": 100.0,
                    "shortName": "Test",
                },
            }]}
        }
        resp = MagicMock(status_code=200)
        resp.json.return_value = data
        mock_get.return_value = resp
        result = get_current_price("TEST")
        assert result["change_pct"] == 10.0


# ═══════════════════════════════════════════════════════════════════
# search_symbols (mock requests)
# ═══════════════════════════════════════════════════════════════════

class TestSearchSymbols:
    @patch("services.multi_source.requests.get")
    def test_returns_results(self, mock_get):
        data = {
            "quotes": [
                {"symbol": "AAPL", "longname": "Apple Inc.", "exchange": "NASDAQ", "quoteType": "EQUITY", "currency": "USD"},
                {"symbol": "AAPL.BA", "longname": "Apple Inc.", "exchange": "BCBA", "quoteType": "EQUITY", "currency": "ARS"},
            ]
        }
        resp = MagicMock(status_code=200)
        resp.json.return_value = data
        mock_get.return_value = resp
        results = search_symbols("AAPL")
        assert len(results) == 2
        assert results[0]["symbol"] == "AAPL"

    @patch("services.multi_source.requests.get")
    def test_returns_empty_on_non_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=403)
        results = search_symbols("AAPL")
        assert results == []

    @patch("services.multi_source.requests.get")
    def test_returns_empty_on_exception(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        results = search_symbols("AAPL")
        assert results == []


# ═══════════════════════════════════════════════════════════════════
# fetch_with_fallback (integration of fallback chain)
# ═══════════════════════════════════════════════════════════════════

class TestFetchWithFallback:
    @patch("services.multi_source._get_custom_sources", return_value=[])
    @patch("services.multi_source.from_yfinance")
    def test_uses_yfinance_first(self, mock_yf, mock_custom):
        mock_yf.return_value = {"source": "yfinance", "rows": [{"date": "2024-01-15", "close": 100}]}
        result = fetch_with_fallback("AAPL")
        assert result["source"] == "yfinance"

    @patch("services.multi_source._get_custom_sources", return_value=[])
    @patch("services.multi_source.from_stooq")
    @patch("services.multi_source.from_yahoo_direct")
    @patch("services.multi_source.from_yfinance")
    def test_falls_to_yahoo_when_yfinance_fails(self, mock_yf, mock_yahoo, mock_stooq, mock_custom):
        mock_yf.return_value = None
        mock_yahoo.return_value = {"source": "yahoo_direct", "rows": [{"date": "2024-01-15", "close": 100}]}
        result = fetch_with_fallback("AAPL")
        assert result["source"] == "yahoo_direct"

    @patch("services.multi_source._get_custom_sources", return_value=[])
    @patch("services.multi_source.from_coingecko")
    @patch("services.multi_source.from_stooq")
    @patch("services.multi_source.from_yahoo_direct")
    @patch("services.multi_source.from_yfinance")
    def test_falls_to_stooq(self, mock_yf, mock_yahoo, mock_stooq, mock_cg, mock_custom):
        mock_yf.return_value = None
        mock_yahoo.return_value = None
        mock_stooq.return_value = {"source": "stooq", "rows": [{"date": "2024-01-15", "close": 100}]}
        result = fetch_with_fallback("AAPL")
        assert result["source"] == "stooq"

    @patch("services.multi_source._get_custom_sources", return_value=[])
    @patch("services.multi_source.from_coingecko")
    @patch("services.multi_source.from_stooq")
    @patch("services.multi_source.from_yahoo_direct")
    @patch("services.multi_source.from_yfinance")
    def test_falls_to_coingecko(self, mock_yf, mock_yahoo, mock_stooq, mock_cg, mock_custom):
        mock_yf.return_value = None
        mock_yahoo.return_value = None
        mock_stooq.return_value = None
        mock_cg.return_value = {"source": "coingecko", "rows": [{"date": "2024-01-15", "close": 100}]}
        result = fetch_with_fallback("BTC-USD")
        assert result["source"] == "coingecko"

    @patch("services.multi_source._get_custom_sources", return_value=[])
    @patch("services.multi_source.from_coingecko")
    @patch("services.multi_source.from_stooq")
    @patch("services.multi_source.from_yahoo_direct")
    @patch("services.multi_source.from_yfinance")
    def test_returns_none_when_all_fail(self, mock_yf, mock_yahoo, mock_stooq, mock_cg, mock_custom):
        mock_yf.return_value = None
        mock_yahoo.return_value = None
        mock_stooq.return_value = None
        mock_cg.return_value = None
        result = fetch_with_fallback("INVALID")
        assert result is None

    @patch("services.multi_source._get_custom_sources")
    @patch("services.multi_source.from_custom_source")
    @patch("services.multi_source.from_yfinance")
    def test_custom_source_takes_priority(self, mock_yf, mock_custom_fetch, mock_custom_list):
        mock_custom_list.return_value = [{"name": "test", "url": "http://example.com"}]
        mock_custom_fetch.return_value = {"source": "custom:test", "rows": [{"date": "2024-01-15", "close": 100}]}
        result = fetch_with_fallback("AAPL")
        assert result["source"] == "custom:test"
        mock_yf.assert_not_called()


# ═══════════════════════════════════════════════════════════════════
# POPULAR_TICKERS integrity
# ═══════════════════════════════════════════════════════════════════

class TestPopularTickers:
    def test_not_empty(self):
        assert len(POPULAR_TICKERS) > 0

    def test_each_has_required_fields(self):
        for t in POPULAR_TICKERS:
            assert "symbol" in t, f"Missing symbol in {t}"
            assert "name" in t, f"Missing name in {t}"
            assert "market" in t, f"Missing market in {t}"
            assert "currency" in t, f"Missing currency in {t}"

    def test_no_duplicate_symbols(self):
        symbols = [t["symbol"] for t in POPULAR_TICKERS]
        assert len(symbols) == len(set(symbols)), f"Duplicate symbols: {[s for s in symbols if symbols.count(s) > 1]}"

    def test_has_crypto(self):
        crypto = [t for t in POPULAR_TICKERS if t["market"] == "CRYPTO"]
        assert len(crypto) >= 2

    def test_has_hk(self):
        hk = [t for t in POPULAR_TICKERS if t["market"] == "HK"]
        assert len(hk) >= 2


# ═══════════════════════════════════════════════════════════════════
# _COINGECKO_IDS integrity
# ═══════════════════════════════════════════════════════════════════

class TestCoingeckoIds:
    def test_btc_present(self):
        assert "btc-usd" in _COINGECKO_IDS

    def test_eth_present(self):
        assert "eth-usd" in _COINGECKO_IDS

    def test_all_keys_lowercase_with_usd_suffix(self):
        for key in _COINGECKO_IDS:
            assert key == key.lower(), f"Key {key} not lowercase"
            assert key.endswith("-usd"), f"Key {key} missing -usd suffix"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
