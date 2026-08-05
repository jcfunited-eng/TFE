"""Compare the ratified generic map with the physical pressure-ratio map.

This is a diagnostic only.  It executes the unchanged canonical L0--L4
functions over the same event-local cochlear pressure envelopes using:

* the live generic native-sensory map, F = 1 + pressure / 2; and
* a physical pressure-ratio field, F = pressure + one PCM quantum.

The second field differs only by an irrelevant constant unit scale from
pressure measured relative to one PCM quantum.  No kernel threshold, field,
or L0--L4 function is modified.
"""

from __future__ import annotations

import hashlib
import io
import json
import wave
from pathlib import Path

import numpy as np
import pandas as pd

from dsf_ai_service.substrate.auditory_reciprocity import (
    PCM_PRESSURE_QUANTUM,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from tools.probe_auditory_full_field_discrimination import _decode_pcm
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import (
    build_gate_l1_state,
    compute_deviation,
    segment_gates,
)
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


RECORDINGS = (
    Path("/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 1.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 2.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Daddy says Hello.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Your Name is Guala.mp3"),
)


def _wav(pcm: bytes) -> bytes:
    payload = io.BytesIO()
    with wave.open(payload, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16_000)
        target.writeframes(pcm)
    return payload.getvalue()


def _field_result(values: tuple[float, ...]) -> dict[str, object]:
    sev = tuple(compute_sev_series(pd.DataFrame({"field": values}), "field"))
    deviation = compute_deviation(sev)
    gates = tuple(segment_gates(sev))
    l1 = tuple(build_gate_l1_state(sev, gates))
    l2 = tuple(interpret_gates(sev, gates))
    l3 = tuple(compute_resonance(l2))
    l4 = tuple(compute_dsf(compute_directional_signal(list(l3))))
    payload = [
        {
            "start": value.gate.start_idx,
            "end": value.gate.end_idx,
            "D_k": float(value.D_k).hex(),
            "M_k": float(value.M_k).hex(),
            "R_rev_k": float(value.R_rev_k).hex(),
            "U_star_k": float(value.U_star_k).hex(),
            "C_k": float(value.C_k).hex(),
            "P_k": float(value.P_k).hex(),
            "B_k": float(value.B_k).hex(),
        }
        for value in l4
    ]
    encoded = json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "gate_count": len(gates),
        "max_deviation": float(np.max(deviation)),
        "l4_sha256": hashlib.sha256(encoded).hexdigest(),
        "nonzero_direction_count": sum(value.D_k != 0.0 for value in l4),
        "nonzero_motion_count": sum(value.M_k != 0.0 for value in l4),
    }


def _recording(path: Path) -> dict[str, object]:
    _event_wav, _sample_count, _pcm_bytes, event = Guala._auditory_tutor_event(
        _wav(_decode_pcm(path))
    )
    generic = []
    pressure_ratio = []
    quantum = float(PCM_PRESSURE_QUANTUM)
    for channel in event.channels:
        pressure = tuple(
            float(value) for value in channel.pressure_envelope_full_scale
        )
        generic.append(_field_result(tuple(1.0 + value / 2.0 for value in pressure)))
        pressure_ratio.append(
            _field_result(tuple(value + quantum for value in pressure))
        )
    return {
        "path": str(path),
        "event_frames": event.frame_count,
        "generic": {
            "gate_counts": [value["gate_count"] for value in generic],
            "max_deviation": max(
                value["max_deviation"] for value in generic
            ),
            "distinct_l4_channels": len({
                value["l4_sha256"] for value in generic
            }),
            "l4_sha256s": [
                value["l4_sha256"] for value in generic
            ],
        },
        "pressure_ratio": {
            "gate_counts": [
                value["gate_count"] for value in pressure_ratio
            ],
            "max_deviation": max(
                value["max_deviation"] for value in pressure_ratio
            ),
            "distinct_l4_channels": len({
                value["l4_sha256"] for value in pressure_ratio
            }),
            "l4_sha256s": [
                value["l4_sha256"] for value in pressure_ratio
            ],
            "nonzero_direction_counts": [
                value["nonzero_direction_count"]
                for value in pressure_ratio
            ],
            "nonzero_motion_counts": [
                value["nonzero_motion_count"]
                for value in pressure_ratio
            ],
        },
    }


def main() -> None:
    reports = tuple(_recording(path) for path in RECORDINGS)
    print(json.dumps({
        "schema": "guala.audit.auditory_pressure_adapter_scale.v1",
        "recordings": reports,
        "cross_recording": {
            "generic_channel_fingerprints_unique": [
                len({
                    report["generic"]["l4_sha256s"][channel]
                    for report in reports
                })
                for channel in range(16)
            ],
            "pressure_ratio_channel_fingerprints_unique": [
                len({
                    report["pressure_ratio"]["l4_sha256s"][channel]
                    for report in reports
                })
                for channel in range(16)
            ],
        },
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
