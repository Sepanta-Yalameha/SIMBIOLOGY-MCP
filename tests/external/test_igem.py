import pytest

from external.igem import part as igem_part

pytestmark = pytest.mark.live


def test_igem_part_live():
    result = igem_part("BBa_J23100")
    assert result["part"] == "BBa_J23100"
    assert result["url"].endswith("/parts/bba-j23100")
    assert result["title"]
    assert result["status"]
    assert isinstance(result["sequence_length"], int)
    assert result["sequence_length"] == len(result["sequence"])
    assert "gc_fraction" in result["sequence_stats"]
    assert "created" in result
    assert "updated" in result
    assert result["content"]
