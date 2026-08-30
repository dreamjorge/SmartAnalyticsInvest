"""Deterministic pandas indicators for OHLCV data."""

from __future__ import annotations

import pandas as pd


def _validate_window(window: int) -> int:
    if not isinstance(window, int) or isinstance(window, bool) or window <= 0:
        raise ValueError("indicator window must be a positive integer")
    return window


def simple_moving_average(series: pd.Series, window: int) -> pd.Series:
    """Return the arithmetic rolling mean for the requested window."""

    valid_window = _validate_window(window)
    return series.rolling(window=valid_window, min_periods=valid_window).mean()


def exponential_moving_average(series: pd.Series, window: int) -> pd.Series:
    """Return the exponential moving average for the requested window."""

    valid_window = _validate_window(window)
    return series.ewm(span=valid_window, adjust=False).mean()


def daily_returns(series: pd.Series) -> pd.Series:
    """Return daily percentage returns with the first row left missing."""

    return series.pct_change(fill_method=None)


def relative_strength_index(series: pd.Series, window: int = 14) -> pd.Series:
    """Return simple rolling RSI values with flat windows conventionally set to 50."""

    valid_window = _validate_window(window)
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    average_gain = gains.rolling(window=valid_window, min_periods=valid_window).mean()
    average_loss = losses.rolling(window=valid_window, min_periods=valid_window).mean()
    rs = average_gain / average_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100.0)
    rsi = rsi.mask((average_loss == 0) & (average_gain == 0), 50.0)
    return rsi


def add_sma(
    frame: pd.DataFrame, *, price_column: str = "close", windows: tuple[int, ...] = (20,)
) -> pd.DataFrame:
    """Return a copy enriched with one SMA column per requested window."""

    enriched = frame.copy()
    for window in windows:
        valid_window = _validate_window(window)
        enriched[f"sma_{valid_window}"] = simple_moving_average(
            enriched[price_column], valid_window
        )
    return enriched


def add_ema(
    frame: pd.DataFrame, *, price_column: str = "close", windows: tuple[int, ...] = (20,)
) -> pd.DataFrame:
    """Return a copy enriched with one EMA column per requested window."""

    enriched = frame.copy()
    for window in windows:
        valid_window = _validate_window(window)
        enriched[f"ema_{valid_window}"] = exponential_moving_average(
            enriched[price_column], valid_window
        )
    return enriched


def add_rsi(
    frame: pd.DataFrame, *, price_column: str = "close", windows: tuple[int, ...] = (14,)
) -> pd.DataFrame:
    """Return a copy enriched with one RSI column per requested window."""

    enriched = frame.copy()
    for window in windows:
        valid_window = _validate_window(window)
        enriched[f"rsi_{valid_window}"] = relative_strength_index(
            enriched[price_column], valid_window
        )
    return enriched


def add_daily_returns(frame: pd.DataFrame, *, price_column: str = "close") -> pd.DataFrame:
    """Return a copy enriched with daily percentage returns."""

    enriched = frame.copy()
    enriched["daily_return"] = daily_returns(enriched[price_column])
    return enriched


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return the MACD line, signal line, and histogram for the requested windows."""

    valid_fast = _validate_window(fast)
    valid_slow = _validate_window(slow)
    valid_signal = _validate_window(signal)
    macd_line = exponential_moving_average(series, valid_fast) - exponential_moving_average(
        series, valid_slow
    )
    signal_line = exponential_moving_average(macd_line, valid_signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def add_macd(
    frame: pd.DataFrame,
    *,
    price_column: str = "close",
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Return a copy enriched with macd, macd_signal, and macd_histogram columns."""

    enriched = frame.copy()
    macd_line, signal_line, histogram = macd(enriched[price_column], fast, slow, signal)
    enriched["macd"] = macd_line
    enriched["macd_signal"] = signal_line
    enriched["macd_histogram"] = histogram
    return enriched


def bollinger_bands(
    series: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return the middle (SMA), upper, and lower Bollinger Bands for the requested window."""

    valid_window = _validate_window(window)
    middle = simple_moving_average(series, valid_window)
    rolling_std = series.rolling(window=valid_window, min_periods=valid_window).std()
    upper = middle + num_std * rolling_std
    lower = middle - num_std * rolling_std
    return middle, upper, lower


def add_bollinger_bands(
    frame: pd.DataFrame,
    *,
    price_column: str = "close",
    windows: tuple[int, ...] = (20,),
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Return a copy enriched with bb_middle/bb_upper/bb_lower columns per window."""

    enriched = frame.copy()
    for window in windows:
        valid_window = _validate_window(window)
        middle, upper, lower = bollinger_bands(enriched[price_column], valid_window, num_std)
        enriched[f"bb_middle_{valid_window}"] = middle
        enriched[f"bb_upper_{valid_window}"] = upper
        enriched[f"bb_lower_{valid_window}"] = lower
    return enriched
