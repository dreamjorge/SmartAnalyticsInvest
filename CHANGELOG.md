# Changelog

All notable changes to SmartAnalyticsInvest will be documented in this file.

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
