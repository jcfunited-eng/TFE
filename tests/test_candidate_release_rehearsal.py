"""Current one-shot task-853 migration and native publication contract."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import dsf_ai_service.candidate_release_rehearsal as rehearsal
import dsf_ai_service.native_production_app as production


BASELINE = "11111111-1111-4111-8111-111111111111"
ACTIVE = "22222222-2222-4222-8222-222222222222"
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
TICK = 23_723_846
GIT_SHA = "a" * 40
IMAGE = "sha256:" + "b" * 64


def _content_generation(
    root: Path,
    generation: str,
    *,
    tick: int,
    payload: bytes | None,
) -> None:
    directory = root / "generations" / generation
    directory.mkdir(parents=True)
    required_files: list[dict[str, object]] = []
    if payload is not None:
        digest = hashlib.sha256(payload).hexdigest()
        chunk = root / "content-chunks" / digest[:2] / digest
        chunk.parent.mkdir(parents=True)
        chunk.write_bytes(payload)
        required_files.append(
            {
                "chunks": [
                    {
                        "schema": "immutable_generation_content_chunk_v1",
                        "sha256": digest,
                        "size_bytes": len(payload),
                    }
                ],
                "generation_uuid": generation,
                "identity": IDENTITY,
                "json_payload": True,
                "relative_path": "guala_core.json",
                "schema": "immutable_generation_content_record_v2",
                "sha256": digest,
                "size_bytes": len(payload),
                "tick": tick,
            }
        )
    manifest = {
        "generation_uuid": generation,
        "identity": IDENTITY,
        "required_files": required_files,
        "schema": "immutable_generation_content_manifest_v2",
        "tick": tick,
    }
    (directory / "MANIFEST.json").write_bytes(
        rehearsal._generation_canonical(manifest)
    )


def _source_root(tmp_path: Path, predecessor: bytes) -> Path:
    source = tmp_path / "source"
    core = rehearsal._canonical(
        {
            "data": {
                "organism_state": {
                    "native_materialized_fabric": {
                        "state_base64": base64.b64encode(predecessor).decode("ascii")
                    }
                }
            }
        }
    )
    _content_generation(
        source / "sealed",
        BASELINE,
        tick=TICK - 1,
        payload=None,
    )
    _content_generation(
        source / "sealed-live-recovery",
        ACTIVE,
        tick=TICK,
        payload=core,
    )
    return source


def test_migration_is_one_shot_and_ordinary_boot_cannot_import_it() -> None:
    rehearsal_source = Path(rehearsal.__file__).read_text(encoding="utf-8")
    production_source = Path(production.__file__).read_text(encoding="utf-8")
    assert "authenticated_task853_organism_migration" in rehearsal_source
    assert "base64.b64decode" in rehearsal_source
    assert "candidate_release_rehearsal" not in production_source
    assert "authenticated_task853_organism_migration" not in production_source
    for forbidden in (
        "physical_surface_lesson",
        "passive_learning",
        "owner_snapshots",
        "start_exact_field_executor",
        "GLMFAB04",
    ):
        assert forbidden not in rehearsal_source


def test_source_extracts_only_the_authenticated_predecessor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    predecessor = b"GLMFAB03-authenticated-test-predecessor"
    monkeypatch.setattr(
        rehearsal,
        "TASK853_GLMFAB03_SHA256",
        hashlib.sha256(predecessor).digest(),
    )
    source = _source_root(tmp_path, predecessor)
    assert rehearsal._predecessor(
        source,
        expected_baseline_generation=BASELINE,
        expected_active_generation=ACTIVE,
        expected_identity=IDENTITY,
        expected_tick=TICK,
    ) == predecessor

    monkeypatch.setattr(rehearsal, "TASK853_GLMFAB03_SHA256", b"x" * 32)
    with pytest.raises(RuntimeError, match="predecessor digest changed"):
        rehearsal._predecessor(
            source,
            expected_baseline_generation=BASELINE,
            expected_active_generation=ACTIVE,
            expected_identity=IDENTITY,
            expected_tick=TICK,
        )


def test_identity_and_source_coordinates_are_fail_closed() -> None:
    assert rehearsal._uuid(BASELINE, "baseline") == BASELINE
    assert rehearsal._identity(IDENTITY) == IDENTITY
    assert rehearsal._tick(TICK) == TICK
    with pytest.raises(ValueError):
        rehearsal._uuid("not-a-generation", "baseline")
    with pytest.raises(ValueError):
        rehearsal._identity("another-organism")
    with pytest.raises(ValueError):
        rehearsal._tick(TICK + 1)


def test_rehearsal_proof_binds_artifact_source_and_native_state(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        rehearsal,
        "_arguments",
        lambda: SimpleNamespace(
            mode="rehearse",
            source_root="/read-only/source",
            native_store_root=None,
            expected_baseline_generation=BASELINE,
            expected_active_generation=ACTIVE,
            expected_identity=IDENTITY,
            expected_tick=TICK,
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
        ),
    )
    monkeypatch.setattr(rehearsal, "_predecessor", lambda *_args, **_kwargs: b"p")
    monkeypatch.setattr(
        rehearsal,
        "_round_trip",
        lambda *_args, **_kwargs: {
            "cognitive_mosaic_count": 0,
            "cognitive_trace_count": 0,
            "formation_activation_count": 0,
            "joint_field_count": 2,
            "joint_neuron_count": 96,
            "publication_reused": False,
            "python_callback_count": 0,
            "resident_state_bytes": 500,
            "resident_state_sha256": "e" * 64,
        },
    )

    assert rehearsal.main() == 0
    proof = json.loads(capsys.readouterr().out)
    receipt = proof.pop("receipt_sha256")
    assert proof["schema"] == rehearsal.PROOF_SCHEMA
    assert proof["source_mount_read_only"] is True
    assert proof["python_cognition_workers_started"] == 0
    assert proof["raw_glorun_current_only"] is True
    assert proof["candidate_git_sha"] == GIT_SHA
    assert proof["candidate_image_digest"] == IMAGE
    assert receipt == hashlib.sha256(rehearsal._canonical(proof)).hexdigest()


def _genesis_arguments() -> SimpleNamespace:
    return SimpleNamespace(
        mode="genesis-rehearse",
        source_root=None,
        native_store_root=None,
        expected_baseline_generation=None,
        expected_active_generation=None,
        expected_identity=IDENTITY,
        expected_tick=None,
        candidate_git_sha=GIT_SHA,
        candidate_image_digest=IMAGE,
    )


@pytest.fixture()
def genesis_rehearsal_root(monkeypatch, tmp_path):
    root = tmp_path / "native-organism-rehearsal"
    monkeypatch.setenv("GUALA_NATIVE_ORGANISM_ROOT", str(root))
    monkeypatch.setenv("GUALA_NATIVE_ORGANISM_IDENTITY", IDENTITY)
    original_state_root = production.STATE_ROOT
    yield root
    production.STATE_ROOT = original_state_root
    production._restored = None
    production._admission = None
    production._boot_error = None
    production._public_observation_body = None
    production._public_observation_etag = None
    production._last_transition_evidence = None
    production._pcm_sessions.clear()


def test_genesis_rehearsal_refuses_a_root_with_a_current_organism(
    genesis_rehearsal_root,
    monkeypatch,
) -> None:
    genesis_rehearsal_root.mkdir(parents=True)
    (genesis_rehearsal_root / "CURRENT").write_bytes(b"existing organism")
    monkeypatch.setattr(rehearsal, "_arguments", _genesis_arguments)
    with pytest.raises(RuntimeError, match="already contains a CURRENT"):
        rehearsal.main()
    assert (genesis_rehearsal_root / "CURRENT").read_bytes() == b"existing organism"


def test_genesis_rehearsal_headless_proof_on_a_fresh_root(
    genesis_rehearsal_root,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(rehearsal, "_arguments", _genesis_arguments)
    assert rehearsal.main() == 0
    proof = json.loads(capsys.readouterr().out)
    receipt = proof.pop("receipt_sha256")
    assert receipt == hashlib.sha256(rehearsal._canonical(proof)).hexdigest()
    assert proof["schema"] == rehearsal.GENESIS_PROOF_SCHEMA
    assert proof["mode"] == "genesis-rehearse"
    assert proof["identity"] == IDENTITY
    assert proof["state_root"] == str(genesis_rehearsal_root)
    assert proof["taught_card_id"] == "alphabet-a"
    assert proof["python_callback_count"] == 0
    # PINS UPDATED 2026-08-06 to the stimulus-boundary retention
    # ratification (2026-08-05), mirroring the lean-teaching suite's
    # documented remeasurement on this exact served path: the rehearsal's
    # two lesson passes now transition 209 + 211 == 420 neurons (every lit
    # hop and both ended hops declare their own exact optical occurrence),
    # and the grown cohort is the 27 retinal card sites — the two ear
    # neurons only ever joined through the old combined-occurrence
    # transport lie, which that ratification removed.
    assert proof["physically_transitioned_neuron_count"] == 420
    assert proof["complete_neuron_fractal_count"] > 0
    assert proof["complete_neuron_count"] == production.CARD_SURFACE_PORT_COUNT
    for field in ("genesis_state_sha256", "post_teach_state_sha256"):
        assert rehearsal._SHA256.fullmatch(proof[field]) is not None
    assert proof["genesis_state_sha256"] != proof["post_teach_state_sha256"]
    assert (genesis_rehearsal_root / "CURRENT").is_file()


def test_publication_requires_an_explicit_native_store(monkeypatch) -> None:
    monkeypatch.setattr(
        rehearsal,
        "_arguments",
        lambda: SimpleNamespace(
            mode="publish",
            source_root="/read-only/source",
            native_store_root=None,
            expected_baseline_generation=BASELINE,
            expected_active_generation=ACTIVE,
            expected_identity=IDENTITY,
            expected_tick=TICK,
            candidate_git_sha=GIT_SHA,
            candidate_image_digest=IMAGE,
        ),
    )
    monkeypatch.setattr(rehearsal, "_predecessor", lambda *_args, **_kwargs: b"p")
    with pytest.raises(ValueError, match="requires --native-store-root"):
        rehearsal.main()
