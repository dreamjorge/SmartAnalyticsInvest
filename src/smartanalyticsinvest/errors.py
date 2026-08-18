"""Domain exceptions for SmartAnalyticsInvest."""


class SmartAnalyticsInvestError(Exception):
    """Base class for predictable SmartAnalyticsInvest errors."""


class MissingColumnsError(SmartAnalyticsInvestError):
    """Raised when a DataFrame lacks required OHLCV columns."""

    def __init__(self, missing_columns: list[str] | tuple[str, ...]):
        self.missing_columns = tuple(missing_columns)
        columns = ", ".join(self.missing_columns)
        super().__init__(f"Missing required OHLCV columns: {columns}")


class DuplicateColumnsError(SmartAnalyticsInvestError):
    """Raised when source columns collapse to duplicate canonical names."""

    def __init__(self, duplicate_columns: list[str] | tuple[str, ...]):
        self.duplicate_columns = tuple(duplicate_columns)
        columns = ", ".join(self.duplicate_columns)
        super().__init__(f"Duplicate canonical OHLCV columns: {columns}")
