"""Isolated full-field audiovisual-source precursor experiment.

This file is deliberately not imported by production.  It asks one narrow
question: can the current, unchanged ``uf_core`` L0--L4 pipeline preserve
enough structure from full-spectrum audio to distinguish a recurring source
from an utterance, music, and a mixture without a fitted threshold or ML?

The experiment is conservative:

* deterministic 16 kHz waveforms provide controlled physical structure;
* every explicit frequency-time lane runs through canonical L0, L1, L2, L3,
  and L4 unchanged;
* the seven L4 fields remain separate throughout comparison;
* the current production-authority ``legacy_unit`` relevance is evaluated as
  authority, while ``structural_activity_diagnostic`` is reported only as the
  diagnostic-only mode its own L0 documentation says it is;
* Krimelack winding, balanced ternary, powers of three, chi, and an isolated
  LivingAtlas are recurrence diagnostics only.  They never decide identity;
* ambiguity and collision return ``unknown`` instead of a forced winner.

Run from the repository root:

    python tools/full_field_source_identity_probe.py

The only output is one machine-readable JSON document on stdout.  ``--pretty``
indents it for inspection.  No state or production file is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from dsf_ai_service.substrate.krimelack import Krimelack
from dsf_ai_service.v4.gualaloom_v6_living_atlas import LivingAtlas
from uf_core.layer0 import RelevanceMode, compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


SAMPLE_RATE_HZ = 16_000
DURATION_S = 6 / 5
FRAME_RATE_HZ = 50
FRAME_LENGTH = SAMPLE_RATE_HZ // FRAME_RATE_HZ
FRAME_HOP = FRAME_LENGTH // 2
FIELD_NAMES = (
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
)

# Full [0, Nyquist] coverage.  The nonzero edges are powers-of-two divisions
# of the physical Nyquist frequency, not boundaries fitted to these sources.
NYQUIST_HZ = SAMPLE_RATE_HZ // 2
FREQUENCY_LANES_HZ = (
    (0, NYQUIST_HZ // 32),
    (NYQUIST_HZ // 32, NYQUIST_HZ // 16),
    (NYQUIST_HZ // 16, NYQUIST_HZ // 8),
    (NYQUIST_HZ // 8, NYQUIST_HZ // 4),
    (NYQUIST_HZ // 4, NYQUIST_HZ // 2),
    (NYQUIST_HZ // 2, NYQUIST_HZ),
)


@dataclass(frozen=True)
class SourcePhysics:
    fundamental_hz: float
    formants_hz: tuple[float, float, float]
    spectral_tilt: float
    breath_hz: tuple[float, float]


SOURCE_A = SourcePhysics(118.0, (620.0, 1_180.0, 2_450.0), 1.10,
                         (3_710.0, 5_330.0))
SOURCE_B = SourcePhysics(206.0, (430.0, 1_760.0, 3_080.0), 1.35,
                         (4_210.0, 6_170.0))

# The utterance is a temporal excitation contour, not text or a token label.
UTTERANCE_ONE = ((1.00, 0.00), (0.72, 0.08), (1.18, -0.04), (0.64, 0.11))
UTTERANCE_TWO = ((0.58, 0.12), (1.22, -0.07), (0.76, 0.04), (1.05, -0.10))


def _raised_cosine_envelope(n: int) -> np.ndarray:
    if n <= 1:
        return np.ones(max(0, n), dtype=np.float64)
    x = np.arange(n, dtype=np.float64) / float(n - 1)
    return np.sin(np.pi * x) ** 2


def synthesize_voice(
    source: SourcePhysics,
    utterance: Sequence[tuple[float, float]],
) -> np.ndarray:
    """Deterministic source-filter-like voiced waveform at 16 kHz.

    ``utterance`` controls only temporal amplitude and pitch motion.  Source
    identity remains in fundamental, formant envelope, spectral tilt, and the
    fixed high-frequency breath components.  No random noise or fitted model
    participates.
    """

    n_total = int(round(SAMPLE_RATE_HZ * DURATION_S))
    segment_edges = np.linspace(0, n_total, len(utterance) + 1, dtype=int)
    waveform = np.zeros(n_total, dtype=np.float64)

    for segment_index, (amplitude, pitch_delta) in enumerate(utterance):
        start = int(segment_edges[segment_index])
        end = int(segment_edges[segment_index + 1])
        n = end - start
        local_time = np.arange(n, dtype=np.float64) / SAMPLE_RATE_HZ
        envelope = float(amplitude) * _raised_cosine_envelope(n)
        f0 = source.fundamental_hz * (1.0 + float(pitch_delta))

        voiced = np.zeros(n, dtype=np.float64)
        max_harmonic = int((NYQUIST_HZ - 1) // f0)
        for harmonic in range(1, max_harmonic + 1):
            frequency = harmonic * f0
            formant_support = sum(
                math.exp(-0.5 * ((frequency - formant) /
                                 (formant / 7.0)) ** 2)
                for formant in source.formants_hz
            )
            amplitude_h = ((0.16 + formant_support) /
                           (harmonic ** source.spectral_tilt))
            voiced += amplitude_h * np.sin(
                2.0 * np.pi * frequency * local_time
                + harmonic * np.pi / 9.0
            )

        breath = sum(
            np.sin(2.0 * np.pi * frequency * local_time + np.pi / 7.0)
            for frequency in source.breath_hz
        )
        waveform[start:end] = envelope * (voiced + 0.035 * breath)

    peak = float(np.max(np.abs(waveform)))
    return waveform / peak if peak > 0.0 else waveform


def synthesize_music() -> np.ndarray:
    """Deterministic chord/arpeggio control spanning the audible spectrum."""

    n_total = int(round(SAMPLE_RATE_HZ * DURATION_S))
    t = np.arange(n_total, dtype=np.float64) / SAMPLE_RATE_HZ
    base_notes = (220.0, 277.182631, 329.627557, 440.0)
    waveform = np.zeros(n_total, dtype=np.float64)
    for note_index, note in enumerate(base_notes):
        rhythmic = 0.5 + 0.5 * np.sin(
            2.0 * np.pi * (note_index + 1) * t / DURATION_S
        )
        for harmonic in range(1, int((NYQUIST_HZ - 1) // note) + 1):
            waveform += (
                rhythmic
                * np.sin(2.0 * np.pi * note * harmonic * t
                         + note_index * np.pi / 5.0)
                / (harmonic ** 1.25)
            )
    waveform *= _raised_cosine_envelope(n_total)
    peak = float(np.max(np.abs(waveform)))
    return waveform / peak if peak > 0.0 else waveform


def build_stimuli() -> dict[str, np.ndarray]:
    source_a_one = synthesize_voice(SOURCE_A, UTTERANCE_ONE)
    source_a_two = synthesize_voice(SOURCE_A, UTTERANCE_TWO)
    source_b_one = synthesize_voice(SOURCE_B, UTTERANCE_ONE)
    music = synthesize_music()
    mixture = source_a_two + source_b_one + music
    mixture /= float(np.max(np.abs(mixture)))
    return {
        "source_a_utterance_one": source_a_one,
        "source_a_utterance_two": source_a_two,
        "source_b_utterance_one": source_b_one,
        "music": music,
        "mixture": mixture,
    }


def frequency_time_lanes(signal: np.ndarray) -> dict[str, np.ndarray]:
    """Return explicit positive spectral-energy trajectories for all lanes."""

    if signal.ndim != 1 or len(signal) < FRAME_LENGTH:
        raise ValueError("signal must be a one-dimensional full audio window")
    window = np.hanning(FRAME_LENGTH)
    frequencies = np.fft.rfftfreq(FRAME_LENGTH, d=1.0 / SAMPLE_RATE_HZ)
    starts = range(0, len(signal) - FRAME_LENGTH + 1, FRAME_HOP)
    spectra = []
    for start in starts:
        frame = signal[start:start + FRAME_LENGTH] * window
        spectra.append(np.abs(np.fft.rfft(frame)) ** 2)
    power = np.asarray(spectra, dtype=np.float64)

    lanes: dict[str, np.ndarray] = {}
    numerical_floor = np.finfo(np.float64).tiny
    for low_hz, high_hz in FREQUENCY_LANES_HZ:
        if high_hz == NYQUIST_HZ:
            mask = (frequencies >= low_hz) & (frequencies <= high_hz)
        else:
            mask = (frequencies >= low_hz) & (frequencies < high_hz)
        energy = np.sum(power[:, mask], axis=1)
        lanes[f"{low_hz}-{high_hz}Hz"] = np.maximum(
            energy, numerical_floor
        )
    return lanes


def _gate_record(gate: object) -> dict[str, int]:
    return {"start_idx": int(gate.start_idx), "end_idx": int(gate.end_idx)}


def run_lane_l0_l4(
    values: np.ndarray,
    relevance_mode: RelevanceMode,
) -> dict[str, object]:
    """Execute unchanged canonical UF layers and retain their explicit output."""

    frame = pd.DataFrame({"signal": values}, index=np.arange(len(values)))
    sev = compute_sev_series(
        frame,
        field_col="signal",
        relevance_mode=relevance_mode,
    )
    gates = segment_gates(sev)
    interpretations = interpret_gates(sev, gates)
    resonance = compute_resonance(interpretations)
    decisions = compute_directional_signal(resonance)
    dsf = compute_dsf(decisions)
    return {
        "relevance_mode": relevance_mode.value,
        "l0_sev": [asdict(value) for value in sev],
        "l1_gates": [_gate_record(value) for value in gates],
        "l2_interpretations": [
            {
                **asdict(value),
                "gate": _gate_record(value.gate),
            }
            for value in interpretations
        ],
        "l3_resonance": [
            {
                "gate": _gate_record(value.gate),
                "R_k": value.R_k,
                "URF_k": value.URF_k,
                "g_k": value.g_k,
                "U_k": value.U_k,
                "IAS_k": value.IAS_k,
                "Hyst_k": value.Hyst_k,
                "raw_k": value.raw_k,
            }
            for value in resonance
        ],
        "l4_dsf": [
            {
                "gate": _gate_record(value.gate),
                **{name: float(getattr(value, name)) for name in FIELD_NAMES},
            }
            for value in dsf
        ],
    }


def expand_l4_to_time(lane_result: Mapping[str, object], n_frames: int) -> np.ndarray:
    """Expand gate-held fields onto their exact original frame intervals."""

    expanded = np.zeros((n_frames, len(FIELD_NAMES)), dtype=np.float64)
    for field_record in lane_result["l4_dsf"]:
        gate = field_record["gate"]
        values = np.asarray(
            [field_record[name] for name in FIELD_NAMES], dtype=np.float64
        )
        expanded[gate["start_idx"]:gate["end_idx"] + 1, :] = values
    return expanded


def full_field_tensor(
    lanes: Mapping[str, np.ndarray],
    lane_results: Mapping[str, Mapping[str, object]],
) -> np.ndarray:
    lane_names = tuple(lanes)
    n_frames = len(lanes[lane_names[0]])
    return np.stack(
        [expand_l4_to_time(lane_results[name], n_frames) for name in lane_names],
        axis=0,
    )


def componentwise_field_distance(
    left: np.ndarray,
    right: np.ndarray,
) -> dict[str, float]:
    if left.shape != right.shape:
        raise ValueError("full-field tensors must have identical topology")
    difference = left - right
    return {
        name: float(np.sqrt(np.mean(difference[:, :, index] ** 2)))
        for index, name in enumerate(FIELD_NAMES)
    }


def componentwise_dominance(
    candidate: Mapping[str, float],
    alternative: Mapping[str, float],
) -> bool:
    """Strict all-field order; ties or crossed fields remain unknown."""

    return all(candidate[name] < alternative[name] for name in FIELD_NAMES)


def secondary_structure(lanes: Mapping[str, np.ndarray], tensor: np.ndarray) -> dict[str, object]:
    """Compute non-authoritative Krimelack/3^/balanced-ternary structure."""

    windings: list[int] = []
    for values in lanes.values():
        centered = values - float(np.mean(values))
        scale = float(np.std(centered))
        normalized = centered / scale if scale > 0.0 else centered
        krimelack = Krimelack()
        krimelack.feed_signal(normalized)
        windings.append(int(krimelack.winding))

    terminal_d = tensor[:, -1, FIELD_NAMES.index("D_k")]
    balanced_trits = tuple(int(np.sign(value)) for value in terminal_d)
    powers_of_three = tuple(3 ** index for index in range(len(windings)))
    return {
        "authority": False,
        "krimelack_windings": windings,
        "powers_of_three": list(powers_of_three),
        "balanced_ternary_trits": list(balanced_trits),
        "balanced_ternary_code": int(sum(
            trit * weight for trit, weight in zip(balanced_trits, powers_of_three)
        )),
        "chi": int(sum(
            winding * weight for winding, weight in zip(windings, powers_of_three)
        )),
    }


def _atlas_candidates(atlas: LivingAtlas, chi: int) -> list[int]:
    return sorted({
        int(entry["motif"])
        for entry in atlas.entries.get(chi, [])
        if entry["strength"] > 0.0
    })


def isolated_atlas_recurrence(
    secondary_by_case: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Exercise exact-chi recurrence and explicitly retain unknown/collision."""

    atlas = LivingAtlas(band=0)
    exemplars = {
        "source_a_utterance_one": 1,
        "source_b_utterance_one": 2,
        "music": 3,
    }
    for tick, (case_name, motif_id) in enumerate(exemplars.items(), start=1):
        atlas.record(
            "source_recurrence_experiment",
            motif_id,
            int(secondary_by_case[case_name]["chi"]),
            tick=tick,
            source="isolated_experiment",
        )

    queries: dict[str, object] = {}
    for case_name in ("source_a_utterance_two", "mixture"):
        chi = int(secondary_by_case[case_name]["chi"])
        candidates = _atlas_candidates(atlas, chi)
        if len(candidates) == 1:
            status = "unique_recurrence"
        elif candidates:
            status = "collision_unknown"
        else:
            status = "no_recurrence_unknown"
        queries[case_name] = {
            "chi": chi,
            "status": status,
            "candidate_motif_ids": candidates,
        }

    # Prove the ambiguity contract independently of whether this particular
    # synthetic set happens to collide naturally.
    collision_atlas = LivingAtlas(band=0)
    collision_chi = int(secondary_by_case["source_a_utterance_one"]["chi"])
    collision_atlas.record("source_recurrence_experiment", 1, collision_chi,
                           tick=1, source="isolated_experiment")
    collision_atlas.record("source_recurrence_experiment", 2, collision_chi,
                           tick=2, source="isolated_experiment")
    collision_candidates = _atlas_candidates(collision_atlas, collision_chi)
    return {
        "authority": False,
        "atlas_isolated": True,
        "trained_exemplars": exemplars,
        "queries": queries,
        "forced_collision_check": {
            "chi": collision_chi,
            "candidate_motif_ids": collision_candidates,
            "status": (
                "collision_unknown" if len(collision_candidates) > 1
                else "invalid_forced_choice"
            ),
        },
        "atlas_live_bindings": atlas.n_live_bindings(),
        "atlas_total_entries": sum(len(value) for value in atlas.entries.values()),
    }


def _separation_report(
    tensors: Mapping[str, np.ndarray],
) -> dict[str, object]:
    within = componentwise_field_distance(
        tensors["source_a_utterance_one"],
        tensors["source_a_utterance_two"],
    )
    between_same_utterance = componentwise_field_distance(
        tensors["source_a_utterance_one"],
        tensors["source_b_utterance_one"],
    )
    between_cross_utterance = componentwise_field_distance(
        tensors["source_a_utterance_two"],
        tensors["source_b_utterance_one"],
    )
    per_field_strict = {
        name: within[name] < min(
            between_same_utterance[name], between_cross_utterance[name]
        )
        for name in FIELD_NAMES
    }

    exemplar_a = tensors["source_a_utterance_one"]
    exemplar_b = tensors["source_b_utterance_one"]
    query_results: dict[str, object] = {}
    for case_name in ("source_a_utterance_two", "music", "mixture"):
        distance_a = componentwise_field_distance(tensors[case_name], exemplar_a)
        distance_b = componentwise_field_distance(tensors[case_name], exemplar_b)
        a_dominates = componentwise_dominance(distance_a, distance_b)
        b_dominates = componentwise_dominance(distance_b, distance_a)
        if a_dominates == b_dominates:
            status = "unknown"
            candidate = None
        elif a_dominates:
            status = "componentwise_dominant"
            candidate = "source_a"
        else:
            status = "componentwise_dominant"
            candidate = "source_b"
        query_results[case_name] = {
            "status": status,
            "candidate": candidate,
            "distance_to_source_a": distance_a,
            "distance_to_source_b": distance_b,
        }

    return {
        "distance_is_measurement_not_identity_authority": True,
        "within_source_different_utterance": within,
        "between_source_same_utterance": between_same_utterance,
        "between_source_cross_utterance": between_cross_utterance,
        "within_strictly_below_both_between_by_field": per_field_strict,
        "all_fields_strictly_separated": all(per_field_strict.values()),
        "exemplar_queries": query_results,
    }


def _waveform_digest(signal: np.ndarray) -> str:
    return hashlib.sha256(signal.astype("<f8", copy=False).tobytes()).hexdigest()


def build_report() -> dict[str, object]:
    tracemalloc.start()
    experiment_start = time.perf_counter()
    stimuli = build_stimuli()

    cases: dict[str, object] = {}
    authority_tensors: dict[str, np.ndarray] = {}
    diagnostic_tensors: dict[str, np.ndarray] = {}
    secondary_by_case: dict[str, object] = {}

    for case_name, signal in stimuli.items():
        case_start = time.perf_counter()
        lanes = frequency_time_lanes(signal)
        authority = {
            lane_name: run_lane_l0_l4(values, RelevanceMode.LEGACY_UNIT)
            for lane_name, values in lanes.items()
        }
        diagnostic = {
            lane_name: run_lane_l0_l4(
                values, RelevanceMode.STRUCTURAL_ACTIVITY_DIAGNOSTIC
            )
            for lane_name, values in lanes.items()
        }
        authority_tensor = full_field_tensor(lanes, authority)
        diagnostic_tensor = full_field_tensor(lanes, diagnostic)
        authority_tensors[case_name] = authority_tensor
        diagnostic_tensors[case_name] = diagnostic_tensor
        secondary = secondary_structure(lanes, authority_tensor)
        secondary_by_case[case_name] = secondary
        cases[case_name] = {
            "sample_count": int(len(signal)),
            "duration_s": len(signal) / SAMPLE_RATE_HZ,
            "waveform_sha256": _waveform_digest(signal),
            "waveform_peak": float(np.max(np.abs(signal))),
            "frequency_time_lane_samples": {
                name: [float(value) for value in values]
                for name, values in lanes.items()
            },
            "authority_l0_l4": authority,
            "diagnostic_only_l0_l4": diagnostic,
            "secondary_structure": secondary,
            "runtime_ms": (time.perf_counter() - case_start) * 1000.0,
        }

    authority_separation = _separation_report(authority_tensors)
    diagnostic_separation = _separation_report(diagnostic_tensors)
    atlas_recurrence = isolated_atlas_recurrence(secondary_by_case)

    authority_supports_identity = bool(
        authority_separation["all_fields_strictly_separated"]
        and authority_separation["exemplar_queries"][
            "source_a_utterance_two"
        ]["candidate"] == "source_a"
    )
    if authority_supports_identity:
        identity_status = "synthetic_structural_separation_observed"
        identity_reason = (
            "the unchanged authority-mode field strictly separated the controlled "
            "within-source pair from both between-source pairs in every retained "
            "field; this is evidence for this synthetic set, not a production "
            "speaker-identity claim"
        )
    else:
        identity_status = "identity_not_decidable"
        identity_reason = (
            "the unchanged authority-mode full field did not provide strict "
            "componentwise source separation; no threshold, chi collision rule, "
            "or diagnostic-only relevance result may force an identity"
        )

    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed_ms = (time.perf_counter() - experiment_start) * 1000.0
    return {
        "schema": "tfe.experiment.full_field_source_identity.v1",
        "scope": {
            "isolated": True,
            "production_code_modified": False,
            "machine_learning_used": False,
            "fitted_threshold_used": False,
            "l0_l4_modified": False,
        },
        "kernel_contract": {
            "authority_relevance_mode": RelevanceMode.LEGACY_UNIT.value,
            "authority_relevance_limitation": (
                "uf_core.layer0 legacy_unit sets relevance r(t)=1 for every sample"
            ),
            "diagnostic_relevance_mode": (
                RelevanceMode.STRUCTURAL_ACTIVITY_DIAGNOSTIC.value
            ),
            "diagnostic_is_production_authority": False,
            "retained_l4_fields": list(FIELD_NAMES),
            "retained_upstream_layers": ["L0_SEV", "L1_gate", "L2_ISF", "L3_resonance"],
        },
        "capture_topology": {
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "nyquist_hz": NYQUIST_HZ,
            "frame_length_samples": FRAME_LENGTH,
            "frame_hop_samples": FRAME_HOP,
            "frequency_lanes_hz": [list(value) for value in FREQUENCY_LANES_HZ],
            "full_nyquist_coverage": (
                FREQUENCY_LANES_HZ[0][0] == 0
                and FREQUENCY_LANES_HZ[-1][1] == NYQUIST_HZ
                and all(left[1] == right[0] for left, right in zip(
                    FREQUENCY_LANES_HZ, FREQUENCY_LANES_HZ[1:]
                ))
            ),
        },
        "controlled_comparisons": {
            "same_source_different_utterance": [
                "source_a_utterance_one", "source_a_utterance_two"
            ],
            "different_source_same_utterance": [
                "source_a_utterance_one", "source_b_utterance_one"
            ],
            "music": "music",
            "mixture": "mixture",
        },
        "cases": cases,
        "authority_separation": authority_separation,
        "diagnostic_only_separation": diagnostic_separation,
        "isolated_living_atlas_recurrence": atlas_recurrence,
        "identity_decision": {
            "status": identity_status,
            "reason": identity_reason,
            "chi_or_ternary_used_as_authority": False,
            "diagnostic_relevance_used_as_authority": False,
        },
        "resources": {
            "runtime_ms": elapsed_ms,
            "tracemalloc_current_bytes": int(current_bytes),
            "tracemalloc_peak_bytes": int(peak_bytes),
            "audio_input_bytes": int(sum(value.nbytes for value in stimuli.values())),
        },
    }


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_report()
    print(json.dumps(
        report,
        allow_nan=False,
        indent=2 if args.pretty else None,
        separators=None if args.pretty else (",", ":"),
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
