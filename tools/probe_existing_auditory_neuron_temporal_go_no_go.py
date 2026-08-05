"""Bounded go/no-go test of Guala's existing auditory learning machinery.

This probe does not invent another auditory identity or quotient.  It uses the
existing production-shaped path:

    authenticated physical PCM
      -> W1 two-ear propagation
      -> unchanged full-field L0--L4
      -> verified receptor settlement
      -> existing exact peak-relation motif neurons
      -> existing temporal relation assemblies
      -> canonical L6 firing

The first two source-disjoint speakers per command grow the shared motif bank.
The next three source-disjoint speakers per command form acoustic temporal
assemblies with every other tested command as explicit contrast.  A sixth,
previously unheard speaker is then fired without learning.  Corpus command
labels only group completed physical exposures for the tutor/contrast step;
they never enter receptor construction, motif construction, or query firing.

This is intentionally a small walk-up test over three commands.  It expands
only if unheard-speaker recall succeeds.  A failure establishes that the
currently implemented adaptive auditory path does not yet generalize at this
boundary; it does not authorize another score, tolerance, or classifier.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import wave
import zipfile
from pathlib import Path
from typing import Mapping

from dsf_ai_service.substrate.auditory_live_motif import (
    build_live_motif_result,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.auditory_temporal_relation_assembly import (
    AuditoryTemporalAssemblyProfile,
    AuditoryTemporalRelationAssemblyOwner,
    TemporalAssemblyFiringState,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    COMMANDS,
    CorpusItem,
    _select_corpus,
)

# These helpers mount the real W1 production authorities.  They supply no
# recognition, label, quotient, or expected outcome.
from tests.test_w1_audiovisual_physical_evidence import (
    _authority,
    _emission,
    _vocal_execution,
    _world,
)


SCHEMA = "guala.audit.existing_auditory_neuron_temporal_go_no_go.v1"
TEST_COMMANDS = COMMANDS[:3]
PRETRAIN_SPEAKERS_PER_COMMAND = 2
ASSEMBLY_SPEAKERS_PER_COMMAND = 3
HELD_OUT_SPEAKERS_PER_COMMAND = 1
AUTHORITY_KEY = b"guala-existing-auditory-neuron-go-no-go-20260727"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _read_pcm(data: bytes) -> bytes:
    with wave.open(io.BytesIO(data), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != REQUIRED_SAMPLE_RATE_HZ
            or source.getcomptype() != "NONE"
        ):
            raise ValueError("speech corpus PCM authority changed")
        result = source.readframes(source.getnframes())
    if len(result) < 320 or len(result) % 2:
        raise ValueError("speech corpus PCM interval changed")
    return result


def _selected(
    items: tuple[CorpusItem, ...],
) -> tuple[
    tuple[CorpusItem, ...],
    tuple[CorpusItem, ...],
    tuple[CorpusItem, ...],
]:
    pretrain = []
    assemblies = []
    held_out = []
    for command in TEST_COMMANDS:
        references = tuple(
            item for item in items
            if (
                item.oracle_command == command
                and item.split == "reference"
            )
        )
        queries = tuple(
            item for item in items
            if (
                item.oracle_command == command
                and item.split == "held_out"
            )
        )
        if len(references) < 5 or not queries:
            raise ValueError("go/no-go corpus partition changed")
        pretrain.extend(references[:PRETRAIN_SPEAKERS_PER_COMMAND])
        assemblies.extend(
            references[
                PRETRAIN_SPEAKERS_PER_COMMAND:
                PRETRAIN_SPEAKERS_PER_COMMAND
                + ASSEMBLY_SPEAKERS_PER_COMMAND
            ]
        )
        held_out.extend(queries[:HELD_OUT_SPEAKERS_PER_COMMAND])
    selected = (*pretrain, *assemblies, *held_out)
    if len({value.speaker_id for value in selected}) != len(selected):
        raise ValueError("go/no-go sources are not globally disjoint")
    return tuple(pretrain), tuple(assemblies), tuple(held_out)


def _motif_owner() -> AuditoryRecurrentMotifOwner:
    return AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="existing-auditory-neuron-go-no-go",
            ear_count=1,
            max_motif_neurons=12_096,
            max_pending_experiences=8,
            max_work_cells_per_observation=4_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        )
    )


def _temporal_owner() -> AuditoryTemporalRelationAssemblyOwner:
    return AuditoryTemporalRelationAssemblyOwner(
        profile=AuditoryTemporalAssemblyProfile.create(
            profile_id="existing-auditory-temporal-go-no-go",
            max_exposures=32,
            max_events_per_exposure=32_768,
            max_assemblies=8,
            max_relations_per_assembly=1_048_576,
            max_state_bytes=128 * 1024 * 1024,
        ),
        authority_key=AUTHORITY_KEY,
    )


def _mounts(
    ordered_items: tuple[CorpusItem, ...],
    pcm_by_item: Mapping[str, bytes],
):
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    source_sample_start = 0
    results = {}
    for sequence, item in enumerate(ordered_items):
        pcm = pcm_by_item[item.item_id]
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
        mount.verify(
            b"evidence-authority-key-for-w1-tests"
        )
        if mount.binaural_receptor_settlement is None:
            raise ValueError("W1 receptor settlement is unavailable")
        results[item.item_id] = mount
        source_sample_start += len(pcm) // 2
    return results


def run_go_no_go(archive_path: Path) -> dict[str, object]:
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("speech corpus archive authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        all_items = _select_corpus(archive)
        pretrain, assembly_items, held_out = _selected(all_items)
        ordered = (*pretrain, *assembly_items, *held_out)
        pcm_by_item = {
            item.item_id: _read_pcm(archive.read(item.archive_member))
            for item in ordered
        }
    mounts = _mounts(tuple(ordered), pcm_by_item)
    motif_owner = _motif_owner()
    temporal_owner = _temporal_owner()
    pretrain_records = []
    for item in pretrain:
        experience = mounts[
            item.item_id
        ].binaural_receptor_settlement.ears[0].experience
        observation = motif_owner.observe(experience)
        pretrain_records.append({
            "item_id": item.item_id,
            "newly_grown_count": len(
                observation.newly_grown_motif_neuron_ids
            ),
            "reinforced_count": len(
                observation.reinforced_motif_neuron_ids
            ),
            "state": observation.state.value,
        })
    exposure_receipts: dict[str, list[str]] = {
        command: [] for command in TEST_COMMANDS
    }
    exposure_records = []
    for item in assembly_items:
        settlement = mounts[
            item.item_id
        ].binaural_receptor_settlement
        experience = settlement.ears[0].experience
        firing = motif_owner.fire(experience)
        observation = motif_owner.observe(experience)
        live = build_live_motif_result(
            experience=experience,
            firing=firing,
            observation=observation,
        )
        exposure = temporal_owner.observe_typed(
            live,
            source_component_receipt_sha256s=(
                *experience.source_event_receipt_sha256s,
            ),
        )
        exposure_receipts[item.oracle_command].append(
            exposure.exposure_receipt_sha256
        )
        exposure_records.append({
            "activation_count": len(live.activation_spans),
            "event_count": len(exposure.events),
            "firing_motif_count": len(
                live.firing_motif_neuron_ids
            ),
            "item_id": item.item_id,
            "learning_firing_motif_count": len(
                live.learning_firing_motif_neuron_ids
            ),
            "newly_grown_count": len(
                live.newly_grown_motif_neuron_ids
            ),
        })
    assemblies = {}
    for command in TEST_COMMANDS:
        positives = tuple(exposure_receipts[command])
        contrasts = tuple(
            receipt
            for other in TEST_COMMANDS
            if other != command
            for receipt in exposure_receipts[other]
        )
        assembly = temporal_owner.learn_acoustic_contrast(
            positive_exposure_receipt_sha256s=positives,
            contrast_exposure_receipt_sha256s=contrasts,
        )
        assemblies[command] = assembly
    assembly_records = {
        command: (
            None
            if assembly is None
            else {
                "assembly_id": assembly.assembly_id,
                "relation_count": len(assembly.relations),
                "required_event_identity_count": len(
                    assembly.required_event_identities
                ),
            }
        )
        for command, assembly in assemblies.items()
    }
    assembly_to_command = {
        assembly.assembly_id: command
        for command, assembly in assemblies.items()
        if assembly is not None
    }
    query_records = []
    pass_count = 0
    for item in held_out:
        experience = mounts[
            item.item_id
        ].binaural_receptor_settlement.ears[0].experience
        firing = motif_owner.fire(experience)
        live = build_live_motif_result(
            experience=experience,
            firing=firing,
            observation=None,
            learning_state="not_attempted_held_out",
            learning_reason=(
                "held-out source fired without sensory learning"
            ),
        )
        temporal = temporal_owner.fire(live.as_record())
        resolved = tuple(
            assembly_to_command[value]
            for value in temporal.complete_assembly_ids
            if value in assembly_to_command
        )
        passed = (
            temporal.state is TemporalAssemblyFiringState.OBSERVED
            and resolved == (item.oracle_command,)
        )
        pass_count += int(passed)
        query_records.append({
            "activation_count": len(live.activation_spans),
            "expected_command": item.oracle_command,
            "firing_motif_count": len(
                live.firing_motif_neuron_ids
            ),
            "item_id": item.item_id,
            "passed": passed,
            "resolved_commands": list(resolved),
            "temporal_state": temporal.state.value,
        })
    result = {
        "archive_sha256": ARCHIVE_SHA256,
        "assembly_records": assembly_records,
        "assembly_speaker_count_per_command": (
            ASSEMBLY_SPEAKERS_PER_COMMAND
        ),
        "commands": list(TEST_COMMANDS),
        "exposure_records": exposure_records,
        "full_field_authority_retained": True,
        "held_out_pass_count": pass_count,
        "held_out_records": query_records,
        "held_out_total": len(held_out),
        "labels_used_before_tutor_grouping": False,
        "l0_l4_modified": False,
        "motif_owner_status": motif_owner.status(),
        "pretrain_records": pretrain_records,
        "pretrain_speaker_count_per_command": (
            PRETRAIN_SPEAKERS_PER_COMMAND
        ),
        "production_modified": False,
        "schema": SCHEMA,
        "source_disjoint_speaker_count": len(ordered),
        "temporal_owner_status": temporal_owner.status(),
        "walk_up_advance_allowed": pass_count == len(held_out),
    }
    return result | {
        "authority_receipt_sha256": _digest(result),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_go_no_go(args.archive)
    if args.output is not None:
        args.output.write_bytes(
            json.dumps(
                report,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            ).encode("utf-8") + b"\n"
        )
    print(json.dumps(
        report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
