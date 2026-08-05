from __future__ import annotations

import hashlib
import json

import pytest

from dsf_ai_service.substrate.authenticated_owner_state_unwrap import (
    AuthenticatedOwnerStateUnwrapError,
    unwrap_authenticated_owner_state,
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _outer(owner: str, state_key: str, inner: object) -> bytes:
    return _canonical({
        "owner_id": owner,
        "schema": "guala.owner_state_body.v1",
        "state": {state_key: inner},
    })


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_strictly_derives_the_inner_authenticated_mosaic_envelope() -> None:
    inner = {
        "body": {
            "mosaics": [],
            "schema": "guala.causal_thing_mosaic.state.v1",
        },
        "schema": "guala.causal_thing_mosaic.state_hmac.v1",
        "state_hmac_sha256": "1" * 64,
    }
    outer = _outer("causal_thing_mosaic", "causal_thing_mosaic", inner)

    result = unwrap_authenticated_owner_state(
        relative_path="owner_state/causal_thing_mosaic.json",
        outer_bytes=outer,
        expected_outer_sha256=_sha(outer),
        expected_owner_id="causal_thing_mosaic",
        expected_state_key="causal_thing_mosaic",
    )

    assert result.outer_file_sha256 == _sha(outer)
    assert json.loads(result.inner_bytes) == inner
    assert result.derived_inner_sha256 == _sha(result.inner_bytes)


def test_changed_manifest_member_fails_before_unwrapping() -> None:
    outer = _outer(
        "causal_thing_mosaic",
        "causal_thing_mosaic",
        None,
    )
    with pytest.raises(
        AuthenticatedOwnerStateUnwrapError,
        match="authenticated manifest member",
    ):
        unwrap_authenticated_owner_state(
            relative_path="owner_state/causal_thing_mosaic.json",
            outer_bytes=outer + b" ",
            expected_outer_sha256=_sha(outer),
            expected_owner_id="causal_thing_mosaic",
            expected_state_key="causal_thing_mosaic",
        )


def test_wrong_owner_or_state_key_fails_closed() -> None:
    outer = _outer(
        "causal_thing_mosaic",
        "causal_thing_mosaic",
        None,
    )
    for owner, key in (
        ("whole_organism_neuron_population", "causal_thing_mosaic"),
        ("causal_thing_mosaic", "whole_organism_neuron_population"),
    ):
        with pytest.raises(AuthenticatedOwnerStateUnwrapError):
            unwrap_authenticated_owner_state(
                relative_path="owner_state/causal_thing_mosaic.json",
                outer_bytes=outer,
                expected_outer_sha256=_sha(outer),
                expected_owner_id=owner,
                expected_state_key=key,
            )
