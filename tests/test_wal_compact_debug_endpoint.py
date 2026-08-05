"""The live API cannot recreate the retired verbatim lifetime ledger."""

import asyncio
import json

from dsf_ai_service import app as appmod


def test_retired_wal_compaction_endpoint_is_gone():
    """The verbatim-ledger compaction surface stays absent, or refuses."""
    if not hasattr(appmod, "debug_wal_compact"):
        # Fully deleted: any route named for it must be absent or refused.
        from fastapi.testclient import TestClient

        response = TestClient(appmod.app).post(
            "/api/v1/gualaloom/debug/wal_compact"
        )
        assert response.status_code in (404, 405, 410)
        return
    response = asyncio.run(appmod.debug_wal_compact())

    assert response.status_code == 410
    payload = json.loads(response.body)
    assert payload == {
        "error": "verbatim lifetime-window storage is retired",
        "memory_authority": "atlas_chi_krimelack_sections_organism",
    }
