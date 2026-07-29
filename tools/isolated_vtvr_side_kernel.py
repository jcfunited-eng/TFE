"""
isolated_vtvr_side_kernel.py
=============================

NON-CANONICAL RESEARCH ARTIFACT — domain-agnostic joint-field side kernel.

Isolated reconstruction of the original UF intent, mirroring the Guala
side kernel "UF Side Kernel VTVR v2 — A Non-Canonical Vector–Time–Volume–
Relation Reconstruction" (27 July 2026):

    Before interpretation, resonance, decision, memory, or meaning, data is
    dimensionalized as one joint Vector–Time–Volume–Relation field.

The kernel knows nothing about any domain. Its inputs are vertices,
exact causal times, simultaneous rational observation vectors, and a
declared physical grouping. Its outputs are the four typed structures and
their receipts. Domain adapters live in separate files and are not this kernel's
concern.

Properties, by construction:

  * Vector    — N vertices enter as ONE simultaneous vector per causal
                time, never N independent scalar kernels.
  * Time      — exact causal timestamps are retained and enter the laws
                (Δt appears in volume and velocity); time is never an
                array index.
  * Volume    — componentwise swept volume |Δx̂|·Δt is retained per
                vertex per time; no cross-vertex sum has authority.
  * Relation  — the complete pair-relation field over all N(N-1)/2 edges
                is retained at every time, including the oriented-area
                (wedge) relation that preserves causal delay structure
                between vertex subsets; never replaced by a count, mean,
                norm, or weighted sum.
  * Exactness — all arithmetic is exact rational (fractions.Fraction);
                all layers emit deterministic SHA-256 receipts over
                canonical JSON. Two identical runs are byte-identical.
  * No scalar collapse — no weighted resonance score, no gating of
                active evidence to zero, no "last row" export. Every
                layer retains the complete typed structure below it.

Declared grouping (non-ratified reconstruction choice): one group over
all N vertices, so the group-gain quotient removes exactly a common
positive rescale of the whole field. Per-vertex gain calibration and
negative gain (orientation reversal) are declared future work, mirroring
the VTVR v2 stance that no particular grouping is ratified.

Declared m=0 conventions (the spec's difference formulas need m-1 and do
not define m=0): backward relation facts r⁻, rΔ, r∧ are zero at m=0
while r⁺ is computed; displacement, velocity, acceleration, and volume
are zero rows at m=0; L2 relation_change at m=0 carries ρ₀ itself rather
than a zero fact — an irregular convention found by the 2026-07-29
adversarial audit, documented here rather than silently changed
mid-experiment (nothing downstream consumes it; receipts are consistent
across all runs).

Known incompleteness (deliberate, mirroring VTVR v2): no causal
segmentation, no adaptive gates, no memory, no L5/L6, no source
separation, no production persistence, no deployment.

Bounds: 2 ≤ N ≤ 64, 2 ≤ M ≤ 2048, strictly increasing exact times.
Cost: O(M·N²) retained in full; truncation is prohibited — exceeding the
declared bound is an error, never a silent cut.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, Sequence, Tuple

N_MIN, N_MAX = 2, 64
M_MIN, M_MAX = 2, 2048

Frac = Fraction


# ---------------------------------------------------------------------------
# Canonical encoding and receipts
# ---------------------------------------------------------------------------

def _f(x: Fraction) -> str:
    """Canonical exact encoding of one rational: 'numerator/denominator'."""
    return f"{x.numerator}/{x.denominator}"


def _encode(obj):
    """Recursively encode Fractions for canonical JSON."""
    if isinstance(obj, Fraction):
        return _f(obj)
    if isinstance(obj, (list, tuple)):
        return [_encode(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): _encode(v) for k, v in obj.items()}
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    raise TypeError(f"Non-canonical value in receipt: {type(obj)!r}")


def receipt_hash(payload) -> str:
    """SHA-256 over canonical JSON: sorted keys, ordered arrays, exact text."""
    canonical = json.dumps(_encode(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Typed structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EdgeRelation:
    """Complete relation fact ρ_{m,ij} — four exact facts, identities kept."""
    i: int
    j: int
    r_minus: Fraction   # x̂_{m-1,i}·x̂_{m-1,j}
    r_plus: Fraction    # x̂_{m,i}·x̂_{m,j}
    r_delta: Fraction   # Δx̂_{m,i}·Δx̂_{m,j}
    r_wedge: Fraction   # x̂_{m-1,i}·x̂_{m,j} − x̂_{m-1,j}·x̂_{m,i}  (lead–lag)


@dataclass(frozen=True)
class L0Field:
    """Complete joint dimensionalization. Nothing here is a summary."""
    h_raw: str
    names: Tuple[str, ...]
    groups: Tuple[Tuple[int, ...], ...]
    times: Tuple[Fraction, ...]
    dts: Tuple[Fraction, ...]
    xhat: Tuple[Tuple[Fraction, ...], ...]        # M × N structural views
    dxhat: Tuple[Tuple[Fraction, ...], ...]       # M × N displacements
    volume: Tuple[Tuple[Fraction, ...], ...]      # M × N swept volume
    volume_accum: Tuple[Fraction, ...]            # N componentwise totals
    relations: Tuple[Tuple[EdgeRelation, ...], ...]  # M × E edge facts


@dataclass(frozen=True)
class VTVREvent:
    """L1: the four typed dimensions held jointly, with one joint receipt."""
    field: L0Field
    h_vtvr: str


@dataclass(frozen=True)
class L2Geometry:
    """Exact joint geometry over the complete L1 object."""
    event: VTVREvent
    velocity: Tuple[Tuple[Fraction, ...], ...]       # M × N
    acceleration: Tuple[Tuple[Fraction, ...], ...]   # M × N
    relation_change: Tuple[Tuple[EdgeRelation, ...], ...]  # M × E (component Δ)


@dataclass(frozen=True)
class L3ResonanceField:
    """Non-scalar resonance: all trajectories available together.
    No weighted score is calculated. No evidence is gated to zero."""
    geometry: L2Geometry
    quiescent: bool


@dataclass(frozen=True)
class L4DSF:
    """Complete Decision Structural Field — seven fields, full indices.
    Cohesion authority is the full edge field, never a count/mean/norm."""
    resonance: L3ResonanceField
    displacement: Tuple[Tuple[Fraction, ...], ...]   # D_{m,i}
    motion: Tuple[Tuple[Fraction, ...], ...]         # M_{m,i} = a_{m,i}
    reversal: Tuple[Tuple[int, ...], ...]            # R^rev_{m,i}
    availability: Tuple[Tuple[str, ...], ...]        # U*_{m,i}: genesis|observed
    cohesion: Tuple[Tuple[EdgeRelation, ...], ...]   # C_m = full ρ field
    pressure: Tuple[Tuple[Fraction, ...], ...]       # P_{m,i} = |a_{m,i}|
    breathing: Tuple[Tuple[Fraction, ...], ...]      # B_{m,i} = v_m − v_{m-1}


@dataclass(frozen=True)
class Experience:
    """Complete bound experience with per-layer receipts."""
    l0: L0Field
    l1: VTVREvent
    l2: L2Geometry
    l3: L3ResonanceField
    l4: L4DSF
    h_layers: Dict[str, str]
    h_experience: str


# ---------------------------------------------------------------------------
# L0 — joint dimensionalization
# ---------------------------------------------------------------------------

def dimensionalize(
    names: Sequence[str],
    times: Sequence[Fraction],
    observations: Sequence[Sequence[Fraction]],
    groups: Sequence[Sequence[int]] | None = None,
) -> L0Field:
    """Build the complete joint L0 field from exact raw observations."""
    n = len(names)
    m = len(times)
    if not (N_MIN <= n <= N_MAX):
        raise ValueError(f"vertex count N={n} outside [{N_MIN},{N_MAX}]")
    if not (M_MIN <= m <= M_MAX):
        raise ValueError(f"observation count M={m} outside [{M_MIN},{M_MAX}]")
    if len(observations) != m:
        raise ValueError("observations/times length mismatch")
    for row in observations:
        if len(row) != n:
            raise ValueError("observation is not a complete simultaneous vector")
    for a, b in zip(times, times[1:]):
        if not b > a:
            raise ValueError("times must be strictly increasing exact rationals")

    if groups is None:
        groups = [tuple(range(n))]
    groups = tuple(tuple(g) for g in groups)
    covered = sorted(i for g in groups for i in g)
    if covered != list(range(n)) or any(len(g) == 0 for g in groups):
        raise ValueError("groups must be nonempty, disjoint, and cover every vertex")

    times_t = tuple(Fraction(t) for t in times)
    x_raw = tuple(tuple(Fraction(v) for v in row) for row in observations)

    h_raw = receipt_hash({
        "names": list(names),
        "groups": [list(g) for g in groups],
        "times": list(times_t),
        "x_raw": [list(r) for r in x_raw],
    })

    # Group-gain structural view
    xhat: List[Tuple[Fraction, ...]] = []
    for row in x_raw:
        out = [Fraction(0)] * n
        for g in groups:
            s = sum(abs(row[i]) for i in g)
            for i in g:
                out[i] = Fraction(0) if s == 0 else row[i] / s
        xhat.append(tuple(out))
    xhat_t = tuple(xhat)

    # Exact causal time
    dts = tuple(
        [Fraction(0)] + [times_t[k] - times_t[k - 1] for k in range(1, m)]
    )

    # Displacement
    zero_row = tuple(Fraction(0) for _ in range(n))
    dxhat = [zero_row] + [
        tuple(xhat_t[k][i] - xhat_t[k - 1][i] for i in range(n))
        for k in range(1, m)
    ]
    dxhat_t = tuple(dxhat)

    # Componentwise swept volume
    volume = [zero_row] + [
        tuple(abs(dxhat_t[k][i]) * dts[k] for i in range(n))
        for k in range(1, m)
    ]
    volume_t = tuple(volume)
    volume_accum = tuple(
        sum((volume_t[k][i] for k in range(m)), Fraction(0)) for i in range(n)
    )

    # Complete pair relations (all edges, every time; m=0 backward facts are 0)
    edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    relations: List[Tuple[EdgeRelation, ...]] = []
    for k in range(m):
        row_rel: List[EdgeRelation] = []
        for (i, j) in edges:
            if k == 0:
                row_rel.append(EdgeRelation(
                    i=i, j=j,
                    r_minus=Fraction(0),
                    r_plus=xhat_t[0][i] * xhat_t[0][j],
                    r_delta=Fraction(0),
                    r_wedge=Fraction(0),
                ))
            else:
                row_rel.append(EdgeRelation(
                    i=i, j=j,
                    r_minus=xhat_t[k - 1][i] * xhat_t[k - 1][j],
                    r_plus=xhat_t[k][i] * xhat_t[k][j],
                    r_delta=dxhat_t[k][i] * dxhat_t[k][j],
                    r_wedge=xhat_t[k - 1][i] * xhat_t[k][j]
                            - xhat_t[k - 1][j] * xhat_t[k][i],
                ))
        relations.append(tuple(row_rel))

    return L0Field(
        h_raw=h_raw,
        names=tuple(names),
        groups=groups,
        times=times_t,
        dts=dts,
        xhat=xhat_t,
        dxhat=dxhat_t,
        volume=volume_t,
        volume_accum=volume_accum,
        relations=tuple(relations),
    )


# ---------------------------------------------------------------------------
# L1 — the VTVR structural event
# ---------------------------------------------------------------------------

def _relations_payload(relations) -> list:
    return [
        [
            {"i": r.i, "j": r.j, "r-": r.r_minus, "r+": r.r_plus,
             "rD": r.r_delta, "r^": r.r_wedge}
            for r in row
        ]
        for row in relations
    ]


def form_event(field: L0Field) -> VTVREvent:
    """One externally closed causal interval; joint structural receipt.

    H_VTVR binds the four structural dimensions (X̂, T, V, R) — the raw
    receipt is deliberately excluded so a declared common-gain quotient
    changes H_raw but not H_VTVR."""
    h_vtvr = receipt_hash({
        "X": [list(r) for r in field.xhat],
        "T": list(field.times),
        "V": {
            "per_time": [list(r) for r in field.volume],
            "accum": list(field.volume_accum),
        },
        "R": _relations_payload(field.relations),
    })
    return VTVREvent(field=field, h_vtvr=h_vtvr)


# ---------------------------------------------------------------------------
# L2 — exact joint geometry
# ---------------------------------------------------------------------------

def compute_geometry(event: VTVREvent) -> L2Geometry:
    f = event.field
    m, n = len(f.times), len(f.names)
    zero_row = tuple(Fraction(0) for _ in range(n))

    velocity = [zero_row]
    for k in range(1, m):
        velocity.append(tuple(f.dxhat[k][i] / f.dts[k] for i in range(n)))
    velocity_t = tuple(velocity)

    acceleration = [zero_row]
    for k in range(1, m):
        acceleration.append(tuple(
            (velocity_t[k][i] - velocity_t[k - 1][i]) / f.dts[k] for i in range(n)
        ))

    relation_change: List[Tuple[EdgeRelation, ...]] = [f.relations[0]]
    for k in range(1, m):
        row = []
        for prev, cur in zip(f.relations[k - 1], f.relations[k]):
            row.append(EdgeRelation(
                i=cur.i, j=cur.j,
                r_minus=cur.r_minus - prev.r_minus,
                r_plus=cur.r_plus - prev.r_plus,
                r_delta=cur.r_delta - prev.r_delta,
                r_wedge=cur.r_wedge - prev.r_wedge,
            ))
        relation_change.append(tuple(row))

    return L2Geometry(
        event=event,
        velocity=velocity_t,
        acceleration=tuple(acceleration),
        relation_change=tuple(relation_change),
    )


# ---------------------------------------------------------------------------
# L3 — non-scalar resonance field
# ---------------------------------------------------------------------------

def compute_resonance_field(geometry: L2Geometry) -> L3ResonanceField:
    f = geometry.event.field
    quiescent = all(
        v == 0 for row in f.volume for v in row
    )
    return L3ResonanceField(geometry=geometry, quiescent=quiescent)


# ---------------------------------------------------------------------------
# L4 — complete Decision Structural Field
# ---------------------------------------------------------------------------

def compute_dsf(res: L3ResonanceField) -> L4DSF:
    f = res.geometry.event.field
    m, n = len(f.times), len(f.names)

    displacement = f.dxhat
    motion = res.geometry.acceleration

    reversal: List[Tuple[int, ...]] = [tuple(0 for _ in range(n))]
    for k in range(1, m):
        reversal.append(tuple(
            1 if f.dxhat[k - 1][i] * f.dxhat[k][i] < 0 else 0
            for i in range(n)
        ))

    availability = tuple(
        tuple(("genesis" if k == 0 else "observed") for _ in range(n))
        for k in range(m)
    )

    pressure = tuple(
        tuple(abs(motion[k][i]) for i in range(n)) for k in range(m)
    )

    zero_row = tuple(Fraction(0) for _ in range(n))
    breathing = [zero_row]
    for k in range(1, m):
        breathing.append(tuple(
            f.volume[k][i] - f.volume[k - 1][i] for i in range(n)
        ))

    return L4DSF(
        resonance=res,
        displacement=displacement,
        motion=motion,
        reversal=tuple(reversal),
        availability=availability,
        cohesion=f.relations,
        pressure=pressure,
        breathing=tuple(breathing),
    )


# ---------------------------------------------------------------------------
# Complete experience
# ---------------------------------------------------------------------------

def run_experience(
    names: Sequence[str],
    times: Sequence[Fraction],
    observations: Sequence[Sequence[Fraction]],
    groups: Sequence[Sequence[int]] | None = None,
) -> Experience:
    """Execute the full walk-up: L0 → L4 with deterministic receipts."""
    l0 = dimensionalize(names, times, observations, groups)
    l1 = form_event(l0)
    l2 = compute_geometry(l1)
    l3 = compute_resonance_field(l2)
    l4 = compute_dsf(l3)

    h_l0 = receipt_hash({
        "h_raw": l0.h_raw,
        "xhat": [list(r) for r in l0.xhat],
        "dts": list(l0.dts),
        "dxhat": [list(r) for r in l0.dxhat],
        "volume": [list(r) for r in l0.volume],
        "relations": _relations_payload(l0.relations),
    })
    h_l1 = l1.h_vtvr
    h_l2 = receipt_hash({
        "velocity": [list(r) for r in l2.velocity],
        "acceleration": [list(r) for r in l2.acceleration],
        "relation_change": _relations_payload(l2.relation_change),
    })
    h_l3 = receipt_hash({"quiescent": l3.quiescent})
    h_l4 = receipt_hash({
        "D": [list(r) for r in l4.displacement],
        "M": [list(r) for r in l4.motion],
        "Rrev": [list(r) for r in l4.reversal],
        "Ustar": [list(r) for r in l4.availability],
        "C": _relations_payload(l4.cohesion),
        "P": [list(r) for r in l4.pressure],
        "B": [list(r) for r in l4.breathing],
    })

    h_layers = {"L0": h_l0, "L1": h_l1, "L2": h_l2, "L3": h_l3, "L4": h_l4}
    h_experience = receipt_hash({
        "h_raw": l0.h_raw,
        **h_layers,
    })

    return Experience(
        l0=l0, l1=l1, l2=l2, l3=l3, l4=l4,
        h_layers=h_layers, h_experience=h_experience,
    )
