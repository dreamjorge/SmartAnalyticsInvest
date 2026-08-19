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
        ["2024-01-01", float("inf"), 11, 9, 10.5, 100],
        ["2024-01-01", 10, 11, 9, "Infinity", 100],
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


def test_clean_ohlcv_without_ticker_preserves_extra_columns_and_does_not_add_ticker():
    source = pd.DataFrame(
        [
            ["2024-01-02", 12, 13, 11, 12.5, 200, "old"],
            ["2024-01-01", 10, 11, 9, 10.5, 100, "first"],
            ["2024-01-02", 14, 15, 13, 14.5, 250, "last"],
        ],
        columns=[*REQUIRED_OHLCV_COLUMNS, "note"],
    )

    cleaned = clean_ohlcv(source)

    assert "ticker" not in cleaned.columns
    assert cleaned["date"].tolist() == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")]
    assert cleaned["note"].tolist() == ["first", "last"]


def test_clean_ohlcv_accepts_trims_sorts_and_preserves_multiple_tickers():
    source = pd.DataFrame(
        [
            ["2024-01-02", 20, 21, 19, 20.5, 200, " MSFT "],
            ["2024-01-01", 10, 11, 9, 10.5, 100, "AAPL"],
            ["2024-01-01", 21, 22, 20, 21.5, 210, " MSFT"],
        ],
        columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
    )

    cleaned = clean_ohlcv(source)

    assert cleaned["ticker"].tolist() == ["AAPL", "MSFT", "MSFT"]
    assert cleaned["date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-02"),
    ]


@pytest.mark.parametrize("bad_ticker", [None, pd.NA, float("nan"), "", "   "])
def test_clean_ohlcv_rejects_null_empty_and_whitespace_tickers(bad_ticker):
    source = pd.DataFrame(
        [["2024-01-01", 10, 11, 9, 10.5, 100, bad_ticker]],
        columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
    )

    with pytest.raises(DataCleaningError, match="ticker"):
        clean_ohlcv(source)


def test_clean_ohlcv_rejects_mixed_valid_and_invalid_tickers():
    source = pd.DataFrame(
        [
            ["2024-01-01", 10, 11, 9, 10.5, 100, "AAPL"],
            ["2024-01-02", 20, 21, 19, 20.5, 200, " "],
        ],
        columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
    )

    with pytest.raises(DataCleaningError, match="ticker"):
        clean_ohlcv(source)


def test_clean_ohlcv_deduplicates_by_ticker_and_date_preserving_extra_columns():
    source = pd.DataFrame(
        [
            ["2024-01-01", 10, 11, 9, 10.5, 100, "MSFT", "keep-msft"],
            ["2024-01-01", 20, 21, 19, 20.5, 200, " AAPL", "old-aapl"],
            ["2024-01-01", 22, 23, 21, 22.5, 220, "AAPL ", "new-aapl"],
            ["2024-01-02", 24, 25, 23, 24.5, 240, "AAPL", "next-aapl"],
        ],
        columns=[*REQUIRED_OHLCV_COLUMNS, "ticker", "note"],
    )

    cleaned = clean_ohlcv(source)

    assert cleaned[["ticker", "date", "close", "note"]].to_dict("records") == [
        {"ticker": "AAPL", "date": pd.Timestamp("2024-01-01"), "close": 22.5, "note": "new-aapl"},
        {"ticker": "AAPL", "date": pd.Timestamp("2024-01-02"), "close": 24.5, "note": "next-aapl"},
        {"ticker": "MSFT", "date": pd.Timestamp("2024-01-01"), "close": 10.5, "note": "keep-msft"},
    ]
