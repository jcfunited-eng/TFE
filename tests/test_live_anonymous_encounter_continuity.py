import hashlib
import json
from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.live_anonymous_encounter_continuity import (
    LiveAnonymousEncounterContinuityAuthority,
    MAX_LIVE_ANONYMOUS_ENCOUNTER_STATE_BYTES,
)
from dsf_ai_service.substrate.visual_region_continuity import (
    CanonicalVisualFrame,
    DeterministicVisualRegionContinuityAuthority,
)


KEY = b"live-anonymous-encounter-test-key"


def _canonical(value):
    return json.dumps(
        value, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _frames(*, split=False, source_base_seconds=0):
    result = []
    for index in range(4):
        pixels = np.full((64, 64), 20 + index * 10, dtype=np.uint8)
        if split:
            pixels[:, 32:] = 180 - index * 10
        result.append(
            CanonicalVisualFrame.from_uint8(
                (source_base_seconds + index + 1) * 1_000_000_000,
                pixels,
            )
        )
    return tuple(result)


def _visual(authority, assembly_id, *, split=False, window_index=0):
    source_start = window_index * 5
    prepared = authority.prepare_retinotopic_inputs(_frames(
        split=split,
        source_base_seconds=source_start,
    ))
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SIGHT
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    built = build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=Fraction(source_start),
        source_time_end=Fraction(source_start + 5),
        observed_substreams={PhysicalSense.SIGHT: prepared.substreams},
        states=states,
    )
    visual = authority.settle_l5(built.boundary, built.receipt_registry)
    causal = ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )
    return visual, causal, built


def _auditory(
    assembly_id,
    causal,
    *,
    sequence=0,
    prior=None,
    stream_id="browser-microphone-epoch",
):
    transport_receipt = hashlib.sha256(
        f"transport-{assembly_id}-{sequence}".encode()
    ).hexdigest()
    cochlear_receipt = hashlib.sha256(
        f"cochlear-{assembly_id}-{sequence}".encode()
    ).hexdigest()
    provisional = AuditoryStreamSettlementReceipt(
        stream_id=stream_id,
        sequence=sequence,
        first_sample_index=sequence * 80_000,
        sample_count=80_000,
        source_time_start=Fraction(sequence * 5),
        source_time_end=Fraction((sequence + 1) * 5),
        assembly_id=assembly_id,
        transport_receipt_sha256=transport_receipt,
        prior_transport_receipt_sha256=(
            prior.transport_receipt_sha256 if prior is not None else None
        ),
        cochlear_receipt_sha256=cochlear_receipt,
        prior_cochlear_state_receipt_sha256=(
            prior.cochlear_receipt_sha256 if prior is not None else None
        ),
        auditory_l5_authority_receipt_sha256="3" * 64,
        causal_settlement_authority_receipt_sha256=(
            causal.authority_receipt_sha256
        ),
        authority_receipt_sha256="0" * 64,
    )
    return AuditoryStreamSettlementReceipt(
        **{
            **{
                field: getattr(provisional, field)
                for field in provisional.__dataclass_fields__
                if field != "authority_receipt_sha256"
            },
            "authority_receipt_sha256": hashlib.sha256(
                _canonical(provisional.payload())
            ).hexdigest(),
        }
    )


def test_encounter_is_unknown_then_unique_without_claiming_sound_source():
    visual_owner = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY
    )
    owner = LiveAnonymousEncounterContinuityAuthority(
        authority_key=KEY, visual_authority=visual_owner
    )
    first_visual, first_causal, _ = _visual(
        visual_owner, "encounter-first"
    )
    first_auditory = _auditory("encounter-first", first_causal)
    first = owner.observe(
        visual=first_visual,
        auditory=first_auditory,
        causal_settlement=first_causal,
    )
    assert first.state == "unknown"
    assert first.acoustic_source == "unknown"
    assert owner.clear_stream("another-stream") is False
    assert owner.status()["active"] is True

    second_visual, second_causal, _ = _visual(
        visual_owner, "encounter-second", window_index=1
    )
    second = owner.observe(
        visual=second_visual,
        auditory=_auditory(
            "encounter-second",
            second_causal,
            sequence=1,
            prior=first_auditory,
        ),
        causal_settlement=second_causal,
    )
    assert second.state == "unique"
    assert second.continuing_visual_lineage_receipt_sha256 is not None
    assert second.acoustic_source == "unknown"
    assert owner.status()["source_attribution"].startswith("unavailable")


def test_multiple_continuing_regions_remain_ambiguous():
    visual_owner = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY
    )
    owner = LiveAnonymousEncounterContinuityAuthority(
        authority_key=KEY, visual_authority=visual_owner
    )
    first_visual, first_causal, _ = _visual(
        visual_owner, "split-first", split=True
    )
    first_auditory = _auditory("split-first", first_causal)
    owner.observe(
        visual=first_visual,
        auditory=first_auditory,
        causal_settlement=first_causal,
    )
    second_visual, second_causal, _ = _visual(
        visual_owner, "split-second", split=True, window_index=1
    )
    observed = owner.observe(
        visual=second_visual,
        auditory=_auditory(
            "split-second",
            second_causal,
            sequence=1,
            prior=first_auditory,
        ),
        causal_settlement=second_causal,
    )
    assert observed.state == "ambiguous"
    assert len(observed.candidate_visual_lineage_receipt_sha256s) == 2
    assert observed.continuing_visual_lineage_receipt_sha256 is None


def test_crossed_assemblies_and_tampering_fail_closed():
    visual_owner = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY
    )
    owner = LiveAnonymousEncounterContinuityAuthority(
        authority_key=KEY, visual_authority=visual_owner
    )
    before = owner.snapshot_encoded()
    visual, causal, built = _visual(visual_owner, "visual-assembly")
    with pytest.raises(ValueError, match="crossed causal assemblies"):
        owner.observe(
            visual=visual,
            auditory=_auditory("auditory-assembly", causal),
            causal_settlement=causal,
        )
    assert owner.snapshot_encoded() == before

    crossed_causal = ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=("different-causal-authority",),
    )
    with pytest.raises(ValueError, match="crossed causal receipt authorities"):
        owner.observe(
            visual=visual,
            auditory=_auditory("visual-assembly", crossed_causal),
            causal_settlement=causal,
        )
    assert owner.snapshot_encoded() == before

    altered = bytearray(before)
    altered[len(altered) // 2] ^= 1
    with pytest.raises(ValueError):
        owner.restore_encoded(bytes(altered))
    assert owner.snapshot_encoded() == before


def test_gap_and_new_stream_rebase_before_continuity_can_resume():
    visual_owner = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY
    )
    owner = LiveAnonymousEncounterContinuityAuthority(
        authority_key=KEY, visual_authority=visual_owner
    )
    first_visual, first_causal, _ = _visual(visual_owner, "gap-first")
    first_auditory = _auditory("gap-first", first_causal)
    owner.observe(
        visual=first_visual,
        auditory=first_auditory,
        causal_settlement=first_causal,
    )
    assert owner.clear_stream(first_auditory.stream_id) is True

    restart_visual, restart_causal, _ = _visual(
        visual_owner, "gap-restart"
    )
    restart_auditory = _auditory(
        "gap-restart",
        restart_causal,
        stream_id="new-microphone-epoch",
    )
    restarted = owner.observe(
        visual=restart_visual,
        auditory=restart_auditory,
        causal_settlement=restart_causal,
    )
    assert restarted.state == "unknown"
    assert restarted.reason == "no_prior_adjacent_audiovisual_encounter"

    next_visual, next_causal, _ = _visual(
        visual_owner, "gap-next", window_index=1
    )
    resumed = owner.observe(
        visual=next_visual,
        auditory=_auditory(
            "gap-next",
            next_causal,
            sequence=1,
            prior=restart_auditory,
            stream_id="new-microphone-epoch",
        ),
        causal_settlement=next_causal,
    )
    assert resumed.state == "unique"

    third_visual, third_causal, _ = _visual(
        visual_owner, "unclosed-new-stream"
    )
    rebased = owner.observe(
        visual=third_visual,
        auditory=_auditory(
            "unclosed-new-stream",
            third_causal,
            stream_id="third-microphone-epoch",
        ),
        causal_settlement=third_causal,
    )
    assert rebased.state == "unknown"
    assert rebased.prior_encounter_authority_receipt_sha256 is None


def test_camera_only_lineages_cannot_enter_an_adjacent_paired_encounter():
    visual_owner = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY
    )
    owner = LiveAnonymousEncounterContinuityAuthority(
        authority_key=KEY, visual_authority=visual_owner
    )
    first_visual, first_causal, _ = _visual(
        visual_owner, "paired-before-camera-only"
    )
    first_auditory = _auditory(
        "paired-before-camera-only", first_causal
    )
    first = owner.observe(
        visual=first_visual,
        auditory=first_auditory,
        causal_settlement=first_causal,
    )
    assert len(first.current_visual_lineage_receipt_sha256s) == 1

    _visual(
        visual_owner,
        "camera-only-intervening",
        split=True,
        window_index=1,
    )
    paired_visual, paired_causal, _ = _visual(
        visual_owner,
        "paired-after-camera-only",
        split=True,
        window_index=1,
    )
    observed = owner.observe(
        visual=paired_visual,
        auditory=_auditory(
            "paired-after-camera-only",
            paired_causal,
            sequence=1,
            prior=first_auditory,
        ),
        causal_settlement=paired_causal,
    )
    assert observed.state == "unknown"
    assert observed.reason == "no_continuing_visual_lineage"
    assert observed.candidate_visual_lineage_receipt_sha256s == ()


def test_persistence_is_capacity_one_and_inactive_after_restart():
    visual_owner = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY
    )
    owner = LiveAnonymousEncounterContinuityAuthority(
        authority_key=KEY, visual_authority=visual_owner
    )
    visual, causal, _ = _visual(visual_owner, "persist-first")
    owner.observe(
        visual=visual,
        auditory=_auditory("persist-first", causal),
        causal_settlement=causal,
    )
    encoded = owner.snapshot_encoded()
    assert len(encoded) < MAX_LIVE_ANONYMOUS_ENCOUNTER_STATE_BYTES

    restored_visual = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY
    )
    restored = LiveAnonymousEncounterContinuityAuthority(
        authority_key=KEY, visual_authority=restored_visual
    )
    restored.restore_encoded(encoded)
    assert restored.status()["active"] is False
    assert restored.status()["state"] == "unknown"
    restored_payload = json.loads(restored.snapshot_encoded())
    original_payload = json.loads(encoded)
    assert restored_payload["payload"]["live"] is False
    assert restored_payload["payload"]["latest"] == (
        original_payload["payload"]["latest"]
    )


def test_rollback_restores_the_prior_live_observation():
    visual_owner = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY
    )
    owner = LiveAnonymousEncounterContinuityAuthority(
        authority_key=KEY, visual_authority=visual_owner
    )
    first_visual, first_causal, _ = _visual(
        visual_owner, "rollback-first"
    )
    first_auditory = _auditory("rollback-first", first_causal)
    first = owner.observe(
        visual=first_visual,
        auditory=first_auditory,
        causal_settlement=first_causal,
    )
    snapshot = owner.snapshot_encoded()
    second_visual, second_causal, _ = _visual(
        visual_owner, "rollback-second", window_index=1
    )
    owner.observe(
        visual=second_visual,
        auditory=_auditory(
            "rollback-second",
            second_causal,
            sequence=1,
            prior=first_auditory,
        ),
        causal_settlement=second_causal,
    )
    owner.rollback_encoded(snapshot)
    assert owner.status()["latest"] == first.as_record()

    persisted = owner.snapshot_encoded()
    owner.restore_encoded(persisted)
    inactive = owner.snapshot_encoded()
    third_visual, third_causal, _ = _visual(
        visual_owner, "rollback-third"
    )
    owner.observe(
        visual=third_visual,
        auditory=_auditory("rollback-third", third_causal),
        causal_settlement=third_causal,
    )
    owner.rollback_encoded(inactive)
    assert owner.status()["active"] is False


def test_repeated_observation_retains_only_one_bounded_receipt_record():
    visual_owner = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY
    )
    owner = LiveAnonymousEncounterContinuityAuthority(
        authority_key=KEY, visual_authority=visual_owner
    )
    visual, causal, _ = _visual(visual_owner, "bounded-current")
    auditory = _auditory("bounded-current", causal)
    for _ in range(1_000):
        owner.observe(
            visual=visual,
            auditory=auditory,
            causal_settlement=causal,
        )
    encoded = owner.snapshot_encoded()
    assert len(encoded) < MAX_LIVE_ANONYMOUS_ENCOUNTER_STATE_BYTES
    assert owner.status()["state_bytes"] == len(encoded)
    assert b"pcm" not in encoded.lower()
    assert b"pixels" not in encoded.lower()
