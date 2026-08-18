import pandas as pd
import pytest

from smartanalyticsinvest.errors import DataCleaningError
from smartanalyticsinvest.pipeline import run_csv_pipeline
from smartanalyticsinvest.schema import REQUIRED_OHLCV_COLUMNS


def test_run_csv_pipeline_returns_clean_sorted_rows_with_sma_and_rsi(tmp_path):
    input_csv = tmp_path / "ohlcv.csv"
    pd.DataFrame(
        [
            ["2024-01-02", 12, 13, 11, 12, 200],
            ["2024-01-01", 10, 11, 9, 10, 100],
            ["2024-01-03", 14, 15, 13, 14, 300],
        ],
        columns=REQUIRED_OHLCV_COLUMNS,
    ).to_csv(input_csv, index=False)

    result = run_csv_pipeline(input_csv, sma_windows=(2,), rsi_window=2)

    assert list(result.columns) == [*REQUIRED_OHLCV_COLUMNS, "sma_2", "rsi_2"]
    assert result["date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
    ]
    assert result["sma_2"].tolist()[1:] == [11.0, 13.0]
    assert result.loc[2, "rsi_2"] == 100.0


def test_run_csv_pipeline_stops_on_cleaning_validation_failure(tmp_path):
    input_csv = tmp_path / "bad.csv"
    pd.DataFrame(
        [["2024-01-01", 10, 11, 9, "bad-close", 100]], columns=REQUIRED_OHLCV_COLUMNS
    ).to_csv(input_csv, index=False)

    with pytest.raises(DataCleaningError):
        run_csv_pipeline(input_csv, sma_windows=(2,), rsi_window=2)
