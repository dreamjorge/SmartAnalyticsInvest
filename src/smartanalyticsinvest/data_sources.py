"""Optional market data source adapters."""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pandas as pd

from smartanalyticsinvest.errors import DataSourceError, MissingColumnsError
from smartanalyticsinvest.schema import REQUIRED_OHLCV_COLUMNS, require_ohlcv_columns

_INSTALL_GUIDANCE = "Install optional market data support with: pip install -e '.[market-data]'"
_REQUIRED_COLUMN_SET = set(REQUIRED_OHLCV_COLUMNS)


def _import_yfinance() -> Any:
    try:
        return import_module("yfinance")
    except ModuleNotFoundError as exc:
        if exc.name == "yfinance":
            raise DataSourceError(f"yfinance is required for Yahoo OHLCV fetching. {_INSTALL_GUIDANCE}") from exc
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
