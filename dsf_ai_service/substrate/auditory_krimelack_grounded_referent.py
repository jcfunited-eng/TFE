"""Bounded controlled-contrast grounding for heard structural kinds.

This curriculum primitive learns only a demonstrated bijection between
auditory Krimelack kind identities and one non-auditory full-field referent.
It does not assign tutor text, dictionary meaning, grammar, or a reply.

Each episode must arrive through a confirmed causal-association admission,
which already proves two distinct exact experiences.  Across at least two
different auditory kinds, every non-auditory root except one must remain
exactly invariant and the remaining root must vary bijectively with kind.
Zero changing roots is ungrounded; more than one is ambiguous; within-kind
conflict fails closed.  Sound is never permitted to ground itself.

Every retained referent value preserves the complete ordered explicit
D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k tuples, topology, coordinates, and causal
source intervals.  Digests are indexes only; the full values remain the
authority.  State is fixed-capacity, canonical, and HMAC authenticated.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_krimelack_causal_association import (
    AUDITORY_KRIMELACK_DELIBERATION_ADMISSION_SCHEMA,
    AuditoryKrimelackDeliberationAdmission,
)
from dsf_ai_service.substrate.auditory_krimelack_causal_occurrence import (
    AuditoryKrimelackCausalOccurrence,
)


AUDITORY_GROUNDED_EPISODE_SCHEMA = (
    "guala.auditory.krimelack_grounded_episode.v1"
)
AUDITORY_GROUNDED_CONSTRUCTION_SCHEMA = (
    "guala.auditory.krimelack_grounded_construction.v1"
)
AUDITORY_GROUNDED_STATE_SCHEMA = (
    "guala.auditory.krimelack_grounded_state.v1"
)
AUDITORY_GROUNDED_ENVELOPE_SCHEMA = (
    "guala.auditory.krimelack_grounded_state_hmac.v1"
)

MAX_AUDITORY_GROUNDED_EPISODES = 16
MAX_AUDITORY_GROUNDED_KINDS = 8
MAX_AUDITORY_GROUNDED_STATE_BYTES = 32 * 1024 * 1024

_EPISODE_HMAC_DOMAIN = (
    b"guala.auditory.krimelack_grounded_episode.v1\0"
)
_CONSTRUCTION_HMAC_DOMAIN = (
    b"guala.auditory.krimelack_grounded_construction.v1\0"
)
_STATE_HMAC_DOMAIN = (
    b"guala.auditory.krimelack_grounded_state.v1\0"
)


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


def _key(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError(
            "auditory grounded referent key must be bytes or text"
        )
    if not 32 <= len(result) <= 4096:
        raise ValueError(
            "auditory grounded referent key has an invalid boundary"
        )
    return result


def _sign(domain: bytes, key: bytes, value: object) -> str:
    return hmac.new(
        key,
        domain + _canonical(value),
        hashlib.sha256,
    ).hexdigest()


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{name} is not a bounded identifier")
    return value


def _admission_from_record(
    value: object,
    *,
    authority_key: bytes,
) -> AuditoryKrimelackDeliberationAdmission:
    expected = {
        "association_authority_receipt_sha256",
        "association_id",
        "authority_hmac_sha256",
        "current_occurrence",
        "kind_id",
        "reinforcement_occurrence_ids",
        "schema",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema")
        != AUDITORY_KRIMELACK_DELIBERATION_ADMISSION_SCHEMA
        or not isinstance(
            value.get("reinforcement_occurrence_ids"), list
        )
    ):
        raise ValueError(
            "auditory grounded admission record changed"
        )
    result = AuditoryKrimelackDeliberationAdmission(
        kind_id=value.get("kind_id"),
        association_id=value.get("association_id"),
        current_occurrence=(
            AuditoryKrimelackCausalOccurrence.from_record(
                value.get("current_occurrence")
            )
        ),
        reinforcement_occurrence_ids=tuple(
            value["reinforcement_occurrence_ids"]
        ),
        association_authority_receipt_sha256=value.get(
            "association_authority_receipt_sha256"
        ),
        authority_hmac_sha256=value.get(
            "authority_hmac_sha256"
        ),
    )
    result.verify(authority_key)
    if result.as_record(authority_key) != dict(value):
        raise ValueError(
            "auditory grounded admission is not canonical"
        )
    return result


def _structural_substream(
    value: Mapping[str, object],
) -> dict[str, object]:
    expected = {
        "coordinates",
        "field_tuples",
        "kernel_basin_receipt_sha256",
        "physical_quantity",
        "physical_unit",
        "profile_receipt_sha256",
        "sensor_id",
        "source_evidence_stream_receipt_sha256",
        "source_sample_commitment_sha256",
        "source_sample_count",
        "substream_id",
        "topology_index",
    }
    if set(value) != expected or not isinstance(
        value.get("field_tuples"), list
    ):
        raise ValueError(
            "auditory grounded substream authority changed"
        )
    tuples = []
    for expected_index, field_tuple in enumerate(
        value["field_tuples"]
    ):
        if (
            not isinstance(field_tuple, Mapping)
            or set(field_tuple)
            != {
                "authority_receipt_sha256",
                "fields",
                "source_index_end",
                "source_index_start",
                "source_l0_l4_trace_receipt_sha256",
                "tuple_index",
            }
            or field_tuple.get("tuple_index") != expected_index
            or not isinstance(field_tuple.get("fields"), list)
            or tuple(
                item[0]
                for item in field_tuple["fields"]
                if isinstance(item, list) and len(item) == 2
            )
            != DSF_FIELD_ORDER
            or len(field_tuple["fields"]) != len(DSF_FIELD_ORDER)
        ):
            raise ValueError(
                "auditory grounded referent lost explicit DSF order"
            )
        tuples.append({
            "fields": field_tuple["fields"],
            "source_index_end": field_tuple.get(
                "source_index_end"
            ),
            "source_index_start": field_tuple.get(
                "source_index_start"
            ),
            "tuple_index": expected_index,
        })
    return {
        "coordinates": value.get("coordinates"),
        "field_tuples": tuples,
        "physical_quantity": value.get("physical_quantity"),
        "physical_unit": value.get("physical_unit"),
        "sensor_id": value.get("sensor_id"),
        "source_sample_count": value.get("source_sample_count"),
        "substream_id": value.get("substream_id"),
        "topology_index": value.get("topology_index"),
    }


def _non_auditory_roots(
    admission: AuditoryKrimelackDeliberationAdmission,
) -> tuple[tuple[str, object], ...]:
    witness = admission.world_witnesses[-1]
    witness.verify(max_bytes=2 * 1024 * 1024)
    try:
        decoded = json.loads(base64.b64decode(
            witness.settlement_payload_base64,
            validate=True,
        ))
    except Exception as error:
        raise ValueError(
            "auditory grounded full-field witness is unreadable"
        ) from error
    interpretations = decoded.get("interpretations")
    if (
        not isinstance(interpretations, list)
        or len(interpretations) != 6
    ):
        raise ValueError(
            "auditory grounded witness lost six-sense structure"
        )
    roots: dict[str, object] = {}
    for sense in interpretations:
        if not isinstance(sense, Mapping):
            raise ValueError(
                "auditory grounded witness sense changed"
            )
        name = _identifier(
            sense.get("sense"),
            "auditory grounded sense",
        )
        if name == "sound":
            continue
        roots[f"sense:{name}:boundary"] = {
            "state": sense.get("state"),
        }
        substreams = sense.get("substreams")
        if not isinstance(substreams, list):
            raise ValueError(
                "auditory grounded witness substreams changed"
            )
        for substream in substreams:
            if not isinstance(substream, Mapping):
                raise ValueError(
                    "auditory grounded witness substream changed"
                )
            substream_id = _identifier(
                substream.get("substream_id"),
                "auditory grounded substream",
            )
            root_id = f"sense:{name}:substream:{substream_id}"
            if root_id in roots:
                raise ValueError(
                    "auditory grounded witness repeats a root"
                )
            roots[root_id] = _structural_substream(substream)
    return tuple((key, roots[key]) for key in sorted(roots))


@dataclass(frozen=True, slots=True)
class AuditoryGroundedEpisode:
    episode_id: str
    kind_id: str
    admission: AuditoryKrimelackDeliberationAdmission
    roots: tuple[tuple[str, object], ...]
    authority_hmac_sha256: str

    def payload(self, authority_key: object) -> dict[str, object]:
        return {
            "admission": self.admission.as_record(authority_key),
            "kind_id": self.kind_id,
            "roots": [[key, value] for key, value in self.roots],
            "schema": AUDITORY_GROUNDED_EPISODE_SCHEMA,
        }

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key)
        self.admission.verify(key)
        for value, name in (
            (self.episode_id, "episode"),
            (self.kind_id, "kind"),
            (self.authority_hmac_sha256, "authority"),
        ):
            sha256_digest(value, f"auditory grounded {name}")
        if (
            self.kind_id != self.admission.kind_id
            or self.roots != _non_auditory_roots(self.admission)
            or tuple(key for key, _value in self.roots)
            != tuple(sorted(key for key, _value in self.roots))
            or self.episode_id
            != _digest({
                "admission_authority_hmac_sha256": (
                    self.admission.authority_hmac_sha256
                ),
                "schema": AUDITORY_GROUNDED_EPISODE_SCHEMA,
            })
            or not hmac.compare_digest(
                self.authority_hmac_sha256,
                _sign(
                    _EPISODE_HMAC_DOMAIN,
                    key,
                    self.payload(key),
                ),
            )
        ):
            raise ValueError(
                "auditory grounded episode authority changed"
            )

    def as_record(self, authority_key: object) -> dict[str, object]:
        self.verify(authority_key)
        return {
            **self.payload(authority_key),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "episode_id": self.episode_id,
        }


@dataclass(frozen=True, slots=True)
class AuditoryGroundedAlternative:
    kind_id: str
    referent_value_sha256: str
    referent_value: object

    def as_record(self) -> dict[str, object]:
        return {
            "kind_id": self.kind_id,
            "referent_value": self.referent_value,
            "referent_value_sha256": self.referent_value_sha256,
        }


@dataclass(frozen=True, slots=True)
class AuditoryGroundedConstruction:
    construction_id: str
    referent_root: str
    alternatives: tuple[AuditoryGroundedAlternative, ...]
    proof_episode_ids: tuple[str, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "alternatives": [
                value.as_record() for value in self.alternatives
            ],
            "proof_episode_ids": list(self.proof_episode_ids),
            "referent_root": self.referent_root,
            "schema": AUDITORY_GROUNDED_CONSTRUCTION_SCHEMA,
        }

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key)
        sha256_digest(
            self.construction_id,
            "auditory grounded construction",
        )
        sha256_digest(
            self.authority_hmac_sha256,
            "auditory grounded construction authority",
        )
        _identifier(
            self.referent_root,
            "auditory grounded referent root",
        )
        if (
            len(self.alternatives) < 2
            or tuple(sorted(
                self.alternatives,
                key=lambda value: value.kind_id,
            ))
            != self.alternatives
            or len({
                value.kind_id for value in self.alternatives
            })
            != len(self.alternatives)
            or len({
                value.referent_value_sha256
                for value in self.alternatives
            })
            != len(self.alternatives)
            or not self.proof_episode_ids
        ):
            raise ValueError(
                "auditory grounded construction cardinality changed"
            )
        for alternative in self.alternatives:
            sha256_digest(
                alternative.kind_id,
                "auditory grounded alternative kind",
            )
            if alternative.referent_value_sha256 != _digest(
                alternative.referent_value
            ):
                raise ValueError(
                    "auditory grounded referent value changed"
                )
        for episode_id in self.proof_episode_ids:
            sha256_digest(
                episode_id,
                "auditory grounded proof episode",
            )
        if (
            self.construction_id != _digest(self.payload())
            or not hmac.compare_digest(
                self.authority_hmac_sha256,
                _sign(
                    _CONSTRUCTION_HMAC_DOMAIN,
                    key,
                    self.payload(),
                ),
            )
        ):
            raise ValueError(
                "auditory grounded construction authority changed"
            )


@dataclass(frozen=True, slots=True)
class AuditoryGroundedLearning:
    state: str
    reason: str
    construction: AuditoryGroundedConstruction | None


@dataclass(frozen=True, slots=True)
class AuditoryGroundedResolution:
    state: str
    reason: str
    kind_id: str
    referent_root: str | None = None
    referent_value: object | None = None
    construction_id: str | None = None


class AuditoryKrimelackGroundedReferentOwner:
    """Bounded exact controlled-contrast auditory grounding owner."""

    def __init__(
        self,
        *,
        authority_key: object,
        log_event: Callable[..., None],
        episode_capacity: int = MAX_AUDITORY_GROUNDED_EPISODES,
        kind_capacity: int = MAX_AUDITORY_GROUNDED_KINDS,
        encoded_state_capacity: int = MAX_AUDITORY_GROUNDED_STATE_BYTES,
    ) -> None:
        if (
            isinstance(episode_capacity, bool)
            or not isinstance(episode_capacity, int)
            or not 2
            <= episode_capacity
            <= MAX_AUDITORY_GROUNDED_EPISODES
            or isinstance(kind_capacity, bool)
            or not isinstance(kind_capacity, int)
            or not 2 <= kind_capacity <= MAX_AUDITORY_GROUNDED_KINDS
            or isinstance(encoded_state_capacity, bool)
            or not isinstance(encoded_state_capacity, int)
            or not 1
            <= encoded_state_capacity
            <= MAX_AUDITORY_GROUNDED_STATE_BYTES
        ):
            raise ValueError(
                "auditory grounded curriculum capacity is invalid"
            )
        self._key = _key(authority_key)
        self._log_event = log_event
        self._episode_capacity = episode_capacity
        self._kind_capacity = kind_capacity
        self._encoded_state_capacity = encoded_state_capacity
        self._lock = threading.RLock()
        self._episodes: dict[str, AuditoryGroundedEpisode] = {}
        self._encoded_bytes = len(self._encoded(self._episodes))

    def _state(
        self,
        episodes: Mapping[str, AuditoryGroundedEpisode],
    ) -> dict[str, object]:
        return {
            "encoded_state_capacity": self._encoded_state_capacity,
            "episode_capacity": self._episode_capacity,
            "episodes": [
                episodes[key].as_record(self._key)
                for key in sorted(episodes)
            ],
            "kind_capacity": self._kind_capacity,
            "schema": AUDITORY_GROUNDED_STATE_SCHEMA,
        }

    def _encoded(
        self,
        episodes: Mapping[str, AuditoryGroundedEpisode],
    ) -> bytes:
        payload = _canonical(self._state(episodes))
        if len(payload) > self._encoded_state_capacity:
            raise RuntimeError(
                "auditory grounded curriculum state capacity is full"
            )
        return payload

    def observe(
        self,
        admission: AuditoryKrimelackDeliberationAdmission,
    ) -> bool:
        if not isinstance(
            admission,
            AuditoryKrimelackDeliberationAdmission,
        ):
            raise TypeError(
                "auditory grounding requires confirmed admission"
            )
        admission.verify(self._key)
        roots = _non_auditory_roots(admission)
        episode_id = _digest({
            "admission_authority_hmac_sha256": (
                admission.authority_hmac_sha256
            ),
            "schema": AUDITORY_GROUNDED_EPISODE_SCHEMA,
        })
        payload = {
            "admission": admission.as_record(self._key),
            "kind_id": admission.kind_id,
            "roots": [[key, value] for key, value in roots],
            "schema": AUDITORY_GROUNDED_EPISODE_SCHEMA,
        }
        episode = AuditoryGroundedEpisode(
            episode_id=episode_id,
            kind_id=admission.kind_id,
            admission=admission,
            roots=roots,
            authority_hmac_sha256=_sign(
                _EPISODE_HMAC_DOMAIN,
                self._key,
                payload,
            ),
        )
        episode.verify(self._key)
        with self._lock:
            if episode_id in self._episodes:
                return False
            kinds = {
                value.kind_id for value in self._episodes.values()
            }
            if (
                len(self._episodes) >= self._episode_capacity
                or admission.kind_id not in kinds
                and len(kinds) >= self._kind_capacity
            ):
                raise RuntimeError(
                    "auditory grounded curriculum capacity is full"
                )
            prospective = dict(self._episodes)
            prospective[episode_id] = episode
            encoded = self._encoded(prospective)
            self._episodes = prospective
            self._encoded_bytes = len(encoded)
        self._log_event(
            "auditory_krimelack_grounded_episode_observed",
            episode_id=episode_id,
            kind_id=admission.kind_id,
            root_count=len(roots),
        )
        return True

    def _derive(self) -> AuditoryGroundedLearning:
        episodes = tuple(
            self._episodes[key] for key in sorted(self._episodes)
        )
        kinds = tuple(sorted({
            value.kind_id for value in episodes
        }))
        if len(kinds) < 2:
            return AuditoryGroundedLearning(
                state="unknown",
                reason="controlled_contrast_absent",
                construction=None,
            )
        root_orders = {
            tuple(key for key, _value in episode.roots)
            for episode in episodes
        }
        if len(root_orders) != 1:
            return AuditoryGroundedLearning(
                state="ambiguous",
                reason="referent_topology_changed",
                construction=None,
            )
        root_ids = next(iter(root_orders))
        candidates = []
        uncontrolled = []
        alternatives_by_root = {}
        for root_id in root_ids:
            values_by_kind: dict[str, dict[str, object]] = {}
            for episode in episodes:
                value = dict(episode.roots)[root_id]
                values_by_kind.setdefault(
                    episode.kind_id, {}
                )[_digest(value)] = value
            if any(
                len(values) != 1
                for values in values_by_kind.values()
            ):
                uncontrolled.append(root_id)
                continue
            values = {
                kind: next(iter(by_digest.items()))
                for kind, by_digest in values_by_kind.items()
            }
            distinct = {
                digest for digest, _value in values.values()
            }
            if len(distinct) == 1:
                continue
            if (
                len(values) == len(kinds)
                and len(distinct) == len(kinds)
            ):
                candidates.append(root_id)
                alternatives_by_root[root_id] = values
            else:
                uncontrolled.append(root_id)
        if uncontrolled:
            return AuditoryGroundedLearning(
                state="conflicting",
                reason="within_kind_or_uncontrolled_change",
                construction=None,
            )
        if not candidates:
            return AuditoryGroundedLearning(
                state="unknown",
                reason="non_auditory_contrast_absent",
                construction=None,
            )
        if len(candidates) != 1:
            return AuditoryGroundedLearning(
                state="ambiguous",
                reason="multiple_referent_roots_changed",
                construction=None,
            )
        root_id = candidates[0]
        values = alternatives_by_root[root_id]
        alternatives = tuple(
            AuditoryGroundedAlternative(
                kind_id=kind,
                referent_value_sha256=values[kind][0],
                referent_value=values[kind][1],
            )
            for kind in kinds
        )
        proof_ids = tuple(
            value.episode_id for value in episodes
        )
        provisional = {
            "alternatives": [
                value.as_record() for value in alternatives
            ],
            "proof_episode_ids": list(proof_ids),
            "referent_root": root_id,
            "schema": AUDITORY_GROUNDED_CONSTRUCTION_SCHEMA,
        }
        construction = AuditoryGroundedConstruction(
            construction_id=_digest(provisional),
            referent_root=root_id,
            alternatives=alternatives,
            proof_episode_ids=proof_ids,
            authority_hmac_sha256=_sign(
                _CONSTRUCTION_HMAC_DOMAIN,
                self._key,
                provisional,
            ),
        )
        construction.verify(self._key)
        return AuditoryGroundedLearning(
            state="grounded",
            reason="unique_controlled_full_field_contrast",
            construction=construction,
        )

    def learn(self) -> AuditoryGroundedLearning:
        with self._lock:
            return self._derive()

    def resolve(self, kind_id: str) -> AuditoryGroundedResolution:
        sha256_digest(kind_id, "auditory grounded query kind")
        with self._lock:
            learned = self._derive()
        if learned.construction is None:
            return AuditoryGroundedResolution(
                state=learned.state,
                reason=learned.reason,
                kind_id=kind_id,
            )
        matching = tuple(
            value
            for value in learned.construction.alternatives
            if value.kind_id == kind_id
        )
        if len(matching) != 1:
            return AuditoryGroundedResolution(
                state="unknown",
                reason="kind_not_in_grounded_contrast",
                kind_id=kind_id,
            )
        selected = matching[0]
        return AuditoryGroundedResolution(
            state="grounded",
            reason="unique_controlled_full_field_contrast",
            kind_id=kind_id,
            referent_root=learned.construction.referent_root,
            referent_value=selected.referent_value,
            construction_id=learned.construction.construction_id,
        )

    def encoded_snapshot(self) -> dict[str, object]:
        with self._lock:
            payload = self._encoded(self._episodes)
        body = {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": AUDITORY_GROUNDED_ENVELOPE_SCHEMA,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        return {
            **body,
            "authority_hmac_sha256": _sign(
                _STATE_HMAC_DOMAIN,
                self._key,
                body,
            ),
        }

    def restore_encoded(self, envelope: object) -> None:
        expected = {
            "authority_hmac_sha256",
            "payload_base64",
            "schema",
            "sha256",
        }
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != expected
            or envelope.get("schema")
            != AUDITORY_GROUNDED_ENVELOPE_SCHEMA
        ):
            raise ValueError(
                "auditory grounded curriculum envelope changed"
            )
        body = {
            "payload_base64": envelope.get("payload_base64"),
            "schema": envelope.get("schema"),
            "sha256": envelope.get("sha256"),
        }
        if not hmac.compare_digest(
            str(envelope.get("authority_hmac_sha256")),
            _sign(_STATE_HMAC_DOMAIN, self._key, body),
        ):
            raise ValueError(
                "auditory grounded curriculum state HMAC changed"
            )
        text = envelope.get("payload_base64")
        if not isinstance(text, str):
            raise ValueError(
                "auditory grounded curriculum state is unreadable"
            )
        try:
            payload = base64.b64decode(text, validate=True)
            decoded = json.loads(payload)
        except Exception as error:
            raise ValueError(
                "auditory grounded curriculum state is unreadable"
            ) from error
        if (
            base64.b64encode(payload).decode("ascii") != text
            or hashlib.sha256(payload).hexdigest()
            != envelope.get("sha256")
            or len(payload) > self._encoded_state_capacity
            or not isinstance(decoded, Mapping)
            or set(decoded)
            != {
                "encoded_state_capacity",
                "episode_capacity",
                "episodes",
                "kind_capacity",
                "schema",
            }
            or decoded.get("schema") != AUDITORY_GROUNDED_STATE_SCHEMA
            or decoded.get("episode_capacity")
            != self._episode_capacity
            or decoded.get("kind_capacity") != self._kind_capacity
            or decoded.get("encoded_state_capacity")
            != self._encoded_state_capacity
            or not isinstance(decoded.get("episodes"), list)
            or len(decoded["episodes"]) > self._episode_capacity
            or _canonical(decoded) != payload
        ):
            raise ValueError(
                "auditory grounded curriculum state boundary changed"
            )
        restored: dict[str, AuditoryGroundedEpisode] = {}
        for record in decoded["episodes"]:
            if (
                not isinstance(record, Mapping)
                or set(record)
                != {
                    "admission",
                    "authority_hmac_sha256",
                    "episode_id",
                    "kind_id",
                    "roots",
                    "schema",
                }
                or record.get("schema")
                != AUDITORY_GROUNDED_EPISODE_SCHEMA
                or not isinstance(record.get("roots"), list)
            ):
                raise ValueError(
                    "auditory grounded episode record changed"
                )
            admission = _admission_from_record(
                record.get("admission"),
                authority_key=self._key,
            )
            episode = AuditoryGroundedEpisode(
                episode_id=record.get("episode_id"),
                kind_id=record.get("kind_id"),
                admission=admission,
                roots=tuple(
                    (item[0], item[1])
                    for item in record["roots"]
                    if isinstance(item, list) and len(item) == 2
                ),
                authority_hmac_sha256=record.get(
                    "authority_hmac_sha256"
                ),
            )
            if len(episode.roots) != len(record["roots"]):
                raise ValueError(
                    "auditory grounded episode roots changed"
                )
            episode.verify(self._key)
            if episode.episode_id in restored:
                raise ValueError(
                    "auditory grounded episode is duplicated"
                )
            restored[episode.episode_id] = episode
        if len({
            value.kind_id for value in restored.values()
        }) > self._kind_capacity:
            raise ValueError(
                "auditory grounded kind capacity changed"
            )
        encoded = self._encoded(restored)
        if encoded != payload:
            raise ValueError(
                "auditory grounded curriculum is not canonical"
            )
        with self._lock:
            self._episodes = restored
            self._encoded_bytes = len(encoded)

    def status(self) -> dict[str, object]:
        with self._lock:
            learned = self._derive()
            return {
                "encoded_bytes": self._encoded_bytes,
                "episode_count": len(self._episodes),
                "kind_count": len({
                    value.kind_id for value in self._episodes.values()
                }),
                "learning_state": learned.state,
                "schema": (
                    "guala.auditory.krimelack_grounded_status.v1"
                ),
            }


__all__ = (
    "AUDITORY_GROUNDED_CONSTRUCTION_SCHEMA",
    "AUDITORY_GROUNDED_ENVELOPE_SCHEMA",
    "AUDITORY_GROUNDED_EPISODE_SCHEMA",
    "AUDITORY_GROUNDED_STATE_SCHEMA",
    "AuditoryGroundedConstruction",
    "AuditoryGroundedLearning",
    "AuditoryGroundedResolution",
    "AuditoryKrimelackGroundedReferentOwner",
)
