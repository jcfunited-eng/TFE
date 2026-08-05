"""Headless proof of the partial-presentation (glimpse) lesson mode.

Drives ``dsf_ai_service.native_production_app`` through its own functions
only: seeded growth-DNA genesis, two full-presentation lessons so a retained
experience exists, then one partial presentation of the same approved card —
a strict subset of the card-surface ports carrying the real card region's
luminance, the remaining card ports carrying their true dark samples, and
silence at both ears.

Every asserted number is what the native observation actually reports.  The
partial-cue and mosaic assertions are truth-coupled to the decoded native
counts: this file never asserts a mosaic the physics did not admit, and it
records the measured refusal instead (see the module docstring of
``_partial_card_lesson_hop_episodes`` for the physical reason).

The same file proves the per-lesson persistence contract: one accepted
intake publishes exactly one durable body, after its last hop, and a failure
to persist leaves CURRENT on the pre-lesson body while poisoning the runtime.
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
    production._last_transition_evidence = None
    production._pcm_sessions.clear()


def _teach(card_id: str, presentation: str | None = None) -> tuple[int, dict]:
    payload: dict[str, object] = {"card_id": card_id}
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

    # Two full presentations: the cohort grows, then the settled experience
    # emits its genuine post-quiescence fractals and is retained.
    first_status, first = _teach(CARD_ID)
    second_status, second = _teach(CARD_ID)
    assert first_status == 200 and second_status == 200
    assert first["totals"]["physically_transitioned_neuron_count"] == SURFACE_PORTS
    assert second["totals"]["complete_neuron_fractal_count"] == SURFACE_PORTS

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
        observed.partial_cue_reassembly_count > 0
    )
    assert body["formations"]["mosaic_count"] == observed.cognitive_mosaic_count
    assert (
        body["generation_state"]["state_sha256"]
        == partial["persisted"]["state_sha256"]
    )

    # MEASURED PHYSICS (2026-08-05, re-measured under Law 1, threshold-
    # integrated delivery): the glimpse commits lawfully, now genuinely OPENS
    # gates, and still admits no mosaic.  What changed physically: the
    # per-site accumulator retains its 2*L*T energy across lessons, so after
    # two full lessons the brightest lit sites carry ~15 of the 1/16 zJ
    # lattice quanta; the glimpse hop takes them past the gate's own opening
    # threshold (17 quanta = the +1 zJ plastic support barrier plus one), the
    # 12 lit chain-prefix sites open, charge crosses the 500 pS chain
    # contacts into the dark members, and the eight dark ended hops close the
    # gates again (measured probe: 81 gate quanta dissipated, 0 gates left
    # open).
    #
    # PIN CHANGED by Law 1, measured before/after on this exact path:
    #   physically_transitioned_neuron_count  BEFORE 12  ->  AFTER 57
    # 57 is the summed per-hop count over the glimpse and its eight ended
    # hops: 12 lit sites on the glimpse hop plus the chain neighbours whose
    # membrane charge the recurrence current actually moves while the
    # injected charge redistributes.
    #
    # The mosaic is still refused, and the refusal reason is now a DIFFERENT
    # one, read from the physics itself (measurement probe replaying
    # admit_physical_mosaic on the persisted body): OriginalRelationNotConnected.
    # The retained ORIGINAL experience is the second full lesson's, which
    # settled with zero gate openings and therefore zero active electrical
    # contacts, so its members are not connected by any active relation.  No
    # electrically active experience has been retained in its place because
    # inter-neuron charge settlement does not quiesce (see the 2026-08-05
    # Law 2 diagnosis: whole-elementary-charge oscillation along the chain).
    # This is recorded, never forced: if the substrate ever admits a mosaic,
    # these assertions report it instead of hiding it.
    if observed.cognitive_mosaic_count == 0:
        assert (
            partial["totals"]["physically_transitioned_neuron_count"] == 57
        )
        assert observed.partial_cue_reassembly_count == 0
    else:
        assert observed.partial_cue_reassembly_count > 0
        assert body["recall"]["status"] == (
            "physical_partial_cue_reassembly_observed"
        )


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
    before_tick = production._restored.organism.readiness().organism_tick

    status, lesson = _teach(CARD_ID)
    assert status == 200
    # Many hops advanced the organism; exactly one body was published.
    assert lesson["hop_count"] >= 3
    assert len(publishes) == 1
    after_tick = production._restored.organism.readiness().organism_tick
    assert after_tick == before_tick + lesson["hop_count"]
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
    with pytest.raises(HTTPException):
        production.native_observation()

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
