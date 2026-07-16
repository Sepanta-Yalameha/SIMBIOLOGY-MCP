from __future__ import annotations

import math

import pytest

from simbiology_mcp.core.sbio_model import (
    _finite_or_none,
    _format_simdata,
    _matlab_string_cell,
    _matlab_variant_value,
    _matrix,
    split_reaction_equation,
)


def test_split_reaction_equation_rejects_unknown_arrow() -> None:
    with pytest.raises(ValueError, match="Unsupported reaction equation"):
        split_reaction_equation("A plus B")


def test_finite_or_none_collapses_non_finite_floats() -> None:
    assert _finite_or_none(math.inf) is None
    assert _finite_or_none(math.nan) is None
    assert _finite_or_none(3.0) == 3.0
    assert _finite_or_none("x") == "x"


def test_matrix_normalizes_none_scalar_vector_and_matrix() -> None:
    assert _matrix(None) == []
    assert _matrix(5) == [[5.0]]
    assert _matrix([1, 2]) == [[1.0], [2.0]]
    assert _matrix([[1, 2], [3, 4]]) == [[1.0, 2.0], [3.0, 4.0]]


def test_format_simdata_handles_single_name_and_matrix_data() -> None:
    result = _format_simdata(time=[0, 1], data=[[10], [8]], names="A", units="hour")

    assert result == {
        "time": [0.0, 1.0],
        "time_units": "hour",
        "names": ["A"],
        "data": {"A": [10.0, 8.0]},
    }


def test_matlab_string_cell_and_variant_value_helpers() -> None:
    assert _matlab_string_cell(["A", "B"]) == "{'A','B'}"
    assert _matlab_variant_value(True) == "1.0"
    assert _matlab_variant_value("ATP") == "'ATP'"

