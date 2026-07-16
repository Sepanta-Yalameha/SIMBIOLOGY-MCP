"""CSV-based analysis tools for exported simulation results."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .registry import register


def _read_series_csv(path: str, delimiter: str = ",") -> tuple[str, list[str], list[dict[str, float]]]:
    """Load a CSV with a time column followed by numeric series columns."""

    if len(delimiter) != 1:
        raise ValueError("delimiter must be a single character.")

    rows: list[dict[str, float]] = []
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None or len(reader.fieldnames) < 2:
            raise ValueError("CSV must contain a time column and at least one series column.")
        columns = [name.strip() for name in reader.fieldnames]
        time_column = columns[0]
        series = columns[1:]
        for row in reader:
            if not any(value not in (None, "") for value in row.values()):
                continue
            parsed = {
                time_column: float(row[time_column]),
                **{name: float(row[name]) for name in series},
            }
            rows.append(parsed)

    if not rows:
        raise ValueError("CSV must contain at least one data row.")
    return time_column, series, rows


def _require_series(requested: str | None, series: list[str]) -> list[str]:
    """Return the requested series list or raise when a name is missing."""

    if requested is None:
        return series
    if requested not in series:
        raise ValueError(f"Series {requested!r} was not found in the CSV.")
    return [requested]


@register("list_series")
def list_series(path: str, delimiter: str = ",") -> dict[str, Any]:
    """List the time column and available series names in an exported CSV."""

    time_column, series, _ = _read_series_csv(path, delimiter=delimiter)
    return {"path": path, "time_column": time_column, "series": series}


@register("steady_state")
def steady_state(path: str, series: str | None = None, delimiter: str = ",") -> dict[str, Any]:
    """Return the last-row value for one series or all series in an exported CSV."""

    time_column, all_series, rows = _read_series_csv(path, delimiter=delimiter)
    target_series = _require_series(series, all_series)
    final_row = rows[-1]
    values = {
        name: {
            "time": final_row[time_column],
            "value": final_row[name],
        }
        for name in target_series
    }
    return {"path": path, "time_column": time_column, "steady_state": values}


@register("series_min")
def series_min(path: str, series: str | None = None, delimiter: str = ",") -> dict[str, Any]:
    """Return the minimum value and its time for one series or all series."""

    time_column, all_series, rows = _read_series_csv(path, delimiter=delimiter)
    target_series = _require_series(series, all_series)
    values = {}
    for name in target_series:
        best = min(rows, key=lambda row: row[name])
        values[name] = {"time": best[time_column], "value": best[name]}
    return {"path": path, "time_column": time_column, "minimum": values}


@register("series_max")
def series_max(path: str, series: str | None = None, delimiter: str = ",") -> dict[str, Any]:
    """Return the maximum value and its time for one series or all series."""

    time_column, all_series, rows = _read_series_csv(path, delimiter=delimiter)
    target_series = _require_series(series, all_series)
    values = {}
    for name in target_series:
        best = max(rows, key=lambda row: row[name])
        values[name] = {"time": best[time_column], "value": best[name]}
    return {"path": path, "time_column": time_column, "maximum": values}
