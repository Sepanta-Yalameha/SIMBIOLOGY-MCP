from external.igem import part as igem_part


def test_igem_part_live():
    result = igem_part("BBa_J23100")
    assert result["part"] == "BBa_J23100"
    assert result["url"].endswith("/parts/bba-j23100")
    assert result["title"]
    assert result["content"]
