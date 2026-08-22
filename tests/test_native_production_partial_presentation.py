"""Behavioral proof of partial card presentation and one-shot persistence.

The lesson reaches the ordinary joint sensorium.  Assertions stay coupled to
the current native observation and its authored surface cardinalities; they do
not pin incidental neuron-transition totals or call a physical formation
semantic recognition.  The persistence checks account explicitly for the
one-time whole-body proprioceptive interval mounted by a newborn's first
admitted trajectory.
"""

from __future__ import annotations

import json

from fastapi import HTTPException
import pytest

from dsf_ai_service import native_production_app as production
from dsf_ai_service.substrate.native_organism_binary_store import (
    NativeOrganismBinaryStoreError,
)


CARD_ID = "alphabet-a"
SURFACE_PORTS = production.CARD_SURFACE_PORT_COUNT
LESSON_PORTS = production.LESSON_PORT_COUNT


@pytest.fixture()
def lean_app(monkeypatch, tmp_path):
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    yield tmp_path
    production._restored = None
    production._admission = None
    production._boot_error = None
    production._public_observation_body = None
    production._public_observation_etag = None
    production._runtime_proof_body = None
    production._last_transition_evidence = None


def _teach(card_id: str, presentation: str | None = None) -> tuple[int, dict]:
    invitation = {
        "schema": production.CURRICULUM_INVITATION_SCHEMA,
        "card_id": card_id,
        "outcome": "presentable",
        "presentation_eligible": True,
        "participant_action_causal_intent_receipt_sha256": "22" * 32,
        "reason": "test fixture physical invitation reached retina",
        "status": "participant_invitation_reached_retina",
    }
    invitation["invitation_receipt_sha256"] = production._receipt(invitation)
    production._curriculum_invitation = invitation
    payload: dict[str, object] = {
        "card_id": card_id,
        "invitation_receipt_sha256": invitation[
            "invitation_receipt_sha256"
        ],
    }
    if presentation is not None:
        payload["presentation"] = presentation
    response = production.teach_card(payload)
    return response.status_code, json.loads(response.body)


def test_partial_presentation_lights_only_a_strict_chain_prefix_subset() -> None:
    # The lit subset is deterministic from the declared topology coordinates
    # and is a contiguous prefix of the authored contact chain.
    luminance = tuple(0.25 + index / 100.0 for index in range(SURFACE_PORTS))
    levels = production._partial_presentation_levels(luminance)
    lit = [index for index, level in enumerate(levels) if level != 0.0]
    assert lit == list(range(production.PARTIAL_PRESENTATION_SITE_COUNT))
    assert 0 < len(lit) < SURFACE_PORTS
    # Lit sites carry the real card values; the rest carry true dark samples.
    for index in lit:
        assert levels[index] == luminance[index]
    assert all(level == 0.0 for level in levels[len(lit):])


def test_partial_presentation_is_refused_for_an_unknown_mode(lean_app) -> None:
    production._startup()
    status, refused = _teach(CARD_ID, "half")
    assert status == 422
    assert refused["accepted"] is False
    assert "presentation" in refused["reason"]
    # Nothing reached the organism.
    assert production._restored.organism.readiness().organism_tick == 0


def test_partial_presentation_after_learning_reports_only_admitted_physics(
    lean_app,
) -> None:
    production._startup()

    # Two full presentations physically perturb and recover the resident
    # body without exhaustion.  A newborn's first lesson also contains its
    # one-time 74-axis proprioceptive initialization, so only lower bounds
    # and authored surface cardinalities are architectural facts here.
    first_status, first = _teach(CARD_ID)
    second_status, second = _teach(CARD_ID)
    assert first_status == 200 and second_status == 200
    for lesson in (first, second):
        assert lesson["totals"]["physically_transitioned_neuron_count"] > 0
        assert lesson["totals"]["dsf_delivery_count"] > 0
        assert lesson["totals"]["rest_recovered_neuron_count"] > 0
        assert lesson["totals"]["energy_exhausted_interval_count"] == 0
    assert first["totals"]["complete_neuron_fractal_count"] >= SURFACE_PORTS
    assert second["totals"]["complete_neuron_fractal_count"] >= SURFACE_PORTS

    # One partial presentation of the same approved card.
    status, partial = _teach(CARD_ID, "partial")
    assert status == 200
    assert partial["accepted"] is True
    assert partial["presentation"] == "partial"
    assert partial["card_id"] == CARD_ID
    assert partial["hop_count"] == 1 + production.PARTIAL_PRESENTATION_ENDED_HOP_COUNT

    # Truth-coupling: the reported partial-cue and mosaic counts are exactly
    # the decoded native observation, never a surface claim.
    observed = production._restored.organism.readiness()
    assert (
        partial["totals"]["partial_cue_reassembly_count"]
        >= partial["observation"]["partial_cue_reassembly_count"]
    )
    assert (
        partial["observation"]["partial_cue_reassembly_count"]
        == observed.partial_cue_reassembly_count
    )
    assert (
        partial["observation"]["cognitive_mosaic_count"]
        == observed.cognitive_mosaic_count
    )

    # The public observation projects the same decoded counts.
    body = json.loads(production._public_observation_body)
    assert (
        body["recall"]["partial_cue_reassembly_count"]
        == observed.partial_cue_reassembly_count
    )
    assert body["recall"]["available"] is (
        observed.endogenous_partial_cue_reassembly_count > 0
    )
    assert body["formations"]["mosaic_count"] == observed.cognitive_mosaic_count
    assert (
        body["generation_state"]["state_sha256"]
        == partial["persisted"]["state_sha256"]
    )

    # The glimpse carries exactly the authored lit subset through real DSF
    # work.  Any recurrence/mosaic is reported only as native physics; this
    # test deliberately makes no claim that it means recognition of "A".
    assert partial["totals"]["physically_transitioned_neuron_count"] > 0
    assert partial["totals"]["dsf_delivery_count"] > 0
    assert partial["totals"]["complete_neuron_fractal_count"] == (
        production.PARTIAL_PRESENTATION_SITE_COUNT
    )
    assert partial["totals"]["energy_exhausted_interval_count"] == 0
    assert body["recall"]["available"] is (
        observed.endogenous_partial_cue_reassembly_count > 0
    )
    assert body["formations"]["mosaic_count"] == observed.cognitive_mosaic_count


def test_one_lesson_persists_exactly_once_after_its_final_hop(
    lean_app, monkeypatch
) -> None:
    production._startup()
    publishes: list[int] = []
    real_publish = production.publish_staged_native_organism

    def counting_publish(*args, **kwargs):
        published = real_publish(*args, **kwargs)
        publishes.append(published.pointer.organism_tick)
        return published

    monkeypatch.setattr(
        production, "publish_staged_native_organism", counting_publish
    )
    before = production._restored.organism.readiness()
    before_tick = before.organism_tick
    initializes_body_proprioception = not (
        before.articulated_body_proprioception_initialized
    )

    status, lesson = _teach(CARD_ID)
    assert status == 200
    # Many hops advanced the organism; exactly one body was published.
    assert lesson["hop_count"] >= 3
    assert len(publishes) == 1
    after = production._restored.organism.readiness()
    after_tick = after.organism_tick
    assert after_tick == (
        before_tick
        + lesson["hop_count"]
        + int(initializes_body_proprioception)
    )
    assert after.articulated_body_proprioception_initialized is True
    assert publishes == [after_tick]
    assert production._restored.pointer.state_sha256 == (
        lesson["persisted"]["state_sha256"]
    )
    # The published body is what a cold restart sees.
    production._startup()
    assert production._restored.organism.readiness().organism_tick == after_tick


def test_failed_persist_keeps_current_and_poisons_the_runtime(
    lean_app, monkeypatch
) -> None:
    production._startup()
    pre_lesson_sha = production._restored.pointer.state_sha256
    pre_lesson_tick = production._restored.organism.readiness().organism_tick

    real_publish = production.publish_staged_native_organism

    def refusing_publish(*_args, **_kwargs):
        raise NativeOrganismBinaryStoreError("injected publication failure")

    monkeypatch.setattr(
        production, "publish_staged_native_organism", refusing_publish
    )
    with pytest.raises(HTTPException) as failure:
        _teach(CARD_ID)
    assert failure.value.status_code == 503
    # The surface degrades honestly instead of serving unpersisted state.
    assert production._restored is None
    assert production._public_observation_body is None
    assert production._runtime_proof_body is None
    with pytest.raises(HTTPException):
        production.native_observation()
    with pytest.raises(HTTPException):
        production.ready_guala()

    # Restart-consistency: the durable body is still the pre-lesson body, so
    # a crash mid-lesson loses only the un-persisted lesson tail.  Only the
    # injected publication failure is lifted; the state root stays patched.
    monkeypatch.setattr(
        production, "publish_staged_native_organism", real_publish
    )
    production._startup()
    assert production._restored.pointer.state_sha256 == pre_lesson_sha
    assert (
        production._restored.organism.readiness().organism_tick
        == pre_lesson_tick
    )
