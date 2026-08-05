"""Diagnose exact identity and Allen-relation L6 locks on five recordings."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import numpy as np

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_live_motif import (
    AUDITORY_LIVE_MOTIF_STATE_ALLOCATION_BYTES,
    build_live_motif_result,
)
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorEventState,
    settle_auditory_receptor_event,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
    receptor_experience_from_full_field_event,
)
from dsf_ai_service.substrate.auditory_temporal_relation_assembly import (
    AuditoryTemporalAssemblyProfile,
    AuditoryTemporalRelationAssemblyOwner,
    _has_relation,
    _run_collapsed_events,
)
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from tools.probe_auditory_full_field_discrimination import _decode_pcm


QUERY = Path("harness/Hello Guala.mp3")
POSITIVES = (
    Path("harness/hello guala 1.mp3"),
    Path("harness/hello guala 2.mp3"),
)
CONTRASTS = (
    Path("docs/Daddy says Hello.mp3"),
    Path("docs/Your Name is Guala.mp3"),
)


def _experience(path: Path, ordinal: int):
    pcm = _decode_pcm(path)
    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32768.0
    capture = transduce_auditory_full_field(
        samples,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    anchor = Fraction(10_000 + ordinal * 100)
    components = auditory_kernel_component_inputs(
        capture,
        source_anchor=anchor,
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"current-real-temporal-recurrence-{ordinal}",
        source_time_start=anchor,
        source_time_end=anchor + Fraction(
            len(samples),
            REQUIRED_SAMPLE_RATE_HZ,
        ),
        observed_substreams={PhysicalSense.SOUND: components},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    l5 = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="utterance")
    boundary = settle_auditory_receptor_event(
        capture=capture,
        auditory_l5=l5,
    )
    if (
        boundary.state is not AuditoryReceptorEventState.OBSERVED
        or boundary.event is None
    ):
        raise RuntimeError(f"receptor boundary failed: {path}")
    return receptor_experience_from_full_field_event(boundary.event)


def _motif_owner() -> AuditoryRecurrentMotifOwner:
    return AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="current-real-form-separation-walkup",
            ear_count=1,
            max_motif_neurons=12_096,
            max_pending_experiences=8,
            max_work_cells_per_observation=4_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=(
                AUDITORY_LIVE_MOTIF_STATE_ALLOCATION_BYTES
            ),
        )
    )


def _temporal_owner() -> AuditoryTemporalRelationAssemblyOwner:
    return AuditoryTemporalRelationAssemblyOwner(
        profile=AuditoryTemporalAssemblyProfile.create(
            profile_id="current-real-form-separation-temporal-walkup",
            max_exposures=8,
            max_events_per_exposure=32_768,
            max_assemblies=2,
            max_relations_per_assembly=1_048_576,
            max_state_bytes=128 * 1024 * 1024,
        ),
        authority_key=b"current-real-temporal-form-walkup-key-v1",
    )


def _relation_direction(assembly, live):
    events = _run_collapsed_events(live.as_record()["activation_spans"])
    by_identity = {}
    for event in events:
        by_identity.setdefault(event.identity, []).append(event)
    mounted = {
        identity: tuple(values)
        for identity, values in by_identity.items()
    }
    matching = sum(
        _has_relation(relation, mounted)
        for relation in assembly.relations
    )
    return canonical_l6_direction(
        dimensions=len(assembly.relations),
        matching_non_null=matching,
        matching_quiescent=0,
    )


def main() -> None:
    paths = (*POSITIVES, *CONTRASTS, QUERY)
    executor = start_exact_field_executor()
    executor.assert_healthy()
    try:
        experiences = tuple(
            _experience(path, ordinal)
            for ordinal, path in enumerate(paths)
        )
    finally:
        stop_exact_field_executor()
    motif = _motif_owner()
    first = motif.observe(experiences[0])
    second = motif.observe(experiences[1])
    temporal = _temporal_owner()
    exposure_receipts = []
    for experience in experiences[:4]:
        firing = motif.fire(experience)
        live = build_live_motif_result(
            experience=experience,
            firing=firing,
            observation=None,
            learning_state="not_attempted_fixed_bank",
            learning_reason="fixed recurrent bank temporal walk-up",
        )
        exposure = temporal.observe_typed(
            live,
            source_component_receipt_sha256s=(
                *experience.source_event_receipt_sha256s,
            ),
        )
        exposure_receipts.append(exposure.exposure_receipt_sha256)
    assembly = temporal.learn_acoustic_contrast(
        positive_exposure_receipt_sha256s=tuple(exposure_receipts[:2]),
        contrast_exposure_receipt_sha256s=tuple(exposure_receipts[2:]),
    )
    print({
        "first_new": len(first.newly_grown_motif_neuron_ids),
        "second_new": len(second.newly_grown_motif_neuron_ids),
        "assembly": assembly is not None,
        "required_event_identities": (
            0 if assembly is None else len(assembly.required_event_identities)
        ),
        "relations": 0 if assembly is None else len(assembly.relations),
    })
    if assembly is None:
        return
    for role, path, experience in zip(
        ("positive", "positive", "contrast", "contrast", "query"),
        paths,
        experiences,
        strict=True,
    ):
        firing = motif.fire(experience)
        live = build_live_motif_result(
            experience=experience,
            firing=firing,
            observation=None,
            learning_state="not_attempted_query",
            learning_reason="held fixed for temporal firing",
        )
        identity_result = temporal.fire(live.as_record())
        identity_direction = next(
            value
            for value in identity_result.l6_directions
            if value["assembly_id"] == assembly.assembly_id
        )
        relation_direction = _relation_direction(assembly, live)
        print({
            "role": role,
            "recording": path.name,
            "combined_lock": (
                identity_direction["locked"]
                and relation_direction.locked
            ),
            "identity_lock": identity_direction["locked"],
            "identity_matching": (
                identity_direction["matching_non_null"]
            ),
            "identity_dimensions": identity_direction["dimensions"],
            "relation_lock": relation_direction.locked,
            "relation_matching": relation_direction.matching_non_null,
            "relation_dimensions": relation_direction.dimensions,
        })


if __name__ == "__main__":
    main()
