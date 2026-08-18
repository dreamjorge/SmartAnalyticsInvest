import pandas as pd
import pytest

from smartanalyticsinvest.errors import MissingColumnsError
from smartanalyticsinvest.schema import (
    NUMERIC_OHLCV_COLUMNS,
    REQUIRED_OHLCV_COLUMNS,
    normalize_ohlcv_columns,
    require_ohlcv_columns,
)


def test_required_ohlcv_columns_are_the_mvp_contract():
    assert REQUIRED_OHLCV_COLUMNS == ("date", "open", "high", "low", "close", "volume")
    assert NUMERIC_OHLCV_COLUMNS == ("open", "high", "low", "close", "volume")


def test_missing_required_columns_raise_canonical_names():
    frame = pd.DataFrame({"date": ["2024-01-01"], "open": [10], "close": [11]})

    with pytest.raises(MissingColumnsError) as excinfo:
        require_ohlcv_columns(frame)

    message = str(excinfo.value)
    assert "high" in message
    assert "low" in message
    assert "volume" in message


def test_extra_columns_do_not_block_validation():
    frame = pd.DataFrame(columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"])

    require_ohlcv_columns(frame)


def test_standard_columns_are_normalized_for_case_and_whitespace_only():
    frame = pd.DataFrame(
        columns=[" Date ", "OPEN", "High", " low", "Close ", "VOLUME", "Adj Close"]
    )

    normalized = normalize_ohlcv_columns(frame)

    assert list(normalized.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "Adj Close",
    ]
