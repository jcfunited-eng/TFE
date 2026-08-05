"""Non-canonical VTVR walk-up through causally grounded THING experience.

This probe asks the next valid side-kernel question.  Several source-disjoint
human voices are physically rendered while one authenticated W1 object is
held.  The learner receives only the resulting causal THING id, capture
authority, and complete VTVR experience.  Corpus words and speaker ids remain
outside the learning boundary and are used only after resolution for scoring.

For each THING, exact structural atoms that recur in every training encounter
are retained.  Atoms are order/topology relations derived from all explicit
VTVR and D/M/R/U/C/P/B fields; raw experiences and their complete receipts
remain authoritative.  No count threshold, similarity score, distance,
nearest exemplar, label, chi identity, Atlas, or ML operation participates.
A held-out experience resolves only if it contains one complete nonempty
THING invariant and no competing invariant.

This remains a reduced, non-canonical research index over complete retained
fields.  It cannot authorize production recognition.  Failure is informative
and stops the walk-up.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import wave
import zipfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
    W1ContactThingEncounterAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from tools.isolated_vtvr_side_kernel_v2 import (
    RelationFact,
    SideKernelExperience,
)
from tools.probe_vtvr_side_kernel_physical_speech_walkup import (
    ARCHIVE_PATH,
    ARCHIVE_PREFIX,
    ARCHIVE_SHA256,
    SpeechItem,
    _archive_sha256,
    _physical_experience,
)


SCHEMA = "guala.research.vtvr_causal_thing_familiarity.v1"
AUTHORITY_KEY = b"guala-vtvr-causal-thing-familiarity-20260727"
WORDS = ("down", "stop", "yes")
TRAINING_SPEAKERS_PER_THING = 3
HELD_OUT_SPEAKERS_PER_THING = 2
MAX_ATOMS_PER_EXPERIENCE = 64_000


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


def _sign(value: object) -> str:
    return hmac.new(
        AUTHORITY_KEY,
        b"guala-vtvr-lived-thing-encounter-v1\0"
        + _canonical(value),
        hashlib.sha256,
    ).hexdigest()


def _items(
    archive: zipfile.ZipFile,
    *,
    word: str,
    count: int,
) -> tuple[SpeechItem, ...]:
    prefix = f"{ARCHIVE_PREFIX}{word}/"
    result = []
    speakers = set()
    for member in sorted(
        value
        for value in archive.namelist()
        if value.startswith(prefix) and value.endswith(".wav")
    ):
        filename = member.rsplit("/", 1)[-1]
        if "_nohash_" not in filename:
            continue
        speaker = filename.split("_nohash_", 1)[0]
        if speaker in speakers:
            continue
        wav_data = archive.read(member)
        with wave.open(io.BytesIO(wav_data), "rb") as source:
            if (
                source.getnchannels() != 1
                or source.getsampwidth() != 2
                or source.getframerate() != 16_000
                or source.getnframes() != 16_000
                or source.getcomptype() != "NONE"
            ):
                continue
            pcm = source.readframes(source.getnframes())
        result.append(SpeechItem(
            oracle_word=word,
            speaker_id=speaker,
            archive_member=member,
            pcm_s16le=pcm,
            wav_sha256=hashlib.sha256(wav_data).hexdigest(),
        ))
        speakers.add(speaker)
        if len(result) == count:
            return tuple(result)
    raise RuntimeError(f"insufficient source-disjoint recordings for {word}")


def _execute(
    world: EmbodimentWorldAuthority,
    command: object,
    ordinal: int,
):
    before = world.observation_snapshot()
    return world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=f"{ordinal:064x}",
        expected_revision=before.revision,
    )


def _thing_id(object_ordinal: int) -> tuple[str, str]:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    sensory = EmbodimentSensoryOutcomeAuthority(
        authority_key=AUTHORITY_KEY
    )
    partition_authority = W1ContactThingEncounterAuthority(
        authority_key=AUTHORITY_KEY,
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    owner = CausalThingMosaicOwner(
        authority_key=AUTHORITY_KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="vtvr-side-lived-thing",
            max_mosaics=1,
            max_partitions_per_mosaic=8,
            max_roots_per_partition=256,
            max_routes=2_048,
            max_state_bytes=32 * 1024 * 1024,
        ),
        partition_authority=partition_authority,
    )
    object_id = f"W1-object-{object_ordinal}"
    target_x = 1_000 * object_ordinal + 500
    if object_ordinal > 1:
        approach_x = target_x - 500
        waypoints = (
            PositionMM(1_000, 2_000, 0),
            PositionMM(approach_x, 2_000, 0),
            PositionMM(approach_x, 1_000, 0),
        )
        for waypoint_ordinal, waypoint in enumerate(waypoints):
            moved = _execute(
                world,
                MoveCommand(PoseMM(waypoint, 0)),
                object_ordinal * 10 + waypoint_ordinal,
            )
            if moved.disposition != "applied":
                raise RuntimeError(
                    "side THING tutor could not follow clear approach path"
                )
    picked = _execute(
        world,
        PickCommand(object_id),
        object_ordinal * 10 + 3,
    )
    if picked.disposition != "applied":
        raise RuntimeError("side THING tutor could not establish contact")
    causal_owner = ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    outcome = sensory.transduce(
        picked.after,
        causal_owner=causal_owner,
        execution_receipt=picked,
        commit=True,
    )
    partition = partition_authority.partition(
        outcome=outcome,
        observation=picked.after,
        execution=picked,
    )
    mosaic = owner.admit(partition)
    return mosaic.thing_id, mosaic.authority_receipt_sha256


def _cmp(left: object, right: object) -> int:
    return -1 if left < right else 1 if left > right else 0


def _span(values: tuple[Fraction, ...]) -> Fraction:
    return max(values) - min(values)


def _peak_index(values: tuple[Fraction, ...]) -> int:
    return max(range(len(values)), key=lambda index: abs(values[index]))


def _relation_sign_run(
    values: tuple[RelationFact, ...],
    field: str,
) -> tuple[int, ...]:
    raw = tuple(
        -1 if getattr(value, field) < 0
        else 1 if getattr(value, field) > 0
        else 0
        for value in values
    )
    collapsed = []
    for value in raw:
        if not collapsed or collapsed[-1] != value:
            collapsed.append(value)
    return tuple(collapsed)


def _pairwise_atoms(
    name: str,
    values: tuple[object, ...],
) -> set[tuple[object, ...]]:
    return {
        (name, left, right, _cmp(values[left], values[right]))
        for left in range(len(values))
        for right in range(left + 1, len(values))
    }


def _atoms(
    experience: SideKernelExperience,
) -> frozenset[tuple[object, ...]]:
    experience.verify()
    field = experience.L4
    width = len(field.D_k[0])
    d = tuple(
        tuple(frame[index] for frame in field.D_k)
        for index in range(width)
    )
    m = tuple(
        tuple(frame[index] for frame in field.M_k)
        for index in range(width)
    )
    r = tuple(
        tuple(frame[index] for frame in field.R_rev_k)
        for index in range(width)
    )
    p = tuple(
        tuple(frame[index] for frame in field.P_k)
        for index in range(width)
    )
    b = tuple(
        tuple(frame[index] for frame in field.B_k)
        for index in range(width)
    )
    vector = tuple(
        tuple(frame[index] for frame in experience.L1.vector)
        for index in range(width)
    )
    atoms = set()
    for name, values in (
        ("D_span_order", tuple(_span(value) for value in d)),
        ("D_peak_time_order", tuple(_peak_index(value) for value in d)),
        ("M_span_order", tuple(_span(value) for value in m)),
        ("M_peak_time_order", tuple(_peak_index(value) for value in m)),
        ("R_count_order", tuple(sum(value) for value in r)),
        ("P_peak_order", tuple(max(value) for value in p)),
        ("B_span_order", tuple(_span(value) for value in b)),
        ("V_span_order", tuple(_span(value) for value in vector)),
        (
            "Volume_total_order",
            experience.L1.accumulated_volume,
        ),
    ):
        atoms.update(_pairwise_atoms(name, values))
    for edge_index, trajectory in enumerate(
        experience.L3.edge_trajectories
    ):
        atoms.add((
            "C_oriented_area_run",
            edge_index,
            _relation_sign_run(trajectory, "oriented_area"),
        ))
        atoms.add((
            "C_displacement_product_run",
            edge_index,
            _relation_sign_run(
                trajectory,
                "displacement_product",
            ),
        ))
    for vertex, states in enumerate(zip(*field.U_star_k, strict=True)):
        atoms.add(("U_state_trajectory", vertex, tuple(states)))
    if len(atoms) > MAX_ATOMS_PER_EXPERIENCE:
        raise RuntimeError("side THING invariant atom capacity exhausted")
    return frozenset(atoms)


@dataclass(frozen=True, slots=True)
class Encounter:
    thing_id: str
    thing_mosaic_receipt_sha256: str
    capture_receipt_sha256: str
    vtvr_receipt_sha256: str
    atoms: frozenset[tuple[object, ...]]
    encounter_hmac_sha256: str
    oracle_word: str
    oracle_speaker: str
    archive_member: str


def _encounter(
    *,
    thing_id: str,
    mosaic_receipt: str,
    item: SpeechItem,
    source_ordinal: int,
) -> Encounter:
    capture, experience = _physical_experience(
        item,
        source_ordinal=source_ordinal,
    )
    payload = {
        "capture_receipt_sha256": capture.authority_receipt_sha256,
        "schema": "guala.research.vtvr_lived_thing_encounter.v1",
        "thing_id": thing_id,
        "thing_mosaic_receipt_sha256": mosaic_receipt,
        "vtvr_receipt_sha256": experience.authority_receipt_sha256,
    }
    return Encounter(
        thing_id=thing_id,
        thing_mosaic_receipt_sha256=mosaic_receipt,
        capture_receipt_sha256=capture.authority_receipt_sha256,
        vtvr_receipt_sha256=experience.authority_receipt_sha256,
        atoms=_atoms(experience),
        encounter_hmac_sha256=_sign(payload),
        oracle_word=item.oracle_word,
        oracle_speaker=item.speaker_id,
        archive_member=item.archive_member,
    )


def run_probe() -> dict[str, object]:
    actual_archive = _archive_sha256(ARCHIVE_PATH)
    if actual_archive != ARCHIVE_SHA256:
        raise RuntimeError("authenticated speech archive changed")
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        corpus = {
            word: _items(
                archive,
                word=word,
                count=(
                    TRAINING_SPEAKERS_PER_THING
                    + HELD_OUT_SPEAKERS_PER_THING
                ),
            )
            for word in WORDS
        }
    thing_by_oracle = {
        word: _thing_id(index + 1)
        for index, word in enumerate(WORDS)
    }
    training = []
    held_out = []
    for word in WORDS:
        thing_id, mosaic_receipt = thing_by_oracle[word]
        for index, item in enumerate(corpus[word]):
            encounter = _encounter(
                thing_id=thing_id,
                mosaic_receipt=mosaic_receipt,
                item=item,
                source_ordinal=index % 2,
            )
            (
                training
                if index < TRAINING_SPEAKERS_PER_THING
                else held_out
            ).append(encounter)

    grouped = {
        thing_id: tuple(
            item for item in training if item.thing_id == thing_id
        )
        for thing_id, _receipt in thing_by_oracle.values()
    }
    common = {
        thing_id: frozenset.intersection(
            *(item.atoms for item in encounters)
        )
        for thing_id, encounters in grouped.items()
    }
    global_common = frozenset.intersection(*common.values())
    invariants = {
        thing_id: atoms - global_common
        for thing_id, atoms in common.items()
    }
    resolutions = []
    correct = 0
    for item in held_out:
        candidates = tuple(sorted(
            thing_id
            for thing_id, invariant in invariants.items()
            if invariant and invariant.issubset(item.atoms)
        ))
        state = (
            "unique"
            if len(candidates) == 1
            else "ambiguous"
            if candidates
            else "unresolved"
        )
        resolved = candidates[0] if state == "unique" else None
        passed = resolved == item.thing_id
        correct += int(passed)
        resolutions.append({
            "archive_member": item.archive_member,
            "candidate_thing_ids": candidates,
            "expected_thing_id": item.thing_id,
            "oracle_speaker": item.oracle_speaker,
            "oracle_word": item.oracle_word,
            "passed": passed,
            "state": state,
            "vtvr_receipt_sha256": item.vtvr_receipt_sha256,
        })
    report = {
        "archive_sha256": actual_archive,
        "claim_allowed": correct == len(held_out),
        "correct": correct,
        "evaluation_oracle": {
            thing_id: word
            for word, (thing_id, _receipt) in thing_by_oracle.items()
        },
        "full_field_retained": True,
        "global_common_atom_count": len(global_common),
        "held_out": resolutions,
        "held_out_count": len(held_out),
        "invariant_atom_counts": {
            thing_id: len(atoms)
            for thing_id, atoms in invariants.items()
        },
        "learning_boundary_received_words": False,
        "reduced_research_index": True,
        "schema": SCHEMA,
        "training_encounters": [
            {
                "archive_member_for_oracle_audit": item.archive_member,
                "atom_count": len(item.atoms),
                "capture_receipt_sha256": item.capture_receipt_sha256,
                "encounter_hmac_sha256": item.encounter_hmac_sha256,
                "oracle_speaker_for_audit": item.oracle_speaker,
                "oracle_word_for_audit": item.oracle_word,
                "thing_id": item.thing_id,
                "thing_mosaic_receipt_sha256": (
                    item.thing_mosaic_receipt_sha256
                ),
                "vtvr_receipt_sha256": item.vtvr_receipt_sha256,
            }
            for item in training
        ],
    }
    report["authority_receipt_sha256"] = _digest(report)
    return report


if __name__ == "__main__":
    print(json.dumps(run_probe(), indent=2, sort_keys=True))
