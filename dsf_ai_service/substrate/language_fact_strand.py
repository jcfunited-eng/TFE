"""Deterministic language Fact-Strand reciprocity.

This module is deliberately isolated from the live engine.  It provides the
substrate object and recall boundary needed to wire language recognition to
Krimelack structure without making a word label, vocabulary table, scalar
score, tunable threshold, or probabilistic model the recognition authority.

One constructor is used for both remembered facts and recall queries:

    language form -> balanced ternary 3^i strands
                  -> LanguageKrimelack events
                  -> full eight-field DSF
                  -> chi topology

Recall first uses an exact structural prerequisite fingerprint as an index.
Every indexed candidate is then checked from the explicit fields.  A match is
accepted only when the query and memory L6-lock in both directions and exactly
one distinct structural equivalence class locks.  No lock, or more than one
distinct lock, is an honest unknown.

Balanced-ternary zero is a valid quiescent state.  It is never overloaded to
mean "unknown": every trit has a separate validity bit.  Padding above a
character's highest required 3^i place is invalid, while zeroes inside its
minimal representation are valid quiescence.

Recognition is not a claim of meaning.  Meaning additionally requires a cited
multimodal BindingWindow whose experience origin is explicitly ``emulated`` or
``observed``.  The emulator can therefore provide auditable pre-embodiment
experience without being misreported as a physical sensor observation.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence

from dsf_ai_service.gualaloom_engine import P3I, TRITS, chi, encode
from dsf_ai_service.substrate.canonical_l6 import (
    L6Direction,
    canonical_l6_direction,
)
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import compute_dsf


DSF_FIELD_NAMES = (
    "D_k",
    "M_k",
    "R_rev",
    "U_star",
    "C_k",
    "P_k",
    "B_k",
    "S_UF",
)
MEANING_ORIGINS = frozenset({"emulated", "observed"})
LANGUAGE_MODALITIES = frozenset({"word", "language"})
# Explicitly ratified experience lanes.  Story scene lanes qualify because
# they are the pre-embodiment story emulator's contextual senses; arbitrary
# metadata does not become "multimodal" merely by using a different label.
EXPERIENCE_MODALITIES = frozenset({
    "sight", "sound", "touch", "smell", "taste",
    "place", "ambient", "participant",
    # 2026-07-16 (Joe: corrections work always): a teacher's correction is
    # experience in its own right -- the taught exchange window carries one
    # real teacher-presence entry, making abstract exchanges ("who are you
    # -> i am guala") citable without sensory descriptor words.
    "teacher",
})


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def _require_sequence(value: object, field_name: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be a JSON array")
    return value


def _require_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a JSON number")
    return float(value)


def _require_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be a JSON integer")
    return value


def _require_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a JSON string")
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LanguageEvent:
    """One immutable event from ``LanguageKrimelack``."""

    t: float
    dw: int
    s: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.t) or not math.isfinite(self.s):
            raise ValueError("Krimelack event values must be finite")
        if self.dw not in (-1, 1):
            raise ValueError("Krimelack event dw must be -1 or +1")

    def to_dict(self) -> dict:
        return {"t": self.t, "dw": self.dw, "s": self.s}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "LanguageEvent":
        value = _require_mapping(value, "event")
        if set(value) != {"t", "dw", "s"}:
            raise ValueError("event JSON must contain exactly t, dw, and s")
        return cls(
            t=_require_number(value["t"], "event.t"),
            dw=_require_int(value["dw"], "event.dw"),
            s=_require_number(value["s"], "event.s"),
        )


@dataclass(frozen=True)
class ExplicitDSF:
    """The L0-L4 field preserved as eight named values, never a score."""

    D_k: float
    M_k: float
    R_rev: float
    U_star: float
    C_k: float
    P_k: float
    B_k: float
    S_UF: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(getattr(self, name)) for name in DSF_FIELD_NAMES):
            raise ValueError("DSF fields must be finite")

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in DSF_FIELD_NAMES}

    @classmethod
    def from_kernel(cls, value: object) -> "ExplicitDSF":
        return cls(**{name: float(getattr(value, name)) for name in DSF_FIELD_NAMES})

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ExplicitDSF":
        value = _require_mapping(value, "dsf")
        if set(value) != set(DSF_FIELD_NAMES):
            raise ValueError("DSF JSON must contain exactly the eight canonical fields")
        return cls(
            **{
                name: _require_number(value[name], f"dsf.{name}")
                for name in DSF_FIELD_NAMES
            }
        )


@dataclass(frozen=True)
class ChiTopology:
    """Euler topology of the valid, non-null balanced-ternary structure."""

    chi: int
    vertices: int
    edges: int

    def __post_init__(self) -> None:
        if self.vertices < 0 or self.edges < 0:
            raise ValueError("chi topology counts cannot be negative")
        if self.chi != self.vertices - self.edges:
            raise ValueError("chi must equal vertices minus edges")

    def to_dict(self) -> dict:
        return {"chi": self.chi, "vertices": self.vertices, "edges": self.edges}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ChiTopology":
        value = _require_mapping(value, "topology")
        if set(value) != {"chi", "vertices", "edges"}:
            raise ValueError("topology JSON must contain exactly chi, vertices, and edges")
        return cls(
            chi=_require_int(value["chi"], "topology.chi"),
            vertices=_require_int(value["vertices"], "topology.vertices"),
            edges=_require_int(value["edges"], "topology.edges"),
        )


@dataclass(frozen=True)
class BindingWindowCitation:
    """Auditable meaning evidence from one closed binding window."""

    window_id: str
    experience_origin: str
    modalities: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.window_id, str) or not self.window_id:
            raise ValueError("binding-window citation requires a window_id")
        if not isinstance(self.experience_origin, str) or self.experience_origin not in MEANING_ORIGINS:
            raise ValueError("experience_origin must be 'emulated' or 'observed'")
        if not isinstance(self.modalities, tuple):
            raise ValueError("binding-window modalities must be an immutable tuple")
        normalized = tuple(dict.fromkeys(str(m).strip().lower() for m in self.modalities))
        if not normalized or any(not modality for modality in normalized):
            raise ValueError("binding-window citation requires named modalities")
        object.__setattr__(self, "modalities", normalized)

    @property
    def is_multimodal_language_experience(self) -> bool:
        modalities = set(self.modalities)
        has_language = bool(modalities & LANGUAGE_MODALITIES)
        has_experience = bool(modalities & EXPERIENCE_MODALITIES)
        return has_language and has_experience

    def to_dict(self) -> dict:
        return {
            "window_id": self.window_id,
            "experience_origin": self.experience_origin,
            "modalities": list(self.modalities),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "BindingWindowCitation":
        value = _require_mapping(value, "binding_window")
        modalities = _require_sequence(value["modalities"], "binding_window.modalities")
        return cls(
            window_id=_require_string(value["window_id"], "binding_window.window_id"),
            experience_origin=_require_string(
                value["experience_origin"], "binding_window.experience_origin"
            ),
            modalities=tuple(
                _require_string(item, "binding_window.modality") for item in modalities
            ),
        )


@dataclass(frozen=True)
class FactProvenance:
    """Source and window lineage carried with a fact, never used to match it."""

    source_tag: str
    trace_id: str = ""
    windows: tuple[BindingWindowCitation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source_tag, str) or not isinstance(self.trace_id, str):
            raise ValueError("provenance source_tag and trace_id must be strings")
        if not isinstance(self.windows, tuple) or any(
            not isinstance(window, BindingWindowCitation) for window in self.windows
        ):
            raise ValueError("provenance windows must be BindingWindowCitation values")

    @property
    def meaning_windows(self) -> tuple[BindingWindowCitation, ...]:
        return tuple(w for w in self.windows if w.is_multimodal_language_experience)

    def to_dict(self) -> dict:
        return {
            "source_tag": self.source_tag,
            "trace_id": self.trace_id,
            "windows": [window.to_dict() for window in self.windows],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "FactProvenance":
        value = _require_mapping(value, "provenance")
        windows = _require_sequence(value.get("windows", ()), "provenance.windows")
        return cls(
            source_tag=_require_string(value.get("source_tag", ""), "provenance.source_tag"),
            trace_id=_require_string(value.get("trace_id", ""), "provenance.trace_id"),
            windows=tuple(
                BindingWindowCitation.from_dict(item)
                for item in windows
            ),
        )


def _minimal_validity_mask(strands: Sequence[Sequence[int]]) -> tuple[bool, ...]:
    mask: list[bool] = []
    for strand in strands:
        highest_non_null = -1
        for position, trit in enumerate(strand):
            if trit != 0:
                highest_non_null = position
        mask.extend(position <= highest_non_null for position in range(len(strand)))
    return tuple(mask)


def _encode_language_char(char: str) -> tuple[int, ...]:
    strand = tuple(encode(char))
    reconstructed = sum(trit * P3I[position] for position, trit in enumerate(strand))
    if reconstructed != ord(char) - 96:
        raise ValueError(
            f"language character {char!r} exceeds the canonical {TRITS}-trit range"
        )
    return strand


def _topology(trits: Sequence[int]) -> ChiTopology:
    chi_value, vertices = chi(tuple(trits))
    return ChiTopology(
        chi=int(chi_value),
        vertices=int(vertices),
        edges=int(vertices - chi_value),
    )


def _event_dicts(events: Sequence[LanguageEvent]) -> list[dict]:
    return [event.to_dict() for event in events]


def _structural_payload(
    *,
    trits: Sequence[int],
    validity_mask: Sequence[bool],
    events: Sequence[LanguageEvent],
    dsf: ExplicitDSF,
    topology: ChiTopology,
) -> dict:
    return {
        "trits": list(trits),
        "validity_mask": list(validity_mask),
        "events": _event_dicts(events),
        "dsf": dsf.to_dict(),
        "topology": topology.to_dict(),
    }


def _reciprocity_prerequisite_payload(
    *,
    trit_count: int,
    events: Sequence[LanguageEvent],
    dsf: ExplicitDSF,
    topology: ChiTopology,
) -> dict:
    """Exact non-label fields that must agree before reciprocal comparison.

    Balanced-ternary values are intentionally absent: they are the field that
    Krimelack non-null reciprocity compares.  This fingerprint is an index,
    never recognition authority; every included field is checked again.
    """

    return {
        "trit_count": trit_count,
        "events": _event_dicts(events),
        "dsf": dsf.to_dict(),
        "topology": topology.to_dict(),
    }


@dataclass(frozen=True)
class LanguageFactStrand:
    """One immutable, structurally validated language Fact Strand."""

    language_form: str
    trits: tuple[int, ...]
    validity_mask: tuple[bool, ...]
    events: tuple[LanguageEvent, ...]
    dsf: ExplicitDSF
    topology: ChiTopology
    provenance: FactProvenance
    structural_fingerprint: str
    reciprocity_fingerprint: str
    strand_id: str

    def __post_init__(self) -> None:
        if self.language_form != self.language_form.lower():
            raise ValueError("language_form must use LanguageKrimelack lowercase normalization")
        if len(self.trits) != len(self.validity_mask):
            raise ValueError("every trit requires one separate validity bit")
        if len(self.trits) != len(self.language_form) * TRITS:
            raise ValueError("balanced-ternary strand count must match language_form")
        if any(trit not in (-1, 0, 1) for trit in self.trits):
            raise ValueError("balanced-ternary trits must be -1, 0, or +1")
        if any(not isinstance(valid, bool) for valid in self.validity_mask):
            raise ValueError("validity mask entries must be bool")
        if any(not valid and trit != 0 for trit, valid in zip(self.trits, self.validity_mask)):
            raise ValueError("invalid balanced-ternary positions must carry no value")

        strands = tuple(_encode_language_char(char) for char in self.language_form)
        expected_trits = tuple(trit for strand in strands for trit in strand)
        expected_mask = _minimal_validity_mask(strands)
        if self.trits != expected_trits or self.validity_mask != expected_mask:
            raise ValueError("language_form and balanced-ternary structure disagree")

        expected_topology = _topology(self.trits)
        if self.topology != expected_topology:
            raise ValueError("stored chi topology does not match the ternary structure")

        expected_dsf = ExplicitDSF.from_kernel(compute_dsf(_event_dicts(self.events)))
        if self.dsf != expected_dsf:
            raise ValueError("stored DSF does not match the full L0-L4 event evaluation")

        structural_payload = _structural_payload(
            trits=self.trits,
            validity_mask=self.validity_mask,
            events=self.events,
            dsf=self.dsf,
            topology=self.topology,
        )
        if self.structural_fingerprint != _sha256(structural_payload):
            raise ValueError("structural fingerprint does not match explicit fields")

        prerequisite_payload = _reciprocity_prerequisite_payload(
            trit_count=len(self.trits),
            events=self.events,
            dsf=self.dsf,
            topology=self.topology,
        )
        if self.reciprocity_fingerprint != _sha256(prerequisite_payload):
            raise ValueError("reciprocity fingerprint does not match explicit fields")

        expected_id = _sha256(
            {
                "structural_fingerprint": self.structural_fingerprint,
                "provenance": self.provenance.to_dict(),
            }
        )
        if self.strand_id != expected_id:
            raise ValueError("strand_id does not match structure and provenance")

    @property
    def has_structural_evidence(self) -> bool:
        return bool(self.events) and any(
            valid and trit != 0
            for trit, valid in zip(self.trits, self.validity_mask)
        )

    @property
    def meaning_windows(self) -> tuple[BindingWindowCitation, ...]:
        return self.provenance.meaning_windows

    def to_dict(self) -> dict:
        return {
            "language_form": self.language_form,
            "trits": list(self.trits),
            "validity_mask": list(self.validity_mask),
            "events": _event_dicts(self.events),
            "dsf": self.dsf.to_dict(),
            "topology": self.topology.to_dict(),
            "provenance": self.provenance.to_dict(),
            "structural_fingerprint": self.structural_fingerprint,
            "reciprocity_fingerprint": self.reciprocity_fingerprint,
            "strand_id": self.strand_id,
        }

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "LanguageFactStrand":
        value = _require_mapping(value, "fact_strand")
        trits = _require_sequence(value["trits"], "fact_strand.trits")
        validity_mask = _require_sequence(
            value["validity_mask"], "fact_strand.validity_mask"
        )
        if any(type(item) is not bool for item in validity_mask):
            raise ValueError("fact_strand.validity_mask entries must be JSON booleans")
        events = _require_sequence(value["events"], "fact_strand.events")
        return cls(
            language_form=_require_string(value["language_form"], "fact_strand.language_form"),
            trits=tuple(_require_int(item, "fact_strand.trit") for item in trits),
            validity_mask=tuple(validity_mask),
            events=tuple(LanguageEvent.from_dict(item) for item in events),
            dsf=ExplicitDSF.from_dict(value["dsf"]),
            topology=ChiTopology.from_dict(value["topology"]),
            provenance=FactProvenance.from_dict(value["provenance"]),
            structural_fingerprint=_require_string(
                value["structural_fingerprint"], "fact_strand.structural_fingerprint"
            ),
            reciprocity_fingerprint=_require_string(
                value["reciprocity_fingerprint"], "fact_strand.reciprocity_fingerprint"
            ),
            strand_id=_require_string(value["strand_id"], "fact_strand.strand_id"),
        )

    @classmethod
    def from_json(cls, value: str) -> "LanguageFactStrand":
        decoded = json.loads(value)
        if not isinstance(decoded, dict):
            raise ValueError("Fact Strand JSON root must be an object")
        return cls.from_dict(decoded)


def construct_language_fact_strand(
    language_form: str,
    *,
    provenance: FactProvenance | None = None,
) -> LanguageFactStrand:
    """Build a query or memory fact through the one canonical v1 path."""

    if not isinstance(language_form, str):
        raise TypeError("language_form must be a string")
    if provenance is not None and not isinstance(provenance, FactProvenance):
        raise TypeError("provenance must be FactProvenance")
    normalized = language_form.lower()
    strands = tuple(_encode_language_char(char) for char in normalized)
    trits = tuple(trit for strand in strands for trit in strand)
    validity_mask = _minimal_validity_mask(strands)

    krimelack = LanguageKrimelack()
    krimelack.transduce(normalized)
    events = tuple(LanguageEvent.from_dict(event) for event in krimelack.events)
    dsf = ExplicitDSF.from_kernel(compute_dsf(_event_dicts(events)))
    topology = _topology(trits)
    actual_provenance = provenance or FactProvenance(source_tag="")

    structural_fingerprint = _sha256(
        _structural_payload(
            trits=trits,
            validity_mask=validity_mask,
            events=events,
            dsf=dsf,
            topology=topology,
        )
    )
    reciprocity_fingerprint = _sha256(
        _reciprocity_prerequisite_payload(
            trit_count=len(trits),
            events=events,
            dsf=dsf,
            topology=topology,
        )
    )
    strand_id = _sha256(
        {
            "structural_fingerprint": structural_fingerprint,
            "provenance": actual_provenance.to_dict(),
        }
    )

    return LanguageFactStrand(
        language_form=normalized,
        trits=trits,
        validity_mask=validity_mask,
        events=events,
        dsf=dsf,
        topology=topology,
        provenance=actual_provenance,
        structural_fingerprint=structural_fingerprint,
        reciprocity_fingerprint=reciprocity_fingerprint,
        strand_id=strand_id,
    )


@dataclass(frozen=True)
class ReciprocalComparison:
    """Field verification and L6 evidence for one query-memory pair."""

    memory_strand_id: str
    prerequisite_fields_equal: bool
    forward: L6Direction
    reverse: L6Direction

    @property
    def bidirectionally_locked(self) -> bool:
        return self.prerequisite_fields_equal and self.forward.locked and self.reverse.locked


def _directional_l6(source: LanguageFactStrand, target: LanguageFactStrand) -> L6Direction:
    comparison_state = []
    matching_non_null = 0
    matching_quiescent = 0
    for index, (source_trit, source_valid) in enumerate(
        zip(source.trits, source.validity_mask)
    ):
        if not source_valid:
            continue
        target_valid = index < len(target.validity_mask) and target.validity_mask[index]
        target_trit = target.trits[index] if index < len(target.trits) else 0
        agrees = target_valid and target_trit == source_trit
        comparison_state.append(1 if agrees else 0)
        if agrees:
            if source_trit == 0:
                matching_quiescent += 1
            else:
                matching_non_null += 1

    return canonical_l6_direction(
        dimensions=len(comparison_state),
        matching_non_null=matching_non_null,
        matching_quiescent=matching_quiescent,
    )


def compare_reciprocally(
    query: LanguageFactStrand,
    memory: LanguageFactStrand,
) -> ReciprocalComparison:
    """Compare two facts without consulting either language label."""

    prerequisite_fields_equal = (
        len(query.trits) == len(memory.trits)
        and query.validity_mask == memory.validity_mask
        and query.events == memory.events
        and query.dsf == memory.dsf
        and query.topology == memory.topology
    )
    return ReciprocalComparison(
        memory_strand_id=memory.strand_id,
        prerequisite_fields_equal=prerequisite_fields_equal,
        forward=_directional_l6(query, memory),
        reverse=_directional_l6(memory, query),
    )


class RecallStatus(str, Enum):
    MATCH = "match"
    UNKNOWN = "unknown"


class RecallReason(str, Enum):
    UNIQUE_RECIPROCAL_CLASS = "unique_reciprocal_class"
    ZERO_EVIDENCE = "zero_evidence"
    NO_STRUCTURAL_CANDIDATE = "no_structural_candidate"
    NO_BIDIRECTIONAL_L6_LOCK = "no_bidirectional_l6_lock"
    AMBIGUOUS_RECIPROCAL_CLASSES = "ambiguous_reciprocal_classes"


@dataclass(frozen=True)
class FactRecallResult:
    status: RecallStatus
    reason: RecallReason
    matched_strands: tuple[LanguageFactStrand, ...] = ()
    comparisons: tuple[ReciprocalComparison, ...] = ()

    @property
    def recognized(self) -> bool:
        return self.status is RecallStatus.MATCH

    @property
    def meaning_grounded(self) -> bool:
        return self.recognized and bool(self.meaning_windows)

    @property
    def meaning_windows(self) -> tuple[BindingWindowCitation, ...]:
        seen: set[tuple[str, str]] = set()
        windows: list[BindingWindowCitation] = []
        for strand in self.matched_strands:
            for window in strand.meaning_windows:
                identity = (window.window_id, window.experience_origin)
                if identity not in seen:
                    seen.add(identity)
                    windows.append(window)
        return tuple(windows)


class LanguageFactMemory:
    """Deterministic in-memory Fact-Strand store and reciprocal recall index."""

    def __init__(self, strands: Iterable[LanguageFactStrand] = ()) -> None:
        self._lock = threading.RLock()
        self._by_id: dict[str, LanguageFactStrand] = {}
        self._reciprocity_index: dict[str, set[str]] = {}
        for strand in strands:
            self.remember(strand)

    def remember(self, strand: LanguageFactStrand) -> bool:
        if not strand.has_structural_evidence:
            raise ValueError("zero-evidence Fact Strands cannot be committed to memory")
        with self._lock:
            if strand.strand_id in self._by_id:
                return False
            self._by_id[strand.strand_id] = strand
            self._reciprocity_index.setdefault(strand.reciprocity_fingerprint, set()).add(
                strand.strand_id
            )
            return True

    def recall(self, query: LanguageFactStrand) -> FactRecallResult:
        if not query.has_structural_evidence:
            return FactRecallResult(
                status=RecallStatus.UNKNOWN,
                reason=RecallReason.ZERO_EVIDENCE,
            )

        with self._lock:
            candidate_ids = tuple(
                sorted(
                    self._reciprocity_index.get(query.reciprocity_fingerprint, set())
                )
            )
            candidates = tuple(self._by_id[strand_id] for strand_id in candidate_ids)
        if not candidate_ids:
            return FactRecallResult(
                status=RecallStatus.UNKNOWN,
                reason=RecallReason.NO_STRUCTURAL_CANDIDATE,
            )

        comparisons = tuple(compare_reciprocally(query, strand) for strand in candidates)
        locked = tuple(
            strand
            for strand, comparison in zip(candidates, comparisons)
            if comparison.bidirectionally_locked
        )
        if not locked:
            return FactRecallResult(
                status=RecallStatus.UNKNOWN,
                reason=RecallReason.NO_BIDIRECTIONAL_L6_LOCK,
                comparisons=comparisons,
            )

        classes: dict[str, list[LanguageFactStrand]] = {}
        for strand in locked:
            classes.setdefault(strand.structural_fingerprint, []).append(strand)
        if len(classes) != 1:
            return FactRecallResult(
                status=RecallStatus.UNKNOWN,
                reason=RecallReason.AMBIGUOUS_RECIPROCAL_CLASSES,
                comparisons=comparisons,
            )

        matched = tuple(next(iter(classes.values())))
        return FactRecallResult(
            status=RecallStatus.MATCH,
            reason=RecallReason.UNIQUE_RECIPROCAL_CLASS,
            matched_strands=matched,
            comparisons=comparisons,
        )

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "schema": "language_fact_strand_reciprocity_v1",
                "strands": [self._by_id[key].to_dict() for key in sorted(self._by_id)],
            }

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "LanguageFactMemory":
        value = _require_mapping(value, "fact_memory")
        if value.get("schema") != "language_fact_strand_reciprocity_v1":
            raise ValueError("unsupported language Fact-Strand memory schema")
        strands = _require_sequence(value.get("strands", ()), "fact_memory.strands")
        return cls(LanguageFactStrand.from_dict(item) for item in strands)

    @classmethod
    def from_json(cls, value: str) -> "LanguageFactMemory":
        decoded = json.loads(value)
        if not isinstance(decoded, dict):
            raise ValueError("Fact-Strand memory JSON root must be an object")
        return cls.from_dict(decoded)

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_id)
