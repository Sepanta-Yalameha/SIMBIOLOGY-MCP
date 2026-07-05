import pytest

from external.igem import part as igem_part

pytestmark = pytest.mark.live


def test_igem_part_live():
    result = igem_part("BBa_J23100")
    assert result["part"] == "BBa_J23100"
    assert result["slug"]
    assert result["title"]
    assert result["status"]
    assert isinstance(result["sequence"], str)
    assert "created" in result
    assert "updated" in result
    assert "license_uuid" in result
