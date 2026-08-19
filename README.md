# SmartAnalyticsInvest

SmartAnalyticsInvest MVP is a deterministic, local CSV analytics package for OHLCV market data. It loads a local CSV file, validates and cleans the required columns, calculates SMA and RSI indicators, and writes an enriched CSV from a minimal CLI.

This MVP does not implement machine-learning predictions, trading recommendations, dashboards, web UI, live network data fetching, or portfolio/risk engines.

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

## Input CSV schema

Your input CSV must include these exact OHLCV columns:

```text
date, open, high, low, close, volume
```

Extra columns may be present, but the MVP requires the six columns above for processing.

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
