from pathlib import Path

import pandas as pd
import pytest

from smartanalyticsinvest.errors import MissingColumnsError
from smartanalyticsinvest.ingestion import load_ohlcv_csv
from smartanalyticsinvest.schema import REQUIRED_OHLCV_COLUMNS

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_ohlcv_csv_reads_local_fixture_with_canonical_columns():
    frame = load_ohlcv_csv(FIXTURES / "ohlcv_valid.csv")

    assert list(frame.columns) == list(REQUIRED_OHLCV_COLUMNS)
    assert len(frame) == 2
    assert frame.loc[0, "close"] == 11


def test_load_ohlcv_csv_missing_local_file_fails_clearly(tmp_path):
    missing = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError) as excinfo:
        load_ohlcv_csv(missing)

    assert str(missing) in str(excinfo.value)


def test_load_ohlcv_csv_rejects_csv_missing_required_columns(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    pd.DataFrame({"date": ["2024-01-01"], "open": [10]}).to_csv(bad_csv, index=False)

    with pytest.raises(MissingColumnsError):
        load_ohlcv_csv(bad_csv)


def test_load_ohlcv_csv_preserves_numeric_looking_ticker_text(tmp_path):
    csv_path = tmp_path / "numeric_tickers.csv"
    csv_path.write_text(
        "date,open,high,low,close,volume,ticker\n"
        "2024-01-01,10,11,9,10.5,100,001\n"
        "2024-01-01,20,21,19,20.5,200,1\n"
    )

    frame = load_ohlcv_csv(csv_path)

    assert frame["ticker"].tolist() == ["001", "1"]
