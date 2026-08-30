# SmartAnalyticsInvest

SmartAnalyticsInvest MVP is a deterministic, local CSV analytics package for OHLCV market data. It loads a local CSV file, validates and cleans the required columns, calculates SMA and RSI indicators, and writes an enriched CSV from a minimal CLI.

This MVP does not implement machine-learning predictions, trading recommendations, dashboards, web UI, required live network data fetching, or portfolio/risk engines.

See `CONTRIBUTING.md` for local setup, issue conventions, and pull request expectations.

## Release readiness

Version `0.1.0` is the initial local-first release candidate. See `CHANGELOG.md` for the release summary; core tests are offline and the Yahoo Finance adapter remains optional through the `market-data` extra.

## Setup

Use Python 3.12 or newer. From the repository root, install the package with development dependencies:

```bash
python3 -m pip install -e '.[dev]'
```

## Run tests

```bash
python3 -m pytest
```

The test suite is offline and uses local deterministic fixtures only.

## Optional experimental Yahoo Finance adapter

Core usage is local-CSV-first and does not require live market data packages. An optional experimental Yahoo Finance adapter is available for callers that choose to install `yfinance`:

```bash
python3 -m pip install -e '.[market-data]'
```

### Single symbol

```python
from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv
from smartanalyticsinvest.pipeline import clean_ohlcv

raw = fetch_yahoo_ohlcv("MSFT", period="1mo", interval="1d")
cleaned = clean_ohlcv(raw)
```

### Multiple symbols

For multi-instrument workflows, fetch and concatenate multiple symbols into a single frame:

```python
from smartanalyticsinvest.data_sources import fetch_yahoo_ohlcv_many
from smartanalyticsinvest.pipeline import clean_ohlcv, enrich_ohlcv

raw = fetch_yahoo_ohlcv_many(["AAPL", "MSFT", "GOOGL"], period="1mo", interval="1d")
cleaned = clean_ohlcv(raw)
result = enrich_ohlcv(cleaned, sma_windows=(20,), rsi_window=14)
```

The adapter returns the canonical lowercase OHLCV columns (`date`, `open`, `high`, `low`, `close`, `volume`) plus a `ticker` column. Multi-symbol fetches are automatically sorted by ticker and date for consistent processing. It imports `yfinance` lazily and raises a predictable project error with install guidance when the optional extra is not installed or Yahoo returns unusable data.

By default, `fetch_yahoo_ohlcv_many` aborts the whole batch if any symbol fails to fetch. Pass `on_error="skip"` for a best-effort mode that fetches the remaining symbols and reports failures instead of aborting:

```python
result = fetch_yahoo_ohlcv_many(["AAPL", "DELISTED", "MSFT"], on_error="skip")
result.attrs["failed_symbols"]  # {"DELISTED": "<error message>"}
```

A `DataSourceError` is still raised if every symbol in the batch fails.

## Input CSV schema

Your input CSV must include these exact OHLCV columns:

```text
date, open, high, low, close, volume
```

Extra columns may be present, but the MVP requires the six columns above for processing. Required values must parse as dates/numbers, prices must be positive, volume must be non-negative, and OHLCV prices must be financially consistent: `high >= low`, `high >= open`, `high >= close`, `low <= open`, and `low <= close`.

### Optional ticker column

CSV files may include an optional lowercase `ticker` column for multiple instruments. When present, ticker values are trimmed, must be non-empty, and rows are sorted/deduplicated by `ticker` and `date`. SMA, RSI, EMA, and daily returns are calculated independently per ticker so indicator values do not cross instrument boundaries.

## Pipeline API indicators

The pipeline defaults remain SMA and RSI only. Python callers can opt into EMA windows and daily percentage returns:

```python
from smartanalyticsinvest.pipeline import run_csv_pipeline

result = run_csv_pipeline(
    "input.csv",
    sma_windows=(20,),
    rsi_window=14,
    ema_windows=(12, 26),
    include_daily_returns=True,
)
```

This adds columns such as `ema_12`, `ema_26`, and `daily_return`; the first daily return in each series is missing.

## CLI usage

Run the local CSV pipeline and write an enriched CSV:

```bash
smartanalyticsinvest input.csv --output enriched.csv --sma-window 20 --rsi-window 14
```

You can also run the module directly:

```bash
python3 -m smartanalyticsinvest.cli input.csv --output enriched.csv
```

The output CSV contains the required OHLCV columns plus indicator columns such as `sma_20` and `rsi_14`.

## Smoke example

The repository includes a tiny deterministic sample CSV:

```bash
python3 -m smartanalyticsinvest.cli examples/sample_ohlcv.csv \
  --output /tmp/sample_enriched.csv \
  --sma-window 2 \
  --rsi-window 2
```

Expected output:

```text
Wrote 5 rows to /tmp/sample_enriched.csv
```

The generated CSV includes the original OHLCV columns plus `sma_2` and `rsi_2`.
