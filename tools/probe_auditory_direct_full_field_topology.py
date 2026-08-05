"""Frozen 51-capture falsification of direct full-field change topology."""

from __future__ import annotations

import hashlib
import json
import sys
import wave
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from tests.test_lived_vocal_teaching_episode import _external_mount
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    _authority as _physical_authority,
)
from tools.isolated_auditory_direct_full_field_topology import (
    MAX_ENCODED_BYTES,
    DirectFullFieldTopology,
    topology_from_events,
)
from tools.probe_auditory_thing_local_familiarity import (
    AUTHORITY_KEY,
    OBJECT_IDS,
    _custody,
    _execute,
    _world,
)
from tools.probe_vtvr_causal_thing_familiarity import (
    ARCHIVE_PATH,
    ARCHIVE_SHA256,
    _archive_sha256,
)


SCHEMA = "guala.audit.auditory_direct_full_field_topology_preflight.v1"
PLAN_PATH = Path(
    "tests/fixtures/auditory_direct_full_field_topology_plan_v1.json"
)
PLAN_SHA256 = (
    "3ea2d10462d4aca14956c287ffe9d75fea26495a447548159c8cb94cd48d984a"
)
MAX_MEMORY_TOPOLOGIES = 48
MAX_REPORT_BYTES = 16 * 1024 * 1024


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


@dataclass(frozen=True, slots=True)
class FrozenItem:
    word: str
    archive_member: str
    speaker_id: str
    wav_sha256: str
    pcm_s16le: bytes


def _load_frozen_inputs() -> tuple[
    dict[str, object],
    dict[str, tuple[FrozenItem, ...]],
]:
    plan_bytes = PLAN_PATH.read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != PLAN_SHA256:
        raise RuntimeError("direct topology plan changed after freeze")
    plan = json.loads(plan_bytes)
    for path_key, digest_key in (
        ("adapter_path", "adapter_sha256"),
        ("corpus_manifest_path", "corpus_manifest_sha256"),
    ):
        source = Path(str(plan[path_key]))
        if hashlib.sha256(source.read_bytes()).hexdigest() != plan[digest_key]:
            raise RuntimeError(f"{source} changed after plan freeze")
    if (
        _archive_sha256(ARCHIVE_PATH) != ARCHIVE_SHA256
        or ARCHIVE_SHA256 != plan["archive_sha256"]
    ):
        raise RuntimeError("speech archive authority changed")
    manifest = json.loads(
        Path(str(plan["corpus_manifest_path"])).read_bytes()
    )
    words = tuple(str(value) for value in plan["words"])
    training_count = int(plan["training_per_thing"])
    held_out_count = int(plan["held_out_per_thing"])
    expected_count = training_count + held_out_count
    corpus: dict[str, tuple[FrozenItem, ...]] = {}
    used_speakers: set[str] = set()
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        for word in words:
            raw_items = manifest["words"][word]
            if len(raw_items) != expected_count:
                raise RuntimeError("frozen word member count changed")
            items = []
            for member, expected_sha in raw_items:
                filename = member.rsplit("/", 1)[-1]
                if "_nohash_" not in filename:
                    raise RuntimeError("frozen member lacks speaker authority")
                speaker = filename.split("_nohash_", 1)[0]
                if speaker in used_speakers:
                    raise RuntimeError("frozen corpus reused a speaker")
                wav_data = archive.read(member)
                if hashlib.sha256(wav_data).hexdigest() != expected_sha:
                    raise RuntimeError("frozen WAV authority changed")
                with wave.open(io.BytesIO(wav_data), "rb") as source:
                    if (
                        source.getnchannels() != 1
                        or source.getsampwidth() != 2
                        or source.getframerate() != 16_000
                        or source.getnframes() != 16_000
                        or source.getcomptype() != "NONE"
                    ):
                        raise RuntimeError("frozen WAV physical format changed")
                    pcm = source.readframes(source.getnframes())
                items.append(
                    FrozenItem(
                        word=word,
                        archive_member=member,
                        speaker_id=speaker,
                        wav_sha256=expected_sha,
                        pcm_s16le=pcm,
                    )
                )
                used_speakers.add(speaker)
            corpus[word] = tuple(items)
    if len(used_speakers) != plan["source_disjoint_speaker_count"]:
        raise RuntimeError("frozen source-disjoint count changed")
    return plan, corpus


def _topology_record(value: DirectFullFieldTopology) -> dict[str, object]:
    value.verify()
    return {
        "authority_receipt_sha256": value.authority_receipt_sha256,
        "change_mask_count": len(value.change_masks),
        "change_masks_hex": [
            f"{mask:016x}" for mask in value.change_masks
        ],
        "encoded_bytes": len(value.encoded()),
        "frame_count": value.frame_count,
        "full_field_witness_root_sha256": (
            value.full_field_witness_root_sha256
        ),
        "topology_root_sha256": value.topology_root_sha256,
    }


def run_probe() -> dict[str, object]:
    plan, corpus = _load_frozen_inputs()
    words = tuple(str(value) for value in plan["words"])
    training_count = int(plan["training_per_thing"])
    held_out_count = int(plan["held_out_per_thing"])
    planned_captures = int(plan["physical_capture_count"])
    object_ids = OBJECT_IDS[: len(words)]
    if len(object_ids) != len(words):
        raise RuntimeError("physical world lacks three THING objects")

    world = _world()
    physical = _physical_authority(world)
    sensory = EmbodimentSensoryOutcomeAuthority(
        authority_key=EVIDENCE_KEY
    )
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=AUTHORITY_KEY + b":direct-full-field-topology",
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    things = CausalThingMosaicOwner(
        authority_key=AUTHORITY_KEY + b":direct-full-field-topology",
        profile=CausalThingMosaicProfile.create(
            profile_id="auditory-direct-full-field-topology-v1",
            max_mosaics=len(words),
            max_partitions_per_mosaic=training_count + 1,
            max_roots_per_partition=256,
            max_routes=65_536,
            max_state_bytes=256 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    training: dict[str, list[DirectFullFieldTopology]] = {
        word: [] for word in words
    }
    held_out: dict[str, DirectFullFieldTopology] = {}
    thing_ids: dict[str, str] = {}
    action_ordinal = 60_000
    custody_ordinal = 60_000
    completed = 0

    for ordinal, (word, object_id) in enumerate(
        zip(words, object_ids, strict=True),
        start=1,
    ):
        approach_x = ordinal * 1_000
        if ordinal > 1:
            for waypoint in (
                PositionMM(1_000, 2_000, 0),
                PositionMM(approach_x, 2_000, 0),
                PositionMM(approach_x, 1_000, 0),
            ):
                action_ordinal += 1
                _execute(
                    world,
                    MoveCommand(PoseMM(waypoint, 0)),
                    causal_ordinal=action_ordinal,
                )
        action_ordinal += 1
        picked = _execute(
            world,
            PickCommand(object_id),
            causal_ordinal=action_ordinal,
        )
        custody_ordinal += 1
        custody = _custody(
            source_mount=physical.mount_action_outcome(picked),
            execution=picked,
            ordinal=custody_ordinal,
        )
        prior = partitions.partition_from_custody(
            custody_authority=custody,
            capability=custody.issue_child(THING_MOSAIC_CONSUMER_ID),
        )
        mosaic = things.admit(prior)
        for item in corpus[word][:training_count]:
            execution, mount = _external_mount(
                world,
                physical,
                item.pcm_s16le,
            )
            completed += 1
            custody_ordinal += 1
            custody = _custody(
                source_mount=mount,
                execution=execution,
                ordinal=custody_ordinal,
            )
            prior = partitions.partition_from_custody(
                custody_authority=custody,
                capability=custody.issue_child(
                    THING_MOSAIC_CONSUMER_ID
                ),
                prior=prior,
            )
            mosaic = things.admit(prior)
            settlement = mount.binaural_receptor_settlement
            if (
                settlement.upstream_causal_settlement_receipt_sha256
                != prior.settlement_receipt_sha256
            ):
                raise ValueError("topology training left THING custody")
            topology = topology_from_events(
                left=settlement.ears[0].event,
                right=settlement.ears[1].event,
            )
            if len(topology.encoded()) > MAX_ENCODED_BYTES:
                raise MemoryError("topology exceeded encoded byte bound")
            training[word].append(topology)
            if completed % 8 == 0:
                print(
                    f"physical training captures: {completed}/48",
                    file=sys.stderr,
                    flush=True,
                )
        thing_ids[word] = mosaic.thing_id
        if ordinal < len(words):
            action_ordinal += 1
            _execute(
                world,
                PlaceCommand(
                    object_id,
                    PositionMM(approach_x - 500, 1_000, 0),
                ),
                causal_ordinal=action_ordinal,
            )

    for word in words:
        item = corpus[word][training_count]
        _execution, mount = _external_mount(
            world,
            physical,
            item.pcm_s16le,
        )
        completed += 1
        settlement = mount.binaural_receptor_settlement
        held_out[word] = topology_from_events(
            left=settlement.ears[0].event,
            right=settlement.ears[1].event,
        )
        print(
            f"physical captures: {completed}/{planned_captures}",
            file=sys.stderr,
            flush=True,
        )

    if completed != planned_captures:
        raise RuntimeError("physical capture count differs from frozen plan")
    if sum(len(value) for value in training.values()) > MAX_MEMORY_TOPOLOGIES:
        raise MemoryError("topology memory count exceeded frozen bound")

    memories = {
        thing_ids[word]: frozenset(
            value.topology_key() for value in training[word]
        )
        for word in words
    }
    evaluations = []
    correct = 0
    for word in words:
        query = held_out[word]
        owners = tuple(
            thing_id
            for thing_id, topology_keys in sorted(memories.items())
            if query.topology_key() in topology_keys
        )
        passed = owners == (thing_ids[word],)
        correct += int(passed)
        evaluations.append(
            {
                "expected_thing_id": thing_ids[word],
                "locked_thing_ids": list(owners),
                "oracle_word": word,
                "passed": passed,
                "state": (
                    "resolved"
                    if len(owners) == 1
                    else "ambiguous"
                    if owners
                    else "unknown"
                ),
                "topology": _topology_record(query),
            }
        )
    full_gate = correct == len(words) * held_out_count
    payload = {
        "adapter_received_labels": False,
        "archive_sha256": ARCHIVE_SHA256,
        "claim_allowed": False,
        "correct": correct,
        "frozen_adapter_sha256": plan["adapter_sha256"],
        "frozen_corpus_manifest_sha256": (
            plan["corpus_manifest_sha256"]
        ),
        "frozen_plan_sha256": PLAN_SHA256,
        "full_gate_passed": full_gate,
        "held_out_count": len(words) * held_out_count,
        "held_out_evaluations": evaluations,
        "l0_l4_modified": False,
        "physical_capture_count": completed,
        "production_wiring_changed": False,
        "reduced_topology_relation": True,
        "relation_loss": (
            "D/M/R/U/C/P/B magnitudes and change durations are witnesses "
            "but not topology identity"
        ),
        "schema": SCHEMA,
        "source_disjoint_speaker_count": (
            plan["source_disjoint_speaker_count"]
        ),
        "training_records": {
            word: [
                {
                    "archive_member": item.archive_member,
                    "speaker_id": item.speaker_id,
                    "topology": _topology_record(topology),
                    "wav_sha256": item.wav_sha256,
                }
                for item, topology in zip(
                    corpus[word][:training_count],
                    training[word],
                    strict=True,
                )
            ]
            for word in words
        },
        "unique_training_topology_counts": {
            word: len(
                {value.topology_key() for value in training[word]}
            )
            for word in words
        },
    }
    result = payload | {
        "authority_receipt_sha256": _digest(payload),
    }
    if len(_canonical(result)) > MAX_REPORT_BYTES:
        raise MemoryError("topology report exceeded frozen byte bound")
    return result


def _invalid_report(exc: BaseException) -> dict[str, object]:
    payload = {
        "claim_allowed": False,
        "error": f"{type(exc).__name__}: {exc}",
        "full_gate_passed": False,
        "schema": SCHEMA,
        "state": "invalid_authority_or_resource",
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


def main() -> int:
    try:
        report = run_probe()
    except (MemoryError, RuntimeError, TypeError, ValueError) as exc:
        print(json.dumps(_invalid_report(exc), indent=2, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["full_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
