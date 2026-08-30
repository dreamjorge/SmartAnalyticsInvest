"""Cleaning and pipeline orchestration for OHLCV data."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from smartanalyticsinvest.errors import DataCleaningError, EmptyDataError
from smartanalyticsinvest.ingestion import load_ohlcv_csv
from smartanalyticsinvest.schema import NUMERIC_OHLCV_COLUMNS, require_ohlcv_columns

_PRICE_COLUMNS = ("open", "high", "low", "close")
_TICKER_COLUMN = "ticker"


def _raise_if_empty(frame: pd.DataFrame) -> None:
    if frame.empty:
        raise EmptyDataError("No OHLCV rows available after cleaning")


def _has_ticker_column(frame: pd.DataFrame) -> bool:
    return _TICKER_COLUMN in frame.columns


def _normalize_ticker_values(frame: pd.DataFrame) -> pd.DataFrame:
    null_mask = frame[_TICKER_COLUMN].isna()
    if bool(null_mask.any()):
        rows = ", ".join(str(index) for index in frame.index[null_mask].tolist())
        raise DataCleaningError(f"Found invalid ticker values in rows: {rows}")

    normalized = frame[_TICKER_COLUMN].astype(str).str.strip()
    empty_mask = normalized.eq("")
    if bool(empty_mask.any()):
        rows = ", ".join(str(index) for index in frame.index[empty_mask].tolist())
        raise DataCleaningError(f"Found invalid ticker values in rows: {rows}")

    frame[_TICKER_COLUMN] = normalized
    return frame


def _clean_sort_and_deduplicate(cleaned: pd.DataFrame) -> pd.DataFrame:
    if _has_ticker_column(cleaned):
        return (
            cleaned.sort_values([_TICKER_COLUMN, "date"], kind="mergesort")
            .drop_duplicates(subset=[_TICKER_COLUMN, "date"], keep="last")
            .reset_index(drop=True)
        )
    return (
        cleaned.sort_values("date", kind="mergesort")
        .drop_duplicates(subset="date", keep="last")
        .reset_index(drop=True)
    )


def clean_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Return validated, sorted, deduplicated OHLCV rows without mutating input."""

    require_ohlcv_columns(frame)
    cleaned = frame.copy()
    _raise_if_empty(cleaned)

    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    for column in NUMERIC_OHLCV_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    invalid_mask = cleaned[["date", *NUMERIC_OHLCV_COLUMNS]].isna().any(axis=1)
    finite_mask = cleaned[list(NUMERIC_OHLCV_COLUMNS)].map(math.isfinite).all(axis=1)
    invalid_mask |= ~finite_mask
    invalid_mask |= cleaned[list(_PRICE_COLUMNS)].le(0).any(axis=1)
    invalid_mask |= cleaned["volume"].lt(0)
    if bool(invalid_mask.any()):
        rows = ", ".join(str(index) for index in cleaned.index[invalid_mask].tolist())
        raise DataCleaningError(f"Found invalid required OHLCV values in rows: {rows}")

    inconsistent_mask = (
        cleaned["high"].lt(cleaned["low"])
        | cleaned["high"].lt(cleaned["open"])
        | cleaned["high"].lt(cleaned["close"])
        | cleaned["low"].gt(cleaned["open"])
        | cleaned["low"].gt(cleaned["close"])
    )
    if bool(inconsistent_mask.any()):
        rows = ", ".join(str(index) for index in cleaned.index[inconsistent_mask].tolist())
        raise DataCleaningError(f"Found inconsistent OHLCV values in rows: {rows}")

    if _has_ticker_column(cleaned):
        cleaned = _normalize_ticker_values(cleaned)

    result = _clean_sort_and_deduplicate(cleaned)
    _raise_if_empty(result)
    return result


def _add_grouped_sma(
    frame: pd.DataFrame, *, price_column: str = "close", windows: tuple[int, ...] = (20,)
) -> pd.DataFrame:
    from smartanalyticsinvest.indicators import simple_moving_average

    enriched = frame.copy()
    grouped_prices = enriched.groupby(_TICKER_COLUMN, sort=False)[price_column]
    for window in windows:
        enriched[f"sma_{window}"] = grouped_prices.transform(
            lambda series, window=window: simple_moving_average(series, window)
        )
    return enriched


def _add_grouped_rsi(
    frame: pd.DataFrame, *, price_column: str = "close", window: int = 14
) -> pd.DataFrame:
    from smartanalyticsinvest.indicators import relative_strength_index

    enriched = frame.copy()
    enriched[f"rsi_{window}"] = enriched.groupby(_TICKER_COLUMN, sort=False)[
        price_column
    ].transform(lambda series: relative_strength_index(series, window))
    return enriched


def _add_grouped_ema(
    frame: pd.DataFrame, *, price_column: str = "close", windows: tuple[int, ...] = (20,)
) -> pd.DataFrame:
    from smartanalyticsinvest.indicators import exponential_moving_average

    enriched = frame.copy()
    grouped_prices = enriched.groupby(_TICKER_COLUMN, sort=False)[price_column]
    for window in windows:
        enriched[f"ema_{window}"] = grouped_prices.transform(
            lambda series, window=window: exponential_moving_average(series, window)
        )
    return enriched


def _add_grouped_daily_returns(frame: pd.DataFrame, *, price_column: str = "close") -> pd.DataFrame:
    from smartanalyticsinvest.indicators import daily_returns

    enriched = frame.copy()
    enriched["daily_return"] = enriched.groupby(_TICKER_COLUMN, sort=False)[price_column].transform(
        daily_returns
    )
    return enriched


def enrich_ohlcv(
    frame: pd.DataFrame,
    *,
    sma_windows: tuple[int, ...] = (20,),
    rsi_window: int = 14,
    ema_windows: tuple[int, ...] = (),
    include_daily_returns: bool = False,
) -> pd.DataFrame:
    """Return cleaned OHLCV rows enriched with configured indicators."""

    if _has_ticker_column(frame):
        enriched = _add_grouped_sma(frame, windows=sma_windows)
        enriched = _add_grouped_rsi(enriched, window=rsi_window)
        enriched = _add_grouped_ema(enriched, windows=ema_windows)
        if include_daily_returns:
            enriched = _add_grouped_daily_returns(enriched)
        return enriched

    from smartanalyticsinvest.indicators import add_daily_returns, add_ema, add_rsi, add_sma

    enriched = add_sma(frame, windows=sma_windows)
    enriched = add_rsi(enriched, window=rsi_window)
    enriched = add_ema(enriched, windows=ema_windows)
    if include_daily_returns:
        enriched = add_daily_returns(enriched)
    return enriched


def run_csv_pipeline(
    input_path: str | Path,
    *,
    sma_windows: tuple[int, ...] = (20,),
    rsi_window: int = 14,
    ema_windows: tuple[int, ...] = (),
    include_daily_returns: bool = False,
) -> pd.DataFrame:
    """Load, clean, and enrich a local OHLCV CSV file."""

    loaded = load_ohlcv_csv(input_path)
    cleaned = clean_ohlcv(loaded)
    return enrich_ohlcv(
        cleaned,
        sma_windows=sma_windows,
        rsi_window=rsi_window,
        ema_windows=ema_windows,
        include_daily_returns=include_daily_returns,
    )
