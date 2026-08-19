"""Command-line interface for local OHLCV CSV enrichment."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

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
    parser.add_argument("--sma-window", type=int, default=20, help="SMA window to calculate")
    parser.add_argument("--rsi-window", type=int, default=14, help="RSI window to calculate")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the local CSV pipeline from command-line arguments."""

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    output_path = Path(args.output)
    try:
        result = run_csv_pipeline(
            args.input_csv,
            sma_windows=(args.sma_window,),
            rsi_window=args.rsi_window,
        )
    except FileNotFoundError:
        print(f"Error: could not read input file: {args.input_csv}", file=sys.stderr)
        return 1
    except (SmartAnalyticsInvestError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    result.to_csv(output_path, index=False)
    print(f"Wrote {len(result)} rows to {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
