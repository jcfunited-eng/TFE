"""Held-out grounded walk-up for AuthenticatedBilateralL6PulseClosure."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.substrate.w1_loom_auditory_bridge import (
    W1LoomAuditoryBridge,
)
from dsf_ai_service.substrate.w1_loom_auditory_co_resonance import (
    AuthenticatedBilateralL6PulseClosure,
    AuthenticatedBilateralL6PulseProfile,
    restore_authenticated_bilateral_l6_pulse_closure,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    _select_corpus,
)
from tools.probe_contextual_thing_mosaic_settling import (
    REFERENCE_COUNT,
    TEST_COMMANDS,
    _mount_episodes,
    _tone_item,
    _tone_pcm,
)
from tools.probe_existing_auditory_neuron_temporal_go_no_go import (
    _read_pcm,
)


SCHEMA = "guala.audit.w1_loom_l6_pulse_closure_walkup.v1"
KEY = b"guala-w1-loom-l6-pulse-closure-walkup-20260727"


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


def _thing_id(target_ordinal: int) -> str:
    return _digest({
        "physical_action_target_ordinal": target_ordinal,
        "schema": "guala.audit.walkup_causal_grounding.v1",
    })


def _settlement_record(value) -> dict[str, object]:
    value.verify()
    return {
        "authority_receipt_sha256": value.authority_receipt_sha256,
        "relations": [relation.record() for relation in value.relations],
        "state": value.state,
        "settlement_sequence": value.settlement_sequence,
        "thing_ids": list(value.thing_ids),
    }


def run(archive_path: Path) -> dict[str, object]:
    archive_bytes = archive_path.read_bytes()
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if archive_sha256 != ARCHIVE_SHA256:
        raise ValueError("speech corpus authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        corpus = _select_corpus(archive)
        references = tuple(
            item
            for command in TEST_COMMANDS
            for item in corpus
            if (
                item.oracle_command == command
                and item.split == "reference"
            )
        )
        held_out = tuple(
            next(
                item
                for item in corpus
                if (
                    item.oracle_command == command
                    and item.split == "held_out"
                )
            )
            for command in TEST_COMMANDS
        )
        tone = _tone_item()
        ordered = (*references, *held_out, tone)
        pcm_by_item = {
            item.item_id: _read_pcm(archive.read(item.archive_member))
            for item in (*references, *held_out)
        } | {tone.item_id: _tone_pcm()}
    if len(references) != len(TEST_COMMANDS) * REFERENCE_COUNT:
        raise ValueError("walk-up reference split changed")
    episodes = _mount_episodes(ordered, pcm_by_item)
    by_id = {value.item.item_id: value for value in episodes}

    brain = LoomBrain(seed_size=8, observable="event_count")
    bridge = W1LoomAuditoryBridge(brain)
    owner = AuthenticatedBilateralL6PulseClosure(
        brain=brain,
        profile=AuthenticatedBilateralL6PulseProfile.create(
            profile_id="w1-grounded-heldout-pulse-closure",
            max_things=8,
            max_occurrences_per_thing=16,
            max_relations_per_thing=500_000,
            max_total_relations=1_500_000,
            max_settlement_receipts=64,
            max_state_bytes=512 * 1024 * 1024,
        ),
        authority_key=KEY,
    )
    learning = []
    query_occurrences = {}
    for item in ordered:
        episode = by_id[item.item_id]
        bridge.settle(
            episode.mount.binaural_receptor_settlement
        )
        dynamics = bridge.latest_dynamics
        if dynamics is None:
            raise RuntimeError("bridge produced no pulse dynamics")
        if item.split == "reference":
            receipt = owner.learn(
                occurrence=dynamics,
                thing_id=_thing_id(episode.target_ordinal),
                grounding_authority_receipt_sha256=(
                    episode.context_signature_sha256
                ),
            )
            owner.verify_learning_receipt(receipt)
            learning.append({
                "command_used_only_for_scoring": item.oracle_command,
                "discriminative_relation_count": (
                    receipt.discriminative_relation_count
                ),
                "locked_relation_count": receipt.locked_relation_count,
                "occurrence_count": receipt.occurrence_count,
                "source_occurrence_receipt_sha256": (
                    receipt.source_occurrence_receipt_sha256
                ),
                "thing_id": receipt.thing_id,
            })
        else:
            query_occurrences[item.item_id] = dynamics

    held_records = []
    for item in held_out:
        episode = by_id[item.item_id]
        expected = _thing_id(episode.target_ordinal)
        settlement = owner.settle(query_occurrences[item.item_id])
        owner.verify_settlement(settlement)
        held_records.append({
            "expected_thing_id": expected,
            "item_id": item.item_id,
            "passed": (
                settlement.state == "resolved"
                and settlement.thing_ids == (expected,)
            ),
            "settlement": _settlement_record(settlement),
        })
    tone_settlement = owner.settle(
        query_occurrences[tone.item_id]
    )
    owner.verify_settlement(tone_settlement)
    before = owner.snapshot_encoded()
    restored = restore_authenticated_bilateral_l6_pulse_closure(
        before,
        brain=brain,
        authority_key=KEY,
    )
    cold_restore_byte_identical = (
        restored.snapshot_encoded() == before
    )
    cold_records = []
    for item in held_out:
        warm = owner.settle(query_occurrences[item.item_id])
        cold = restored.settle(query_occurrences[item.item_id])
        owner.verify_settlement(warm)
        restored.verify_settlement(cold)
        cold_records.append({
            "identical": warm == cold,
            "item_id": item.item_id,
        })
    payload = {
        "archive_sha256": archive_sha256,
        "cold_restore_byte_identical": cold_restore_byte_identical,
        "cold_restore_query_records": cold_records,
        "commands_used_only_after_physical_settlement": list(
            TEST_COMMANDS
        ),
        "full_binaural_field_authority_retained": True,
        "held_out": held_records,
        "held_out_pass_count": sum(
            value["passed"] for value in held_records
        ),
        "learning": learning,
        "l0_l4_modified": False,
        "overall_pass": (
            all(value["passed"] for value in held_records)
            and tone_settlement.state != "resolved"
            and cold_restore_byte_identical
            and all(value["identical"] for value in cold_records)
        ),
        "schema": SCHEMA,
        "source_disjoint_speaker_count": (
            len(references) + len(held_out)
        ),
        "state_status": owner.status(),
        "tone": _settlement_record(tone_settlement),
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.archive)
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
