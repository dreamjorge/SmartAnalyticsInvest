import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from smartanalyticsinvest.errors import DataSourceError
from smartanalyticsinvest.pipeline import clean_ohlcv


def test_fetch_yahoo_ohlcv_normalizes_columns_and_ticker(monkeypatch):
    captured = {}

    def download(symbol, **kwargs):
        captured["symbol"] = symbol
        captured["kwargs"] = kwargs
        return pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [110.0, 111.0],
                "Low": [95.0, 96.0],
                "Close": [105.0, 106.0],
                "Volume": [1000, 1100],
                "Adj Close": [104.5, 105.5],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
        )

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=download))

    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv

    result = fetch_yahoo_ohlcv("MSFT", start="2024-01-01", end="2024-01-31")

    assert captured == {
        "symbol": "MSFT",
        "kwargs": {
            "start": "2024-01-01",
            "end": "2024-01-31",
            "period": "1mo",
            "interval": "1d",
            "progress": False,
        },
    }
    assert list(result.columns) == ["date", "open", "high", "low", "close", "volume", "ticker"]
    assert result["ticker"].tolist() == ["MSFT", "MSFT"]
    assert result["date"].tolist() == list(pd.to_datetime(["2024-01-02", "2024-01-03"]))
    assert clean_ohlcv(result).shape == (2, 7)


def test_fetch_yahoo_ohlcv_uses_only_price_field_level_for_multiindex_columns(monkeypatch):
    index = pd.to_datetime(["2024-01-02"])
    columns = pd.MultiIndex.from_tuples(
        [
            ("Adj Close", "OPEN"),
            ("Open", "OPEN"),
            ("High", "OPEN"),
            ("Low", "OPEN"),
            ("Close", "OPEN"),
            ("Volume", "OPEN"),
        ]
    )
    downloaded = pd.DataFrame(
        [[999.0, 100.0, 110.0, 95.0, 105.0, 1000]], index=index, columns=columns
    )
    monkeypatch.setitem(
        sys.modules, "yfinance", SimpleNamespace(download=lambda *args, **kwargs: downloaded)
    )

    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv

    result = fetch_yahoo_ohlcv("OPEN")

    assert result.loc[0, "open"] == 100.0
    assert result.loc[0, "close"] == 105.0
    assert result.loc[0, "ticker"] == "OPEN"


def test_fetch_yahoo_ohlcv_missing_optional_dependency_has_install_guidance(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", None)

    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv

    with pytest.raises(DataSourceError, match=r"pip install -e '\.\[market-data\]'"):
        fetch_yahoo_ohlcv("MSFT")


@pytest.mark.parametrize(
    "downloaded, match",
    [
        (pd.DataFrame(), "No OHLCV data returned"),
        (
            pd.DataFrame(
                {"Open": [100.0], "High": [110.0], "Low": [95.0], "Volume": [1000]},
                index=pd.to_datetime(["2024-01-02"]),
            ),
            "Missing required OHLCV columns: close",
        ),
    ],
)
def test_fetch_yahoo_ohlcv_fails_for_empty_or_malformed_data(monkeypatch, downloaded, match):
    monkeypatch.setitem(
        sys.modules, "yfinance", SimpleNamespace(download=lambda *args, **kwargs: downloaded)
    )

    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv

    with pytest.raises(DataSourceError, match=match):
        fetch_yahoo_ohlcv("MSFT")


def test_fetch_yahoo_ohlcv_many_concatenates_multiple_symbols(monkeypatch):
    def download(symbol, **kwargs):
        prices = {"AAPL": (150, 160, 145, 155), "MSFT": (300, 310, 295, 305)}
        open_p, high_p, low_p, close_p = prices[symbol]
        return pd.DataFrame(
            {
                "Open": [open_p, open_p + 1],
                "High": [high_p, high_p + 1],
                "Low": [low_p, low_p + 1],
                "Close": [close_p, close_p + 1],
                "Volume": [1000, 1100],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
        )

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=download))

    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv_many

    result = fetch_yahoo_ohlcv_many(["AAPL", "MSFT"], period="1mo")

    assert len(result) == 4
    assert list(result.columns) == ["date", "open", "high", "low", "close", "volume", "ticker"]
    assert result["ticker"].unique().tolist() == ["AAPL", "MSFT"]
    assert (result.iloc[0:2]["ticker"] == "AAPL").all()
    assert (result.iloc[2:4]["ticker"] == "MSFT").all()
    assert result.loc[0, "open"] == 150.0
    assert result.loc[2, "open"] == 300.0


def test_fetch_yahoo_ohlcv_many_sorts_by_ticker_and_date(monkeypatch):
    def download(symbol, **kwargs):
        if symbol == "AAPL":
            dates = pd.to_datetime(["2024-01-03", "2024-01-02"])
        else:
            dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        return pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [110.0, 111.0],
                "Low": [95.0, 96.0],
                "Close": [105.0, 106.0],
                "Volume": [1000, 1100],
            },
            index=dates,
        )

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=download))

    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv_many

    result = fetch_yahoo_ohlcv_many(["MSFT", "AAPL"])

    tickers = result["ticker"].tolist()
    assert tickers == ["AAPL", "AAPL", "MSFT", "MSFT"]
    aapl_dates = result[result["ticker"] == "AAPL"]["date"].tolist()
    msft_dates = result[result["ticker"] == "MSFT"]["date"].tolist()
    assert aapl_dates == sorted(aapl_dates)
    assert msft_dates == sorted(msft_dates)


def test_fetch_yahoo_ohlcv_many_fails_on_empty_symbol_list():
    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv_many

    with pytest.raises(DataSourceError, match="No symbols provided"):
        fetch_yahoo_ohlcv_many([])


def test_fetch_yahoo_ohlcv_many_rejects_unsupported_on_error_value():
    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv_many

    with pytest.raises(ValueError, match="on_error must be 'raise' or 'skip'"):
        fetch_yahoo_ohlcv_many(["AAPL"], on_error="rais")


def test_fetch_yahoo_ohlcv_many_fails_on_individual_symbol_failure(monkeypatch):
    def download(symbol, **kwargs):
        if symbol == "BAD":
            raise ValueError("Invalid symbol")
        return pd.DataFrame(
            {
                "Open": [100.0],
                "High": [110.0],
                "Low": [95.0],
                "Close": [105.0],
                "Volume": [1000],
            },
            index=pd.to_datetime(["2024-01-02"]),
        )

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=download))

    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv_many

    with pytest.raises(DataSourceError, match="Failed to fetch BAD"):
        fetch_yahoo_ohlcv_many(["AAPL", "BAD", "MSFT"])


def test_fetch_yahoo_ohlcv_many_skips_failing_symbols_in_best_effort_mode(monkeypatch):
    def download(symbol, **kwargs):
        if symbol == "BAD":
            raise ValueError("Invalid symbol")
        return pd.DataFrame(
            {
                "Open": [100.0],
                "High": [110.0],
                "Low": [95.0],
                "Close": [105.0],
                "Volume": [1000],
            },
            index=pd.to_datetime(["2024-01-02"]),
        )

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=download))

    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv_many

    result = fetch_yahoo_ohlcv_many(["AAPL", "BAD", "MSFT"], on_error="skip")

    assert result["ticker"].tolist() == ["AAPL", "MSFT"]
    assert list(result.attrs["failed_symbols"].keys()) == ["BAD"]
    assert "Invalid symbol" in result.attrs["failed_symbols"]["BAD"]


def test_fetch_yahoo_ohlcv_many_best_effort_mode_still_raises_if_all_symbols_fail(monkeypatch):
    def download(symbol, **kwargs):
        raise ValueError("Invalid symbol")

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=download))

    from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv_many

    with pytest.raises(DataSourceError, match="No OHLCV data returned for any of 2 symbols"):
        fetch_yahoo_ohlcv_many(["BAD", "WORSE"], on_error="skip")
