from __future__ import annotations

from pathlib import Path

import pytest

from simbiology_mcp.tools import analysis_tools

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "analysis_sample.csv"


def test_list_series_reads_sample_csv() -> None:
    assert analysis_tools.list_series(str(SAMPLE)) == {
        "path": str(SAMPLE),
        "time_column": "time",
        "series": ["A", "B"],
    }


def test_steady_state_returns_last_row_values() -> None:
    assert analysis_tools.steady_state(str(SAMPLE), series="A") == {
        "path": str(SAMPLE),
        "time_column": "time",
        "steady_state": {"A": {"time": 3.0, "value": 5.0}},
    }

    assert analysis_tools.steady_state(str(SAMPLE)) == {
        "path": str(SAMPLE),
        "time_column": "time",
        "steady_state": {
            "A": {"time": 3.0, "value": 5.0},
            "B": {"time": 3.0, "value": 4.0},
        },
    }


def test_series_min_and_max_return_value_and_time() -> None:
    assert analysis_tools.series_min(str(SAMPLE), series="B") == {
        "path": str(SAMPLE),
        "time_column": "time",
        "minimum": {"B": {"time": 2.0, "value": 2.0}},
    }
    assert analysis_tools.series_max(str(SAMPLE), series="A") == {
        "path": str(SAMPLE),
        "time_column": "time",
        "maximum": {"A": {"time": 2.0, "value": 6.0}},
    }


def test_analysis_tools_support_custom_delimiter(tmp_path: Path) -> None:
    sample = tmp_path / "sample.csv"
    sample.write_text("minutes;Drug;Metabolite\n0;1;5\n1;3;4\n")

    assert analysis_tools.list_series(str(sample), delimiter=";")["series"] == ["Drug", "Metabolite"]
    assert analysis_tools.steady_state(str(sample), series="Drug", delimiter=";")["steady_state"]["Drug"] == {
        "time": 1.0,
        "value": 3.0,
    }


def test_analysis_tools_reject_missing_series() -> None:
    with pytest.raises(ValueError, match="not found"):
        analysis_tools.series_max(str(SAMPLE), series="C")

