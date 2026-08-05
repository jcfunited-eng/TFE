#!/usr/bin/env python3
"""Fresh heldout test of self-babble auditory structure on real speech.

The substrate first experiences only deterministic physical self-babbles.
The recurrent auditory owner is then frozen and fired read-only against all
recorded external corpus variants.  Directory names are evaluator truth only;
they are never supplied to the substrate.

The exact pass law has no score or tolerance: every heldout occurrence must
fire a nonempty motif set, all variants of one evaluator class must yield one
identical set, and the eight class sets must be pairwise distinct.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import wave
from fractions import Fraction
from pathlib import Path

from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryMotorResourceProfile,
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
    LaryngealExcitationConfiguration,
    VocalTractConfiguration,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from tests.test_articulatory_self_vocal_motor import _heard


CORPUS_ROOT = Path(
    "dsf_ai_service/curriculum/assets/speech_commands"
)
EVALUATOR_CLASSES = (
    "down",
    "go",
    "left",
    "no",
    "right",
    "stop",
    "up",
    "yes",
)
KEY = b"articulatory-self-transform-heldout-probe-key"
BASE_APEX = (420, 90, 520, 120, 680, 160, 760, 240)
INITIAL = (90, 110, 150, 210, 280, 360, 470, 620)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _program(*, rotation: int, peak: int) -> ArticulatoryProgram:
    rotated = BASE_APEX[rotation:] + BASE_APEX[:rotation]
    return ArticulatoryProgram.create(
        sample_count=3_200,
        larynx=LaryngealExcitationConfiguration(
            cycle_samples=80,
            open_samples=48,
            peak_volume_velocity_pcm=peak,
        ),
        tract=VocalTractConfiguration(
            initial_section_area_mm2=INITIAL,
            apex_section_area_mm2=rotated,
            final_section_area_mm2=INITIAL,
            radiation_load_area_mm2=900,
            wall_retention_ppm=990_000,
        ),
    )


def _read_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as source:
        if (
            source.getnchannels(),
            source.getsampwidth(),
            source.getframerate(),
        ) != (1, 2, 16_000):
            raise ValueError(f"{path} left the PCM16/16 kHz boundary")
        return source.readframes(source.getnframes())


def run_probe() -> dict[str, object]:
    owner = ArticulatorySelfVocalMotorOwner(
        authority_key=KEY,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="heldout-self-babble-transformations",
            max_programs=8,
            max_state_bytes=128 * 1024,
        ),
    )
    auditory = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="heldout-self-babble-auditory-q",
            ear_count=1,
            max_motif_neurons=12_096,
            max_pending_experiences=16,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=256 * 1024 * 1024,
        )
    )
    babble_records: list[dict[str, object]] = []
    occurrence = 1
    for rotation in (0, 2, 4, 6):
        grown: list[str] = []
        for peak in (14_000, 16_000):
            program = owner.admit_program(
                _program(rotation=rotation, peak=peak)
            )
            synthesis = owner.synthesize(
                program_id=program.program_id,
                source_time_start=Fraction(occurrence),
            )
            _event, experience = _heard(
                synthesis.radiated_pcm_s16le, occurrence
            )
            observed = auditory.observe(experience)
            grown.extend(observed.newly_grown_motif_neuron_ids)
            babble_records.append({
                "excitation_pcm_sha256": hashlib.sha256(
                    synthesis.excitation_pcm_s16le
                ).hexdigest(),
                "grown_motif_count": len(
                    observed.newly_grown_motif_neuron_ids
                ),
                "program_id": program.program_id,
                "radiated_pcm_sha256": hashlib.sha256(
                    synthesis.radiated_pcm_s16le
                ).hexdigest(),
                "rotation": rotation,
            })
            occurrence += 1
        if not grown:
            raise RuntimeError(
                "self-babble pair failed to form recurrent structure"
            )
    frozen_state = auditory.snapshot_encoded()

    heldout_records: list[dict[str, object]] = []
    signatures_by_class: dict[str, set[tuple[str, ...]]] = {}
    nonempty = 0
    for evaluator_class in EVALUATOR_CLASSES:
        paths = tuple(sorted(
            (CORPUS_ROOT / evaluator_class).glob("*.wav")
        ))
        if len(paths) < 3:
            raise RuntimeError(
                "heldout evaluator class lacks three physical variants"
            )
        signatures_by_class[evaluator_class] = set()
        for path in paths:
            pcm = _read_pcm(path)
            _event, experience = _heard(pcm, occurrence)
            before = auditory.snapshot_encoded()
            firing = auditory.fire(experience)
            after = auditory.snapshot_encoded()
            if before != frozen_state or after != frozen_state:
                raise RuntimeError(
                    "heldout firing changed the frozen self-babble owner"
                )
            signature = firing.firing_motif_neuron_ids
            if signature:
                nonempty += 1
            signatures_by_class[evaluator_class].add(signature)
            heldout_records.append({
                "evaluator_class": evaluator_class,
                "firing_motif_count": len(signature),
                "firing_motif_neuron_ids": list(signature),
                "path": path.as_posix(),
                "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            })
            occurrence += 1

    exact_class_signatures = {
        evaluator_class: next(iter(signatures))
        for evaluator_class, signatures in signatures_by_class.items()
        if len(signatures) == 1 and next(iter(signatures))
    }
    every_occurrence_fired = nonempty == len(heldout_records)
    within_class_exact = all(
        len(signatures) == 1
        for signatures in signatures_by_class.values()
    )
    all_classes_nonempty = len(exact_class_signatures) == len(
        EVALUATOR_CLASSES
    )
    pairwise_distinct = (
        all_classes_nonempty
        and len(set(exact_class_signatures.values()))
        == len(EVALUATOR_CLASSES)
    )
    claim_allowed = (
        every_occurrence_fired
        and within_class_exact
        and pairwise_distinct
    )
    report = {
        "babble": {
            "program_count": len(owner.programs),
            "records": babble_records,
            "retained_pcm_bytes": owner.status()["retained_pcm_bytes"],
            "self_grown_motif_count": len(auditory.motif_neurons),
        },
        "claim_allowed": claim_allowed,
        "heldout": {
            "class_count": len(EVALUATOR_CLASSES),
            "every_occurrence_fired": every_occurrence_fired,
            "nonempty_occurrence_count": nonempty,
            "occurrence_count": len(heldout_records),
            "pairwise_distinct_class_signatures": pairwise_distinct,
            "records": heldout_records,
            "within_class_exact": within_class_exact,
        },
        "law": (
            "nonempty exact self-babble motif firing for every occurrence; "
            "one exact firing set within each evaluator class; pairwise "
            "distinct sets across all evaluator classes"
        ),
        "result": (
            "passed"
            if claim_allowed
            else "failed_no_external_distinction_claim"
        ),
        "schema": (
            "guala.probe.articulatory_self_transform_external_distinction.v1"
        ),
        "substrate_inputs": (
            "self-babble physical programs only; evaluator directory names "
            "were not supplied to the auditory owner"
        ),
    }
    report["authority_receipt_sha256"] = hashlib.sha256(
        _canonical(report)
    ).hexdigest()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "/tmp/w1_articulatory_self_transform_external_distinction.json"
        ),
    )
    arguments = parser.parse_args()
    report = run_probe()
    arguments.output.write_bytes(_canonical(report) + b"\n")
    print(json.dumps({
        "authority_receipt_sha256": report[
            "authority_receipt_sha256"
        ],
        "claim_allowed": report["claim_allowed"],
        "heldout": {
            key: value
            for key, value in report["heldout"].items()
            if key != "records"
        },
        "output": arguments.output.as_posix(),
        "result": report["result"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
