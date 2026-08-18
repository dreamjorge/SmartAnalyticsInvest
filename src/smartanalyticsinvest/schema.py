"""OHLCV schema normalization and validation."""

from __future__ import annotations

import pandas as pd

from smartanalyticsinvest.errors import MissingColumnsError

REQUIRED_OHLCV_COLUMNS: tuple[str, ...] = ("date", "open", "high", "low", "close", "volume")
NUMERIC_OHLCV_COLUMNS: tuple[str, ...] = ("open", "high", "low", "close", "volume")

_STANDARD_COLUMN_NAMES = set(REQUIRED_OHLCV_COLUMNS)


def _canonical_column_name(column: object) -> object:
    if not isinstance(column, str):
        return column
    candidate = column.strip().lower()
    if candidate in _STANDARD_COLUMN_NAMES:
        return candidate
    return column


def normalize_ohlcv_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with standard OHLCV headers canonicalized.

    Only exact standard names are accepted after case folding and surrounding
    whitespace trimming. Broader aliases such as ``Adj Close`` are preserved.
    """

    normalized = frame.copy()
    normalized.columns = [_canonical_column_name(column) for column in frame.columns]
    return normalized


def require_ohlcv_columns(frame: pd.DataFrame) -> None:
    """Raise MissingColumnsError unless all required OHLCV columns are present."""

    present = set(frame.columns)
    missing = [column for column in REQUIRED_OHLCV_COLUMNS if column not in present]
    if missing:
        raise MissingColumnsError(missing)
