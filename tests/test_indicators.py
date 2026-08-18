import pandas as pd
import pytest

from smartanalyticsinvest.indicators import (
    add_rsi,
    add_sma,
    relative_strength_index,
    simple_moving_average,
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


@pytest.mark.parametrize("window", [0, -1, 1.5, "2"])
def test_sma_and_rsi_reject_invalid_windows(window):
    with pytest.raises(ValueError, match="window"):
        simple_moving_average(pd.Series([10, 12, 14]), window)
    with pytest.raises(ValueError, match="window"):
        relative_strength_index(pd.Series([10, 12, 14]), window)


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

    enriched = add_rsi(frame, window=2)

    assert pd.isna(enriched.loc[0, "rsi_2"])
    assert pd.isna(enriched.loc[1, "rsi_2"])
    assert enriched.loc[2, "rsi_2"] == 50.0
    assert "rsi_2" not in frame.columns
    pd.testing.assert_frame_equal(frame, original)


def test_relative_strength_index_declining_series_reaches_zero_after_window():
    rsi = relative_strength_index(pd.Series([13, 12, 11]), 2)

    assert pd.isna(rsi.iloc[0])
    assert pd.isna(rsi.iloc[1])
    assert rsi.iloc[2] == 0.0
