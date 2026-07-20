"""The live API cannot recreate the retired verbatim lifetime ledger."""

import asyncio
import json

from dsf_ai_service import app as appmod


def test_retired_wal_compaction_endpoint_is_gone():
    response = asyncio.run(appmod.debug_wal_compact())

    assert response.status_code == 410
    payload = json.loads(response.body)
    assert payload == {
        "error": "verbatim lifetime-window storage is retired",
        "memory_authority": "atlas_chi_krimelack_sections_organism",
    }
