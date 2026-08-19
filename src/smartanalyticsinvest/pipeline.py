"""Cleaning and pipeline orchestration for OHLCV data."""

from __future__ import annotations

from pathlib import Path
import math

import pandas as pd

from smartanalyticsinvest.errors import DataCleaningError, EmptyDataError
from smartanalyticsinvest.ingestion import load_ohlcv_csv
from smartanalyticsinvest.schema import NUMERIC_OHLCV_COLUMNS, REQUIRED_OHLCV_COLUMNS, require_ohlcv_columns

_PRICE_COLUMNS = ("open", "high", "low", "close")


def _raise_if_empty(frame: pd.DataFrame) -> None:
    if frame.empty:
        raise EmptyDataError("No OHLCV rows available after cleaning")


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

    if "ticker" in cleaned.columns and cleaned["ticker"].dropna().nunique() > 1:
        raise DataCleaningError("Found multiple instruments in OHLCV frame; split by ticker first")

    result = (
        cleaned.sort_values("date", kind="mergesort")
        .drop_duplicates(subset="date", keep="last")
        .reset_index(drop=True)
    )
    _raise_if_empty(result)
    return result


def enrich_ohlcv(
    frame: pd.DataFrame, *, sma_windows: tuple[int, ...] = (20,), rsi_window: int = 14
) -> pd.DataFrame:
    """Return cleaned OHLCV rows enriched with configured indicators."""

    from smartanalyticsinvest.indicators import add_rsi, add_sma

    enriched = add_sma(frame, windows=sma_windows)
    return add_rsi(enriched, window=rsi_window)


def run_csv_pipeline(
    input_path: str | Path, *, sma_windows: tuple[int, ...] = (20,), rsi_window: int = 14
) -> pd.DataFrame:
    """Load, clean, and enrich a local OHLCV CSV file."""

    loaded = load_ohlcv_csv(input_path)
    cleaned = clean_ohlcv(loaded)
    return enrich_ohlcv(cleaned, sma_windows=sma_windows, rsi_window=rsi_window)
