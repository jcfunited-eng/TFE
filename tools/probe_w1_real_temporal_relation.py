"""Repeat the real temporal relation diagnostic through physical W1 mounting."""

from __future__ import annotations

from dsf_ai_service.substrate.auditory_live_motif import (
    build_live_motif_result,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
)
from tools.probe_auditory_full_field_discrimination import _decode_pcm
from tools.probe_real_recurrent_motif_form_separation import (
    CONTRASTS,
    POSITIVES,
    QUERY,
    _motif_owner,
    _relation_direction,
    _temporal_owner,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    _authority,
    _emission,
    _vocal_execution,
    _world,
)


def _hop_closed_pcm(path) -> bytes:
    pcm = _decode_pcm(path)
    sample_count = len(pcm) // 2
    closed_count = (
        sample_count // OBSERVATION_HOP_SAMPLES
        * OBSERVATION_HOP_SAMPLES
    )
    if closed_count < 2 * OBSERVATION_HOP_SAMPLES:
        raise ValueError("W1 diagnostic recording is too short")
    return pcm[:closed_count * 2]


def _experiences(paths):
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    source_sample_start = 0
    results = []
    for sequence, path in enumerate(paths):
        pcm = _hop_closed_pcm(path)
        execution = _vocal_execution(
            world,
            epoch,
            sequence=sequence,
            source_sample_start=source_sample_start,
            pcm=pcm,
        )
        emission = _emission(
            authority,
            epoch,
            execution,
            sequence=sequence,
            source_sample_start=source_sample_start,
            pcm=pcm,
        )
        mount = authority.mount(
            epoch_token=epoch,
            sequence=sequence,
            execution_receipt=execution,
            acoustic_emission=emission,
        )
        mount.verify(EVIDENCE_KEY)
        if mount.binaural_receptor_settlement is None:
            raise RuntimeError("W1 receptor settlement is unavailable")
        results.append(
            mount.binaural_receptor_settlement.ears[0].experience
        )
        source_sample_start += len(pcm) // 2
    return tuple(results)


def main() -> None:
    paths = (*POSITIVES, *CONTRASTS, QUERY)
    experiences = _experiences(paths)
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
            learning_reason="fixed recurrent bank W1 temporal walk-up",
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
            learning_reason="held fixed for W1 temporal firing",
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
