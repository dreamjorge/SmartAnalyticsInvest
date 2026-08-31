"""Optional market data source adapters."""

from __future__ import annotations

import sqlite3
from importlib import import_module
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from smartanalyticsinvest.errors import DataSourceError, MissingColumnsError
from smartanalyticsinvest.schema import REQUIRED_OHLCV_COLUMNS, require_ohlcv_columns

_INSTALL_GUIDANCE = "Install optional market data support with: pip install -e '.[market-data]'"
_REQUIRED_COLUMN_SET = set(REQUIRED_OHLCV_COLUMNS)

_STOCKSTREAMDB_PRICE_QUERY = "SELECT ticker, date, open, high, low, close, volume FROM stock_prices"
_STOCKSTREAMDB_FUNDAMENTALS_QUERY = (
    "SELECT f.ticker, f.date, f.pe_ratio, f.eps, f.market_cap, f.revenue, f.net_income, "
    "f.total_assets FROM fundamentals f INNER JOIN (SELECT ticker, date, "
    "MAX(fundamental_id) AS max_id FROM fundamentals{ticker_filter} GROUP BY ticker, date) "
    "latest ON f.fundamental_id = latest.max_id"
)
_STOCKSTREAMDB_SENTIMENT_QUERY = (
    "SELECT ticker, date, AVG(sentiment_score) AS sentiment_score "
    "FROM sentiment_analysis{ticker_filter} GROUP BY ticker, date"
)
_STOCKSTREAMDB_MACRO_QUERY = "SELECT series_id, date, value FROM macro_indicators"


def _import_yfinance() -> Any:
    try:
        return import_module("yfinance")
    except ModuleNotFoundError as exc:
        if exc.name == "yfinance":
            raise DataSourceError(
                f"yfinance is required for Yahoo OHLCV fetching. {_INSTALL_GUIDANCE}"
            ) from exc
        raise


def _canonical_yahoo_column(column: object) -> str | None:
    if isinstance(column, tuple):
        if not column:
            return None
        return _canonical_yahoo_column(column[0])

    if not isinstance(column, str):
        return None

    canonical = column.strip().lower()
    if canonical in _REQUIRED_COLUMN_SET:
        return canonical
    return None


def _normalize_yahoo_frame(downloaded: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if downloaded.empty:
        raise DataSourceError(f"No OHLCV data returned for {symbol}")

    columns: dict[str, pd.Series] = {}
    for column in downloaded.columns:
        canonical = _canonical_yahoo_column(column)
        if canonical is None or canonical in columns:
            continue
        columns[canonical] = downloaded[column]

    if "date" not in columns:
        columns["date"] = pd.Series(downloaded.index, index=downloaded.index)

    normalized = pd.DataFrame(columns, index=downloaded.index)
    try:
        require_ohlcv_columns(normalized)
    except MissingColumnsError as exc:
        raise DataSourceError(str(exc)) from exc

    result = normalized.loc[:, list(REQUIRED_OHLCV_COLUMNS)].copy()
    result["ticker"] = str(symbol)
    return result.reset_index(drop=True)


def fetch_yahoo_ohlcv(
    symbol: str,
    *,
    start: str | None = None,
    end: str | None = None,
    period: str = "1mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch one symbol from Yahoo Finance and return canonical OHLCV rows.

    This adapter requires the optional ``market-data`` dependency extra and imports
    ``yfinance`` lazily so core CSV workflows remain dependency-free and offline.
    """

    yf = _import_yfinance()
    downloaded = yf.download(
        symbol,
        start=start,
        end=end,
        period=period,
        interval=interval,
        progress=False,
    )
    return _normalize_yahoo_frame(downloaded, symbol)


def fetch_yahoo_ohlcv_many(
    symbols: list[str] | tuple[str, ...],
    *,
    start: str | None = None,
    end: str | None = None,
    period: str = "1mo",
    interval: str = "1d",
    on_error: Literal["raise", "skip"] = "raise",
) -> pd.DataFrame:
    """Fetch multiple symbols from Yahoo Finance and return concatenated OHLCV rows.

    Fetches each symbol individually and concatenates results into a single frame
    with the ``ticker`` column populated, suitable for multi-ticker CSV pipelines.

    With ``on_error="raise"`` (the default), the first symbol that fails to fetch
    raises a ``DataSourceError`` and aborts the whole batch. With ``on_error="skip"``,
    a failing symbol is skipped and fetching continues for the remaining symbols;
    the failed symbols are available on the returned frame's ``attrs["failed_symbols"]``.

    This adapter requires the optional ``market-data`` dependency extra.
    """

    if not symbols:
        raise DataSourceError("No symbols provided to fetch_yahoo_ohlcv_many")
    if on_error not in ("raise", "skip"):
        raise ValueError(f"on_error must be 'raise' or 'skip', got {on_error!r}")

    frames = []
    failed_symbols: dict[str, str] = {}
    for symbol in symbols:
        try:
            frame = fetch_yahoo_ohlcv(
                symbol,
                start=start,
                end=end,
                period=period,
                interval=interval,
            )
            frames.append(frame)
        except Exception as exc:
            if on_error == "raise":
                raise DataSourceError(f"Failed to fetch {symbol}: {exc}") from exc
            failed_symbols[str(symbol)] = str(exc)

    if not frames:
        raise DataSourceError(f"No OHLCV data returned for any of {len(symbols)} symbols")

    concatenated = pd.concat(frames, ignore_index=True)
    result = concatenated.sort_values(by=["ticker", "date"]).reset_index(drop=True)
    result.attrs["failed_symbols"] = failed_symbols
    return result


def _read_price_frame(
    connection: sqlite3.Connection, tickers: list[str] | tuple[str, ...] | None
) -> pd.DataFrame:
    if tickers is None:
        return pd.read_sql_query(_STOCKSTREAMDB_PRICE_QUERY, connection, parse_dates=["date"])
    placeholders = ", ".join("?" for _ in tickers)
    query = f"{_STOCKSTREAMDB_PRICE_QUERY} WHERE ticker IN ({placeholders})"
    return pd.read_sql_query(query, connection, params=list(tickers), parse_dates=["date"])


def _read_fundamentals_frame(
    connection: sqlite3.Connection, tickers: list[str] | tuple[str, ...] | None
) -> pd.DataFrame:
    if tickers is None:
        query = _STOCKSTREAMDB_FUNDAMENTALS_QUERY.format(ticker_filter="")
        return pd.read_sql_query(query, connection, parse_dates=["date"])
    placeholders = ", ".join("?" for _ in tickers)
    query = _STOCKSTREAMDB_FUNDAMENTALS_QUERY.format(
        ticker_filter=f" WHERE ticker IN ({placeholders})"
    )
    return pd.read_sql_query(query, connection, params=list(tickers), parse_dates=["date"])


def _read_sentiment_frame(
    connection: sqlite3.Connection, tickers: list[str] | tuple[str, ...] | None
) -> pd.DataFrame:
    if tickers is None:
        query = _STOCKSTREAMDB_SENTIMENT_QUERY.format(ticker_filter="")
        return pd.read_sql_query(query, connection, parse_dates=["date"])
    placeholders = ", ".join("?" for _ in tickers)
    query = _STOCKSTREAMDB_SENTIMENT_QUERY.format(
        ticker_filter=f" WHERE ticker IN ({placeholders})"
    )
    return pd.read_sql_query(query, connection, params=list(tickers), parse_dates=["date"])


def _join_macro_indicators(
    frame: pd.DataFrame,
    connection: sqlite3.Connection,
    macro_series: list[str] | tuple[str, ...] | None,
    publication_lag_days: int,
) -> pd.DataFrame:
    query = _STOCKSTREAMDB_MACRO_QUERY
    if macro_series is None:
        macro = pd.read_sql_query(query, connection, parse_dates=["date"])
    else:
        placeholders = ", ".join("?" for _ in macro_series)
        query += f" WHERE series_id IN ({placeholders})"
        macro = pd.read_sql_query(
            query, connection, params=list(macro_series), parse_dates=["date"]
        )
    if macro.empty:
        return frame

    pivoted = (
        macro.pivot_table(index="date", columns="series_id", values="value")
        .sort_index()
        .ffill()
        .reset_index()
    )
    pivoted.columns = ["date"] + [f"macro_{column}" for column in pivoted.columns[1:]]
    if publication_lag_days:
        pivoted["date"] = pivoted["date"] + pd.Timedelta(days=publication_lag_days)

    merged = pd.merge_asof(
        frame.sort_values("date"), pivoted.sort_values("date"), on="date", direction="backward"
    )
    return merged


def load_stockstreamdb(
    db_path: str | Path,
    *,
    tickers: list[str] | tuple[str, ...] | None = None,
    include_fundamentals: bool = False,
    include_sentiment: bool = False,
    include_macro: bool = False,
    macro_series: list[str] | tuple[str, ...] | None = None,
    macro_publication_lag_days: int = 0,
) -> pd.DataFrame:
    """Load canonical OHLCV rows from a StockStreamDB SQLite database.

    Reads the ``stock_prices`` table produced by
    `StockStreamDB <https://github.com/dreamjorge/StockStreamDB>`_, whose schema
    (``ticker, date, open, high, low, close, volume``) already matches this project's
    canonical OHLCV shape. Only the ``sqlite3`` standard library module is used, so
    this adapter needs no extra dependency and does not require StockStreamDB itself
    to be installed.

    With ``include_fundamentals``/``include_sentiment``, the ``fundamentals`` and
    ``sentiment_analysis`` tables are left-joined onto the result by ``ticker``/``date``
    (sentiment scores are averaged per ticker/date), adding extra feature columns
    useful for downstream model training.

    With ``include_macro``, FRED macro-economic series from the ``macro_indicators``
    table (not ticker-specific) are pivoted into one ``macro_<series_id>`` column per
    series, forward-filled, and joined onto every ticker's rows using the most recent
    observation as of each row's date (``pd.merge_asof``, backward direction) — macro
    series are typically lower-frequency than daily prices and don't need exact date
    alignment. Pass ``macro_series`` to restrict to specific FRED series IDs.

    FRED's ``date`` for a series such as CPI, GDP, or unemployment is the start of the
    reporting period, not the day the data was actually published — releases commonly
    lag the observation date by two to six weeks (and are sometimes later revised).
    Joining on the raw observation date therefore leaks future information into any
    row dated before the real publication date. Pass ``macro_publication_lag_days``
    (e.g. ``30``) to shift each series' observation dates forward by a conservative
    number of days before joining, so a value only becomes visible on/after the date
    it would plausibly have been available. This defaults to ``0`` for backward
    compatibility, but ``0`` is only safe for series published same-day (e.g. most
    market/rate series); for anything with real-world publication lag, callers doing
    model training should pass an explicit lag.
    """

    db_file = Path(db_path)
    if not db_file.is_file():
        raise FileNotFoundError(db_file)

    try:
        with sqlite3.connect(str(db_file)) as connection:
            frame = _read_price_frame(connection, tickers)

            if frame.empty:
                raise DataSourceError(f"No OHLCV data returned from {db_file}")

            if include_fundamentals:
                fundamentals = _read_fundamentals_frame(connection, tickers)
                frame = frame.merge(fundamentals, on=["ticker", "date"], how="left")

            if include_sentiment:
                sentiment = _read_sentiment_frame(connection, tickers)
                frame = frame.merge(sentiment, on=["ticker", "date"], how="left")

            if include_macro:
                frame = _join_macro_indicators(
                    frame, connection, macro_series, macro_publication_lag_days
                )
    except (sqlite3.DatabaseError, pd.errors.DatabaseError) as exc:
        raise DataSourceError(f"Could not read StockStreamDB database {db_file}: {exc}") from exc

    return frame.sort_values(by=["ticker", "date"]).reset_index(drop=True)
