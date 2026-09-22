"""Exact persistence proof for one indivisible Guala organism state."""

from __future__ import annotations

import hashlib
import json


class WholeOrganismPersistenceError(RuntimeError):
    pass


WHOLE_ORGANISM_STATE_CONTRACT = "guala.native_exact_organism_state.v2"


def _canonical(value) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise WholeOrganismPersistenceError(
            "whole-organism state is not canonical JSON"
        ) from error


def whole_organism_mutation_root(encoded_core: bytes) -> str:
    """Verify and hash the exact causal state without per-mechanism owners."""
    if not isinstance(encoded_core, bytes) or not encoded_core:
        raise WholeOrganismPersistenceError(
            "whole-organism frozen body is invalid"
        )
    try:
        envelope = json.loads(encoded_core)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WholeOrganismPersistenceError(
            "whole-organism frozen body is not JSON"
        ) from error
    if not isinstance(envelope, dict):
        raise WholeOrganismPersistenceError(
            "whole-organism envelope is not an object"
        )
    identity = envelope.get("guala_identity")
    saved_tick = envelope.get("saved_at_tick")
    data = envelope.get("data")
    if (
        not isinstance(identity, str)
        or not identity
        or isinstance(saved_tick, bool)
        or not isinstance(saved_tick, int)
        or saved_tick < 0
        or not isinstance(data, dict)
        or data.get("continuity_contract")
        != WHOLE_ORGANISM_STATE_CONTRACT
        or data.get("tick") != saved_tick
        or not isinstance(data.get("organism_state"), dict)
    ):
        raise WholeOrganismPersistenceError(
            "whole-organism envelope contract changed"
        )
    organism_bytes = _canonical(data["organism_state"])
    organism_sha256 = hashlib.sha256(organism_bytes).hexdigest()
    if (
        data.get("organism_state_bytes") != len(organism_bytes)
        or data.get("organism_state_sha256") != organism_sha256
        or data.get("state_file_ticks")
        != {"guala_core.json": saved_tick}
    ):
        raise WholeOrganismPersistenceError(
            "whole-organism state integrity changed"
        )
    causal_body = {
        "guala_identity": identity,
        "organism_state": data["organism_state"],
        "tick": saved_tick,
    }
    return hashlib.sha256(
        b"guala-whole-organism-mutation-v1\0" + _canonical(causal_body)
    ).hexdigest()


__all__ = (
    "WHOLE_ORGANISM_STATE_CONTRACT",
    "WholeOrganismPersistenceError",
    "whole_organism_mutation_root",
)
