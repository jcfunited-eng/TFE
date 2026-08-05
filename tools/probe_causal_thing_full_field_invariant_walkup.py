"""Exact learned full-field invariant walk-up inside causal THING classes.

The causal THING report supplies only authenticated class membership for
training occurrences.  Candidate invariants are exact intersections of
structural propositions across repeated nonidentical auditory full fields,
followed by exact cross-THING fission.  Queries never use a physical root
hash, item id, label, distance, score, threshold, nearest exemplar, ML, or an
L0--L4 modification.

Candidate selection is frozen before final queries: the first declared
quotient whose invariants uniquely route every leave-one-reference-out
occurrence is selected.  Only then are a never-admitted speaker, a different
recording from a trained speaker, and an unrelated tone evaluated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np

from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_PREFIX,
    ARCHIVE_SHA256,
    _pcm_from_wav,
    _select_corpus,
)
from tools.probe_auditory_receptor_topology_census import (
    _l4_trajectory,
    _receptor_trajectory,
    _transduce,
)
from tools.probe_contextual_thing_mosaic_settling import (
    TEST_COMMANDS,
    _tone_pcm,
)


SCHEMA = "guala.audit.causal_thing_full_field_invariant_walkup.v1"
CAUSAL_REPORT_SCHEMA = (
    "guala.audit.causal_thing_reciprocal_variant_learning.v1"
)

TRAINING_MEMBERS = {
    "down": (
        "004ae714_nohash_0.wav",
        "00b01445_nohash_1.wav",
        "00f0204f_nohash_0.wav",
        "0132a06d_nohash_1.wav",
        "0137b3f4_nohash_2.wav",
    ),
    "go": (
        "01bb6a2a_nohash_3.wav",
        "022cd682_nohash_0.wav",
        "023a61ad_nohash_2.wav",
        "026290a7_nohash_0.wav",
        "02746d24_nohash_0.wav",
    ),
    "left": (
        "012c8314_nohash_0.wav",
        "01648c51_nohash_0.wav",
        "0397ecda_nohash_1.wav",
        "03c96658_nohash_1.wav",
        "0e5193e6_nohash_0.wav",
    ),
}
TRAINED_SPEAKER_REPEAT_MEMBERS = {
    "down": "0132a06d_nohash_4.wav",
    "go": "01bb6a2a_nohash_4.wav",
    "left": "0e5193e6_nohash_1.wav",
}

LaneKey = tuple[str, str, str, str]
Token = tuple[object, ...]
TokenSet = frozenset[Token]
TokenFunction = Callable[[Mapping[LaneKey, Sequence[Fraction]]], TokenSet]


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


def _speaker(member: str) -> str:
    return member.split("_nohash_", 1)[0]


@dataclass(frozen=True, slots=True)
class AuditItem:
    item_id: str
    oracle_command: str
    speaker_id: str
    archive_member: str
    kind: str
    ordinal: int


def _item(
    *,
    command: str,
    member_name: str,
    kind: str,
    ordinal: int,
) -> AuditItem:
    archive_member = f"{ARCHIVE_PREFIX}{command}/{member_name}"
    return AuditItem(
        item_id=_digest({
            "archive_member": archive_member,
            "kind": kind,
            "schema": "guala.audit.full_field_invariant_item.v1",
        }),
        oracle_command=command,
        speaker_id=_speaker(member_name),
        archive_member=archive_member,
        kind=kind,
        ordinal=ordinal,
    )


def _direction_word(values: Sequence[Fraction]) -> tuple[int, ...]:
    directions = tuple(
        (right > left) - (right < left)
        for left, right in zip(values, values[1:])
    )
    return tuple(
        value
        for index, value in enumerate(directions)
        if index == 0 or value != directions[index - 1]
    )


def _word_tokens(
    trajectory: Mapping[LaneKey, Sequence[Fraction]],
) -> TokenSet:
    return frozenset(
        (*lane, "temporal-run-word", *_direction_word(values))
        for lane, values in trajectory.items()
    )


def _local_tokens(
    trajectory: Mapping[LaneKey, Sequence[Fraction]],
) -> TokenSet:
    result = set()
    for lane, values in trajectory.items():
        word = _direction_word(values)
        for width in (1, 2, 3):
            result.update(
                (*lane, "temporal-local", width, *word[start:start + width])
                for start in range(len(word) - width + 1)
            )
    return frozenset(result)


def _channel_index(channel_id: str) -> int:
    if not channel_id.startswith("erb_"):
        raise ValueError("full-field invariant channel identity changed")
    return int(channel_id.split("_", 1)[1])


def _spatial_tokens(
    trajectory: Mapping[LaneKey, Sequence[Fraction]],
) -> TokenSet:
    groups: dict[
        tuple[str, str, str],
        list[tuple[int, Sequence[Fraction]]],
    ] = {}
    for (boundary, channel, component, field), values in trajectory.items():
        groups.setdefault(
            (boundary, component, field), []
        ).append((_channel_index(channel), values))
    result = set()
    for family, channels in groups.items():
        ordered = sorted(channels)
        for (left_index, left), (right_index, right) in zip(
            ordered, ordered[1:], strict=False
        ):
            if right_index != left_index + 1 or len(left) != len(right):
                raise ValueError("full-field spatial adjacency changed")
            order = tuple(
                (right_value > left_value) - (right_value < left_value)
                for left_value, right_value in zip(left, right, strict=True)
            )
            word = tuple(
                value
                for index, value in enumerate(order)
                if index == 0 or value != order[index - 1]
            )
            for width in (1, 2, 3):
                result.update(
                    (
                        *family,
                        left_index,
                        right_index,
                        "spatial-local",
                        width,
                        *word[start:start + width],
                    )
                    for start in range(len(word) - width + 1)
                )
    return frozenset(result)


def _combined_tokens(
    trajectory: Mapping[LaneKey, Sequence[Fraction]],
) -> TokenSet:
    return _local_tokens(trajectory) | _spatial_tokens(trajectory)


CANDIDATES: tuple[tuple[str, TokenFunction], ...] = (
    ("complete_lane_run_words", _word_tokens),
    ("lane_local_order_topology", _local_tokens),
    ("adjacent_channel_order_topology", _spatial_tokens),
    ("temporal_and_spatial_order_topology", _combined_tokens),
)


def _invariants(
    thing_items: Mapping[str, Sequence[AuditItem]],
    token_by_item: Mapping[str, TokenSet],
) -> tuple[dict[str, TokenSet], int]:
    recurrent = {
        thing_id: frozenset.intersection(*(
            token_by_item[item.item_id] for item in items
        ))
        for thing_id, items in thing_items.items()
    }
    shared = frozenset(
        token
        for values in recurrent.values()
        for token in values
        if sum(token in other for other in recurrent.values()) > 1
    )
    return {
        thing_id: values - shared
        for thing_id, values in recurrent.items()
    }, len(shared)


def _route(
    invariants: Mapping[str, TokenSet],
    observed: TokenSet,
) -> tuple[str, tuple[str, ...]]:
    matches = tuple(sorted(
        thing_id
        for thing_id, required in invariants.items()
        if required and required.issubset(observed)
    ))
    return (
        "unique"
        if len(matches) == 1
        else "ambiguous"
        if matches
        else "unresolved",
        matches,
    )


def _causal_thing_ids(report_path: Path) -> dict[str, str]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    authority = report.pop("authority_receipt_sha256", None)
    if (
        report.get("schema") != CAUSAL_REPORT_SCHEMA
        or not report.get("different_physical_things_remained_separate")
        or _digest(report) != authority
    ):
        raise ValueError("causal THING class report authority changed")
    result = {
        value["command_used_only_to_select_physical_test_object"]: (
            value["thing_id"]
        )
        for value in report["encounter_records"]
        if value["encounter_kind"] == "contact-genesis"
    }
    if set(result) != set(TEST_COMMANDS) or len(set(result.values())) != 3:
        raise ValueError("causal THING class membership changed")
    return result


def _mount_trajectory(signal: np.ndarray, ordinal: int) -> dict[
    LaneKey, tuple[Fraction, ...]
]:
    capture = _transduce(signal, 16)
    receptor = _receptor_trajectory(capture)
    l4, _elapsed = _l4_trajectory(
        capture,
        assembly_id=f"thing-invariant-{ordinal}",
        source_anchor=Fraction(ordinal * 2),
    )
    result = dict(receptor)
    result.update(l4)
    if len(result) != 288:
        raise RuntimeError("full-field invariant lost auditory topology")
    return result


def run(archive_path: Path, causal_report_path: Path) -> dict[str, object]:
    archive_bytes = archive_path.read_bytes()
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if archive_sha256 != ARCHIVE_SHA256:
        raise ValueError("speech corpus authority changed")
    thing_id_by_command = _causal_thing_ids(causal_report_path)
    training = tuple(
        _item(
            command=command,
            member_name=member,
            kind="grounded-training-variant",
            ordinal=command_index * 10 + member_index,
        )
        for command_index, command in enumerate(TEST_COMMANDS)
        for member_index, member in enumerate(TRAINING_MEMBERS[command])
    )
    repeats = tuple(
        _item(
            command=command,
            member_name=TRAINED_SPEAKER_REPEAT_MEMBERS[command],
            kind="fresh-trained-speaker-repeat",
            ordinal=40 + command_index,
        )
        for command_index, command in enumerate(TEST_COMMANDS)
    )
    with zipfile.ZipFile(archive_path) as archive:
        selected = _select_corpus(archive)
        held_out = tuple(
            _item(
                command=command,
                member_name=next(
                    value.archive_member.rsplit("/", 1)[1]
                    for value in selected
                    if value.oracle_command == command
                    and value.split == "held_out"
                ),
                kind="fresh-never-admitted-speaker",
                ordinal=50 + command_index,
            )
            for command_index, command in enumerate(TEST_COMMANDS)
        )
        items = training + repeats + held_out
        if any(item.archive_member not in archive.namelist() for item in items):
            raise ValueError("full-field invariant corpus member changed")
        signals = {
            item.item_id: _pcm_from_wav(archive.read(item.archive_member))
            for item in items
        }
    speakers = {
        item.speaker_id for item in training + held_out
    }
    if len(speakers) != len(training) + len(held_out):
        raise ValueError(
            "training and never-admitted speakers are not source-disjoint"
        )
    tone_id = _digest({
        "schema": "guala.audit.full_field_invariant_tone.v1"
    })
    signals[tone_id] = (
        np.frombuffer(_tone_pcm(), dtype="<i2").astype(np.float64)
        / 32_768.0
    )
    trajectories = {
        item.item_id: _mount_trajectory(
            signals[item.item_id], item.ordinal
        )
        for item in items
    }
    trajectories[tone_id] = _mount_trajectory(signals[tone_id], 99)
    training_by_thing = {
        thing_id_by_command[command]: tuple(
            item
            for item in training
            if item.oracle_command == command
        )
        for command in TEST_COMMANDS
    }

    candidate_records = []
    selected_name = None
    selected_tokens = None
    selected_invariants = None
    for candidate_name, token_function in CANDIDATES:
        token_by_item = {
            item_id: token_function(trajectory)
            for item_id, trajectory in trajectories.items()
        }
        leave_one_out = []
        for expected_thing, class_items in training_by_thing.items():
            for omitted in class_items:
                reduced = {
                    thing_id: tuple(
                        item for item in values
                        if item.item_id != omitted.item_id
                    )
                    for thing_id, values in training_by_thing.items()
                }
                invariants, _shared = _invariants(
                    reduced, token_by_item
                )
                state, thing_ids = _route(
                    invariants, token_by_item[omitted.item_id]
                )
                leave_one_out.append({
                    "item_id": omitted.item_id,
                    "passed": (
                        state == "unique"
                        and thing_ids == (expected_thing,)
                    ),
                    "state": state,
                    "thing_ids": list(thing_ids),
                })
        invariants, shared_count = _invariants(
            training_by_thing, token_by_item
        )
        tone_state, tone_ids = _route(
            invariants, token_by_item[tone_id]
        )
        training_pass = (
            all(value["passed"] for value in leave_one_out)
            and tone_state == "unresolved"
        )
        candidate_records.append({
            "candidate": candidate_name,
            "fissioned_shared_token_count": shared_count,
            "invariant_dimensions_by_thing": {
                thing_id: len(values)
                for thing_id, values in invariants.items()
            },
            "leave_one_out_pass_count": sum(
                value["passed"] for value in leave_one_out
            ),
            "leave_one_out_total": len(leave_one_out),
            "tone_state": tone_state,
            "training_selection_pass": training_pass,
        })
        if selected_name is None and training_pass:
            selected_name = candidate_name
            selected_tokens = token_by_item
            selected_invariants = invariants
    final_records = []
    if (
        selected_name is not None
        and selected_tokens is not None
        and selected_invariants is not None
    ):
        for item in repeats + held_out:
            expected = thing_id_by_command[item.oracle_command]
            state, thing_ids = _route(
                selected_invariants,
                selected_tokens[item.item_id],
            )
            final_records.append({
                "expected_thing_id": expected,
                "item_id": item.item_id,
                "kind": item.kind,
                "passed": (
                    state == "unique"
                    and thing_ids == (expected,)
                ),
                "speaker_id": item.speaker_id,
                "state": state,
                "thing_ids": list(thing_ids),
            })
        tone_state, tone_ids = _route(
            selected_invariants, selected_tokens[tone_id]
        )
    else:
        tone_state, tone_ids = "not_evaluated", ()
    payload = {
        "archive_sha256": archive_sha256,
        "candidate_order_declared_before_final_queries": [
            name for name, _function in CANDIDATES
        ],
        "candidate_records": candidate_records,
        "causal_membership_source_authority_sha256": json.loads(
            causal_report_path.read_text(encoding="utf-8")
        )["authority_receipt_sha256"],
        "exact_query_hash_membership_used": False,
        "final_queries": final_records,
        "final_query_pass_count": sum(
            value["passed"] for value in final_records
        ),
        "final_query_total": len(final_records),
        "full_field_lane_count": 288,
        "live_wiring_performed": False,
        "overall_pass": (
            selected_name is not None
            and len(final_records) == 6
            and all(value["passed"] for value in final_records)
            and tone_state == "unresolved"
        ),
        "schema": SCHEMA,
        "selected_candidate": selected_name,
        "tone": {
            "state": tone_state,
            "thing_ids": list(tone_ids),
        },
        "unseen_variant_query_count": len(held_out),
        "trained_speaker_fresh_repeat_query_count": len(repeats),
    }
    return payload | {"authority_receipt_sha256": _digest(payload)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--causal-report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.archive, args.causal_report)
    encoded = json.dumps(
        report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
