"""Command-line interface for local OHLCV CSV enrichment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from smartanalyticsinvest.errors import SmartAnalyticsInvestError
from smartanalyticsinvest.pipeline import run_csv_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the SmartAnalyticsInvest CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="smartanalyticsinvest",
        description="Enrich a local OHLCV CSV with deterministic SMA and RSI columns.",
    )
    parser.add_argument("input_csv", help="Local OHLCV CSV input path")
    parser.add_argument("--output", "-o", required=True, help="Output CSV path for enriched rows")
    parser.add_argument(
        "--sma-window",
        type=int,
        action="append",
        dest="sma_windows",
        help="SMA window to calculate (can be repeated for multiple windows)",
    )
    parser.add_argument(
        "--rsi-window",
        type=int,
        action="append",
        dest="rsi_windows",
        help="RSI window to calculate (can be repeated for multiple windows)",
    )
    parser.add_argument(
        "--ema-window",
        type=int,
        action="append",
        dest="ema_windows",
        help="EMA window to calculate (can be repeated for multiple windows)",
    )
    parser.add_argument(
        "--include-daily-returns",
        action="store_true",
        help="Include daily percentage returns column in output",
    )
    parser.add_argument(
        "--include-macd",
        action="store_true",
        help="Include macd, macd_signal, and macd_histogram columns in output",
    )
    parser.add_argument("--macd-fast", type=int, default=12, help="MACD fast EMA window")
    parser.add_argument("--macd-slow", type=int, default=26, help="MACD slow EMA window")
    parser.add_argument("--macd-signal", type=int, default=9, help="MACD signal EMA window")
    parser.add_argument(
        "--bollinger-window",
        type=int,
        action="append",
        dest="bollinger_windows",
        help="Bollinger Bands window to calculate (can be repeated for multiple windows)",
    )
    parser.add_argument(
        "--bollinger-num-std",
        type=float,
        default=2.0,
        help="Number of standard deviations for the Bollinger Bands (default: 2.0)",
    )
    parser.add_argument(
        "--atr-window",
        type=int,
        action="append",
        dest="atr_windows",
        help="ATR (Average True Range) window to calculate (can be repeated for multiple windows)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the local CSV pipeline from command-line arguments."""

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    output_path = Path(args.output)
    sma_windows = tuple(args.sma_windows) if args.sma_windows else (20,)
    rsi_windows = tuple(args.rsi_windows) if args.rsi_windows else (14,)
    ema_windows = tuple(args.ema_windows) if args.ema_windows else ()
    bollinger_windows = tuple(args.bollinger_windows) if args.bollinger_windows else ()
    atr_windows = tuple(args.atr_windows) if args.atr_windows else ()

    try:
        result = run_csv_pipeline(
            args.input_csv,
            sma_windows=sma_windows,
            rsi_windows=rsi_windows,
            ema_windows=ema_windows,
            include_daily_returns=args.include_daily_returns,
            include_macd=args.include_macd,
            macd_fast=args.macd_fast,
            macd_slow=args.macd_slow,
            macd_signal=args.macd_signal,
            bollinger_windows=bollinger_windows,
            bollinger_num_std=args.bollinger_num_std,
            atr_windows=atr_windows,
        )
    except FileNotFoundError:
        print(f"Error: could not read input file: {args.input_csv}", file=sys.stderr)
        return 1
    except (SmartAnalyticsInvestError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        result.to_csv(output_path, index=False)
    except OSError as exc:
        print(f"Error: could not write output file: {output_path}: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(result)} rows to {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
