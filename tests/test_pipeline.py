import pandas as pd
import pytest

from smartanalyticsinvest.errors import DataCleaningError
from smartanalyticsinvest.pipeline import clean_ohlcv, enrich_ohlcv, run_csv_pipeline
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

    result = run_csv_pipeline(input_csv, sma_windows=(2,), rsi_windows=(2,))

    assert list(result.columns) == [*REQUIRED_OHLCV_COLUMNS, "sma_2", "rsi_2"]
    assert result["date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
    ]
    assert result["sma_2"].tolist()[1:] == [11.0, 13.0]
    assert result.loc[2, "rsi_2"] == 100.0


def test_run_csv_pipeline_preserves_default_indicator_columns(tmp_path):
    input_csv = tmp_path / "ohlcv.csv"
    pd.DataFrame(
        [
            ["2024-01-01", 10, 11, 9, 10, 100],
            ["2024-01-02", 12, 13, 11, 12, 200],
        ],
        columns=REQUIRED_OHLCV_COLUMNS,
    ).to_csv(input_csv, index=False)

    result = run_csv_pipeline(input_csv)

    assert list(result.columns) == [*REQUIRED_OHLCV_COLUMNS, "sma_20", "rsi_14"]


def test_run_csv_pipeline_optionally_adds_ema_and_daily_returns(tmp_path):
    input_csv = tmp_path / "ohlcv.csv"
    pd.DataFrame(
        [
            ["2024-01-01", 10, 11, 9, 10, 100],
            ["2024-01-02", 12, 13, 11, 12, 200],
            ["2024-01-03", 14, 15, 13, 14, 300],
        ],
        columns=REQUIRED_OHLCV_COLUMNS,
    ).to_csv(input_csv, index=False)

    result = run_csv_pipeline(
        input_csv,
        sma_windows=(2,),
        rsi_windows=(2,),
        ema_windows=(2,),
        include_daily_returns=True,
    )

    assert list(result.columns) == [
        *REQUIRED_OHLCV_COLUMNS,
        "sma_2",
        "rsi_2",
        "ema_2",
        "daily_return",
    ]
    assert result["ema_2"].tolist() == pytest.approx([10.0, 11.333333, 13.111111], rel=1e-6)
    assert pd.isna(result.loc[0, "daily_return"])
    assert result.loc[1, "daily_return"] == pytest.approx(0.2)


def test_run_csv_pipeline_stops_on_cleaning_validation_failure(tmp_path):
    input_csv = tmp_path / "bad.csv"
    pd.DataFrame(
        [["2024-01-01", 10, 11, 9, "bad-close", 100]], columns=REQUIRED_OHLCV_COLUMNS
    ).to_csv(input_csv, index=False)

    with pytest.raises(DataCleaningError):
        run_csv_pipeline(input_csv, sma_windows=(2,), rsi_windows=(2,))


def test_enrich_ohlcv_groups_sma_by_ticker_without_multiindex():
    cleaned = clean_ohlcv(
        pd.DataFrame(
            [
                ["2024-01-01", 10, 11, 9, 10, 100, "B"],
                ["2024-01-01", 100, 101, 99, 100, 100, "A"],
                ["2024-01-02", 12, 13, 11, 12, 100, "B"],
                ["2024-01-02", 102, 103, 101, 102, 100, "A"],
            ],
            columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
        )
    )

    result = enrich_ohlcv(cleaned, sma_windows=(2,), rsi_windows=(2,))

    assert not isinstance(result.index, pd.MultiIndex)
    assert result["ticker"].tolist() == ["A", "A", "B", "B"]
    assert pd.isna(result.loc[0, "sma_2"])
    assert result.loc[1, "sma_2"] == 101.0
    assert pd.isna(result.loc[2, "sma_2"])
    assert result.loc[3, "sma_2"] == 11.0


def test_enrich_ohlcv_groups_ema_and_daily_returns_by_ticker():
    cleaned = clean_ohlcv(
        pd.DataFrame(
            [
                ["2024-01-01", 100, 101, 99, 100, 100, "B"],
                ["2024-01-02", 110, 111, 109, 110, 100, "B"],
                ["2024-01-01", 10, 11, 9, 10, 100, "A"],
                ["2024-01-02", 12, 13, 11, 12, 100, "A"],
            ],
            columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
        )
    )

    result = enrich_ohlcv(
        cleaned,
        sma_windows=(2,),
        rsi_windows=(2,),
        ema_windows=(2,),
        include_daily_returns=True,
    )

    assert result["ticker"].tolist() == ["A", "A", "B", "B"]
    assert result.loc[0, "ema_2"] == 10.0
    assert result.loc[1, "ema_2"] == pytest.approx(11.333333, rel=1e-6)
    assert result.loc[2, "ema_2"] == 100.0
    assert result.loc[3, "ema_2"] == pytest.approx(106.666667, rel=1e-6)
    assert pd.isna(result.loc[0, "daily_return"])
    assert result.loc[1, "daily_return"] == pytest.approx(0.2)
    assert pd.isna(result.loc[2, "daily_return"])
    assert result.loc[3, "daily_return"] == pytest.approx(0.1)


def test_enrich_ohlcv_groups_rsi_diff_by_ticker():
    cleaned = clean_ohlcv(
        pd.DataFrame(
            [
                ["2024-01-01", 50, 51, 49, 50, 100, "A"],
                ["2024-01-02", 49, 50, 48, 49, 100, "A"],
                ["2024-01-03", 51, 52, 50, 51, 100, "A"],
                ["2024-01-01", 100, 101, 99, 100, 100, "B"],
                ["2024-01-02", 110, 111, 109, 110, 100, "B"],
                ["2024-01-03", 120, 121, 119, 120, 100, "B"],
            ],
            columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
        )
    )

    result = enrich_ohlcv(cleaned, sma_windows=(2,), rsi_windows=(2,))

    b_rsi = result.loc[result["ticker"].eq("B"), "rsi_2"].tolist()
    assert pd.isna(b_rsi[0])
    assert pd.isna(b_rsi[1])
    assert b_rsi[2] == 100.0


def test_run_csv_pipeline_accepts_multi_ticker_csv_and_keeps_grouped_output(tmp_path):
    input_csv = tmp_path / "multi.csv"
    pd.DataFrame(
        [
            ["2024-01-02", 12, 13, 11, 12, 200, " MSFT"],
            ["2024-01-01", 10, 11, 9, 10, 100, "AAPL "],
            ["2024-01-02", 14, 15, 13, 14, 300, "AAPL"],
        ],
        columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
    ).to_csv(input_csv, index=False)

    result = run_csv_pipeline(input_csv, sma_windows=(2,), rsi_windows=(2,))

    assert [*REQUIRED_OHLCV_COLUMNS, "ticker", "sma_2", "rsi_2"] == list(result.columns)
    assert result[["ticker", "date"]].to_dict("records") == [
        {"ticker": "AAPL", "date": pd.Timestamp("2024-01-01")},
        {"ticker": "AAPL", "date": pd.Timestamp("2024-01-02")},
        {"ticker": "MSFT", "date": pd.Timestamp("2024-01-02")},
    ]
    assert pd.isna(result.loc[2, "sma_2"])


def test_single_ticker_indicators_match_equivalent_no_ticker_input():
    rows = [
        ["2024-01-01", 10, 11, 9, 10, 100],
        ["2024-01-02", 12, 13, 11, 12, 100],
        ["2024-01-03", 11, 12, 10, 11, 100],
    ]
    no_ticker = enrich_ohlcv(
        clean_ohlcv(pd.DataFrame(rows, columns=REQUIRED_OHLCV_COLUMNS)),
        sma_windows=(2,),
        rsi_windows=(2,),
    )
    with_ticker = enrich_ohlcv(
        clean_ohlcv(
            pd.DataFrame(
                [row + ["ONLY"] for row in rows], columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"]
            )
        ),
        sma_windows=(2,),
        rsi_windows=(2,),
    )

    pd.testing.assert_series_equal(with_ticker["sma_2"], no_ticker["sma_2"], check_names=False)
    pd.testing.assert_series_equal(with_ticker["rsi_2"], no_ticker["rsi_2"], check_names=False)
    assert with_ticker["ticker"].tolist() == ["ONLY", "ONLY", "ONLY"]


def test_enrich_ohlcv_accepts_multiple_rsi_windows_without_ticker():
    rows = [
        ["2024-01-01", 10, 11, 9, 10, 100],
        ["2024-01-02", 12, 13, 11, 12, 100],
        ["2024-01-03", 11, 12, 10, 11, 100],
        ["2024-01-04", 13, 14, 12, 13, 100],
    ]
    cleaned = clean_ohlcv(pd.DataFrame(rows, columns=REQUIRED_OHLCV_COLUMNS))

    result = enrich_ohlcv(cleaned, sma_windows=(2,), rsi_windows=(2, 3))

    assert [*REQUIRED_OHLCV_COLUMNS, "sma_2", "rsi_2", "rsi_3"] == list(result.columns)
    assert result["rsi_2"].notna().sum() < len(result)
    assert result["rsi_3"].notna().sum() < result["rsi_2"].notna().sum()


def test_enrich_ohlcv_accepts_multiple_rsi_windows_grouped_by_ticker():
    cleaned = clean_ohlcv(
        pd.DataFrame(
            [
                ["2024-01-01", 10, 11, 9, 10, 100, "A"],
                ["2024-01-02", 12, 13, 11, 12, 100, "A"],
                ["2024-01-03", 11, 12, 10, 11, 100, "A"],
                ["2024-01-04", 13, 14, 12, 13, 100, "A"],
            ],
            columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
        )
    )

    result = enrich_ohlcv(cleaned, sma_windows=(2,), rsi_windows=(2, 3))

    assert [*REQUIRED_OHLCV_COLUMNS, "ticker", "sma_2", "rsi_2", "rsi_3"] == list(result.columns)


def test_enrich_ohlcv_optionally_adds_macd_without_ticker():
    rows = [
        ["2024-01-01", 9, 11, 8, 10, 100],
        ["2024-01-02", 10, 12, 9, 11, 100],
        ["2024-01-03", 11, 13, 10, 12, 100],
        ["2024-01-04", 10, 12, 9, 11, 100],
        ["2024-01-05", 12, 14, 11, 13, 100],
    ]
    cleaned = clean_ohlcv(pd.DataFrame(rows, columns=REQUIRED_OHLCV_COLUMNS))

    result = enrich_ohlcv(
        cleaned, sma_windows=(2,), include_macd=True, macd_fast=2, macd_slow=3, macd_signal=2
    )

    assert [
        *REQUIRED_OHLCV_COLUMNS,
        "sma_2",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
    ] == list(result.columns)
    assert not result["macd"].isna().all()


def test_enrich_ohlcv_optionally_adds_macd_grouped_by_ticker():
    cleaned = clean_ohlcv(
        pd.DataFrame(
            [
                ["2024-01-01", 9, 11, 8, 10, 100, "A"],
                ["2024-01-02", 10, 12, 9, 11, 100, "A"],
                ["2024-01-03", 11, 13, 10, 12, 100, "A"],
                ["2024-01-04", 10, 12, 9, 11, 100, "A"],
                ["2024-01-05", 12, 14, 11, 13, 100, "A"],
            ],
            columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
        )
    )

    result = enrich_ohlcv(
        cleaned, sma_windows=(2,), include_macd=True, macd_fast=2, macd_slow=3, macd_signal=2
    )

    assert [
        *REQUIRED_OHLCV_COLUMNS,
        "ticker",
        "sma_2",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
    ] == list(result.columns)


def test_enrich_ohlcv_optionally_adds_bollinger_bands_without_ticker():
    rows = [
        ["2024-01-01", 9, 11, 8, 10, 100],
        ["2024-01-02", 10, 12, 9, 11, 100],
        ["2024-01-03", 11, 13, 10, 12, 100],
        ["2024-01-04", 10, 12, 9, 11, 100],
        ["2024-01-05", 12, 14, 11, 13, 100],
    ]
    cleaned = clean_ohlcv(pd.DataFrame(rows, columns=REQUIRED_OHLCV_COLUMNS))

    result = enrich_ohlcv(cleaned, sma_windows=(2,), bollinger_windows=(3,))

    assert [
        *REQUIRED_OHLCV_COLUMNS,
        "sma_2",
        "rsi_14",
        "bb_middle_3",
        "bb_upper_3",
        "bb_lower_3",
    ] == list(result.columns)
    assert result.loc[2, "bb_middle_3"] == 11.0


def test_enrich_ohlcv_optionally_adds_bollinger_bands_grouped_by_ticker():
    cleaned = clean_ohlcv(
        pd.DataFrame(
            [
                ["2024-01-01", 9, 11, 8, 10, 100, "A"],
                ["2024-01-02", 10, 12, 9, 11, 100, "A"],
                ["2024-01-03", 11, 13, 10, 12, 100, "A"],
                ["2024-01-04", 10, 12, 9, 11, 100, "A"],
                ["2024-01-05", 12, 14, 11, 13, 100, "A"],
            ],
            columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
        )
    )

    result = enrich_ohlcv(cleaned, sma_windows=(2,), bollinger_windows=(3,))

    assert [
        *REQUIRED_OHLCV_COLUMNS,
        "ticker",
        "sma_2",
        "rsi_14",
        "bb_middle_3",
        "bb_upper_3",
        "bb_lower_3",
    ] == list(result.columns)
    assert result.loc[2, "bb_middle_3"] == 11.0


def test_enrich_ohlcv_optionally_adds_atr_without_ticker():
    rows = [
        ["2024-01-01", 10, 11, 9, 10, 100],
        ["2024-01-02", 14, 15, 14, 14, 100],
        ["2024-01-03", 14, 15, 13, 14, 100],
        ["2024-01-04", 15, 16, 14, 15, 100],
        ["2024-01-05", 16, 17, 15, 16, 100],
    ]
    cleaned = clean_ohlcv(pd.DataFrame(rows, columns=REQUIRED_OHLCV_COLUMNS))

    result = enrich_ohlcv(cleaned, sma_windows=(2,), atr_windows=(3,))

    assert [*REQUIRED_OHLCV_COLUMNS, "sma_2", "rsi_14", "atr_3"] == list(result.columns)
    assert result.loc[2, "atr_3"] == pytest.approx(3.0)
    assert result.loc[4, "atr_3"] == pytest.approx(2.0)


def test_enrich_ohlcv_atr_does_not_leak_previous_close_across_tickers():
    cleaned = clean_ohlcv(
        pd.DataFrame(
            [
                ["2024-01-01", 10, 11, 9, 10, 100, "A"],
                ["2024-01-02", 14, 15, 14, 14, 100, "A"],
                ["2024-01-03", 14, 15, 13, 14, 100, "A"],
                ["2024-01-04", 15, 16, 14, 15, 100, "A"],
                ["2024-01-05", 16, 17, 15, 16, 100, "A"],
                ["2024-01-01", 95, 100, 90, 95, 100, "B"],
            ],
            columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
        )
    )

    result = enrich_ohlcv(cleaned, atr_windows=(1,))

    b_row = result.loc[result["ticker"].eq("B")].iloc[0]
    assert b_row["atr_1"] == pytest.approx(10.0)
