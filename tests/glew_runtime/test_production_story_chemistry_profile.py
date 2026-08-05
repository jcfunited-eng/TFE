from __future__ import annotations

import json
from fractions import Fraction

from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.glew_runtime.story_chemistry import (
    PRODUCTION_STORY_CHEMISTRY_AUTHORITY_SCOPE,
    PRODUCTION_STORY_CHEMISTRY_MANIFEST_ID,
    PRODUCTION_STORY_PORT_LANES,
    StoryChemistryRuntime,
    StoryChemistryStatus,
    StoryKernelBridgeStatus,
    StoryPhysicalBoundaryEvent,
    StoryPhysicalBoundaryObservation,
    authenticate_production_story_chemistry_profile,
    build_story_frozen_kernel_inputs,
    evolve_story_chemistry_event,
    mount_packaged_production_story_chemistry,
    mount_production_story_chemistry_profile,
    production_story_chemistry_profile_payload,
    restore_story_chemistry,
    story_boundary_observation_receipt_payload,
    story_chemistry_checkpoint_payload,
)


RUNTIME_KEY = b"test process only: injected production-profile runtime secret"
RUNTIME_KEY_ID = "test-production-story-runtime-key"
CHECKPOINT_KEY = b"test process only: injected checkpoint runtime secret"
CHECKPOINT_KEY_ID = "test-production-story-checkpoint-key"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _observation(
    *,
    event_id: str,
    port_id: str,
    unit: str,
    start: Fraction,
    end: Fraction,
    flux: Fraction,
) -> StoryPhysicalBoundaryObservation:
    observation_id = f"{event_id}:{port_id}:boundary"
    provenance = _canonical_bytes(
        {
            "boundary": observation_id,
            "origin": "production-profile-conformance-physical-input",
            "schema": "glew.production_story_chemistry.conformance_provenance.v1",
        }
    )
    payload = story_boundary_observation_receipt_payload(
        event_id=event_id,
        observation_id=observation_id,
        port_id=port_id,
        source_time_start=start,
        source_time_end=end,
        signed_native_flux=flux,
        native_flux_unit=unit,
        provenance_receipt_sha256=receipt_sha256(provenance),
    )
    return StoryPhysicalBoundaryObservation(
        event_id=event_id,
        observation_id=observation_id,
        port_id=port_id,
        source_time_start=start,
        source_time_end=end,
        signed_native_flux=flux,
        native_flux_unit=unit,
        provenance_receipt_sha256=receipt_sha256(provenance),
        provenance_receipt_payload=provenance,
        observation_receipt_sha256=receipt_sha256(payload),
        observation_receipt_payload=payload,
    )


def _five_sense_event(
    *,
    runtime: StoryChemistryRuntime,
    event_id: str,
    start: Fraction,
    end: Fraction,
    fluxes: tuple[Fraction, Fraction, Fraction, Fraction, Fraction],
) -> StoryPhysicalBoundaryEvent:
    return StoryPhysicalBoundaryEvent(
        event_id=event_id,
        observations=tuple(
            _observation(
                event_id=event_id,
                port_id=port.port_id,
                unit=port.native_signal_unit,
                start=start,
                end=end,
                flux=flux,
            )
            for port, flux in zip(runtime.manifest.ports, fluxes, strict=True)
        ),
    )


def _mount():
    return mount_packaged_production_story_chemistry(
        runtime_authentication_key=RUNTIME_KEY,
        runtime_key_id=RUNTIME_KEY_ID,
    )


def test_packaged_profile_is_production_authority_without_an_embedded_secret():
    payload = production_story_chemistry_profile_payload()
    body = json.loads(payload)

    assert body["authority_scope"] == PRODUCTION_STORY_CHEMISTRY_AUTHORITY_SCOPE
    assert body["manifest_id"] == PRODUCTION_STORY_CHEMISTRY_MANIFEST_ID
    assert b'"authentication"' not in payload
    assert b'"key_id"' not in payload
    assert b'"signature_sha256"' not in payload
    assert b"candidate" not in payload.lower()
    assert b"biological" not in payload.lower()

    mounted = _mount()
    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    manifest = mounted.runtime.manifest
    assert tuple(
        (port.port_id, port.kernel_binding.lane_id) for port in manifest.ports
    ) == PRODUCTION_STORY_PORT_LANES
    assert [backend.working_precision_bits for backend in manifest.backends] == [128, 256]
    assert len(
        {
            (
                port.native_signal_unit_authority_receipt_sha256,
                port.kernel_binding.authority_receipt_sha256,
                port.time_unit.authority_receipt_sha256,
                port.activation_susceptibility.authority_receipt_sha256,
                port.initial_state.receipt_sha256,
            )
            for port in manifest.ports
        }
    ) == 5
    for port in manifest.ports:
        assert port.time_unit.seconds_per_unit == Fraction(1)
        assert (
            port.activation_susceptibility
            .susceptibility_per_native_signal_unit_per_time_unit
            == Fraction(1)
        )
        assert [rate.rate_per_time_unit for rate in port.rates] == [
            Fraction(1),
            Fraction(0),
            Fraction(1),
        ]
        assert port.initial_state.components == (
            Fraction(1),
            Fraction(0),
            Fraction(0),
        )


def test_runtime_authentication_and_stale_physical_receipts_fail_closed():
    payload = production_story_chemistry_profile_payload()
    missing_secret = mount_production_story_chemistry_profile(
        profile_body_payload=payload,
        runtime_authentication_key=b"",
        runtime_key_id=RUNTIME_KEY_ID,
    )
    body = json.loads(payload)
    body["ports"][0]["activation_susceptibility"][
        "susceptibility_per_native_signal_unit_per_time_unit"
    ] = "2/1"
    stale_receipt = mount_production_story_chemistry_profile(
        profile_body_payload=_canonical_bytes(body),
        runtime_authentication_key=RUNTIME_KEY,
        runtime_key_id=RUNTIME_KEY_ID,
    )

    assert missing_secret.status is StoryChemistryStatus.UNKNOWN
    assert missing_secret.runtime is None
    assert "authentication key is missing" in missing_secret.reason
    assert stale_receipt.status is StoryChemistryStatus.UNKNOWN
    assert stale_receipt.runtime is None
    assert "differs from the signed manifest" in stale_receipt.reason


def test_production_five_sense_chemistry_conforms_and_mounts_frozen_kernel_inputs():
    mounted = _mount()
    assert mounted.runtime is not None
    fluxes = (
        Fraction(1, 2),
        Fraction(-1, 3),
        Fraction(0),
        Fraction(2, 3),
        Fraction(-3, 4),
    )
    first = evolve_story_chemistry_event(
        runtime=mounted.runtime,
        event=_five_sense_event(
            runtime=mounted.runtime,
            event_id="production-five-sense-frame-1",
            start=Fraction(0),
            end=Fraction(1),
            fluxes=fluxes,
        ),
    )
    assert first.status is StoryChemistryStatus.EVOLVED
    assert len(first.outputs) == 5
    for output, signed_flux in zip(first.outputs, fluxes, strict=True):
        activation = output.chemical_evolution_receipt.effective_activation
        generator = output.chemical_evolution_receipt.generator
        assert output.signed_native_flux == signed_flux
        assert activation.signed_native_signal == signed_flux
        assert activation.native_signal_magnitude == abs(signed_flux)
        assert activation.propensity_per_time_unit == abs(signed_flux)
        assert (
            first.runtime.receipt_registry.resolve(
                activation.receipt_sha256,
                "production effective activation receipt",
            )
            == activation.receipt_payload
        )
        assert (
            first.runtime.receipt_registry.resolve(
                generator.receipt_sha256,
                "production chemical generator receipt",
            )
            == generator.receipt_payload
        )
        for column in range(3):
            assert sum(
                (
                    entry.value
                    for entry in generator.entries
                    if entry.column == column
                ),
                Fraction(0),
            ) == 0

    second = evolve_story_chemistry_event(
        runtime=first.runtime,
        event=_five_sense_event(
            runtime=first.runtime,
            event_id="production-five-sense-frame-2",
            start=Fraction(1),
            end=Fraction(2),
            fluxes=fluxes,
        ),
    )
    assert second.status is StoryChemistryStatus.EVOLVED
    bridged = build_story_frozen_kernel_inputs(
        runtime=second.runtime,
        output_frames=(first.outputs, second.outputs),
        source_epoch="production-five-sense-conformance-epoch",
    )

    assert bridged.status is StoryKernelBridgeStatus.READY
    assert len(bridged.streams) == 5
    assert len(bridged.kernel_inputs) == 5
    assert tuple(stream.lane_id for stream in bridged.streams) == tuple(
        lane_id for _, lane_id in PRODUCTION_STORY_PORT_LANES
    )
    for stream, kernel_input, flux in zip(
        bridged.streams,
        bridged.kernel_inputs,
        fluxes,
        strict=True,
    ):
        assert tuple(sample.signal for sample in stream.samples) == (flux, flux)
        assert tuple(
            sample.dimensionless_field for sample in kernel_input.samples
        ) == (Fraction(1) + flux / 2, Fraction(1) + flux / 2)
        assert tuple(sample.l0_relevance for sample in kernel_input.samples) == tuple(
            sample.relevance for sample in stream.samples
        )


def test_production_checkpoint_restart_is_bit_exact_and_continues_identically():
    mounted = _mount()
    assert mounted.runtime is not None
    first_fluxes = (
        Fraction(1, 5),
        Fraction(-2, 5),
        Fraction(3, 5),
        Fraction(-4, 5),
        Fraction(1),
    )
    first = evolve_story_chemistry_event(
        runtime=mounted.runtime,
        event=_five_sense_event(
            runtime=mounted.runtime,
            event_id="production-restart-frame-1",
            start=Fraction(0),
            end=Fraction(1),
            fluxes=first_fluxes,
        ),
    )
    assert first.status is StoryChemistryStatus.EVOLVED
    checkpoint = story_chemistry_checkpoint_payload(
        runtime=first.runtime,
        checkpoint_id="production-five-sense-checkpoint-1",
        authentication_key=CHECKPOINT_KEY,
        key_id=CHECKPOINT_KEY_ID,
    )
    manifest_envelope = authenticate_production_story_chemistry_profile(
        profile_body_payload=production_story_chemistry_profile_payload(),
        runtime_authentication_key=RUNTIME_KEY,
        runtime_key_id=RUNTIME_KEY_ID,
    )
    restored = restore_story_chemistry(
        manifest_envelope_payload=manifest_envelope,
        manifest_authentication_key=RUNTIME_KEY,
        manifest_expected_key_id=RUNTIME_KEY_ID,
        checkpoint_envelope_payload=checkpoint,
        checkpoint_authentication_key=CHECKPOINT_KEY,
        checkpoint_expected_key_id=CHECKPOINT_KEY_ID,
    )

    assert restored.status is StoryChemistryStatus.MOUNTED
    assert restored.runtime is not None
    assert restored.runtime.states == first.runtime.states
    assert restored.runtime.receipt_registry == first.runtime.receipt_registry

    second_fluxes = (
        Fraction(-1, 7),
        Fraction(2, 7),
        Fraction(-3, 7),
        Fraction(4, 7),
        Fraction(-5, 7),
    )
    continuation_event = _five_sense_event(
        runtime=first.runtime,
        event_id="production-restart-frame-2",
        start=Fraction(1),
        end=Fraction(2),
        fluxes=second_fluxes,
    )
    uninterrupted = evolve_story_chemistry_event(
        runtime=first.runtime,
        event=continuation_event,
    )
    restarted = evolve_story_chemistry_event(
        runtime=restored.runtime,
        event=continuation_event,
    )

    assert uninterrupted.status is StoryChemistryStatus.EVOLVED
    assert restarted.status is StoryChemistryStatus.EVOLVED
    assert restarted.outputs == uninterrupted.outputs
    assert restarted.runtime.states == uninterrupted.runtime.states
    assert (
        restarted.runtime.receipt_registry
        == uninterrupted.runtime.receipt_registry
    )
