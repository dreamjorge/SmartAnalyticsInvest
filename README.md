# SmartAnalyticsInvest

SmartAnalyticsInvest MVP is a deterministic, local CSV analytics package for OHLCV market data. It loads a local CSV file, validates and cleans the required columns, calculates SMA and RSI indicators, and writes an enriched CSV from a minimal CLI.

This MVP does not implement machine-learning predictions, trading recommendations, dashboards, web UI, required live network data fetching, or portfolio/risk engines.

See `CONTRIBUTING.md` for local setup, issue conventions, and pull request expectations.

## Release readiness

Version `0.1.0` is the initial local-first release candidate. See `CHANGELOG.md` for the release summary; core tests are offline and the Yahoo Finance adapter remains optional through the `market-data` extra.

## Setup

Use Python 3.14 or newer. From the repository root, install the package with development dependencies:

```bash
python3 -m pip install -e '.[dev]'
```

## Run tests

```bash
python3 -m pytest
```

The test suite is offline and uses local deterministic fixtures only.

## Linting and formatting

```bash
python3 -m ruff check .
python3 -m ruff format --check .
```

Both run in CI. Optionally install the local pre-commit hook (`.pre-commit-config.yaml`) to run them automatically before each commit:

```bash
pip install pre-commit
pre-commit install
```

## Static type checking

```bash
python3 -m mypy src/smartanalyticsinvest
```

Runs in strict mode (see `[tool.mypy]` in `pyproject.toml`) and in CI alongside Ruff and pytest.

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
result = enrich_ohlcv(cleaned, sma_windows=(20,), rsi_windows=(14,))
```

The adapter returns the canonical lowercase OHLCV columns (`date`, `open`, `high`, `low`, `close`, `volume`) plus a `ticker` column. Multi-symbol fetches are automatically sorted by ticker and date for consistent processing. It imports `yfinance` lazily and raises a predictable project error with install guidance when the optional extra is not installed or Yahoo returns unusable data.

By default, `fetch_yahoo_ohlcv_many` aborts the whole batch if any symbol fails to fetch. Pass `on_error="skip"` for a best-effort mode that fetches the remaining symbols and reports failures instead of aborting:

```python
result = fetch_yahoo_ohlcv_many(["AAPL", "DELISTED", "MSFT"], on_error="skip")
result.attrs["failed_symbols"]  # {"DELISTED": "<error message>"}
```

A `DataSourceError` is still raised if every symbol in the batch fails.

## Optional StockStreamDB historical data loader

If you already collect historical OHLCV data with [StockStreamDB](https://github.com/dreamjorge/StockStreamDB) (a separate project that fetches Yahoo Finance data, fundamentals, and news sentiment into a local SQLite database), load it directly instead of re-fetching:

```python
from smartanalyticsinvest.data_sources import load_stockstreamdb
from smartanalyticsinvest.pipeline import clean_ohlcv

raw = load_stockstreamdb("stockstreamdb.db", tickers=["AAPL", "MSFT"])
cleaned = clean_ohlcv(raw)
```

This reads StockStreamDB's `stock_prices` table directly via the standard-library `sqlite3` module — no extra dependency, and StockStreamDB itself doesn't need to be installed, only its database file. `tickers` filters at the SQL level (including for `fundamentals`/`sentiment_analysis` below), so a single-ticker request doesn't load the whole database into memory. Pass `include_fundamentals=True`/`include_sentiment=True` to left-join StockStreamDB's `fundamentals` (P/E ratio, EPS, market cap, revenue, net income, total assets) and `sentiment_analysis` (average sentiment score per ticker/date) tables onto the result as extra feature columns, useful for downstream model training. If a ticker/date has more than one fundamentals snapshot (StockStreamDB's schema allows this), only the most recently inserted one is used, so the join never duplicates OHLCV rows.

Pass `include_macro=True` to also join FRED macro-economic series (interest rates, inflation, unemployment, etc.) from StockStreamDB's `macro_indicators` table — one `macro_<series_id>` column per series, broadcast to every ticker since macro data isn't ticker-specific:

```python
raw = load_stockstreamdb(
    "stockstreamdb.db", include_macro=True, macro_series=["FEDFUNDS", "UNRATE"]
)
```

Macro series are usually lower-frequency than daily prices (e.g. monthly), so each row gets the most recent observation as of its date (forward-filled, via `pandas.merge_asof`) rather than requiring an exact date match. Omit `macro_series` to include every series present in the database.

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
    rsi_windows=(14,),
    ema_windows=(12, 26),
    include_daily_returns=True,
    include_macd=True,
)
```

This adds columns such as `ema_12`, `ema_26`, and `daily_return`; the first daily return in each series is missing. Like `sma_windows` and `ema_windows`, `rsi_windows` accepts multiple windows (e.g. `rsi_windows=(7, 14)`) to produce one `rsi_<window>` column per window.

`include_macd=True` adds `macd`, `macd_signal`, and `macd_histogram` columns using the standard 12/26/9 EMA windows; override them with `macd_fast`, `macd_slow`, and `macd_signal`.

`bollinger_windows` accepts one or more SMA windows to produce `bb_middle_<window>`, `bb_upper_<window>`, and `bb_lower_<window>` columns (upper/lower are the middle band plus/minus `bollinger_num_std` standard deviations, default `2.0`):

```python
result = run_csv_pipeline("input.csv", bollinger_windows=(20,))
```

`atr_windows` accepts one or more windows to produce `atr_<window>` columns (Average True Range, using `high`/`low`/`close` together rather than a single price column):

```python
result = run_csv_pipeline("input.csv", atr_windows=(14,))
```

## CLI usage

Run the local CSV pipeline and write an enriched CSV:

```bash
smartanalyticsinvest input.csv --output enriched.csv --sma-window 20 --rsi-window 14
```

`--rsi-window` is repeatable, like `--sma-window` and `--ema-window`:

```bash
smartanalyticsinvest input.csv --output enriched.csv --rsi-window 7 --rsi-window 14
```

Add `--include-macd` for `macd`, `macd_signal`, and `macd_histogram` columns (defaults to the standard 12/26/9 EMA windows, overridable with `--macd-fast`/`--macd-slow`/`--macd-signal`):

```bash
smartanalyticsinvest input.csv --output enriched.csv --include-macd
```

Add `--bollinger-window` (repeatable, like `--sma-window`) for `bb_middle_<window>`/`bb_upper_<window>`/`bb_lower_<window>` columns, optionally overriding the band width with `--bollinger-num-std`:

```bash
smartanalyticsinvest input.csv --output enriched.csv --bollinger-window 20 --bollinger-num-std 2.5
```

Add `--atr-window` (repeatable, like `--sma-window`) for `atr_<window>` (Average True Range) columns:

```bash
smartanalyticsinvest input.csv --output enriched.csv --atr-window 14
```

You can also run the module directly:

```bash
python3 -m smartanalyticsinvest.cli input.csv --output enriched.csv
```

The output CSV contains the required OHLCV columns plus indicator columns such as `sma_20` and `rsi_14`.

### Output formats

By default the output format is inferred from `--output`'s file extension (`.csv`, `.json`, or `.parquet`); anything else defaults to CSV. Override it explicitly with `--output-format`:

```bash
smartanalyticsinvest input.csv --output enriched.parquet
smartanalyticsinvest input.csv --output enriched.out --output-format json
```

Parquet output requires the optional `file-formats` extra:

```bash
python3 -m pip install -e '.[file-formats]'
```

### Batch processing multiple files

Pass more than one input path (or a glob pattern) to process a whole directory of per-symbol CSVs in one run. `--output` is then treated as an output directory, and each input's enriched result is written there as `<input-stem>.<format>`:

```bash
smartanalyticsinvest data/aapl.csv data/msft.csv --output enriched/ --sma-window 20
smartanalyticsinvest "data/*.csv" --output enriched/
```

The output directory is created if it doesn't exist. Each file is processed independently and a bad file doesn't abort the batch: failures (including unreadable inputs, e.g. permission errors) are reported per file, a `Processed N/M input files successfully` summary is printed, and the exit code is non-zero if any file failed. Single-input invocations are unaffected and keep writing directly to `--output` as a file.

If two inputs would map to the same output filename (e.g. `region-a/prices.csv` and `region-b/prices.csv` both stem to `prices.csv`), the batch is rejected upfront with an error naming the colliding inputs, before any file is written — nothing is silently overwritten.

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
