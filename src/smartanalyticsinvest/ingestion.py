"""Local CSV ingestion for canonical OHLCV data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from smartanalyticsinvest.schema import normalize_ohlcv_columns, require_ohlcv_columns


def load_ohlcv_csv(path: str | Path) -> pd.DataFrame:
    """Load a local OHLCV CSV file and validate its required columns."""

    csv_path = Path(path)
    frame = pd.read_csv(csv_path, dtype={"ticker": "string"})
    normalized = normalize_ohlcv_columns(frame)
    require_ohlcv_columns(normalized)
    return normalized
