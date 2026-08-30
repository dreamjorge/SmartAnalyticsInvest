import pandas as pd

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
    expected_columns = [*REQUIRED_OHLCV_COLUMNS, "sma_3", "sma_5", "rsi_14", "ema_7", "daily_return"]
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
