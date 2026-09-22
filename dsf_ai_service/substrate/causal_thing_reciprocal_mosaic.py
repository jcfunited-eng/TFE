"""Causally owned reciprocal trace classes for retained THING mosaics.

The THING owner is the sole identity authority.  Encounter partitions and
passive whole-organism learning records may contribute complete experienced
sensory roots to the same physically continuous THING.  No sensory comparison,
label, threshold, distance, score, nearest exemplar, chi/psi identity, or ML
operation can create or merge a THING.

Evocation uses exact equality only to establish recurrence of a trace that was
already experienced and retained under causal custody.  A unique recurrence is
not final recognition, familiarity, word identity, meaning, or generalization.
A never-experienced trace remains unresolved; a trace retained by more than one
THING remains ambiguous.

``sensory_expansion_owner`` remains as a legacy compatibility input for
existing callers.  New active ownership must use
``passive_learning_owner``.  Partition, passive-record, and legacy-expansion
receipts are preserved in separate fields and are never relabelled as one
another.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaic,
    CausalThingMosaicOwner,
    FullFieldSensoryRoot,
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    CausalThingSensoryExpansionOwner,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PassiveWholeOrganismThingLearningOwner,
)


CLASS_SCHEMA = "guala.causal_thing.reciprocal_variant_class.v2"
EVOCATION_SCHEMA = "guala.causal_thing.reciprocal_evocation.v2"
STATUS_SCHEMA = "guala.causal_thing.reciprocal_mosaic.status.v2"

_CLASS_DOMAIN = b"guala-causal-thing-reciprocal-class-v2\0"
_EVOCATION_DOMAIN = b"guala-causal-thing-reciprocal-evocation-v2\0"
_TRACE_RECURRENCE_SCOPE = "exact_experienced_trace_recurrence_only"
_HEX = frozenset("0123456789abcdef")
_SENSES = tuple(value.value for value in SENSE_ORDER)


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
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("reciprocal mosaic authority key changed")
    return hashlib.sha256(
        b"guala-causal-thing-reciprocal-owner-v2\0" + raw
    ).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def _canonical_cue_senses(
    values: tuple[str, ...],
) -> tuple[str, ...]:
    selected = frozenset(values)
    return tuple(sense for sense in _SENSES if sense in selected)


def _root_identity(root: FullFieldSensoryRoot) -> tuple[str, str, int, str]:
    return (
        root.sense,
        root.physical_value_sha256,
        root.topology_index,
        root.full_evidence_json,
    )


def _unique_roots(
    roots: tuple[FullFieldSensoryRoot, ...],
) -> tuple[FullFieldSensoryRoot, ...]:
    by_identity = {}
    for root in roots:
        root.verify()
        by_identity[_root_identity(root)] = root
    return tuple(by_identity[key] for key in sorted(by_identity))


def _exact_experienced_trace_recurrence(
    roots: tuple[FullFieldSensoryRoot, ...],
    *,
    cue_senses: tuple[str, ...],
    cue_route_keys: tuple[tuple[str, str], ...],
) -> bool:
    """Test recurrence of one retained trace, never recognition/familiarity."""

    retained_route_keys = tuple(sorted(
        root.route_key
        for root in roots
        if root.sense in cue_senses
    ))
    return bool(retained_route_keys) and retained_route_keys == cue_route_keys


@dataclass(frozen=True, slots=True)
class CausalThingReciprocalClass:
    thing_id: str
    thing_mosaic_receipt_sha256: str
    partition_receipt_sha256s: tuple[str, ...]
    passive_record_receipt_sha256s: tuple[str, ...]
    legacy_sensory_expansion_receipt_sha256s: tuple[str, ...]
    roots_by_sense: tuple[
        tuple[str, tuple[FullFieldSensoryRoot, ...]], ...
    ]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def full_field_roots(self) -> tuple[FullFieldSensoryRoot, ...]:
        return tuple(
            root
            for _sense, roots in self.roots_by_sense
            for root in roots
        )

    def payload(self) -> dict[str, object]:
        return {
            "legacy_sensory_expansion_receipt_sha256s": list(
                self.legacy_sensory_expansion_receipt_sha256s
            ),
            "partition_receipt_sha256s": list(
                self.partition_receipt_sha256s
            ),
            "passive_record_receipt_sha256s": list(
                self.passive_record_receipt_sha256s
            ),
            "roots_by_sense": [
                {
                    "roots": [root.record() for root in roots],
                    "sense": sense,
                }
                for sense, roots in self.roots_by_sense
            ],
            "schema": CLASS_SCHEMA,
            "thing_id": self.thing_id,
            "thing_mosaic_receipt_sha256": (
                self.thing_mosaic_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class CausalThingReciprocalEvocation:
    state: str
    cue_senses: tuple[str, ...]
    cue_roots: tuple[FullFieldSensoryRoot, ...]
    matching_route_keys: tuple[tuple[str, str], ...]
    thing_ids: tuple[str, ...]
    candidate: CausalThingReciprocalClass | None
    evoked_full_field_roots: tuple[FullFieldSensoryRoot, ...]
    authority_scope: str
    final_recognition_authority: bool
    familiarity_authority: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "authority_scope": self.authority_scope,
            "candidate_class_receipt_sha256": (
                None
                if self.candidate is None
                else self.candidate.authority_receipt_sha256
            ),
            "cue_roots": [root.record() for root in self.cue_roots],
            "cue_senses": list(self.cue_senses),
            "evoked_full_field_roots": [
                root.record() for root in self.evoked_full_field_roots
            ],
            "familiarity_authority": self.familiarity_authority,
            "final_recognition_authority": (
                self.final_recognition_authority
            ),
            "matching_route_keys": [
                list(value) for value in self.matching_route_keys
            ],
            "schema": EVOCATION_SCHEMA,
            "state": self.state,
            "thing_ids": list(self.thing_ids),
        }


class CausalThingReciprocalMosaicOwner:
    """Derive bounded reciprocal trace classes from causal THING custody."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        thing_owner: CausalThingMosaicOwner,
        passive_learning_owner: (
            PassiveWholeOrganismThingLearningOwner | None
        ) = None,
        sensory_expansion_owner: (
            CausalThingSensoryExpansionOwner | None
        ) = None,
        max_classes: int,
        max_roots_per_class: int,
        max_cue_roots: int,
    ) -> None:
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError(
                "reciprocal mosaic requires the causal THING owner"
            )
        if (
            passive_learning_owner is not None
            and not isinstance(
                passive_learning_owner,
                PassiveWholeOrganismThingLearningOwner,
            )
        ):
            raise TypeError(
                "reciprocal mosaic passive learning owner is not typed"
            )
        if (
            passive_learning_owner is not None
            and getattr(passive_learning_owner, "_things", None)
            is not thing_owner
        ):
            raise ValueError(
                "reciprocal mosaic crossed passive THING ownership"
            )
        if (
            sensory_expansion_owner is not None
            and not isinstance(
                sensory_expansion_owner,
                CausalThingSensoryExpansionOwner,
            )
        ):
            raise TypeError(
                "reciprocal mosaic sensory expansion owner is not typed"
            )
        root = _key(authority_key)
        self._class_key = hashlib.sha256(
            _CLASS_DOMAIN + root
        ).digest()
        self._evocation_key = hashlib.sha256(
            _EVOCATION_DOMAIN + root
        ).digest()
        self._things = thing_owner
        self._passive_learning = passive_learning_owner
        self._sensory_expansions = sensory_expansion_owner
        self._max_classes = _positive(max_classes, "reciprocal class capacity")
        self._max_roots_per_class = _positive(
            max_roots_per_class,
            "reciprocal root capacity",
        )
        self._max_cue_roots = _positive(
            max_cue_roots,
            "reciprocal cue capacity",
        )

    def verify_thing_owner_exact(
        self,
        thing_owner: CausalThingMosaicOwner,
    ) -> None:
        """Require the one in-process THING identity owner used here."""

        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError(
                "reciprocal mosaic ownership check requires a THING owner"
            )
        if self._things is not thing_owner:
            raise ValueError(
                "reciprocal mosaic crossed causal THING ownership"
            )

    def _roots_for_mosaic(
        self,
        mosaic: CausalThingMosaic,
    ) -> tuple[FullFieldSensoryRoot, ...]:
        contact_roots = tuple(
            root
            for partition in mosaic.partitions
            for root in partition.full_field_roots
        )
        passive_roots = (
            ()
            if self._passive_learning is None
            else self._passive_learning.roots_for_thing(mosaic.thing_id)
        )
        legacy_roots = (
            ()
            if self._sensory_expansions is None
            else self._sensory_expansions.roots_for_thing(mosaic.thing_id)
        )
        return _unique_roots(contact_roots + passive_roots + legacy_roots)

    def _verify_class(
        self,
        value: CausalThingReciprocalClass,
    ) -> None:
        if not isinstance(value, CausalThingReciprocalClass):
            raise TypeError("reciprocal THING class is not typed")
        _sha(value.thing_id, "reciprocal THING id")
        _sha(
            value.thing_mosaic_receipt_sha256,
            "reciprocal THING mosaic",
        )
        matches = tuple(
            mosaic
            for mosaic in self._things.mosaics
            if mosaic.thing_id == value.thing_id
        )
        if len(matches) != 1:
            raise ValueError(
                "reciprocal class does not name one retained THING"
            )
        mosaic = matches[0]
        expected_partitions = tuple(
            partition.authority_receipt_sha256
            for partition in mosaic.partitions
        )
        expected_passive = (
            ()
            if self._passive_learning is None
            else self._passive_learning.receipts_for_thing(value.thing_id)
        )
        expected_legacy = (
            ()
            if self._sensory_expansions is None
            else self._sensory_expansions.receipts_for_thing(value.thing_id)
        )
        expected_roots = self._roots_for_mosaic(mosaic)
        expected_roots_by_sense = tuple(
            (
                sense,
                tuple(
                    root for root in expected_roots
                    if root.sense == sense
                ),
            )
            for sense in _SENSES
            if any(root.sense == sense for root in expected_roots)
        )
        if (
            not value.partition_receipt_sha256s
            or value.thing_mosaic_receipt_sha256
            != mosaic.authority_receipt_sha256
            or value.partition_receipt_sha256s != expected_partitions
            or value.passive_record_receipt_sha256s != expected_passive
            or value.legacy_sensory_expansion_receipt_sha256s
            != expected_legacy
            or value.roots_by_sense != expected_roots_by_sense
            or len(value.full_field_roots) > self._max_roots_per_class
        ):
            raise ValueError("reciprocal THING class extent changed")
        for receipt in value.partition_receipt_sha256s:
            _sha(receipt, "reciprocal partition")
        for receipt in value.passive_record_receipt_sha256s:
            _sha(receipt, "reciprocal passive record")
        for receipt in value.legacy_sensory_expansion_receipt_sha256s:
            _sha(receipt, "reciprocal legacy sensory expansion")
        for root in value.full_field_roots:
            root.verify()
        expected_signature = hmac.new(
            self._class_key,
            _CLASS_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_signature, value.authority_hmac_sha256
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_signature,
                "payload": value.payload(),
            })
        ):
            raise ValueError("reciprocal THING class authority changed")

    def _form_class(
        self,
        mosaic: CausalThingMosaic,
    ) -> CausalThingReciprocalClass:
        roots = self._roots_for_mosaic(mosaic)
        roots_by_sense = tuple(
            (
                sense,
                tuple(root for root in roots if root.sense == sense),
            )
            for sense in _SENSES
            if any(root.sense == sense for root in roots)
        )
        if (
            not roots_by_sense
            or len(roots) > self._max_roots_per_class
        ):
            raise RuntimeError(
                "reciprocal THING class root capacity exhausted"
            )
        partition_receipts = tuple(
            value.authority_receipt_sha256
            for value in mosaic.partitions
        )
        passive_receipts = (
            ()
            if self._passive_learning is None
            else self._passive_learning.receipts_for_thing(
                mosaic.thing_id
            )
        )
        legacy_receipts = (
            ()
            if self._sensory_expansions is None
            else self._sensory_expansions.receipts_for_thing(
                mosaic.thing_id
            )
        )
        payload = {
            "legacy_sensory_expansion_receipt_sha256s": list(
                legacy_receipts
            ),
            "partition_receipt_sha256s": list(partition_receipts),
            "passive_record_receipt_sha256s": list(passive_receipts),
            "roots_by_sense": [
                {
                    "roots": [root.record() for root in sense_roots],
                    "sense": sense,
                }
                for sense, sense_roots in roots_by_sense
            ],
            "schema": CLASS_SCHEMA,
            "thing_id": mosaic.thing_id,
            "thing_mosaic_receipt_sha256": (
                mosaic.authority_receipt_sha256
            ),
        }
        signature = hmac.new(
            self._class_key,
            _CLASS_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = CausalThingReciprocalClass(
            thing_id=mosaic.thing_id,
            thing_mosaic_receipt_sha256=(
                mosaic.authority_receipt_sha256
            ),
            partition_receipt_sha256s=partition_receipts,
            passive_record_receipt_sha256s=passive_receipts,
            legacy_sensory_expansion_receipt_sha256s=legacy_receipts,
            roots_by_sense=roots_by_sense,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self._verify_class(result)
        return result

    def classes(self) -> tuple[CausalThingReciprocalClass, ...]:
        mosaics = self._things.mosaics
        if len(mosaics) > self._max_classes:
            raise RuntimeError(
                "reciprocal THING class capacity exhausted"
            )
        return tuple(
            self._form_class(mosaic)
            for mosaic in mosaics
        )

    def retained_trigger_partition(
        self,
        thing_class: CausalThingReciprocalClass,
        settlement_receipt_sha256: str,
    ) -> str | None:
        """Return the partition that physically admitted one settlement."""

        self._verify_class(thing_class)
        _sha(
            settlement_receipt_sha256,
            "reciprocal trigger settlement",
        )
        matches = tuple(
            partition.authority_receipt_sha256
            for mosaic in self._things.mosaics
            if (
                mosaic.thing_id == thing_class.thing_id
                and mosaic.authority_receipt_sha256
                == thing_class.thing_mosaic_receipt_sha256
            )
            for partition in mosaic.partitions
            if (
                partition.authority_receipt_sha256
                in thing_class.partition_receipt_sha256s
                and partition.settlement_receipt_sha256
                == settlement_receipt_sha256
            )
        )
        if len(matches) > 1:
            raise ValueError(
                "one THING retained the same settlement in two partitions"
            )
        return matches[0] if matches else None

    def verify_evocation(
        self,
        value: CausalThingReciprocalEvocation,
    ) -> None:
        """Verify one exact-trace result without granting recognition."""

        if not isinstance(value, CausalThingReciprocalEvocation):
            raise TypeError("reciprocal THING evocation is not typed")
        if (
            value.state not in {"unique", "ambiguous", "unresolved"}
            or value.authority_scope != _TRACE_RECURRENCE_SCOPE
            or value.final_recognition_authority is not False
            or value.familiarity_authority is not False
            or not value.cue_senses
            or value.cue_senses
            != _canonical_cue_senses(value.cue_senses)
            or any(sense not in _SENSES for sense in value.cue_senses)
            or not value.cue_roots
            or len(value.cue_roots) > self._max_cue_roots
        ):
            raise ValueError("reciprocal THING evocation extent changed")
        for root in value.cue_roots:
            root.verify()
        for root in value.evoked_full_field_roots:
            root.verify()
        for digest, label in (
            (value.authority_hmac_sha256, "reciprocal evocation HMAC"),
            (
                value.authority_receipt_sha256,
                "reciprocal evocation authority",
            ),
        ):
            _sha(digest, label)
        classes = {item.thing_id: item for item in self.classes()}
        if value.state == "unique":
            if (
                value.candidate is None
                or value.thing_ids != (value.candidate.thing_id,)
                or classes.get(value.candidate.thing_id) != value.candidate
                or value.evoked_full_field_roots
                != value.candidate.full_field_roots
            ):
                raise ValueError(
                    "unique reciprocal THING evocation changed"
                )
            self._verify_class(value.candidate)
        elif (
            value.candidate is not None
            or value.evoked_full_field_roots
        ):
            raise ValueError(
                "non-unique reciprocal THING evocation selected a class"
            )
        expected = hmac.new(
            self._evocation_key,
            _EVOCATION_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError(
                "reciprocal THING evocation authority changed"
            )

    def evoke(
        self,
        settlement: CausalExperienceSettlement,
        *,
        cue_senses: tuple[str, ...],
    ) -> CausalThingReciprocalEvocation:
        """Report exact recurrence of one already-experienced sensory trace.

        ``unique`` means one retained THING owns the exact cue trace.  It does
        not establish final recognition, familiarity, meaning, or an unseen
        variant relation.
        """

        if (
            not cue_senses
            or cue_senses != _canonical_cue_senses(cue_senses)
            or any(value not in _SENSES for value in cue_senses)
        ):
            raise ValueError("reciprocal cue senses changed")
        roots = tuple(
            root
            for root in full_field_sensory_roots(settlement)
            if root.sense in cue_senses
        )
        if not roots:
            raise ValueError("reciprocal evocation has no observed cue")
        if len(roots) > self._max_cue_roots:
            raise RuntimeError("reciprocal cue capacity exhausted")
        classes = self.classes()
        by_id = {value.thing_id: value for value in classes}
        cue_keys = tuple(sorted(root.route_key for root in roots))
        contact_matches = tuple(
            (
                mosaic.thing_id,
                "partition",
                partition.authority_receipt_sha256,
            )
            for mosaic in self._things.mosaics
            for partition in mosaic.partitions
            if _exact_experienced_trace_recurrence(
                partition.full_field_roots,
                cue_senses=cue_senses,
                cue_route_keys=cue_keys,
            )
        )
        passive_matches = (
            ()
            if self._passive_learning is None
            else tuple(
                (
                    record.thing_id,
                    "passive_record",
                    record.authority_receipt_sha256,
                )
                for record in self._passive_learning.records
                if _exact_experienced_trace_recurrence(
                    record.full_field_roots,
                    cue_senses=cue_senses,
                    cue_route_keys=cue_keys,
                )
            )
        )
        legacy_matches = (
            ()
            if self._sensory_expansions is None
            else tuple(
                (
                    expansion.thing_id,
                    "legacy_sensory_expansion",
                    expansion.authority_receipt_sha256,
                )
                for expansion in self._sensory_expansions.expansions
                if _exact_experienced_trace_recurrence(
                    expansion.full_field_roots,
                    cue_senses=cue_senses,
                    cue_route_keys=cue_keys,
                )
            )
        )
        matches = contact_matches + passive_matches + legacy_matches
        thing_ids = tuple(sorted({
            thing_id for thing_id, _source_kind, _receipt in matches
        }))
        state = (
            "unique"
            if len(thing_ids) == 1
            else "ambiguous"
            if thing_ids
            else "unresolved"
        )
        candidate = by_id[thing_ids[0]] if state == "unique" else None
        evoked = (
            candidate.full_field_roots
            if candidate is not None
            else ()
        )
        provisional = CausalThingReciprocalEvocation(
            state=state,
            cue_senses=cue_senses,
            cue_roots=roots,
            matching_route_keys=cue_keys if matches else (),
            thing_ids=thing_ids,
            candidate=candidate,
            evoked_full_field_roots=evoked,
            authority_scope=_TRACE_RECURRENCE_SCOPE,
            final_recognition_authority=False,
            familiarity_authority=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._evocation_key,
            _EVOCATION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = CausalThingReciprocalEvocation(
            state=provisional.state,
            cue_senses=provisional.cue_senses,
            cue_roots=provisional.cue_roots,
            matching_route_keys=provisional.matching_route_keys,
            thing_ids=provisional.thing_ids,
            candidate=provisional.candidate,
            evoked_full_field_roots=provisional.evoked_full_field_roots,
            authority_scope=provisional.authority_scope,
            final_recognition_authority=(
                provisional.final_recognition_authority
            ),
            familiarity_authority=provisional.familiarity_authority,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify_evocation(result)
        return result

    def status(self) -> dict[str, object]:
        classes = self.classes()
        return {
            "authority_scope": _TRACE_RECURRENCE_SCOPE,
            "classes": len(classes),
            "experienced_variant_roots": sum(
                len(value.full_field_roots) for value in classes
            ),
            "familiarity_authority": False,
            "final_recognition_authority": False,
            "integrated_passive_records": (
                0
                if self._passive_learning is None
                else self._passive_learning.status()["records"]
            ),
            "legacy_sensory_expansions": (
                0
                if self._sensory_expansions is None
                else self._sensory_expansions.status()["expansions"]
            ),
            "max_classes": self._max_classes,
            "max_cue_roots": self._max_cue_roots,
            "max_roots_per_class": self._max_roots_per_class,
            "schema": STATUS_SCHEMA,
            "signal_matching": False,
            "unseen_variant_guessing": False,
        }


__all__ = (
    "CausalThingReciprocalClass",
    "CausalThingReciprocalEvocation",
    "CausalThingReciprocalMosaicOwner",
)
