import sys

import pandas as pd
import pytest

from smartanalyticsinvest.cli import main
from smartanalyticsinvest.schema import REQUIRED_OHLCV_COLUMNS


def _write_valid_csv(path, rows=16):
    data = []
    for day in range(1, rows + 1):
        close = 100 + day
        data.append([f"2024-01-{day:02d}", close - 1, close + 1, close - 2, close, 1000 + day])
    pd.DataFrame(data, columns=REQUIRED_OHLCV_COLUMNS).to_csv(path, index=False)


def test_cli_main_writes_enriched_csv_with_success_summary(tmp_path, capsys):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv)

    exit_code = main([str(input_csv), "--output", str(output_csv), "--sma-window", "3"])

    captured = capsys.readouterr()
    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert "Wrote 16 rows" in captured.out
    assert str(output_csv) in captured.out
    assert captured.err == ""
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_3", "rsi_14"] == list(written.columns)
    assert written.loc[2, "sma_3"] == 102.0
    assert written.loc[14, "rsi_14"] == 100.0


def test_cli_main_writes_ticker_aware_csv_without_new_option(tmp_path, capsys):
    input_csv = tmp_path / "multi.csv"
    output_csv = tmp_path / "out.csv"
    pd.DataFrame(
        [
            ["2024-01-02", 12, 13, 11, 12, 200, " MSFT"],
            ["2024-01-01", 10, 11, 9, 10, 100, "AAPL "],
            ["2024-01-02", 14, 15, 13, 14, 300, "AAPL"],
        ],
        columns=[*REQUIRED_OHLCV_COLUMNS, "ticker"],
    ).to_csv(input_csv, index=False)

    exit_code = main([str(input_csv), "--output", str(output_csv), "--sma-window", "2"])

    captured = capsys.readouterr()
    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert "Wrote 3 rows" in captured.out
    assert [*REQUIRED_OHLCV_COLUMNS, "ticker", "sma_2", "rsi_14"] == list(written.columns)
    assert written["ticker"].tolist() == ["AAPL", "AAPL", "MSFT"]
    assert written.loc[1, "sma_2"] == 12.0
    assert pd.isna(written.loc[2, "sma_2"])


def test_cli_main_reports_missing_input_without_traceback(tmp_path, capsys):
    missing_csv = tmp_path / "missing.csv"
    output_csv = tmp_path / "out.csv"

    exit_code = main([str(missing_csv), "--output", str(output_csv)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert not output_csv.exists()
    assert "error:" in captured.err.lower()
    assert "could not read input file" in captured.err.lower()
    assert str(missing_csv) in captured.err
    assert "traceback" not in captured.err.lower()
    assert captured.out == ""


def test_cli_main_reports_missing_required_columns_without_traceback(tmp_path, capsys):
    input_csv = tmp_path / "bad-columns.csv"
    output_csv = tmp_path / "out.csv"
    pd.DataFrame([{"date": "2024-01-01", "close": 10}]).to_csv(input_csv, index=False)

    exit_code = main([str(input_csv), "--output", str(output_csv)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert not output_csv.exists()
    assert "error:" in captured.err.lower()
    assert "missing required ohlcv columns" in captured.err.lower()
    assert "open" in captured.err
    assert "traceback" not in captured.err.lower()
    assert captured.out == ""


def test_cli_main_reports_invalid_indicator_window_without_traceback(tmp_path, capsys):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "out.csv"
    _write_valid_csv(input_csv)

    exit_code = main([str(input_csv), "--output", str(output_csv), "--sma-window", "0"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert not output_csv.exists()
    assert "error:" in captured.err.lower()
    assert "window" in captured.err.lower()
    assert "traceback" not in captured.err.lower()
    assert captured.out == ""


def test_cli_main_reports_omitted_output_option_without_traceback(tmp_path, capsys):
    input_csv = tmp_path / "input.csv"
    _write_valid_csv(input_csv)

    exit_code = main([str(input_csv)])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "usage:" in captured.err.lower()
    assert "--output" in captured.err
    assert "traceback" not in captured.err.lower()
    assert captured.out == ""


def test_cli_main_reports_output_write_failure_without_traceback(tmp_path, capsys):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "missing-parent" / "out.csv"
    _write_valid_csv(input_csv)

    exit_code = main([str(input_csv), "--output", str(output_csv)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "error:" in captured.err.lower()
    assert "could not write output file" in captured.err.lower()
    assert str(output_csv) in captured.err
    assert "traceback" not in captured.err.lower()
    assert captured.out == ""


def test_cli_main_accepts_multiple_sma_windows(tmp_path, capsys):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv)

    exit_code = main(
        [str(input_csv), "--output", str(output_csv), "--sma-window", "3", "--sma-window", "5"]
    )

    captured = capsys.readouterr()
    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert "Wrote 16 rows" in captured.out
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_3", "sma_5", "rsi_14"] == list(written.columns)
    assert written.loc[2, "sma_3"] == 102.0
    assert written.loc[4, "sma_5"] == 103.0


def test_cli_main_accepts_ema_windows(tmp_path, capsys):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv)

    exit_code = main(
        [str(input_csv), "--output", str(output_csv), "--sma-window", "3", "--ema-window", "5"]
    )

    captured = capsys.readouterr()
    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert "Wrote 16 rows" in captured.out
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_3", "rsi_14", "ema_5"] == list(written.columns)
    assert not written["ema_5"].isna().all()


def test_cli_main_accepts_daily_returns(tmp_path, capsys):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv)

    exit_code = main(
        [
            str(input_csv),
            "--output",
            str(output_csv),
            "--sma-window",
            "3",
            "--include-daily-returns",
        ]
    )

    captured = capsys.readouterr()
    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert "Wrote 16 rows" in captured.out
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_3", "rsi_14", "daily_return"] == list(written.columns)
    assert pd.isna(written.loc[0, "daily_return"])
    assert not pd.isna(written.loc[1, "daily_return"])


def test_cli_main_accepts_combined_flags(tmp_path):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv)

    exit_code = main(
        [
            str(input_csv),
            "--output",
            str(output_csv),
            "--sma-window",
            "3",
            "--sma-window",
            "5",
            "--ema-window",
            "7",
            "--rsi-window",
            "14",
            "--include-daily-returns",
        ]
    )

    written = pd.read_csv(output_csv)
    assert exit_code == 0
    expected_columns = [
        *REQUIRED_OHLCV_COLUMNS,
        "sma_3",
        "sma_5",
        "rsi_14",
        "ema_7",
        "daily_return",
    ]
    assert expected_columns == list(written.columns)


def test_cli_main_accepts_multiple_rsi_windows(tmp_path):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv)

    exit_code = main(
        [str(input_csv), "--output", str(output_csv), "--rsi-window", "7", "--rsi-window", "21"]
    )

    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_20", "rsi_7", "rsi_21"] == list(written.columns)


def test_cli_main_default_sma_window_when_not_specified(tmp_path):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv, rows=25)

    exit_code = main([str(input_csv), "--output", str(output_csv), "--rsi-window", "14"])

    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_20", "rsi_14"] == list(written.columns)


def test_cli_main_accepts_macd_flags(tmp_path):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv)

    exit_code = main(
        [
            str(input_csv),
            "--output",
            str(output_csv),
            "--include-macd",
            "--macd-fast",
            "3",
            "--macd-slow",
            "5",
            "--macd-signal",
            "2",
        ]
    )

    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert [
        *REQUIRED_OHLCV_COLUMNS,
        "sma_20",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
    ] == list(written.columns)
    assert not written["macd"].isna().all()


def test_cli_main_accepts_bollinger_flags(tmp_path):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv)

    exit_code = main(
        [
            str(input_csv),
            "--output",
            str(output_csv),
            "--bollinger-window",
            "5",
            "--bollinger-num-std",
            "1.5",
        ]
    )

    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert [
        *REQUIRED_OHLCV_COLUMNS,
        "sma_20",
        "rsi_14",
        "bb_middle_5",
        "bb_upper_5",
        "bb_lower_5",
    ] == list(written.columns)
    assert not written["bb_middle_5"].isna().all()


def test_cli_main_accepts_multiple_atr_windows(tmp_path):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "enriched.csv"
    _write_valid_csv(input_csv)

    exit_code = main(
        [str(input_csv), "--output", str(output_csv), "--atr-window", "5", "--atr-window", "10"]
    )

    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_20", "rsi_14", "atr_5", "atr_10"] == list(written.columns)
    assert not written["atr_5"].isna().all()


def test_cli_main_infers_json_output_format_from_extension(tmp_path):
    input_csv = tmp_path / "input.csv"
    output_json = tmp_path / "enriched.json"
    _write_valid_csv(input_csv)

    exit_code = main([str(input_csv), "--output", str(output_json)])

    assert exit_code == 0
    written = pd.read_json(output_json)
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_20", "rsi_14"] == list(written.columns)


def test_cli_main_infers_parquet_output_format_from_extension(tmp_path):
    pytest.importorskip("pyarrow")
    input_csv = tmp_path / "input.csv"
    output_parquet = tmp_path / "enriched.parquet"
    _write_valid_csv(input_csv)

    exit_code = main([str(input_csv), "--output", str(output_parquet)])

    assert exit_code == 0
    written = pd.read_parquet(output_parquet)
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_20", "rsi_14"] == list(written.columns)


def test_cli_main_output_format_flag_overrides_extension(tmp_path):
    input_csv = tmp_path / "input.csv"
    output_path = tmp_path / "enriched.out"
    _write_valid_csv(input_csv)

    exit_code = main([str(input_csv), "--output", str(output_path), "--output-format", "json"])

    assert exit_code == 0
    written = pd.read_json(output_path)
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_20", "rsi_14"] == list(written.columns)


def test_cli_main_reports_missing_parquet_dependency_without_traceback(
    tmp_path, monkeypatch, capsys
):
    input_csv = tmp_path / "input.csv"
    output_parquet = tmp_path / "enriched.parquet"
    _write_valid_csv(input_csv)
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    monkeypatch.setitem(sys.modules, "fastparquet", None)

    exit_code = main([str(input_csv), "--output", str(output_parquet)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert not output_parquet.exists()
    assert "error:" in captured.err.lower()
    assert "pip install -e '.[file-formats]'" in captured.err
    assert "traceback" not in captured.err.lower()


def test_cli_main_processes_multiple_input_files_into_output_directory(tmp_path):
    input_a = tmp_path / "a.csv"
    input_b = tmp_path / "b.csv"
    output_dir = tmp_path / "enriched"
    _write_valid_csv(input_a)
    _write_valid_csv(input_b)

    exit_code = main([str(input_a), str(input_b), "--output", str(output_dir), "--sma-window", "3"])

    assert exit_code == 0
    written_a = pd.read_csv(output_dir / "a.csv")
    written_b = pd.read_csv(output_dir / "b.csv")
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_3", "rsi_14"] == list(written_a.columns)
    assert [*REQUIRED_OHLCV_COLUMNS, "sma_3", "rsi_14"] == list(written_b.columns)


def test_cli_main_batch_mode_creates_output_directory_and_reports_summary(tmp_path, capsys):
    input_a = tmp_path / "a.csv"
    input_b = tmp_path / "b.csv"
    output_dir = tmp_path / "does-not-exist-yet"
    _write_valid_csv(input_a)
    _write_valid_csv(input_b)

    exit_code = main([str(input_a), str(input_b), "--output", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output_dir.is_dir()
    assert "Processed 2/2 input files successfully" in captured.out


def test_cli_main_batch_mode_continues_past_one_bad_file(tmp_path, capsys):
    input_good = tmp_path / "good.csv"
    input_missing = tmp_path / "missing.csv"
    output_dir = tmp_path / "enriched"
    _write_valid_csv(input_good)

    exit_code = main([str(input_good), str(input_missing), "--output", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert (output_dir / "good.csv").exists()
    assert not (output_dir / "missing.csv").exists()
    assert "could not read input file" in captured.err.lower()
    assert "Processed 1/2 input files successfully" in captured.out


def test_cli_main_batch_mode_rejects_colliding_output_names(tmp_path, capsys):
    region_a = tmp_path / "region-a"
    region_b = tmp_path / "region-b"
    region_a.mkdir()
    region_b.mkdir()
    input_a = region_a / "prices.csv"
    input_b = region_b / "prices.csv"
    output_dir = tmp_path / "enriched"
    _write_valid_csv(input_a)
    _write_valid_csv(input_b)

    exit_code = main([str(input_a), str(input_b), "--output", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "multiple inputs would overwrite the same output file" in captured.err.lower()
    assert str(input_a) in captured.err
    assert str(input_b) in captured.err
    # Detected before processing starts: neither file is written.
    assert not (output_dir / "prices.csv").exists()


def test_cli_main_batch_mode_rejects_case_insensitive_colliding_output_names(tmp_path, capsys):
    region_a = tmp_path / "region-a"
    region_b = tmp_path / "region-b"
    region_a.mkdir()
    region_b.mkdir()
    input_a = region_a / "prices.csv"
    input_b = region_b / "Prices.csv"
    output_dir = tmp_path / "enriched"
    _write_valid_csv(input_a)
    _write_valid_csv(input_b)

    exit_code = main([str(input_a), str(input_b), "--output", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "multiple inputs would overwrite the same output file" in captured.err.lower()
    assert not (output_dir / "prices.csv").exists()
    assert not (output_dir / "Prices.csv").exists()


def test_cli_main_batch_mode_continues_past_unreadable_input(tmp_path, capsys):
    input_good = tmp_path / "good.csv"
    input_dir_as_file = tmp_path / "not_a_file.csv"
    input_dir_as_file.mkdir()
    output_dir = tmp_path / "enriched"
    _write_valid_csv(input_good)

    exit_code = main([str(input_good), str(input_dir_as_file), "--output", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert (output_dir / "good.csv").exists()
    assert "could not read input file" in captured.err.lower()
    assert "Processed 1/2 input files successfully" in captured.out


def test_cli_main_batch_mode_output_format_flag_applies_to_all_files(tmp_path):
    input_a = tmp_path / "a.csv"
    input_b = tmp_path / "b.csv"
    output_dir = tmp_path / "enriched"
    _write_valid_csv(input_a)
    _write_valid_csv(input_b)

    exit_code = main(
        [str(input_a), str(input_b), "--output", str(output_dir), "--output-format", "json"]
    )

    assert exit_code == 0
    assert pd.read_json(output_dir / "a.json").shape[0] == 16
    assert pd.read_json(output_dir / "b.json").shape[0] == 16


def test_cli_main_expands_glob_pattern_for_multiple_inputs(tmp_path):
    _write_valid_csv(tmp_path / "aapl.csv")
    _write_valid_csv(tmp_path / "msft.csv")
    output_dir = tmp_path / "enriched"

    exit_code = main([str(tmp_path / "*.csv"), "--output", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "aapl.csv").exists()
    assert (output_dir / "msft.csv").exists()
