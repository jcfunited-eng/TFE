"""Exact causal receipt verification for retained legacy-v1 generations."""

from __future__ import annotations

import json
from pathlib import Path

from dsf_ai_service.substrate.deployment_generation import (
    CAUSAL_GENERATION_RECEIPT,
    CAUSAL_GENERATION_SCHEMA,
    CAUSAL_PROJECTION_SCHEMA,
    _generation_causal_contract,
    verified_causal_generation_receipt,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)


IDENTITY = "legacy-causal-projection-compatibility"


def _legacy_engine_envelope(timestamp: str) -> dict:
    return {
        "schema_version": "v7.4.0",
        "guala_identity": IDENTITY,
        "saved_at_tick": 17,
        "saved_at_timestamp": timestamp,
        "data": {
            "tick": 17,
            "causal": "unchanged",
        },
    }


def _commit_projection_source(
    root: Path,
    source: Path,
    *,
    timestamp: str,
):
    source.mkdir()
    (source / "guala_core.json").write_text(
        json.dumps(_legacy_engine_envelope(timestamp))
    )
    (source / "organism.bin").write_bytes(b"same-legacy-organism")
    return ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=("guala_core.json", "organism.bin"),
    ).commit(
        tick=17,
        files={
            "guala_core.json": source / "guala_core.json",
            "organism.bin": source / "organism.bin",
        },
    )


def _commit_receipt_generation(
    root: Path,
    source: Path,
    *,
    causal_sha256: str,
    operational_sha256: str,
):
    receipt = source / CAUSAL_GENERATION_RECEIPT
    receipt.write_text(json.dumps({
        "schema": CAUSAL_GENERATION_SCHEMA,
        "projection_schema": CAUSAL_PROJECTION_SCHEMA,
        "state_revision": 12,
        "causal_state_sha256": causal_sha256,
        "operational_metadata_sha256": operational_sha256,
    }))
    return ImmutableGenerationStore(
        root,
        identity=IDENTITY,
        required_files=(
            CAUSAL_GENERATION_RECEIPT,
            "guala_core.json",
            "organism.bin",
        ),
    ).commit(
        tick=17,
        files={
            CAUSAL_GENERATION_RECEIPT: receipt,
            "guala_core.json": source / "guala_core.json",
            "organism.bin": source / "organism.bin",
        },
    )


def test_legacy_v1_receipt_uses_its_original_operational_projection(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    projection = _commit_projection_source(
        tmp_path / "projection-store",
        source,
        timestamp="2026-07-29T08:00:00Z",
    )
    causal_sha256, operational_sha256 = _generation_causal_contract(
        projection
    )
    assert (
        causal_sha256
        == "ad3c4c3f96caf77492e33a4603e4342c85fa1536f6019b950a91c4c84179e1f1"
    )
    assert (
        operational_sha256
        == "e582b906f2c2809eb99a70e2e5f1902781e099ca7ca9b0d68c1e97e35ab3f871"
    )
    sealed = _commit_receipt_generation(
        tmp_path / "sealed-store",
        source,
        causal_sha256=causal_sha256,
        operational_sha256=operational_sha256,
    )

    receipt = verified_causal_generation_receipt(sealed)

    assert receipt is not None
    assert receipt.state_revision == 12
    assert receipt.causal_state_sha256 == causal_sha256
    assert receipt.operational_metadata_sha256 == operational_sha256


def test_legacy_v1_timestamp_changes_only_operational_projection(
    tmp_path: Path,
) -> None:
    first = _commit_projection_source(
        tmp_path / "first-store",
        tmp_path / "first-source",
        timestamp="2026-07-29T08:00:00Z",
    )
    second = _commit_projection_source(
        tmp_path / "second-store",
        tmp_path / "second-source",
        timestamp="2026-07-29T08:05:00Z",
    )

    first_causal, first_operational = _generation_causal_contract(first)
    second_causal, second_operational = _generation_causal_contract(second)

    assert second_causal == first_causal
    assert second_operational != first_operational
