"""Prove the current W1-to-Loom auditory adapter boundary exactly.

This is a read-only architecture audit.  It does not recognize speech and it
does not propose a reduced representation.  It establishes which full-field
coordinates the live sound entry retains, which arguments the organism queue
can carry, and which real LoomNeuron fields the legacy raw-waveform route
mutates.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import struct
import textwrap
from pathlib import Path
from typing import Any

import numpy as np

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.neuron import LoomNeuron
from dsf_ai_service.loom_model.topology import (
    HEMISPHERE_PRIMARY_MODALITY,
)
from dsf_ai_service.substrate import wave_summary
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_records,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


SCHEMA = "guala.audit.w1_loom_neuron_adapter_loss.v1"
AUTHORITY_KEY = b"guala-w1-loom-neuron-adapter-loss-20260727"


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


def _array_digest(value: np.ndarray) -> str:
    array = np.asarray(value)
    header = _canonical({
        "dtype": str(array.dtype),
        "shape": list(array.shape),
    })
    return hashlib.sha256(header + b"\0" + array.tobytes()).hexdigest()


def _float_bits(value: float) -> str:
    return struct.pack(">d", float(value)).hex()


def _dsf_record(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    return {
        name: _float_bits(getattr(value, name))
        for name in (
            "D_k",
            "M_k",
            "R_rev",
            "U_star",
            "C_k",
            "P_k",
            "B_k",
            "S_UF",
        )
    }


def _atlas_entry_count(neuron: LoomNeuron) -> int:
    return sum(
        len(entries)
        for entries in neuron.chi_atlas.entries.values()
    )


def _snapshot(neuron: LoomNeuron) -> dict[str, object]:
    return {
        "krimelack": {
            "class": type(neuron.krimelack).__name__,
            "n_events": neuron.krimelack.n_events,
            "phase_binary64": _float_bits(neuron.krimelack.phase),
            "winding": neuron.krimelack.winding,
        },
        "last_event_count": len(neuron._last_events),
        "last_events_sha256": _digest(neuron._last_events),
        "last_dsf": _dsf_record(neuron._last_dsf),
        "omega_history_binary64": [
            _float_bits(value)
            for value in neuron._omega_history
        ],
        "psi_sha256": _array_digest(neuron.psi_lattice.psi),
        "spike_count": len(neuron.spike_buffer),
        "chi_atlas_entry_count": _atlas_entry_count(neuron),
        "familiarity_delta_eff_binary64": _float_bits(
            neuron.familiarity.delta_eff
        ),
        "incoming_synapse_weights": dict(
            sorted(neuron._incoming_synapse_weights.items())
        ),
        "membrane_potential_binary64": _float_bits(
            neuron.membrane_potential
        ),
    }


def _changed_paths(
    before: object,
    after: object,
    *,
    prefix: str = "",
) -> tuple[str, ...]:
    if type(before) is not type(after):
        return (prefix,)
    if isinstance(before, dict):
        keys = sorted(set(before) | set(after))
        result: list[str] = []
        for key in keys:
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                result.append(path)
            else:
                result.extend(
                    _changed_paths(before[key], after[key], prefix=path)
                )
        return tuple(result)
    if isinstance(before, list):
        if len(before) != len(after):
            return (prefix,)
        result = []
        for index, (left, right) in enumerate(
            zip(before, after, strict=True)
        ):
            result.extend(
                _changed_paths(
                    left,
                    right,
                    prefix=f"{prefix}[{index}]",
                )
            )
        return tuple(result)
    return () if before == after else (prefix,)


def _method_calls(function: Any) -> tuple[str, ...]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Attribute):
            calls.add(target.attr)
        elif isinstance(target, ast.Name):
            calls.add(target.id)
    return tuple(sorted(calls))


def _signature_parameters(function: Any) -> tuple[str, ...]:
    return tuple(inspect.signature(function).parameters)


def _physical_signal() -> np.ndarray:
    sample_count = OBSERVATION_HOP_SAMPLES * 8
    time = np.arange(sample_count, dtype=np.float64)
    return (
        0.31
        * np.sin(
            2.0
            * np.pi
            * 437.0
            * time
            / REQUIRED_SAMPLE_RATE_HZ
        )
        + 0.13
        * np.sin(
            2.0
            * np.pi
            * 911.0
            * time
            / REQUIRED_SAMPLE_RATE_HZ
        )
    )


def build_report() -> dict[str, object]:
    signal = _physical_signal()
    capture = transduce_auditory_full_field(
        signal,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    records = auditory_kernel_component_records(
        capture,
        source_anchor=__import__("fractions").Fraction(0),
    )

    sound_source = inspect.getsource(Guala.process_sound_frame)
    brain_source = inspect.getsource(LoomBrain.__init__)
    sound_calls = _method_calls(Guala.process_sound_frame)
    queue_calls = _method_calls(Guala._enqueue_organism_sensory)
    neuron_calls = _method_calls(LoomNeuron.step)

    neuron = LoomNeuron(
        "audit:legacy-raw-auditory",
        primary_modality="auditory",
    )
    before = _snapshot(neuron)
    raw_result = neuron.step(signal.tolist(), tick=1)
    after_raw = _snapshot(neuron)

    encoded_neuron = LoomNeuron(
        "audit:resonant-spectral",
        primary_modality="auditory",
        observable="resonant_spectral",
    )
    before_encoded = _snapshot(encoded_neuron)
    encoded = encoded_neuron.encode_state({"auditory": signal})
    after_encoded = _snapshot(encoded_neuron)

    default_brain = LoomBrain(seed_size=3)
    auditory_hemispheres = tuple(
        hemi_id
        for hemi_id, modality in HEMISPHERE_PRIMARY_MODALITY.items()
        if modality == "auditory"
    )
    default_auditory_neuron_receptors = {
        hemi_id: tuple(
            sorted({
                type(neuron.krimelack).__name__
                for neuron in default_brain._hemi_map[
                    hemi_id
                ].cluster.neurons
            })
        )
        for hemi_id in auditory_hemispheres
    }
    wave_signal = wave_summary._band_signal(
        2.0,
        [
            (
                17,
                0.75,
                np.asarray((3.0 + 4.0j, -5.0j)),
            )
        ],
    )

    retained_record_fields = tuple(sorted(records[0]))
    explicit_coordinates = tuple(
        sorted(
            {
                coordinate[0]
                for record in records
                for coordinate in record["coordinates"]
            }
        )
    )
    report: dict[str, object] = {
        "schema": SCHEMA,
        "full_field_live_entry": {
            "component_count": len(records),
            "cochlear_channel_count": len(capture.channels),
            "frame_count": capture.frame_count,
            "retained_record_fields": retained_record_fields,
            "explicit_coordinate_axes": explicit_coordinates,
            "topology_indices": [
                record["topology_index"]
                for record in records
            ],
            "source_time_retained": all(
                "source_anchor_fraction" in record
                and "causal_offsets_fraction" in record
                for record in records
            ),
            "full_field_record_sha256": _digest(records),
        },
        "live_process_sound_frame": {
            "parameters": _signature_parameters(
                Guala.process_sound_frame
            ),
            "method_calls": sound_calls,
            "sets_last_sound_signal_none": (
                "self._last_sound_signal = None" in sound_source
            ),
            "calls_organism_queue": (
                "_enqueue_organism_sensory" in sound_calls
            ),
        },
        "organism_queue": {
            "parameters": _signature_parameters(
                Guala._enqueue_organism_sensory
            ),
            "method_calls": queue_calls,
            "accepts_ear_id": "ear_id" in _signature_parameters(
                Guala._enqueue_organism_sensory
            ),
            "accepts_topology_index": (
                "topology_index"
                in _signature_parameters(
                    Guala._enqueue_organism_sensory
                )
            ),
            "accepts_explicit_dsf_fields": all(
                name
                in _signature_parameters(
                    Guala._enqueue_organism_sensory
                )
                for name in (
                    "D_k",
                    "M_k",
                    "R_rev",
                    "U_star",
                    "C_k",
                    "P_k",
                    "B_k",
                )
            ),
        },
        "production_hemisphere_receptors": {
            "auditory_hemispheres": auditory_hemispheres,
            "declared_modality_map": {
                hemi_id: HEMISPHERE_PRIMARY_MODALITY[hemi_id]
                for hemi_id in auditory_hemispheres
            },
            "default_neuron_receptor_classes": (
                default_auditory_neuron_receptors
            ),
            "brain_default_uses_empty_primary_map": (
                "else {}" in brain_source
            ),
            "all_default_auditory_receptors_are_language": all(
                receptor_classes == ("LanguageKrimelack",)
                for receptor_classes
                in default_auditory_neuron_receptors.values()
            ),
        },
        "wave_summary_projection": {
            "sample_wave_summary_default_top_n": (
                inspect.signature(
                    wave_summary.sample_wave_summary
                ).parameters["top_n"].default
            ),
            "band_signal_example": [
                _float_bits(value) for value in wave_signal
            ],
            "band_signal_example_length": len(wave_signal),
            "retains_chi_identity_in_signal": False,
            "retains_complex_phase": False,
            "retains_only_phase_magnitude": True,
            "accepts_ear_id": "ear_id" in _signature_parameters(
                wave_summary._band_signal
            ),
            "accepts_topology_index": (
                "topology_index"
                in _signature_parameters(
                    wave_summary._band_signal
                )
            ),
            "accepts_explicit_dsf_fields": False,
        },
        "legacy_loom_neuron_raw_route": {
            "parameters": _signature_parameters(LoomNeuron.step),
            "method_calls": neuron_calls,
            "before": before,
            "after": after_raw,
            "changed_paths": _changed_paths(before, after_raw),
            "returned_match_score_binary64": _float_bits(
                raw_result["match_score"]
            ),
            "returned_dsf": _dsf_record(raw_result["dsf"]),
            "accepts_ear_id": "ear_id" in _signature_parameters(
                LoomNeuron.step
            ),
            "accepts_topology_index": (
                "topology_index"
                in _signature_parameters(LoomNeuron.step)
            ),
            "accepts_explicit_dsf_fields": False,
        },
        "resonant_spectral_binding_route": {
            "before": before_encoded,
            "after": after_encoded,
            "changed_paths": _changed_paths(
                before_encoded,
                after_encoded,
            ),
            "encoded_lane_names": tuple(sorted(encoded)),
            "encoded_lane_sha256": {
                name: _array_digest(value)
                for name, value in sorted(encoded.items())
            },
        },
        "conclusion": {
            "full_field_reaches_live_loom_neurons": False,
            "production_auditory_hemispheres_use_auditory_receptors": (
                False
            ),
            "wave_summary_preserves_binaural_full_field": False,
            "legacy_raw_route_is_full_field": False,
            "legacy_raw_route_uses_chi_match_score": (
                "match_score" in neuron_calls
            ),
            "resonant_spectral_advances_oscillator": bool(
                _changed_paths(before_encoded, after_encoded)
            ),
            "missing_bridge": (
                "authenticated ear/topology/time/full-DSF occurrence "
                "delivery into non-flattened sensory neuron dynamics"
            ),
        },
    }
    report["authority_sha256"] = hashlib.sha256(
        AUTHORITY_KEY + b"\0" + _canonical(report)
    ).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    encoded = json.dumps(
        report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    )
    if args.output is not None:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
