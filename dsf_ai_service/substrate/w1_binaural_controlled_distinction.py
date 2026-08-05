"""Exact controlled distinctions over W1 binaural grounding evidence.

The owner learns no labels.  It receives independently authenticated W1
grounding episodes whose non-auditory topology is identical and permits
exactly one physical root to vary.  Each structural alternative must appear
in at least two source-disjoint episodes.

For each alternative, its diagnostic conjunction is:

    intersection(all positive left/right q cells)
    minus
    union(all contrast left/right q cells)

An empty conjunction remains unresolved.  There is no threshold, vote,
winner, scalar score, fallback, transcript, lookup table, or reduced DSF
projection.  Ear identity remains part of every diagnostic cell.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidence,
    W1BinauralGroundingEvidenceAuthority,
)


W1_CONTROLLED_DISTINCTION_PROFILE_SCHEMA = (
    "guala.w1.binaural_controlled_distinction.profile.v1"
)
W1_CONTROLLED_DISTINCTION_SCHEMA = (
    "guala.w1.binaural_controlled_distinction.v1"
)
W1_CONTROLLED_DISTINCTION_STATE_SCHEMA = (
    "guala.w1.binaural_controlled_distinction.state.v1"
)
W1_CONTROLLED_DISTINCTION_ENVELOPE_SCHEMA = (
    "guala.w1.binaural_controlled_distinction.state_hmac.v1"
)
_DISTINCTION_DOMAIN = (
    b"guala-w1-binaural-controlled-distinction-v1\0"
)
_STATE_DOMAIN = (
    b"guala-w1-binaural-controlled-distinction-state-v1\0"
)
_HEX = frozenset("0123456789abcdef")
_MINIMUM_POSITIVE_EPISODES = 2


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("W1 controlled-distinction key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 controlled-distinction key boundary changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{name} must be a bounded identifier")
    return value


@dataclass(frozen=True, slots=True)
class W1ControlledDistinctionResourceProfile:
    profile_id: str
    max_distinctions: int
    max_episodes_per_distinction: int
    max_alternatives_per_distinction: int
    max_diagnostic_cells_per_alternative: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_distinctions: int,
        max_episodes_per_distinction: int,
        max_alternatives_per_distinction: int,
        max_diagnostic_cells_per_alternative: int,
        max_state_bytes: int,
    ) -> "W1ControlledDistinctionResourceProfile":
        provisional = cls(
            profile_id=_identifier(
                profile_id, "W1 controlled-distinction profile"
            ),
            max_distinctions=_positive(
                max_distinctions, "W1 distinction capacity"
            ),
            max_episodes_per_distinction=_positive(
                max_episodes_per_distinction,
                "W1 distinction episode capacity",
            ),
            max_alternatives_per_distinction=_positive(
                max_alternatives_per_distinction,
                "W1 distinction alternative capacity",
            ),
            max_diagnostic_cells_per_alternative=_positive(
                max_diagnostic_cells_per_alternative,
                "W1 distinction diagnostic-cell capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes, "W1 distinction state bytes"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_distinctions=provisional.max_distinctions,
            max_episodes_per_distinction=(
                provisional.max_episodes_per_distinction
            ),
            max_alternatives_per_distinction=(
                provisional.max_alternatives_per_distinction
            ),
            max_diagnostic_cells_per_alternative=(
                provisional.max_diagnostic_cells_per_alternative
            ),
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_alternatives_per_distinction": (
                self.max_alternatives_per_distinction
            ),
            "max_diagnostic_cells_per_alternative": (
                self.max_diagnostic_cells_per_alternative
            ),
            "max_distinctions": self.max_distinctions,
            "max_episodes_per_distinction": (
                self.max_episodes_per_distinction
            ),
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": W1_CONTROLLED_DISTINCTION_PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            )
        }

    def verify(self) -> None:
        _identifier(
            self.profile_id, "W1 controlled-distinction profile"
        )
        for value, name in (
            (self.max_distinctions, "W1 distinction capacity"),
            (
                self.max_episodes_per_distinction,
                "W1 distinction episode capacity",
            ),
            (
                self.max_alternatives_per_distinction,
                "W1 distinction alternative capacity",
            ),
            (
                self.max_diagnostic_cells_per_alternative,
                "W1 distinction diagnostic-cell capacity",
            ),
            (self.max_state_bytes, "W1 distinction state bytes"),
        ):
            _positive(value, name)
        _sha256(
            self.authority_receipt_sha256,
            "W1 controlled-distinction profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError(
                "W1 controlled-distinction profile changed"
            )


@dataclass(frozen=True, slots=True, order=True)
class W1DiagnosticCell:
    ear_id: str
    neuron_id: str

    def record(self) -> dict[str, str]:
        return {
            "ear_id": self.ear_id,
            "neuron_id": self.neuron_id,
        }

    def verify(self) -> None:
        if self.ear_id not in ("left", "right"):
            raise ValueError("W1 diagnostic cell lost ear identity")
        _sha256(self.neuron_id, "W1 diagnostic q neuron")


@dataclass(frozen=True, slots=True)
class W1StructuralAlternative:
    root: GroundingRoot
    diagnostic_cells: tuple[W1DiagnosticCell, ...]
    positive_episode_receipt_sha256s: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return bool(self.diagnostic_cells)

    def record(self) -> dict[str, object]:
        return {
            "diagnostic_cells": [
                value.record() for value in self.diagnostic_cells
            ],
            "positive_episode_receipt_sha256s": list(
                self.positive_episode_receipt_sha256s
            ),
            "root": self.root.as_record(),
        }

    def verify(
        self,
        profile: W1ControlledDistinctionResourceProfile,
    ) -> None:
        self.root.verify()
        if (
            len(self.diagnostic_cells)
            > profile.max_diagnostic_cells_per_alternative
            or self.diagnostic_cells
            != tuple(sorted(set(self.diagnostic_cells)))
            or len(self.positive_episode_receipt_sha256s)
            < _MINIMUM_POSITIVE_EPISODES
            or self.positive_episode_receipt_sha256s
            != tuple(
                sorted(set(self.positive_episode_receipt_sha256s))
            )
        ):
            raise ValueError("W1 structural alternative changed")
        for value in self.diagnostic_cells:
            value.verify()
        for value in self.positive_episode_receipt_sha256s:
            _sha256(value, "W1 positive grounding episode")


@dataclass(frozen=True, slots=True)
class W1BinauralControlledDistinction:
    distinction_id: str
    varying_root_id: str
    fixed_root_commitments: tuple[tuple[str, str], ...]
    alternatives: tuple[W1StructuralAlternative, ...]
    source_episode_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "alternatives": [
                value.record() for value in self.alternatives
            ],
            "fixed_root_commitments": [
                [root_id, value_sha256]
                for root_id, value_sha256
                in self.fixed_root_commitments
            ],
            "schema": W1_CONTROLLED_DISTINCTION_SCHEMA,
            "source_episode_receipt_sha256s": list(
                self.source_episode_receipt_sha256s
            ),
            "varying_root_id": self.varying_root_id,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "distinction_id": self.distinction_id,
        }


def _cells(
    evidence: W1BinauralGroundingEvidence,
) -> frozenset[W1DiagnosticCell]:
    return frozenset(
        W1DiagnosticCell(value.ear_id, value.neuron_id)
        for value in evidence.activations
    )


def _root_map(
    evidence: W1BinauralGroundingEvidence,
) -> dict[str, GroundingRoot]:
    result = {value.root_id: value for value in evidence.roots}
    if len(result) != len(evidence.roots):
        raise ValueError("W1 grounding episode repeats a root")
    return result


class W1BinauralControlledDistinctionOwner:
    """Bounded owner of exact contrast-grown binaural conjunctions."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1ControlledDistinctionResourceProfile,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
    ) -> None:
        if not isinstance(
            grounding_authority,
            W1BinauralGroundingEvidenceAuthority,
        ):
            raise TypeError(
                "W1 distinction requires binaural grounding authority"
            )
        resource_profile.verify()
        root_key = hashlib.sha256(_key(authority_key)).digest()
        self._distinction_key = hashlib.sha256(
            _DISTINCTION_DOMAIN + root_key
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + root_key
        ).digest()
        self._profile = resource_profile
        self._grounding = grounding_authority
        self._distinctions: dict[
            str, W1BinauralControlledDistinction
        ] = {}
        self._lock = threading.RLock()

    @property
    def distinctions(
        self,
    ) -> tuple[W1BinauralControlledDistinction, ...]:
        with self._lock:
            return tuple(
                self._distinctions[key]
                for key in sorted(self._distinctions)
            )

    def _verify_distinction(
        self,
        distinction: W1BinauralControlledDistinction,
    ) -> None:
        _sha256(distinction.distinction_id, "W1 distinction")
        _sha256(
            distinction.authority_hmac_sha256,
            "W1 distinction HMAC",
        )
        _identifier(
            distinction.varying_root_id, "W1 varying physical root"
        )
        if (
            not 2
            <= len(distinction.alternatives)
            <= self._profile.max_alternatives_per_distinction
            or distinction.alternatives
            != tuple(sorted(
                distinction.alternatives,
                key=lambda value: value.root.value_sha256,
            ))
            or distinction.fixed_root_commitments
            != tuple(sorted(set(
                distinction.fixed_root_commitments
            )))
            or distinction.source_episode_receipt_sha256s
            != tuple(sorted(set(
                distinction.source_episode_receipt_sha256s
            )))
            or len(distinction.source_episode_receipt_sha256s)
            > self._profile.max_episodes_per_distinction
        ):
            raise ValueError("W1 controlled distinction changed")
        used_positive: set[str] = set()
        used_diagnostics: set[W1DiagnosticCell] = set()
        for alternative in distinction.alternatives:
            alternative.verify(self._profile)
            if (
                alternative.root.root_id
                != distinction.varying_root_id
                or used_positive.intersection(
                    alternative.positive_episode_receipt_sha256s
                )
                or used_diagnostics.intersection(
                    alternative.diagnostic_cells
                )
            ):
                raise ValueError(
                    "W1 distinction alternatives are not independent"
                )
            used_positive.update(
                alternative.positive_episode_receipt_sha256s
            )
            used_diagnostics.update(alternative.diagnostic_cells)
        if used_positive != set(
            distinction.source_episode_receipt_sha256s
        ):
            raise ValueError(
                "W1 distinction lost positive source episodes"
            )
        payload = distinction.payload()
        signature = hmac.new(
            self._distinction_key,
            _DISTINCTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            distinction.distinction_id != _digest(payload)
            or not hmac.compare_digest(
                signature, distinction.authority_hmac_sha256
            )
        ):
            raise ValueError("W1 distinction authority changed")

    def learn(
        self,
        *,
        varying_root_id: str,
        episodes: tuple[W1BinauralGroundingEvidence, ...],
    ) -> W1BinauralControlledDistinction:
        varying_root_id = _identifier(
            varying_root_id, "W1 varying physical root"
        )
        if (
            not isinstance(episodes, tuple)
            or not episodes
            or len(episodes) > self._profile.max_episodes_per_distinction
        ):
            raise ValueError("W1 distinction episode boundary changed")
        for episode in episodes:
            self._grounding.verify(episode)
        source_receipts = tuple(sorted(
            episode.authority_receipt_sha256
            for episode in episodes
        ))
        if len(set(source_receipts)) != len(episodes):
            raise ValueError(
                "W1 distinction requires independent source episodes"
            )
        root_maps = tuple(_root_map(value) for value in episodes)
        root_ids = tuple(sorted(root_maps[0]))
        if (
            varying_root_id not in root_maps[0]
            or any(tuple(sorted(value)) != root_ids for value in root_maps)
        ):
            raise ValueError(
                "W1 distinction root topology changed across contrast"
            )
        fixed = []
        for root_id in root_ids:
            if root_id == varying_root_id:
                continue
            commitments = {
                value[root_id].value_sha256 for value in root_maps
            }
            if len(commitments) != 1:
                raise ValueError(
                    "W1 distinction varies more than one physical root"
                )
            fixed.append((root_id, commitments.pop()))
        groups: dict[
            str, list[tuple[W1BinauralGroundingEvidence, GroundingRoot]]
        ] = {}
        for episode, roots in zip(episodes, root_maps, strict=True):
            root = roots[varying_root_id]
            groups.setdefault(root.value_sha256, []).append(
                (episode, root)
            )
        if (
            not 2
            <= len(groups)
            <= self._profile.max_alternatives_per_distinction
            or any(
                len(values) < _MINIMUM_POSITIVE_EPISODES
                for values in groups.values()
            )
        ):
            raise ValueError(
                "W1 distinction requires two independent positives "
                "per physical alternative"
            )
        alternatives = []
        all_cells_by_group = {
            value_sha256: tuple(
                _cells(episode)
                for episode, _root in values
            )
            for value_sha256, values in groups.items()
        }
        for value_sha256 in sorted(groups):
            values = groups[value_sha256]
            positives = all_cells_by_group[value_sha256]
            positive_intersection = set(positives[0])
            for cells in positives[1:]:
                positive_intersection.intersection_update(cells)
            contrast_union: set[W1DiagnosticCell] = set()
            for other_sha256, cell_sets in all_cells_by_group.items():
                if other_sha256 == value_sha256:
                    continue
                for cells in cell_sets:
                    contrast_union.update(cells)
            diagnostic = tuple(sorted(
                positive_intersection.difference(contrast_union)
            ))
            if (
                len(diagnostic)
                > self._profile.max_diagnostic_cells_per_alternative
            ):
                raise RuntimeError(
                    "W1 distinction diagnostic-cell capacity exhausted"
                )
            alternatives.append(W1StructuralAlternative(
                root=values[0][1],
                diagnostic_cells=diagnostic,
                positive_episode_receipt_sha256s=tuple(sorted(
                    episode.authority_receipt_sha256
                    for episode, _root in values
                )),
            ))
        payload = {
            "alternatives": [
                value.record() for value in alternatives
            ],
            "fixed_root_commitments": [
                [root_id, value_sha256]
                for root_id, value_sha256 in sorted(fixed)
            ],
            "schema": W1_CONTROLLED_DISTINCTION_SCHEMA,
            "source_episode_receipt_sha256s": list(source_receipts),
            "varying_root_id": varying_root_id,
        }
        signature = hmac.new(
            self._distinction_key,
            _DISTINCTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        distinction = W1BinauralControlledDistinction(
            distinction_id=_digest(payload),
            varying_root_id=varying_root_id,
            fixed_root_commitments=tuple(sorted(fixed)),
            alternatives=tuple(alternatives),
            source_episode_receipt_sha256s=source_receipts,
            authority_hmac_sha256=signature,
        )
        self._verify_distinction(distinction)
        with self._lock:
            existing = self._distinctions.get(
                distinction.distinction_id
            )
            if existing is not None:
                if existing != distinction:
                    raise ValueError(
                        "W1 distinction identity conflicted"
                    )
                return existing
            if (
                len(self._distinctions)
                >= self._profile.max_distinctions
            ):
                raise RuntimeError(
                    "W1 controlled-distinction capacity exhausted"
                )
            staged = dict(self._distinctions)
            staged[distinction.distinction_id] = distinction
            self._encoded(staged)
            self._distinctions = staged
        return distinction

    def resolve(
        self,
        *,
        distinction: W1BinauralControlledDistinction,
        evidence: W1BinauralGroundingEvidence,
    ) -> tuple[GroundingRoot, ...]:
        self._verify_distinction(distinction)
        self._grounding.verify(evidence)
        active = _cells(evidence)
        result = tuple(
            alternative.root
            for alternative in distinction.alternatives
            if (
                alternative.diagnostic_cells
                and set(alternative.diagnostic_cells).issubset(active)
            )
        )
        return result

    def _encoded(
        self,
        distinctions: Mapping[
            str, W1BinauralControlledDistinction
        ],
    ) -> bytes:
        body = {
            "distinctions": [
                distinctions[key].record()
                for key in sorted(distinctions)
            ],
            "resource_profile": self._profile.record(),
            "schema": W1_CONTROLLED_DISTINCTION_STATE_SCHEMA,
        }
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "body_base64": base64.b64encode(
                _canonical(body)
            ).decode("ascii"),
            "schema": W1_CONTROLLED_DISTINCTION_ENVELOPE_SCHEMA,
            "state_hmac_sha256": signature,
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError(
                "W1 controlled-distinction state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._distinctions)

    def status(self) -> dict[str, int | bool]:
        with self._lock:
            resolved = sum(
                alternative.resolved
                for distinction in self._distinctions.values()
                for alternative in distinction.alternatives
            )
            unresolved = sum(
                not alternative.resolved
                for distinction in self._distinctions.values()
                for alternative in distinction.alternatives
            )
            return {
                "capacity": self._profile.max_distinctions,
                "count": len(self._distinctions),
                "resolved_alternatives": resolved,
                "unresolved_alternatives": unresolved,
                "state_bytes": len(
                    self._encoded(self._distinctions)
                ),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }


__all__ = [
    "W1BinauralControlledDistinction",
    "W1BinauralControlledDistinctionOwner",
    "W1ControlledDistinctionResourceProfile",
    "W1DiagnosticCell",
    "W1StructuralAlternative",
]
