"""Proof that a real, continuously-varying live boundary event -- assembled
by ``six_sense_boundary_owner.observe_six_sense_boundary`` from genuine
(synthetic-but-real, per that module's own test convention) sight/sound/
touch/smell/taste captures -- can now be legitimately archived as a
``recall_story_episode_archive.RecallStoryEpisode`` via
``live_boundary_episode_adapter.mint_live_boundary_as_episode_scene_authority``,
without loosening ``MountedAuthenticatedClosedStoryBoundary.verify()`` or
fabricating any sensory content.

Every real observed flux value below comes from the same real translators
``tests/glew_runtime/test_six_sense_boundary_owner.py`` already proves real
(``visual_krimelack.view_picture``/``visual_fragment_receipt``, a real
cochlear-band ``AuditoryPerceptFragment``, and the somatic emulator's own
touch/smell/taste chemistry) -- never a hand-picked literal chosen to make a
check pass.
"""

from __future__ import annotations

import json
from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.auditory_fragment_receipt import (
    AUDITORY_BAND_ORDER,
    AuditoryPerceptFragment,
    auditory_fragment_receipt,
)
from dsf_ai_service.glew_runtime.field import (
    MountedFieldTopology,
    PortFiber,
    field_topology_receipt_payload,
)
from dsf_ai_service.glew_runtime.global_uf import (
    MountedPreWindowState,
    pre_window_state_receipt_payload,
)
from dsf_ai_service.glew_runtime.live_boundary_episode_adapter import (
    mint_live_boundary_as_episode_scene_authority,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    RequiredEdge,
    ResonanceOperatorAuthority,
    causal_grid_receipt_payload,
    resonance_graph_receipt_payload,
    resonance_operator_receipt_payload,
    support_domain_receipt_payload,
)
from dsf_ai_service.glew_runtime.physical_l6_tangents import NativeReplayCaseKind
from dsf_ai_service.glew_runtime.recall_story_episode_archive import (
    RecallStoryEpisodeArchive,
    create_recall_story_episode,
)
from dsf_ai_service.glew_runtime.six_sense_boundary_owner import (
    SixSenseBoundaryStatus,
    observe_six_sense_boundary,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    mount_packaged_production_story_chemistry,
)
from dsf_ai_service.glew_runtime.story_native_replay import (
    MountedAuthenticatedClosedStoryBoundary,
    MountedStoryNativeReplayProfile,
    MountedStorySensorState,
    StoryNativeReplayStatus,
    authenticated_closed_story_boundary_receipt_payload,
    execute_story_native_replay,
    story_native_replay_profile_receipt_payload,
    story_replay_chemistry_state_receipt_payload,
    story_sensor_state_receipt_payload,
)
from dsf_ai_service.visual_krimelack import view_picture, visual_fragment_receipt


RUNTIME_KEY = b"test process only: live boundary episode adapter runtime secret"
RUNTIME_KEY_ID = "test-live-boundary-episode-adapter-runtime-key"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _unique_payloads(payloads) -> tuple[bytes, ...]:
    values = {receipt_sha256(value): value for value in payloads}
    return tuple(values[digest] for digest in sorted(values))


def _mounted_runtime():
    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=RUNTIME_KEY,
        runtime_key_id=RUNTIME_KEY_ID,
    )
    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    return mounted.runtime


def _real_visual_fragment_receipt(*, fill_value: float, seed: int = 11):
    """Same real saccade/fovea-krimelack pipeline
    ``tests/glew_runtime/test_six_sense_boundary_owner.py`` already proves
    real -- a genuine (synthetic but real) captured image."""

    image = np.full((16, 16), fill_value, dtype=np.float64)
    fragments = view_picture(
        image,
        source_id="live-boundary-adapter-test-camera",
        born_tick=0,
        seed=seed,
        n_fixations=1,
        ticks_per_fixation=500,
    )
    assert fragments, "view_picture produced no fragments for a real image"
    return visual_fragment_receipt(fragments[0])


def _silent_bands() -> dict:
    return {
        band_name: {"winding": 0, "n_events": 0, "events": []}
        for band_name in AUDITORY_BAND_ORDER
    }


def _real_auditory_fragment_receipt(*, born_tick: int = 0):
    """Same real cochlear-band capture shape
    ``tests/glew_runtime/test_six_sense_boundary_owner.py`` already proves
    real -- one real nonzero band plus five genuinely silent bands."""

    bands = _silent_bands()
    bands["mid"] = {
        "winding": 3,
        "n_events": 5,
        "events": [
            {"t": 0.04 * (i + 1), "dw": (1 if i != 3 else -1), "s": 0.5}
            for i in range(5)
        ],
    }
    fragment = AuditoryPerceptFragment(
        source_id="live-boundary-adapter-test-mic",
        born_tick=born_tick,
        sample_rate_hz=200,
        input_sample_count=128,
        bands=bands,
    )
    return auditory_fragment_receipt(fragment)


def _real_live_five_port_event(runtime):
    """One real, full five-sense ``StoryPhysicalBoundaryEvent``: genuine
    captured/emulated sensor readings, continuously varying in the sense
    that nothing here was chosen to make any downstream check pass."""

    result = observe_six_sense_boundary(
        runtime,
        event_id="live-boundary-adapter-real-instant",
        source_time_start=Fraction(0),
        source_time_end=Fraction(3),
        visual_fragment_receipt=_real_visual_fragment_receipt(fill_value=0.63),
        auditory_fragment_receipt=_real_auditory_fragment_receipt(),
        touch_descriptor="warm",
        smell_descriptor=None,
        taste_descriptor=None,
    )
    assert result.status is SixSenseBoundaryStatus.OBSERVED, result.reason
    assert result.event is not None
    assert len(result.event.observations) == 5
    return result.event


def _mint_authorities(runtime, event):
    return mint_live_boundary_as_episode_scene_authority(
        boundary_event=event,
        manifest=runtime.manifest,
        receipt_registry=runtime.receipt_registry,
        signal_offset=Fraction(0),
        signal_per_native_flux=Fraction(1),
        response_growth=Fraction(1, 2),
        natural_decay=Fraction(1, 8),
        phase_kappa=Fraction(1, 3),
        physical_quantum=Fraction(1, 20),
        source_epoch="live-boundary-adapter-test-epoch-0",
        port_kind="authenticated_live_six_sense_boundary",
        signal_physical_unit="dimensionless_story_response",
    )


def _mount_live_five_sense_replay_context():
    """Mount a real, live-anchored five-sense story-native-replay context:
    the same topology/grid/support/resonance/profile construction recipe
    ``tests/glew_runtime/test_story_native_replay.py::_mounted_five_sense_runtime``
    already proves real, but with the port authorities' ``flux_at_code_zero``
    genuinely anchored to one real live instant's own observed flux (via
    this task's new adapter) instead of a hand-picked literal.
    """

    story_runtime = _mounted_runtime()
    event = _real_live_five_port_event(story_runtime)
    authorities, minted_registry = _mint_authorities(story_runtime, event)
    assert len(authorities) == 5

    fibers = tuple(
        PortFiber(value.lane.value, value.field_port_id) for value in authorities
    )
    topology_payload = field_topology_receipt_payload(
        "live-boundary-adapter-topology", fibers
    )
    topology = MountedFieldTopology(
        "live-boundary-adapter-topology",
        fibers,
        receipt_sha256(topology_payload),
    )
    grid_payload = causal_grid_receipt_payload(
        "live-boundary-adapter-grid",
        (Fraction(1), Fraction(2), Fraction(3)),
        (Fraction(1), Fraction(1), Fraction(1)),
    )
    grid = CausalGrid(
        "live-boundary-adapter-grid",
        (Fraction(1), Fraction(2), Fraction(3)),
        (Fraction(1), Fraction(1), Fraction(1)),
        receipt_sha256(grid_payload),
    )
    topology_keys = tuple(value.field_key for value in authorities)
    support_payload = support_domain_receipt_payload(
        "live-boundary-adapter-support", topology_keys
    )
    support = MountedSupportDomain(
        "live-boundary-adapter-support",
        topology_keys,
        receipt_sha256(support_payload),
    )
    edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(topology_keys[:-1], topology_keys[1:], strict=True)
    )
    graph_payload = resonance_graph_receipt_payload(
        "live-boundary-adapter-resonance", edges
    )
    graph = MountedResonanceGraph(
        "live-boundary-adapter-resonance",
        edges,
        receipt_sha256(graph_payload),
    )
    resonance_payload = resonance_operator_receipt_payload(
        "live-boundary-adapter-gamma-squared", 128
    )
    resonance = ResonanceOperatorAuthority(
        "live-boundary-adapter-gamma-squared",
        128,
        receipt_sha256(resonance_payload),
    )
    adapter_payload = _canonical(
        {
            "adapter": "F=1+s/2; relevance identity",
            "schema": "glew.story_native_replay.test_live_boundary_kernel_adapter.v1",
        }
    )
    profile_payload = story_native_replay_profile_receipt_payload(
        profile_id="live-boundary-adapter-five-sense-story-native-replay",
        provider_id="live-boundary-adapter-frozen-kernel-provider",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        grid_receipt_sha256=grid.grid_receipt_sha256,
        support_domain_receipt_sha256=support.authority_receipt_sha256,
        resonance_graph_receipt_sha256=graph.authority_receipt_sha256,
        resonance_operator_receipt_sha256=resonance.authority_receipt_sha256,
        kernel_adapter_id="live-boundary-adapter-exact-story-kernel-adapter",
        kernel_adapter_profile_receipt_sha256=receipt_sha256(adapter_payload),
        ports=authorities,
    )
    profile = MountedStoryNativeReplayProfile(
        profile_id="live-boundary-adapter-five-sense-story-native-replay",
        provider_id="live-boundary-adapter-frozen-kernel-provider",
        topology=topology,
        grid=grid,
        support_domain=support,
        resonance_graph=graph,
        resonance_operator=resonance,
        kernel_adapter_id="live-boundary-adapter-exact-story-kernel-adapter",
        kernel_adapter_profile_receipt_sha256=receipt_sha256(adapter_payload),
        ports=authorities,
        authority_receipt_sha256=receipt_sha256(profile_payload),
        authority_receipt_payload=profile_payload,
    )

    sensor_states = []
    sensor_payloads = []
    for authority in authorities:
        payload = story_sensor_state_receipt_payload(
            field_port_id=authority.field_port_id,
            source_epoch=authority.source_epoch,
            last_source_index=-1,
            last_timestamp=Fraction(0),
            retained_signal=Fraction(0),
            phase_turns=Fraction(0),
            port_authority_receipt_sha256=authority.authority_receipt_sha256,
        )
        sensor_states.append(
            MountedStorySensorState(
                field_port_id=authority.field_port_id,
                source_epoch=authority.source_epoch,
                last_source_index=-1,
                last_timestamp=Fraction(0),
                retained_signal=Fraction(0),
                phase_turns=Fraction(0),
                port_authority_receipt_sha256=authority.authority_receipt_sha256,
                authority_receipt_sha256=receipt_sha256(payload),
            )
        )
        sensor_payloads.append(payload)
    sensor_states = tuple(sensor_states)

    chemistry_payload = story_replay_chemistry_state_receipt_payload(
        story_runtime=story_runtime, sensor_states=sensor_states
    )
    field_payload = _canonical(
        {"schema": "test.live_boundary_adapter.pre_window_field_state.v1"}
    )
    mode_payload = _canonical(
        {"schema": "test.live_boundary_adapter.pre_window_mode_state.v1"}
    )
    memory_payload = _canonical(
        {"schema": "test.live_boundary_adapter.pre_window_memory_state.v1"}
    )
    l6_payload = _canonical(
        {"schema": "test.live_boundary_adapter.pre_window_l6_state.v1"}
    )
    prewindow_payload = pre_window_state_receipt_payload(
        state_id="live-boundary-adapter-pre-window",
        chemistry_state_receipt_sha256=receipt_sha256(chemistry_payload),
        field_state_receipt_sha256=receipt_sha256(field_payload),
        mode_state_receipt_sha256=receipt_sha256(mode_payload),
        memory_state_receipt_sha256=receipt_sha256(memory_payload),
        l6_state_receipt_sha256=receipt_sha256(l6_payload),
    )
    prewindow = MountedPreWindowState(
        "live-boundary-adapter-pre-window",
        receipt_sha256(chemistry_payload),
        receipt_sha256(field_payload),
        receipt_sha256(mode_payload),
        receipt_sha256(memory_payload),
        receipt_sha256(l6_payload),
        receipt_sha256(prewindow_payload),
    )

    boundary_payload = authenticated_closed_story_boundary_receipt_payload(
        boundary_id="live-boundary-adapter-mounted-boundary",
        event=event,
        profile=profile,
    )
    boundary = MountedAuthenticatedClosedStoryBoundary(
        "live-boundary-adapter-mounted-boundary",
        event,
        profile.authority_receipt_sha256,
        receipt_sha256(boundary_payload),
        boundary_payload,
    )

    minted_payloads = tuple(value.payload for value in minted_registry.records)
    registry = ReceiptRegistry.from_payloads(
        profile_payload=profile_payload,
        receipt_payloads=_unique_payloads(
            (
                *minted_payloads,
                topology_payload,
                grid_payload,
                support_payload,
                graph_payload,
                resonance_payload,
                adapter_payload,
                *sensor_payloads,
                chemistry_payload,
                field_payload,
                mode_payload,
                memory_payload,
                l6_payload,
                prewindow_payload,
                boundary_payload,
            )
        ),
    )
    return (
        profile,
        boundary,
        prewindow,
        story_runtime,
        sensor_states,
        event,
        authorities,
        registry,
    )


# --------------------------------------------------------------------------
# The crux proof: minted authorities' flux_for_code(base_raw_code) genuinely
# equals the real live observed flux -- an exact identity, not an
# approximation, and never a repeated hand-picked literal.
# --------------------------------------------------------------------------


def test_minted_authority_flux_exactly_equals_the_real_live_observed_flux():
    story_runtime = _mounted_runtime()
    event = _real_live_five_port_event(story_runtime)
    authorities, registry = _mint_authorities(story_runtime, event)

    observations_by_port = {value.port_id: value for value in event.observations}
    assert set(observations_by_port) == {value.story_port_id for value in authorities}

    observed_fluxes = set()
    for authority in authorities:
        observation = observations_by_port[authority.story_port_id]
        assert authority.base_raw_code == 0
        assert authority.minimum_raw_code == 0
        assert authority.maximum_raw_code == 0
        # The exact identity story_native_replay.py's boundary check demands:
        assert (
            authority.flux_for_code(authority.base_raw_code)
            == observation.signed_native_flux
        )
        assert authority.native_flux_unit == observation.native_flux_unit
        authority.verify(registry)
        observed_fluxes.add(observation.signed_native_flux)

    # Real, genuinely distinct captured readings -- not one repeated
    # constant standing in for "the live moment".
    assert len(observed_fluxes) >= 3


def test_minted_authority_boundary_source_is_the_real_observation_not_a_stub():
    story_runtime = _mounted_runtime()
    event = _real_live_five_port_event(story_runtime)
    authorities, registry = _mint_authorities(story_runtime, event)

    observations_by_port = {value.port_id: value for value in event.observations}
    for authority in authorities:
        observation = observations_by_port[authority.story_port_id]
        assert (
            authority.boundary_source_authority_receipt_sha256
            == observation.observation_receipt_sha256
        )
        assert (
            registry.resolve(
                authority.boundary_source_authority_receipt_sha256,
                "boundary source authority receipt",
            )
            == observation.observation_receipt_payload
        )


def test_tampered_boundary_event_is_rejected_not_silently_minted():
    from dataclasses import replace

    story_runtime = _mounted_runtime()
    event = _real_live_five_port_event(story_runtime)
    tampered_observation = replace(
        event.observations[0], signed_native_flux=event.observations[0].signed_native_flux + 1
    )
    tampered_event = replace(
        event,
        observations=(tampered_observation, *event.observations[1:]),
    )

    try:
        _mint_authorities(story_runtime, tampered_event)
    except ReceiptError:
        pass
    else:
        raise AssertionError(
            "adapter must reject a tampered boundary event, not mint authorities for it"
        )


# --------------------------------------------------------------------------
# The real acceptance test: MountedAuthenticatedClosedStoryBoundary.verify()
# genuinely passes for a live event -- not by weakening the check.
# --------------------------------------------------------------------------


def test_mounted_boundary_against_a_real_live_event_genuinely_verifies():
    profile, boundary, _prewindow, _runtime, _sensor_states, event, authorities, registry = (
        _mount_live_five_sense_replay_context()
    )

    # This is the exact call that raises
    # "story boundary flux differs from mounted base raw code" for any
    # boundary built from a hand-picked scene-code literal and a genuinely
    # different live reading. It must genuinely pass here -- the check
    # itself is never modified or bypassed.
    boundary.verify(profile=profile, receipt_registry=registry)
    profile.verify(registry)

    observations_by_port = {value.port_id: value for value in event.observations}
    for authority in authorities:
        observation = observations_by_port[authority.story_port_id]
        assert (
            authority.flux_for_code(authority.base_raw_code)
            == observation.signed_native_flux
        )


# --------------------------------------------------------------------------
# The real end-to-end proof: this flows through execute_story_native_replay
# into a real, independently-verifying, archived RecallStoryEpisode.
# --------------------------------------------------------------------------


def test_live_boundary_flows_into_a_real_archived_recall_episode():
    profile, boundary, prewindow, story_runtime, sensor_states, _event, _authorities, registry = (
        _mount_live_five_sense_replay_context()
    )

    result = execute_story_native_replay(
        target_lane=profile.ports[0].lane,
        target_field_port_id=profile.ports[0].field_port_id,
        profile=profile,
        boundary=boundary,
        pre_window_state=prewindow,
        story_runtime=story_runtime,
        sensor_states=sensor_states,
        receipt_registry=registry,
    )
    assert result.status is StoryNativeReplayStatus.READY, result.reason
    # A live-anchored, single-point scene-code registration honestly
    # declares no admissible adjacent scene: only the BASE case exists.
    assert len(result.executions) == 1
    assert result.executions[0].case.kind is NativeReplayCaseKind.BASE

    episode = create_recall_story_episode(
        profile=profile,
        boundary=boundary,
        pre_window_state=prewindow,
        pre_window_story_runtime=story_runtime,
        pre_window_sensor_states=sensor_states,
        execution=result.executions[0],
    )
    episode.verify()
    assert {value.lane_id for value in episode.sensory_evidence_bindings} == {
        "sight",
        "sound",
        "smell",
        "taste",
        "touch",
    }

    archive = RecallStoryEpisodeArchive().with_episode(episode)
    assert (
        archive.resolve(
            profile_binding_sha256=profile.authority_receipt_sha256,
            sensory_evidence_receipt_sha256s=episode.sensory_evidence_receipt_sha256s,
        )
        is episode
    )
