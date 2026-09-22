"""Authenticated transient transfer for one anonymous passive sensory window."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.embodiment_world import (
    DEFAULT_MAX_ENCODED_STATE_BYTES,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.native_evidence_custody import (
    MAX_NATIVE_EVIDENCE_RECEIPT_BYTES,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SETTLEMENT,
)


PROFILE_SCHEMA = "guala.anonymous_passive_window.profile.v2"
RECEIPT_SCHEMA = "guala.anonymous_passive_window.receipt.v1"
STATE_SCHEMA = "guala.anonymous_passive_window.state.v2"
ENVELOPE_SCHEMA = "guala.anonymous_passive_window.state_hmac.v2"
_RECEIPT_DOMAIN = b"guala-anonymous-passive-window-receipt-v1\0"
_STATE_DOMAIN = b"guala-anonymous-passive-window-state-v2\0"
_IDENTITY_SCHEMA = "guala.anonymous_settled_window.identity.v1"
_CONSTRUCTION_AUTHORITY = object()
_PREPARED_AUTHORITY = object()
_UNDO_AUTHORITY = object()
_HEX = frozenset("0123456789abcdef")
_SENSES = ("sight", "sound", "touch", "smell", "taste", "body")

# One transient mount carries the exact upstream receipt registry, a topology
# receipt containing one digest and coordinate record per admitted sample, and
# one bounded world observation.  JSON string escaping can double the topology
# extent, so its exact transfer allowance is counted twice.  This transient
# ceiling is deliberately separate from the retained one-receipt lineage.
MAX_ANONYMOUS_PASSIVE_WINDOW_TRANSFER_BYTES = (
    MAX_NATIVE_EVIDENCE_RECEIPT_BYTES
    + 2 * MAX_NATIVE_SAMPLES_PER_SETTLEMENT * 512
    + DEFAULT_MAX_ENCODED_STATE_BYTES
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("anonymous passive-window key changed type")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("anonymous passive-window key changed extent")
    return result


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"anonymous passive-window {label} changed")
    return value


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"anonymous passive-window {label} changed")
    return value


def _exact_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"anonymous passive-window {label} changed")
    return value


def _exact_positive_int(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ValueError(f"anonymous passive-window {label} changed")
    return value


@dataclass(frozen=True, slots=True)
class AnonymousPassiveWindowProfile:
    profile_id: str
    max_mounts: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_mounts: int,
        max_state_bytes: int,
    ) -> "AnonymousPassiveWindowProfile":
        if (
            isinstance(max_mounts, bool)
            or max_mounts != 1
            or isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or not 0 < max_state_bytes <= 256 * 1024 * 1024
        ):
            raise ValueError(
                "anonymous passive-window profile must be a one-slot "
                "bounded transfer"
            )
        provisional = cls(
            profile_id=_identifier(profile_id, "profile"),
            max_mounts=1,
            max_state_bytes=max_state_bytes,
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_mounts=provisional.max_mounts,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_mounts": self.max_mounts,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        expected = AnonymousPassiveWindowProfile.create(
            profile_id=self.profile_id,
            max_mounts=self.max_mounts,
            max_state_bytes=self.max_state_bytes,
        )
        if expected != self:
            raise ValueError(
                "anonymous passive-window profile authority changed"
            )

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class AnonymousSettledWindowIdentity:
    window_id: str
    assembly_id: str
    settlement_receipt_sha256: str
    assembly_receipt_sha256: str

    def record(self) -> dict[str, object]:
        payload = {
            "assembly_id": self.assembly_id,
            "assembly_receipt_sha256": self.assembly_receipt_sha256,
            "schema": _IDENTITY_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "window_id": self.window_id,
        }
        return {**payload, "identity_sha256": _digest(payload)}


@dataclass(frozen=True, slots=True)
class AnonymousPassiveWindowReceipt:
    window_id: str
    assembly_id: str
    settlement_receipt_sha256: str
    assembly_receipt_sha256: str
    world_observation_receipt_sha256: str
    observed_senses: tuple[str, ...]
    auditory_topology: str
    auditory_receptor_ids: tuple[str, ...]
    audiovisual: bool
    topology_json: str
    topology_sha256: str
    full_field_tuple_count: int
    meaning_authority: bool
    word_authority: bool
    label_authority: bool
    recognition_authority: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def settled_window_identity(
        self,
    ) -> AnonymousSettledWindowIdentity:
        return AnonymousSettledWindowIdentity(
            window_id=self.window_id,
            assembly_id=self.assembly_id,
            settlement_receipt_sha256=(
                self.settlement_receipt_sha256
            ),
            assembly_receipt_sha256=self.assembly_receipt_sha256,
        )

    def payload(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "assembly_receipt_sha256": self.assembly_receipt_sha256,
            "auditory_receptor_ids": list(
                self.auditory_receptor_ids
            ),
            "auditory_topology": self.auditory_topology,
            "audiovisual": self.audiovisual,
            "full_field_tuple_count": self.full_field_tuple_count,
            "label_authority": self.label_authority,
            "meaning_authority": self.meaning_authority,
            "observed_senses": list(self.observed_senses),
            "recognition_authority": self.recognition_authority,
            "schema": RECEIPT_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "topology_json": self.topology_json,
            "topology_sha256": self.topology_sha256,
            "window_id": self.window_id,
            "word_authority": self.word_authority,
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        _identifier(self.window_id, "identity")
        _identifier(self.assembly_id, "assembly identity")
        if self.assembly_id not in (
            self.window_id,
            f"causal-{self.window_id}",
        ):
            raise ValueError(
                "anonymous passive-window assembly identity changed"
            )
        for value, label in (
            (self.settlement_receipt_sha256, "settlement"),
            (self.assembly_receipt_sha256, "assembly"),
            (
                self.world_observation_receipt_sha256,
                "world observation",
            ),
            (self.topology_sha256, "topology"),
            (self.authority_hmac_sha256, "HMAC"),
            (self.authority_receipt_sha256, "authority"),
        ):
            _sha(value, label)
        if (
            not isinstance(self.observed_senses, tuple)
            or not self.observed_senses
            or len(set(self.observed_senses))
            != len(self.observed_senses)
            or any(value not in _SENSES for value in self.observed_senses)
            or not isinstance(self.auditory_receptor_ids, tuple)
            or any(
                _identifier(value, "auditory receptor") != value
                for value in self.auditory_receptor_ids
            )
            or self.auditory_receptor_ids
            != tuple(sorted(set(self.auditory_receptor_ids)))
            or (
                self.auditory_topology == "mono"
                and len(self.auditory_receptor_ids) != 1
            )
            or (
                self.auditory_topology == "binaural"
                and len(self.auditory_receptor_ids) != 2
            )
            or (
                self.auditory_topology == "not_observed"
                and self.auditory_receptor_ids
            )
            or self.auditory_topology
            not in {"mono", "binaural", "not_observed"}
            or (
                ("sound" in self.observed_senses)
                != (self.auditory_topology != "not_observed")
            )
            or _exact_bool(self.audiovisual, "audiovisual")
            != (
                "sight" in self.observed_senses
                and "sound" in self.observed_senses
            )
            or _exact_positive_int(
                self.full_field_tuple_count,
                "full-field extent",
            )
            != self.full_field_tuple_count
            or _exact_bool(
                self.meaning_authority,
                "meaning authority",
            )
            or _exact_bool(self.word_authority, "word authority")
            or _exact_bool(self.label_authority, "label authority")
            or _exact_bool(
                self.recognition_authority,
                "recognition authority",
            )
        ):
            raise ValueError(
                "anonymous passive-window receipt structure changed"
            )
        if not isinstance(self.topology_json, str):
            raise ValueError(
                "anonymous passive-window topology record changed"
            )
        try:
            topology = json.loads(self.topology_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                "anonymous passive-window topology record is unreadable"
            ) from error
        if (
            _canonical(topology).decode("ascii") != self.topology_json
            or hashlib.sha256(
                self.topology_json.encode("ascii")
            ).hexdigest()
            != self.topology_sha256
        ):
            raise ValueError(
                "anonymous passive-window topology authority changed"
            )
        expected = hmac.new(
            key,
            _RECEIPT_DOMAIN + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, self.authority_hmac_sha256)
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": self.payload(),
            })
        ):
            raise ValueError(
                "anonymous passive-window receipt authority changed"
            )


@dataclass(frozen=True, slots=True)
class AnonymousPassiveWindowMount:
    receipt: AnonymousPassiveWindowReceipt
    settlement: CausalExperienceSettlement
    world_observation: ObservationSnapshot
    _construction_authority: object = field(repr=False)


@dataclass(slots=True)
class _Phase:
    value: str


@dataclass(frozen=True, slots=True)
class PreparedAnonymousPassiveWindow:
    mount: AnonymousPassiveWindowMount
    _prior: tuple[AnonymousPassiveWindowReceipt, ...] = field(
        repr=False
    )
    _staged: tuple[AnonymousPassiveWindowReceipt, ...] = field(
        repr=False
    )
    _phase: _Phase = field(repr=False, compare=False)
    _owner: object = field(repr=False, compare=False)
    _authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class AnonymousPassiveWindowUndo:
    _prior: tuple[AnonymousPassiveWindowReceipt, ...] = field(
        repr=False
    )
    _staged: tuple[AnonymousPassiveWindowReceipt, ...] = field(
        repr=False
    )
    _epoch: int = field(repr=False)
    _owner: object = field(repr=False, compare=False)
    _authority: object = field(repr=False, compare=False)


class AnonymousPassiveWindowCapacityError(RuntimeError):
    pass


class AnonymousPassiveWindowAuthority:
    """Issue one bounded transient mount and retain only receipt lineage."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: AnonymousPassiveWindowProfile,
        world_authority: EmbodimentWorldAuthority,
        max_transfer_bytes: int | None = None,
    ) -> None:
        self._key = _key(authority_key)
        if not isinstance(profile, AnonymousPassiveWindowProfile):
            raise TypeError(
                "anonymous passive-window profile is not typed"
            )
        profile.verify()
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "anonymous passive-window world authority is not typed"
            )
        self._profile = profile
        if max_transfer_bytes is None:
            max_transfer_bytes = profile.max_state_bytes
        if (
            isinstance(max_transfer_bytes, bool)
            or not isinstance(max_transfer_bytes, int)
            or not profile.max_state_bytes
            <= max_transfer_bytes
            <= 256 * 1024 * 1024
        ):
            raise ValueError(
                "anonymous passive-window transfer boundary changed"
            )
        self._max_transfer_bytes = max_transfer_bytes
        self._world = world_authority
        self._lineage: tuple[AnonymousPassiveWindowReceipt, ...] = ()
        self._prepared: PreparedAnonymousPassiveWindow | None = None
        self._latest_undo_epoch: int | None = None
        self._next_epoch = 1
        self._owner = object()
        self._lock = threading.RLock()
        if len(self._encoded(self._lineage)) > profile.max_state_bytes:
            raise AnonymousPassiveWindowCapacityError(
                "anonymous passive-window empty state exceeds capacity"
            )

    @property
    def receipt_lineage(
        self,
    ) -> tuple[AnonymousPassiveWindowReceipt, ...]:
        with self._lock:
            return self._lineage

    @staticmethod
    def _topology(
        settlement: CausalExperienceSettlement,
    ) -> tuple[str, tuple[str, ...], bool, str, int]:
        observed = tuple(
            value
            for value in settlement.interpretations
            if value.state == "observed"
        )
        sound = next(
            (value for value in observed if value.sense == "sound"),
            None,
        )
        if sound is None:
            if not observed:
                raise ValueError(
                    "anonymous passive window has no observed sense"
                )
            receptors = ()
            auditory_topology = "not_observed"
        else:
            receptors = tuple(sorted({
                value.sensor_id for value in sound.substreams
            }))
            if len(receptors) == 1:
                auditory_topology = "mono"
            elif len(receptors) == 2:
                auditory_topology = "binaural"
            else:
                raise ValueError(
                    "anonymous passive-window auditory receptor topology "
                    "is neither mono nor binaural"
                )
        topology = []
        field_count = 0
        for sense in observed:
            substreams = []
            for substream in sense.substreams:
                for field_tuple in substream.field_tuples:
                    if tuple(
                        name for name, _value in field_tuple.fields
                    ) != DSF_FIELD_ORDER:
                        raise ValueError(
                            "anonymous passive window flattened its DSF "
                            "field"
                        )
                    field_count += 1
                substreams.append({
                    "coordinates": [
                        list(value)
                        for value in substream.coordinates
                    ],
                    "field_tuple_receipts": [
                        value.authority_receipt_sha256
                        for value in substream.field_tuples
                    ],
                    "physical_quantity": (
                        substream.physical_quantity
                    ),
                    "physical_unit": substream.physical_unit,
                    "sensor_id": substream.sensor_id,
                    "substream_id": substream.substream_id,
                    "topology_index": substream.topology_index,
                })
            topology.append({
                "boundary_receipt_sha256": (
                    sense.boundary_receipt_sha256
                ),
                "sense": sense.sense,
                "substreams": substreams,
                "topology_receipt_sha256": (
                    sense.topology_receipt_sha256
                ),
            })
        topology_json = _canonical(topology).decode("ascii")
        return (
            auditory_topology,
            receptors,
            all(
                any(value.sense == required for value in observed)
                for required in ("sight", "sound")
            ),
            topology_json,
            field_count,
        )

    def _verify_mount(
        self,
        mount: AnonymousPassiveWindowMount,
    ) -> None:
        if (
            not isinstance(mount, AnonymousPassiveWindowMount)
            or mount._construction_authority
            is not _CONSTRUCTION_AUTHORITY
        ):
            raise TypeError(
                "anonymous passive-window mount is not authoritative"
            )
        receipt = mount.receipt
        if not isinstance(receipt, AnonymousPassiveWindowReceipt):
            raise TypeError(
                "anonymous passive-window receipt is not typed"
            )
        mount.settlement.verify()
        self._world.verify_observation_snapshot(
            mount.world_observation
        )
        (
            auditory_topology,
            receptors,
            audiovisual,
            topology_json,
            field_count,
        ) = self._topology(mount.settlement)
        if (
            mount.settlement.language_events
            or mount.settlement.routing_chis
            or mount.settlement.source_tags
        ):
            raise ValueError(
                "anonymous passive window carried symbolic or source "
                "authority"
            )
        expected_senses = tuple(
            value.sense
            for value in mount.settlement.interpretations
            if value.state == "observed"
        )
        if (
            mount.settlement.assembly_id != receipt.assembly_id
            or receipt.settlement_receipt_sha256
            != mount.settlement.authority_receipt_sha256
            or receipt.assembly_receipt_sha256
            != mount.settlement.assembly_receipt_sha256
            or receipt.world_observation_receipt_sha256
            != mount.world_observation.authority_receipt_sha256
            or receipt.observed_senses != expected_senses
            or receipt.auditory_topology != auditory_topology
            or receipt.auditory_receptor_ids != receptors
            or receipt.audiovisual != audiovisual
            or receipt.topology_json != topology_json
            or receipt.full_field_tuple_count != field_count
        ):
            raise ValueError(
                "anonymous passive-window mount linkage changed"
            )
        receipt.verify(self._key)

    def verify_mount(
        self,
        mount: AnonymousPassiveWindowMount,
    ) -> None:
        with self._lock:
            self._verify_mount(mount)

    @staticmethod
    def _transfer_extent_bytes(
        mount: AnonymousPassiveWindowMount,
    ) -> int:
        """Count exact retained bytes without hex-duplicating every receipt."""

        records = mount.settlement.receipt_registry.records
        if len({value.digest for value in records}) != len(records):
            raise ValueError(
                "anonymous passive-window transfer repeats a receipt"
            )
        return (
            sum(len(value.payload) for value in records)
            + len(_canonical(mount.receipt.record()))
            + len(_canonical(mount.world_observation.as_record()))
        )

    def prepare(
        self,
        *,
        window_id: str,
        settlement: CausalExperienceSettlement,
        world_observation: ObservationSnapshot,
    ) -> PreparedAnonymousPassiveWindow:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "anonymous passive-window mutation already prepared"
                )
            if not isinstance(
                settlement,
                CausalExperienceSettlement,
            ):
                raise TypeError(
                    "anonymous passive-window settlement is not typed"
                )
            settlement.verify()
            self._world.verify_observation_snapshot(world_observation)
            (
                auditory_topology,
                receptors,
                audiovisual,
                topology_json,
                field_count,
            ) = self._topology(settlement)
            provisional = AnonymousPassiveWindowReceipt(
                window_id=_identifier(window_id, "identity"),
                assembly_id=settlement.assembly_id,
                settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                assembly_receipt_sha256=(
                    settlement.assembly_receipt_sha256
                ),
                world_observation_receipt_sha256=(
                    world_observation.authority_receipt_sha256
                ),
                observed_senses=tuple(
                    value.sense
                    for value in settlement.interpretations
                    if value.state == "observed"
                ),
                auditory_topology=auditory_topology,
                auditory_receptor_ids=receptors,
                audiovisual=audiovisual,
                topology_json=topology_json,
                topology_sha256=hashlib.sha256(
                    topology_json.encode("ascii")
                ).hexdigest(),
                full_field_tuple_count=field_count,
                meaning_authority=False,
                word_authority=False,
                label_authority=False,
                recognition_authority=False,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._key,
                _RECEIPT_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            receipt = AnonymousPassiveWindowReceipt(
                window_id=provisional.window_id,
                assembly_id=provisional.assembly_id,
                settlement_receipt_sha256=(
                    provisional.settlement_receipt_sha256
                ),
                assembly_receipt_sha256=(
                    provisional.assembly_receipt_sha256
                ),
                world_observation_receipt_sha256=(
                    provisional.world_observation_receipt_sha256
                ),
                observed_senses=provisional.observed_senses,
                auditory_topology=provisional.auditory_topology,
                auditory_receptor_ids=(
                    provisional.auditory_receptor_ids
                ),
                audiovisual=provisional.audiovisual,
                topology_json=provisional.topology_json,
                topology_sha256=provisional.topology_sha256,
                full_field_tuple_count=(
                    provisional.full_field_tuple_count
                ),
                meaning_authority=False,
                word_authority=False,
                label_authority=False,
                recognition_authority=False,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            mount = AnonymousPassiveWindowMount(
                receipt=receipt,
                settlement=settlement,
                world_observation=world_observation,
                _construction_authority=_CONSTRUCTION_AUTHORITY,
            )
            self._verify_mount(mount)
            staged = (receipt,)
            transfer_extent_bytes = self._transfer_extent_bytes(mount)
            retained_state_bytes = len(self._encoded(staged))
            if (
                transfer_extent_bytes > self._max_transfer_bytes
                or retained_state_bytes > self._profile.max_state_bytes
            ):
                raise AnonymousPassiveWindowCapacityError(
                    "anonymous passive-window transfer capacity exhausted "
                    f"(transfer_bytes={transfer_extent_bytes}, "
                    f"transfer_limit={self._max_transfer_bytes}, "
                    f"retained_bytes={retained_state_bytes}, "
                    f"retained_limit={self._profile.max_state_bytes})"
                )
            prepared = PreparedAnonymousPassiveWindow(
                mount=mount,
                _prior=self._lineage,
                _staged=staged,
                _phase=_Phase("prepared"),
                _owner=self._owner,
                _authority=_PREPARED_AUTHORITY,
            )
            self._prepared = prepared
            return prepared

    def _verify_prepared(
        self,
        prepared: PreparedAnonymousPassiveWindow,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedAnonymousPassiveWindow,
            )
            or prepared._authority is not _PREPARED_AUTHORITY
            or prepared._owner is not self._owner
            or self._prepared is not prepared
            or prepared._phase.value != "prepared"
            or prepared._prior != self._lineage
        ):
            raise ValueError(
                "anonymous passive-window prepared custody changed"
            )

    def commit_prepared(
        self,
        prepared: PreparedAnonymousPassiveWindow,
    ) -> AnonymousPassiveWindowUndo:
        with self._lock:
            self._verify_prepared(prepared)
            epoch = self._next_epoch
            self._next_epoch += 1
            self._lineage = prepared._staged
            self._prepared = None
            self._latest_undo_epoch = epoch
            prepared._phase.value = "committed"
            return AnonymousPassiveWindowUndo(
                _prior=prepared._prior,
                _staged=prepared._staged,
                _epoch=epoch,
                _owner=self._owner,
                _authority=_UNDO_AUTHORITY,
            )

    def discard_prepared(
        self,
        prepared: PreparedAnonymousPassiveWindow,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared)
            self._prepared = None
            prepared._phase.value = "discarded"

    def rollback_committed(
        self,
        undo: AnonymousPassiveWindowUndo,
    ) -> None:
        with self._lock:
            if (
                self._prepared is not None
                or not isinstance(undo, AnonymousPassiveWindowUndo)
                or undo._authority is not _UNDO_AUTHORITY
                or undo._owner is not self._owner
                or self._latest_undo_epoch != undo._epoch
                or self._lineage != undo._staged
            ):
                raise ValueError(
                    "anonymous passive-window undo is stale"
                )
            self._lineage = undo._prior
            self._latest_undo_epoch = None

    def _body(
        self,
        lineage: tuple[AnonymousPassiveWindowReceipt, ...],
    ) -> dict[str, object]:
        if len(lineage) > 1:
            raise ValueError(
                "anonymous passive-window lineage exceeded one slot"
            )
        for receipt in lineage:
            receipt.verify(self._key)
        return {
            "profile": self._profile.record(),
            "receipt_lineage": [
                value.record() for value in lineage
            ],
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        lineage: tuple[AnonymousPassiveWindowReceipt, ...],
    ) -> bytes:
        body = self._body(lineage)
        return _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "anonymous passive-window mutation is prepared"
                )
            encoded = self._encoded(self._lineage)
            if len(encoded) > self._profile.max_state_bytes:
                raise AnonymousPassiveWindowCapacityError(
                    "anonymous passive-window state capacity exhausted"
                )
            return encoded

    @staticmethod
    def _receipt_from_record(
        value: object,
    ) -> AnonymousPassiveWindowReceipt:
        if not isinstance(value, dict):
            raise ValueError(
                "anonymous passive-window lineage is not a record"
            )
        expected = {
            "assembly_id",
            "assembly_receipt_sha256",
            "auditory_receptor_ids",
            "auditory_topology",
            "audiovisual",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "full_field_tuple_count",
            "label_authority",
            "meaning_authority",
            "observed_senses",
            "recognition_authority",
            "schema",
            "settlement_receipt_sha256",
            "topology_json",
            "topology_sha256",
            "window_id",
            "word_authority",
            "world_observation_receipt_sha256",
        }
        if set(value) != expected or value.get("schema") != RECEIPT_SCHEMA:
            raise ValueError(
                "anonymous passive-window lineage schema changed"
            )
        observed = value.get("observed_senses")
        receptors = value.get("auditory_receptor_ids")
        if not isinstance(observed, list) or not isinstance(receptors, list):
            raise ValueError(
                "anonymous passive-window lineage topology changed"
            )
        return AnonymousPassiveWindowReceipt(
            window_id=value.get("window_id"),
            assembly_id=value.get("assembly_id"),
            settlement_receipt_sha256=value.get(
                "settlement_receipt_sha256"
            ),
            assembly_receipt_sha256=value.get(
                "assembly_receipt_sha256"
            ),
            world_observation_receipt_sha256=value.get(
                "world_observation_receipt_sha256"
            ),
            observed_senses=tuple(observed),
            auditory_topology=value.get("auditory_topology"),
            auditory_receptor_ids=tuple(receptors),
            audiovisual=value.get("audiovisual"),
            topology_json=value.get("topology_json"),
            topology_sha256=value.get("topology_sha256"),
            full_field_tuple_count=value.get(
                "full_field_tuple_count"
            ),
            meaning_authority=value.get("meaning_authority"),
            word_authority=value.get("word_authority"),
            label_authority=value.get("label_authority"),
            recognition_authority=value.get(
                "recognition_authority"
            ),
            authority_hmac_sha256=value.get(
                "authority_hmac_sha256"
            ),
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: AnonymousPassiveWindowProfile,
        world_authority: EmbodimentWorldAuthority,
        encoded: bytes,
        max_transfer_bytes: int | None = None,
    ) -> "AnonymousPassiveWindowAuthority":
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            world_authority=world_authority,
            max_transfer_bytes=max_transfer_bytes,
        )
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > profile.max_state_bytes
        ):
            raise ValueError(
                "anonymous passive-window restore extent changed"
            )
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "anonymous passive-window state is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError(
                "anonymous passive-window state envelope changed"
            )
        body = envelope.get("body")
        if (
            not isinstance(body, dict)
            or set(body) != {"profile", "receipt_lineage", "schema"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != profile.record()
        ):
            raise ValueError(
                "anonymous passive-window state body changed"
            )
        lineage_records = body.get("receipt_lineage")
        if (
            not isinstance(lineage_records, list)
            or len(lineage_records) > 1
        ):
            raise ValueError(
                "anonymous passive-window state lineage changed"
            )
        signature = envelope.get("state_hmac_sha256")
        _sha(signature, "state HMAC")
        expected_signature = hmac.new(
            owner._key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError(
                "anonymous passive-window cold authority changed"
            )
        lineage = tuple(
            owner._receipt_from_record(value)
            for value in lineage_records
        )
        for receipt in lineage:
            receipt.verify(owner._key)
        owner._lineage = lineage
        if owner.snapshot_encoded() != encoded:
            raise ValueError(
                "anonymous passive-window cold state changed"
            )
        return owner


__all__ = (
    "AnonymousPassiveWindowAuthority",
    "AnonymousPassiveWindowCapacityError",
    "AnonymousPassiveWindowMount",
    "AnonymousPassiveWindowProfile",
    "AnonymousPassiveWindowReceipt",
    "AnonymousPassiveWindowUndo",
    "AnonymousSettledWindowIdentity",
    "MAX_ANONYMOUS_PASSIVE_WINDOW_TRANSFER_BYTES",
    "PreparedAnonymousPassiveWindow",
)
