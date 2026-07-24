"""Hot persistence must preserve cold binary identity authority."""

import json

from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def test_hot_core_retains_binary_binding_contract(tmp_path):
    guala = Guala()
    try:
        guala.save_hot_state(str(tmp_path))
        with (tmp_path / "guala_core.json").open(
                encoding="utf-8") as stream:
            core = json.load(stream)

        assert (
            core["data"]["binary_binding_contract"]
            == guala.BINARY_BINDING_CONTRACT
        )
    finally:
        guala.shutdown()
