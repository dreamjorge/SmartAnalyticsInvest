"""Command-line interface for local OHLCV CSV enrichment."""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from smartanalyticsinvest.errors import SmartAnalyticsInvestError
from smartanalyticsinvest.pipeline import run_csv_pipeline

_OUTPUT_FORMATS = ("csv", "json", "parquet")
_PARQUET_INSTALL_GUIDANCE = "Install Parquet support with: pip install -e '.[file-formats]'"


def _infer_output_format(output_path: Path) -> str:
    suffix = output_path.suffix.lstrip(".").lower()
    return suffix if suffix in _OUTPUT_FORMATS else "csv"


def _write_output(result: pd.DataFrame, output_path: Path, output_format: str) -> None:
    if output_format == "json":
        result.to_json(output_path, orient="records", date_format="iso")
    elif output_format == "parquet":
        result.to_parquet(output_path, index=False)
    else:
        result.to_csv(output_path, index=False)


def _expand_input_paths(patterns: list[str]) -> list[str]:
    """Expand glob patterns (for shells that don't expand them, e.g. Windows) as-is otherwise."""

    expanded: list[str] = []
    for pattern in patterns:
        if any(char in pattern for char in "*?["):
            matches = sorted(glob.glob(pattern))
            expanded.extend(matches if matches else [pattern])
        else:
            expanded.append(pattern)
    return expanded


def _process_one(
    input_path: str, output_path: Path, output_format: str, pipeline_kwargs: dict[str, Any]
) -> int:
    try:
        result = run_csv_pipeline(input_path, **pipeline_kwargs)
    except FileNotFoundError:
        print(f"Error: could not read input file: {input_path}", file=sys.stderr)
        return 1
    except (SmartAnalyticsInvestError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        _write_output(result, output_path, output_format)
    except OSError as exc:
        print(f"Error: could not write output file: {output_path}: {exc}", file=sys.stderr)
        return 1
    except ImportError as exc:
        print(f"Error: {exc}. {_PARQUET_INSTALL_GUIDANCE}", file=sys.stderr)
        return 1

    print(f"Wrote {len(result)} rows to {output_path}")
    return 0


def _process_batch(
    input_paths: list[str], output_dir: Path, output_format: str, pipeline_kwargs: dict[str, Any]
) -> int:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Error: could not create output directory: {output_dir}: {exc}", file=sys.stderr)
        return 1

    failures = 0
    for input_path in input_paths:
        output_path = output_dir / f"{Path(input_path).stem}.{output_format}"
        if _process_one(input_path, output_path, output_format, pipeline_kwargs) != 0:
            failures += 1

    total = len(input_paths)
    print(f"Processed {total - failures}/{total} input files successfully")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    """Build the SmartAnalyticsInvest CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="smartanalyticsinvest",
        description="Enrich a local OHLCV CSV with deterministic SMA and RSI columns.",
    )
    parser.add_argument(
        "input_csv",
        nargs="+",
        help=(
            "One or more local OHLCV CSV input paths (or glob patterns). "
            "With more than one input, --output is treated as an output directory."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output path for enriched rows (a directory when multiple inputs are given)",
    )
    parser.add_argument(
        "--output-format",
        choices=_OUTPUT_FORMATS,
        default=None,
        help="Output file format (default: inferred from --output's extension, else csv)",
    )
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

    input_paths = _expand_input_paths(args.input_csv)
    sma_windows = tuple(args.sma_windows) if args.sma_windows else (20,)
    rsi_windows = tuple(args.rsi_windows) if args.rsi_windows else (14,)
    ema_windows = tuple(args.ema_windows) if args.ema_windows else ()
    bollinger_windows = tuple(args.bollinger_windows) if args.bollinger_windows else ()
    atr_windows = tuple(args.atr_windows) if args.atr_windows else ()
    pipeline_kwargs: dict[str, Any] = {
        "sma_windows": sma_windows,
        "rsi_windows": rsi_windows,
        "ema_windows": ema_windows,
        "include_daily_returns": args.include_daily_returns,
        "include_macd": args.include_macd,
        "macd_fast": args.macd_fast,
        "macd_slow": args.macd_slow,
        "macd_signal": args.macd_signal,
        "bollinger_windows": bollinger_windows,
        "bollinger_num_std": args.bollinger_num_std,
        "atr_windows": atr_windows,
    }

    if len(input_paths) == 1:
        output_path = Path(args.output)
        output_format = args.output_format or _infer_output_format(output_path)
        return _process_one(input_paths[0], output_path, output_format, pipeline_kwargs)

    output_format = args.output_format or "csv"
    return _process_batch(input_paths, Path(args.output), output_format, pipeline_kwargs)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
