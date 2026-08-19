import pandas as pd
import pytest

from smartanalyticsinvest.indicators import (
    add_daily_returns,
    add_ema,
    add_rsi,
    add_sma,
    daily_returns,
    exponential_moving_average,
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
