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
