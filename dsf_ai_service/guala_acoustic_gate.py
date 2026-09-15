"""Level 1 of her structural hierarchy: the acoustic gate.

A spoken sound as one discrete event with a beginning and an end, whose structure
is computed inside its own boundaries so that the same sound met again is the
same event whatever came before it (docs/GL-SPC-ACOUSTIC-GATE-C1-20260915-v1.md).

Everything here is a pure function of cochlear frames; nothing is named, matched
to text, or compared by distance. The declared numbers are stated once below.
The open event is a plain dict so that her body carries it across beats and
restarts exactly; the same step function serves the offline harness and her beat.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Sequence

import pandas as pd

from dsf_ai_service.guala_cochlea import CHANNELS_PER_EAR, one_self_hearing_hop
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import build_gate_l1_state, segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf

# Her ear's bands (the same grouping her ear streams use): 16 ERB channels into six.
EAR_BAND_CHANNELS = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11), (12, 13), (14, 15))
EAR_BANDS = len(EAR_BAND_CHANNELS)
FRAMES_PER_HOP = 25                 # 26 envelope frames a hop; the closing boundary frame belongs to the next hop
GRAIN = 6                           # decimals kept per frame value (her streams' own grain), so a frame re-encodes exactly
# The boundary law, declared once (spec §3):
SOUNDING_FRACTION_OF_PEAK = 8       # a frame sounds when it reaches one eighth of the event's own running peak
PAUSE_FRAMES = 12                   # 120 ms of quiet closes an event (the gap between spoken words)
MAX_EVENT_FRAMES = FRAMES_PER_HOP * 12   # twelve beats: a long sound becomes a sequence of events
HEARD_ENERGY_FLOOR = 0.004          # her hearing floor on the hop's peak profile (the organism's own)
# The event's own structure (spec §4):
KERNEL_MINIMUM = 24                 # frames the kernel needs; shorter events keep their quantized shapes
SHAPE_EIGHTHS = 8                   # a short event's band fractions are kept in eighths (declared once)
STREAM_FLOOR = 0.05                 # the organism's own floor under every kernel series

# A frame: (energy, band_0 .. band_5); energy = the mean envelope over the 16 channels,
# each band the fraction of the frame's energy in it (all zero in silence).
Frame = tuple[float, ...]
SILENT_FRAME: Frame = (0.0,) * (1 + EAR_BANDS)


@dataclass(frozen=True, slots=True)
class AcousticEvent:
    start_frame: int                 # absolute frame index at which it opened
    end_frame: int                   # absolute frame index of its last sounding frame (inclusive)
    peak: float                      # its own peak frame energy
    key: str                         # sha-256 (16 hex) of its structure
    gates_per_band: tuple[int, ...]  # how many gates the kernel found inside it per band (0s when too short)
    tokens: tuple[tuple[str, ...], ...]   # the per-band gate tokens (regime + seven signs), or the quantized shapes

    @property
    def frames(self) -> int:
        return self.end_frame - self.start_frame + 1

    @property
    def beats(self) -> int:
        return (self.frames + FRAMES_PER_HOP - 1) // FRAMES_PER_HOP


def frames_of_cochleae(cochleae: Sequence[Sequence[float]]) -> tuple[Frame, ...]:
    """One hop's 25 frames at her ear from the cochlea's channels (one ear; the two
    are identical for a mono card), each value at her grain."""

    one_ear = cochleae[:CHANNELS_PER_EAR]
    frames = []
    for index in range(FRAMES_PER_HOP):
        channels = [float(one_ear[channel][index]) for channel in range(CHANNELS_PER_EAR)]
        total = sum(channels)
        if total <= 0.0:
            frames.append(SILENT_FRAME)
            continue
        energy = round(total / CHANNELS_PER_EAR, GRAIN)
        shape = tuple(round(sum(channels[c] for c in band) / total, GRAIN) for band in EAR_BAND_CHANNELS)
        frames.append((energy,) + shape)
    return tuple(frames)


def hop_frames(pressure_s16le: bytes) -> tuple[tuple[Frame, ...], bool]:
    """One hop's frames, and whether the hop is heard at all by the floor of her hop
    law (its peak profile above her hearing floor; the organism adds its ambient
    law). Frames of an unheard hop are silence to the gate law."""

    _times, _legacy, cochleae, _consumed = one_self_hearing_hop(pressure_s16le)
    one_ear = cochleae[:CHANNELS_PER_EAR]
    peak_profile_energy = sum(max(one_ear[channel]) for channel in range(CHANNELS_PER_EAR)) / CHANNELS_PER_EAR
    return frames_of_cochleae(cochleae), peak_profile_energy >= HEARD_ENERGY_FLOOR


def _sign(value: float) -> str:
    return "+" if value > 0 else ("-" if value < 0 else "0")


def event_structure(frames: Sequence[Sequence[float]]) -> tuple[str, tuple[int, ...], tuple[tuple[str, ...], ...]]:
    """The structure of an event from its own frames only: per band, the kernel's
    gates inside it (regime letter and seven sign atoms) when it is long enough,
    else its per-frame shapes in eighths. Returns (key, gates per band, tokens)."""

    if len(frames) >= KERNEL_MINIMUM:
        tokens = []
        counts = []
        for band in range(EAR_BANDS):
            series = [STREAM_FLOOR + float(frame[1 + band]) for frame in frames]
            sev = compute_sev_series(pd.DataFrame({"field": series}), "field")
            gates = tuple(segment_gates(sev))
            build_gate_l1_state(sev, gates)
            l2 = tuple(interpret_gates(sev, gates))
            l4 = tuple(compute_dsf(compute_directional_signal(list(compute_resonance(l2)))))
            band_tokens = tuple(
                l2[i].regime[0] + _sign(l4[i].D_k) + _sign(l4[i].M_k) + _sign(l4[i].R_rev_k)
                + _sign(l4[i].U_star_k - 0.5) + _sign(l4[i].C_k) + _sign(l4[i].P_k) + _sign(l4[i].B_k)
                for i in range(len(gates))
            )
            tokens.append(band_tokens)
            counts.append(len(gates))
        material = "|".join(" ".join(t) for t in tokens) + f"|beats={(len(frames) + FRAMES_PER_HOP - 1) // FRAMES_PER_HOP}"
        return hashlib.sha256(material.encode("ascii")).hexdigest()[:16], tuple(counts), tuple(tokens)
    # Too short for the kernel: the ordered shapes in eighths are its exact identity.
    quantized = tuple("".join(str(min(SHAPE_EIGHTHS, int(round(float(value) * SHAPE_EIGHTHS)))) for value in frame[1:]) for frame in frames)
    material = "short:" + ",".join(quantized)
    return hashlib.sha256(material.encode("ascii")).hexdigest()[:16], (0,) * EAR_BANDS, (quantized,)


def _close(open_event: dict[str, Any]) -> AcousticEvent:
    kept = open_event["frames"][: int(open_event["last"]) - int(open_event["start"]) + 1]   # up to its last sounding frame
    key, counts, tokens = event_structure(kept)
    return AcousticEvent(int(open_event["start"]), int(open_event["last"]), float(open_event["peak"]), key, counts, tokens)


def gate_step(open_event: dict[str, Any] | None, frames: Sequence[Sequence[float]], heard: bool, base_index: int,
              ) -> tuple[dict[str, Any] | None, list[AcousticEvent], list[int]]:
    """The boundary law over one hop's frames (absolute index base_index + i).
    Returns (the open event after the hop, the events closed within it, the lengths
    of quiet runs inside events that a sounding frame ended: the measured datum
    for a pause law read from her own record). Deterministic and bounded: the open
    event holds at most MAX_EVENT_FRAMES frames."""

    closed: list[AcousticEvent] = []
    quiet_runs: list[int] = []
    for offset, raw in enumerate(frames):
        index = base_index + offset
        frame = tuple(float(v) for v in raw) if heard else SILENT_FRAME
        energy = frame[0]
        if open_event is None:
            if heard and energy > 0.0:
                open_event = {"frames": [list(frame)], "start": index, "peak": energy, "quiet": 0, "last": index}
            continue
        open_event["peak"] = max(float(open_event["peak"]), energy)
        sounding = energy > 0.0 and energy * SOUNDING_FRACTION_OF_PEAK >= float(open_event["peak"])
        open_event["frames"].append(list(frame))
        if sounding:
            if int(open_event["quiet"]) > 0:
                quiet_runs.append(int(open_event["quiet"]))
            open_event["quiet"] = 0
            open_event["last"] = index
        else:
            open_event["quiet"] = int(open_event["quiet"]) + 1
        if int(open_event["quiet"]) >= PAUSE_FRAMES or len(open_event["frames"]) >= MAX_EVENT_FRAMES:
            closed.append(_close(open_event))
            open_event = None
    return open_event, closed, quiet_runs


class AcousticGate:
    """The boundary law run frame by frame across hops (the offline harness). Feed
    hops in order; events come out as they close."""

    def __init__(self) -> None:
        self._frame_index = 0
        self._open: dict[str, Any] | None = None

    @property
    def open(self) -> bool:
        return self._open is not None

    def feed(self, pressure_s16le: bytes) -> list[AcousticEvent]:
        frames, heard = hop_frames(pressure_s16le)
        return self.feed_frames(frames, heard)

    def feed_frames(self, frames: Sequence[Sequence[float]], heard: bool) -> list[AcousticEvent]:
        self._open, closed, _runs = gate_step(self._open, frames, heard, self._frame_index)
        self._frame_index += len(frames)
        return closed

    def flush(self) -> list[AcousticEvent]:
        """Close the open event at the end of a recording (silence follows)."""

        if self._open is None:
            return []
        event = _close(self._open)
        self._open = None
        return [event]


def events_of(hops: Sequence[bytes]) -> list[AcousticEvent]:
    """All the events in a recording given as hops, in order (the last one flushed)."""

    gate = AcousticGate()
    out: list[AcousticEvent] = []
    for hop in hops:
        out.extend(gate.feed(hop))
    out.extend(gate.flush())
    return out


__all__ = ("AcousticEvent", "AcousticGate", "Frame", "SILENT_FRAME", "EAR_BANDS", "FRAMES_PER_HOP", "MAX_EVENT_FRAMES", "PAUSE_FRAMES",
           "event_structure", "events_of", "frames_of_cochleae", "gate_step", "hop_frames")
