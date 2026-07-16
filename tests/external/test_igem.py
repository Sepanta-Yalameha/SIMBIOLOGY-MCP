import pytest

from simbiology_mcp.external.igem import IgemUnavailableError, part as igem_part

pytestmark = pytest.mark.live


def test_igem_part_live():
    try:
        result = igem_part("BBa_J23100")
    except IgemUnavailableError as exc:
        pytest.skip(str(exc))
    assert result["part"] == "BBa_J23100"
    assert result["slug"]
    assert result["title"]
    assert result["status"]
    assert isinstance(result["sequence"], str)
    assert "created" in result
    assert "updated" in result
    assert "license_uuid" in result

