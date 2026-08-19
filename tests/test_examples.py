from pathlib import Path

import pandas as pd

from smartanalyticsinvest.cli import main

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_documented_sample_cli_smoke(tmp_path, capsys):
    sample_csv = REPOSITORY_ROOT / "examples" / "sample_ohlcv.csv"
    output_csv = tmp_path / "sample_enriched.csv"

    exit_code = main(
        [
            str(sample_csv),
            "--output",
            str(output_csv),
            "--sma-window",
            "2",
            "--rsi-window",
            "2",
        ]
    )

    captured = capsys.readouterr()
    written = pd.read_csv(output_csv)
    assert exit_code == 0
    assert "Wrote 5 rows" in captured.out
    assert captured.err == ""
    assert list(written.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "sma_2",
        "rsi_2",
    ]
    assert written.loc[1, "sma_2"] == 105.5
