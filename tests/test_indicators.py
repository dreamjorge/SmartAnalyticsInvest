import pandas as pd
import pytest

from smartanalyticsinvest.indicators import (
    add_atr,
    add_bollinger_bands,
    add_daily_returns,
    add_ema,
    add_macd,
    add_rsi,
    add_sma,
    average_true_range,
    bollinger_bands,
    daily_returns,
    exponential_moving_average,
    macd,
    relative_strength_index,
    simple_moving_average,
    true_range,
)


def test_simple_moving_average_uses_close_rolling_mean():
    sma = simple_moving_average(pd.Series([10, 12, 14]), 2)

    assert pd.isna(sma.iloc[0])
    assert sma.iloc[1:].tolist() == [11.0, 13.0]


def test_add_sma_creates_window_columns_without_mutating_input():
    frame = pd.DataFrame({"close": [10, 12, 14]})
    original = frame.copy(deep=True)

    enriched = add_sma(frame, windows=(2,))

    assert enriched["sma_2"].tolist()[1:] == [11.0, 13.0]
    assert "sma_2" not in frame.columns
    pd.testing.assert_frame_equal(frame, original)


def test_exponential_moving_average_uses_pandas_ewm_span_without_adjustment():
    ema = exponential_moving_average(pd.Series([10.0, 12.0, 14.0]), 2)

    assert ema.tolist() == pytest.approx([10.0, 11.333333, 13.111111], rel=1e-6)


def test_daily_returns_uses_percentage_change_with_missing_first_row():
    returns = daily_returns(pd.Series([10.0, 12.0, 9.0]))

    assert pd.isna(returns.iloc[0])
    assert returns.iloc[1:].tolist() == pytest.approx([0.2, -0.25])


def test_daily_returns_does_not_fill_missing_prices():
    returns = daily_returns(pd.Series([10.0, None, 12.0]))

    assert returns.isna().tolist() == [True, True, True]


def test_daily_returns_passes_no_fill_method_explicitly(monkeypatch):
    calls = []
    original_pct_change = pd.Series.pct_change

    def spy_pct_change(self, *args, **kwargs):
        calls.append(kwargs)
        return original_pct_change(self, *args, **kwargs)

    monkeypatch.setattr(pd.Series, "pct_change", spy_pct_change)

    daily_returns(pd.Series([10.0, None, 12.0]))

    assert calls == [{"fill_method": None}]


def test_add_ema_and_daily_returns_create_columns_without_mutating_input():
    frame = pd.DataFrame({"close": [10.0, 12.0, 14.0]})
    original = frame.copy(deep=True)

    enriched = add_daily_returns(add_ema(frame, windows=(2,)))

    assert enriched["ema_2"].tolist() == pytest.approx([10.0, 11.333333, 13.111111], rel=1e-6)
    assert pd.isna(enriched.loc[0, "daily_return"])
    assert enriched.loc[1, "daily_return"] == pytest.approx(0.2)
    assert "ema_2" not in frame.columns
    assert "daily_return" not in frame.columns
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("window", [0, -1, 1.5, "2"])
def test_sma_rsi_and_ema_reject_invalid_windows(window):
    with pytest.raises(ValueError, match="window"):
        simple_moving_average(pd.Series([10, 12, 14]), window)
    with pytest.raises(ValueError, match="window"):
        relative_strength_index(pd.Series([10, 12, 14]), window)
    with pytest.raises(ValueError, match="window"):
        exponential_moving_average(pd.Series([10, 12, 14]), window)


def test_relative_strength_index_has_deterministic_bounded_values():
    rsi = relative_strength_index(pd.Series([10, 12, 11, 13]), 2)

    assert pd.isna(rsi.iloc[0])
    assert pd.isna(rsi.iloc[1])
    assert rsi.dropna().between(0, 100).all()
    assert rsi.iloc[2] == pytest.approx(66.6667, rel=1e-4)
    assert rsi.iloc[3] == pytest.approx(66.6667, rel=1e-4)


def test_add_rsi_creates_column_without_mutating_input_and_flat_series_is_neutral():
    frame = pd.DataFrame({"close": [10, 10, 10]})
    original = frame.copy(deep=True)

    enriched = add_rsi(frame, windows=(2,))

    assert pd.isna(enriched.loc[0, "rsi_2"])
    assert pd.isna(enriched.loc[1, "rsi_2"])
    assert enriched.loc[2, "rsi_2"] == 50.0
    assert "rsi_2" not in frame.columns
    pd.testing.assert_frame_equal(frame, original)


def test_add_rsi_creates_one_column_per_requested_window():
    frame = pd.DataFrame({"close": [10, 12, 11, 13, 12]})

    enriched = add_rsi(frame, windows=(2, 3))

    assert "rsi_2" in enriched.columns
    assert "rsi_3" in enriched.columns
    assert enriched["rsi_2"].notna().sum() > enriched["rsi_3"].notna().sum()


def test_relative_strength_index_declining_series_reaches_zero_after_window():
    rsi = relative_strength_index(pd.Series([13, 12, 11]), 2)

    assert pd.isna(rsi.iloc[0])
    assert pd.isna(rsi.iloc[1])
    assert rsi.iloc[2] == 0.0


def test_macd_matches_hand_computed_ema_difference_and_signal():
    series = pd.Series([10.0, 11, 12, 11, 13, 14, 13, 15, 16, 15])

    macd_line, signal_line, histogram = macd(series, fast=3, slow=5, signal=2)

    assert macd_line.tolist() == pytest.approx(
        [
            0.0,
            0.166667,
            0.361111,
            0.199074,
            0.445216,
            0.619727,
            0.407943,
            0.602691,
            0.733825,
            0.488566,
        ],
        rel=1e-4,
    )
    assert signal_line.tolist() == pytest.approx(
        [
            0.0,
            0.111111,
            0.277778,
            0.225309,
            0.371914,
            0.537123,
            0.451003,
            0.552129,
            0.673260,
            0.550131,
        ],
        rel=1e-4,
    )
    assert histogram.tolist() == pytest.approx((macd_line - signal_line).tolist(), rel=1e-9)


def test_add_macd_creates_columns_without_mutating_input():
    frame = pd.DataFrame({"close": [10.0, 11, 12, 11, 13, 14, 13, 15, 16, 15]})
    original = frame.copy(deep=True)

    enriched = add_macd(frame, fast=3, slow=5, signal=2)

    assert list(enriched.columns) == ["close", "macd", "macd_signal", "macd_histogram"]
    assert enriched["macd"].tolist() == pytest.approx(
        [
            0.0,
            0.166667,
            0.361111,
            0.199074,
            0.445216,
            0.619727,
            0.407943,
            0.602691,
            0.733825,
            0.488566,
        ],
        rel=1e-4,
    )
    pd.testing.assert_frame_equal(frame, original)


def test_bollinger_bands_matches_hand_computed_sma_and_std():
    series = pd.Series([10.0, 12, 11, 13, 14])

    middle, upper, lower = bollinger_bands(series, window=3, num_std=2.0)

    assert middle.tolist() == pytest.approx(
        [float("nan"), float("nan"), 11.0, 12.0, 12.666667], nan_ok=True, rel=1e-6
    )
    assert upper.tolist() == pytest.approx(
        [float("nan"), float("nan"), 12.632993, 13.632993, 15.161105], nan_ok=True, rel=1e-6
    )
    assert lower.tolist() == pytest.approx(
        [float("nan"), float("nan"), 9.367007, 10.367007, 10.172228], nan_ok=True, rel=1e-6
    )


def test_bollinger_bands_supports_window_of_one_with_population_std():
    series = pd.Series([10.0, 12.0, 11.0])

    middle, upper, lower = bollinger_bands(series, window=1, num_std=2.0)

    assert middle.tolist() == [10.0, 12.0, 11.0]
    assert upper.tolist() == [10.0, 12.0, 11.0]
    assert lower.tolist() == [10.0, 12.0, 11.0]


@pytest.mark.parametrize("num_std", [0, -1, float("nan"), float("inf"), "2"])
def test_bollinger_bands_rejects_invalid_num_std(num_std):
    with pytest.raises(ValueError, match="num_std"):
        bollinger_bands(pd.Series([10.0, 12.0, 11.0]), window=2, num_std=num_std)


def test_add_bollinger_bands_creates_columns_per_window_without_mutating_input():
    frame = pd.DataFrame({"close": [10.0, 12, 11, 13, 14]})
    original = frame.copy(deep=True)

    enriched = add_bollinger_bands(frame, windows=(3,), num_std=2.0)

    assert list(enriched.columns) == ["close", "bb_middle_3", "bb_upper_3", "bb_lower_3"]
    assert enriched.loc[2, "bb_middle_3"] == 11.0
    assert enriched.loc[2, "bb_upper_3"] == pytest.approx(12.632993, rel=1e-6)
    assert enriched.loc[2, "bb_lower_3"] == pytest.approx(9.367007, rel=1e-6)
    pd.testing.assert_frame_equal(frame, original)


def test_true_range_uses_gap_from_prior_close_when_larger_than_high_low_range():
    frame = pd.DataFrame(
        {
            "high": [11.0, 15.0, 15.0, 16.0, 17.0],
            "low": [9.0, 14.0, 13.0, 14.0, 15.0],
            "close": [10.0, 14.0, 14.0, 15.0, 16.0],
        }
    )

    tr = true_range(frame)

    assert tr.tolist() == pytest.approx([2.0, 5.0, 2.0, 2.0, 2.0])


def test_average_true_range_matches_hand_computed_rolling_mean():
    frame = pd.DataFrame(
        {
            "high": [11.0, 15.0, 15.0, 16.0, 17.0],
            "low": [9.0, 14.0, 13.0, 14.0, 15.0],
            "close": [10.0, 14.0, 14.0, 15.0, 16.0],
        }
    )

    atr = average_true_range(frame, window=3)

    assert atr.tolist() == pytest.approx([float("nan"), float("nan"), 3.0, 3.0, 2.0], nan_ok=True)


def test_add_atr_creates_one_column_per_requested_window_without_mutating_input():
    frame = pd.DataFrame(
        {
            "high": [11.0, 15.0, 15.0, 16.0, 17.0],
            "low": [9.0, 14.0, 13.0, 14.0, 15.0],
            "close": [10.0, 14.0, 14.0, 15.0, 16.0],
        }
    )
    original = frame.copy(deep=True)

    enriched = add_atr(frame, windows=(3, 4))

    assert "atr_3" in enriched.columns
    assert "atr_4" in enriched.columns
    assert enriched["atr_3"].notna().sum() > enriched["atr_4"].notna().sum()
    pd.testing.assert_frame_equal(frame, original)
