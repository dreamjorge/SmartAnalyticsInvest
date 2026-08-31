# Changelog

All notable changes to SmartAnalyticsInvest will be documented in this file.

## Unreleased

- **Breaking:** Minimum supported Python version raised from 3.12 to 3.14. 3.12 and 3.13 are no longer supported.
- **Breaking:** `enrich_ohlcv`/`run_csv_pipeline`'s `rsi_window: int` keyword argument is now `rsi_windows: tuple[int, ...]`, matching the existing `sma_windows`/`ema_windows` pattern. `indicators.add_rsi`'s `window` keyword is now `windows` for the same reason. The CLI's `--rsi-window` flag keeps its name and is now repeatable, like `--sma-window`/`--ema-window`.
- Added `data_sources.load_stockstreamdb()`, an optional loader that reads OHLCV rows (and optionally fundamentals/sentiment) from a [StockStreamDB](https://github.com/dreamjorge/StockStreamDB) SQLite database, for callers who already collect historical data with that project.
- Added a `py.typed` marker (PEP 561) so external projects that depend on `smartanalyticsinvest` get real type checking instead of `mypy` skipping it as untyped.
- `data_sources.load_stockstreamdb()` gained `include_macro`/`macro_series` to join FRED macro-economic indicators from StockStreamDB's `macro_indicators` table, forward-filled and aligned to each row's date via `merge_asof`.
- **Fixed** (found via automated code review): `load_stockstreamdb()`'s `fundamentals` join could silently duplicate OHLCV rows in a many-to-many merge if a ticker/date had more than one fundamentals snapshot; it now keeps only the most recently inserted one. `tickers` filtering is now pushed into SQL for the price/fundamentals/sentiment queries instead of loading full tables into pandas first.
- **Fixed** the CLI's batch mode (`--output` as a directory): inputs with the same filename stem in different directories (e.g. `region-a/prices.csv` and `region-b/prices.csv`) could silently overwrite each other's output; batches with colliding output names are now rejected upfront, before any file is written. Unreadable inputs (e.g. permission errors, a directory passed as input) are now handled as a per-file failure instead of aborting the whole batch with a traceback.
- **Fixed** (found via automated code review, on the downstream [SmartDirectionNet](https://github.com/dreamjorge/SmartDirectionNet) project): `load_stockstreamdb(include_macro=True)` joined FRED series on their raw observation date, which for series like CPI/GDP/unemployment is the start of the reporting period rather than the actual publication date, leaking future information into training data. Added `macro_publication_lag_days` to shift observations forward by a conservative number of days before joining; defaults to `0` for backward compatibility.
- **Fixed** (found via automated code review): `macro_publication_lag_days` accepted negative values, which shifted macro observations *earlier* and worsened the very look-ahead leakage the option exists to prevent; it now must be a non-negative integer (booleans rejected too).
- **Fixed** (found via automated code review): batch mode's output-collision detection compared paths with exact string equality, so on case-insensitive filesystems (the macOS/Windows default) two inputs like `region-a/prices.csv` and `region-b/Prices.csv` would go undetected and silently overwrite each other; the comparison is now case-insensitive.
- **Fixed** (found via automated code review): the case-insensitive collision check above still missed Unicode-normalization-equivalent filenames (e.g. a precomposed vs. decomposed accented character), which also collide on normalization-insensitive filesystems such as default macOS APFS; paths are now Unicode-normalized (NFC) before case-folding.

## 0.1.1 - 2026-08-19

Patch release for source distribution completeness.

- Added `MANIFEST.in` so source distributions include `CHANGELOG.md`, `LICENSE`, `README.md`, tests, fixtures, and examples.
- Verified packaged metadata tests from an unpacked source distribution.

## 0.1.0 - 2026-08-19

Initial release preparation for the local-first OHLCV analytics toolkit.

- Added a deterministic local CSV CLI and pipeline for validating, cleaning, enriching, and exporting OHLCV data.
- Implemented OHLCV schema and financial consistency validation with predictable project errors.
- Added SMA, RSI, optional EMA, and daily return indicator calculations.
- Supported optional `ticker` grouping so multi-instrument CSV files are sorted, deduplicated, and enriched independently per ticker.
- Added an optional Yahoo Finance adapter behind the `market-data` extra while keeping core usage offline and local-file-first.
- Added sample OHLCV data and a documented CLI smoke example.
- Added offline pytest coverage, Ruff checks, and GitHub Actions CI for the package.
