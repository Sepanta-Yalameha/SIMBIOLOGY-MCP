import pytest

from simbiology_mcp.external import sabio

pytestmark = pytest.mark.live


def test_sabio_search_live():
    try:
        result = sabio.search(substrate="ATP", organism="Escherichia coli", limit=1)
    except (RuntimeError, OSError) as exc:
        pytest.skip(f"SABIO-RK unavailable: {exc}")

    assert result["total_count"] > 0
    assert result["results"]
    assert result["results"][0]["parameters"]
