import pandas as pd
import pytest

from smartanalyticsinvest.errors import DataCleaningError, EmptyDataError
from smartanalyticsinvest.pipeline import clean_ohlcv
from smartanalyticsinvest.schema import REQUIRED_OHLCV_COLUMNS


def _frame(rows):
    return pd.DataFrame(rows, columns=REQUIRED_OHLCV_COLUMNS)


def test_clean_ohlcv_parses_dates_sorts_coerces_numbers_and_keeps_last_duplicate():
    source = _frame(
        [
            ["2024-01-02", "12", "13", "11", "12.5", "200"],
            ["2024-01-01", "10", "11", "9", "10.5", "100"],
            ["2024-01-02", "14", "15", "13", "14.5", "250"],
        ]
    )

    cleaned = clean_ohlcv(source)

    assert list(cleaned.columns) == list(REQUIRED_OHLCV_COLUMNS)
    assert cleaned["date"].tolist() == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")]
    assert cleaned["close"].tolist() == [10.5, 14.5]
    assert cleaned.loc[1, "open"] == 14
    assert pd.api.types.is_numeric_dtype(cleaned["volume"])


@pytest.mark.parametrize(
    "bad_row",
    [
        ["not-a-date", 10, 11, 9, 10.5, 100],
        ["2024-01-01", 10, 11, 9, "not-a-number", 100],
        ["2024-01-01", 10, 11, 9, None, 100],
        ["2024-01-01", 0, 11, 9, 10.5, 100],
        ["2024-01-01", 10, -1, 9, 10.5, 100],
        ["2024-01-01", 10, 11, 9, 10.5, -1],
    ],
)
def test_clean_ohlcv_fails_fast_for_invalid_required_values_by_default(bad_row):
    with pytest.raises(DataCleaningError, match="invalid required"):
        clean_ohlcv(_frame([bad_row]))


def test_clean_ohlcv_raises_empty_data_error_for_no_rows():
    with pytest.raises(EmptyDataError):
        clean_ohlcv(pd.DataFrame(columns=REQUIRED_OHLCV_COLUMNS))


def test_clean_ohlcv_preserves_extra_columns_in_messy_sorted_duplicate_fixture():
    source = pd.DataFrame(
        [
            ["2024-01-03", 13, 14, 12, 13.5, 300, "late"],
            ["2024-01-01", 10, 11, 9, 10.5, 100, "first"],
            ["2024-01-01", 11, 12, 10, 11.5, 150, "replacement"],
            ["2024-01-02", 12, 13, 11, 12.5, 200, "middle"],
        ],
        columns=[*REQUIRED_OHLCV_COLUMNS, "note"],
    )
    original = source.copy(deep=True)

    cleaned = clean_ohlcv(source)

    assert cleaned["date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
    ]
    assert cleaned["note"].tolist() == ["replacement", "middle", "late"]
    pd.testing.assert_frame_equal(source, original)


def test_clean_ohlcv_rejects_invalid_rows_before_dropping_from_messy_fixture():
    source = pd.DataFrame(
        [
            ["2024-01-02", 12, 13, 11, 12.5, 200, "valid"],
            ["bad-date", 12, 13, 11, 12.5, 200, "invalid"],
        ],
        columns=[*REQUIRED_OHLCV_COLUMNS, "note"],
    )

    with pytest.raises(DataCleaningError, match="invalid required"):
        clean_ohlcv(source)
