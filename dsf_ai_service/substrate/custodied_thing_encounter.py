"""Custody-native causal THING encounter partitioning.

One already-settled physical occurrence enters through a bounded read-only
custody capability.  The world execution supplies entity continuity; no
sensory lane supplies identity.  Every observed full-field sensory root
participates symmetrically in the retained mosaic, while an unavailable lane
remains honestly absent.

``ThingEncounterPartition.entity_root_keys`` is retained as the mounted v1
transport field.  In this authority it means *participating encounter roots*,
not roots that identify the entity.  The authenticated reciprocal hold
relation and its causal before/after chain are the only entity-continuity
authority.

No sensory producer is available here, so this module cannot transduce,
rebuild, remount, or resettle an occurrence.  It contains no labels, sensory
priority, similarity, score, threshold, transcript, Chi, Atlas, or ML path.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac

from dsf_ai_service.substrate.causal_thing_mosaic import (
    _PARTITION_DOMAIN,
    ThingEncounterPartition,
    W1ContactThingEncounterAuthority,
    _canonical,
    _digest,
    _sha,
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
)


THING_MOSAIC_CONSUMER_ID = "causal-thing-mosaic"
PHYSICAL_SURFACE_CONTINUITY_SCHEMA = (
    "guala.physical_surface.continuity_witness.v1"
)
_PHYSICAL_SURFACE_CONTINUITY_DOMAIN = (
    b"guala-physical-surface-continuity-witness-v1\0"
)


@dataclass(frozen=True, slots=True)
class PhysicalSurfaceContinuityWitness:
    """Authenticated continuity of one optically focused physical entity."""

    settlement_receipt_sha256: str
    settlement_structural_fingerprint: str
    world_observation_receipt_sha256: str
    world_revision: int
    entity_continuity_hmac_sha256: str
    foveal_scan_receipt_sha256: str
    foveal_observation_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "entity_continuity_hmac_sha256": (
                self.entity_continuity_hmac_sha256
            ),
            "foveal_observation_receipt_sha256": (
                self.foveal_observation_receipt_sha256
            ),
            "foveal_scan_receipt_sha256": (
                self.foveal_scan_receipt_sha256
            ),
            "schema": PHYSICAL_SURFACE_CONTINUITY_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "world_revision": self.world_revision,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    @classmethod
    def from_record(
        cls,
        raw: object,
    ) -> "PhysicalSurfaceContinuityWitness":
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "entity_continuity_hmac_sha256",
            "foveal_observation_receipt_sha256",
            "foveal_scan_receipt_sha256",
            "schema",
            "settlement_receipt_sha256",
            "settlement_structural_fingerprint",
            "world_observation_receipt_sha256",
            "world_revision",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != PHYSICAL_SURFACE_CONTINUITY_SCHEMA
        ):
            raise ValueError("physical surface continuity record changed")
        values = dict(raw)
        values.pop("schema")
        return cls(**values)


def _participating_root_keys(
    partition_roots,
) -> tuple[tuple[str, str], ...]:
    """Return every independently observed sensory root in stable order."""

    return tuple(sorted(root.route_key for root in partition_roots))


class CustodiedW1ContactThingEncounterAuthority(
    W1ContactThingEncounterAuthority
):
    """Partition one contacted entity without making any sense authoritative."""

    def entity_continuity_from_custody(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        capability: SettledExperienceConsumerCapability,
    ) -> str:
        if not isinstance(
            custody_authority,
            SettledExperienceCustodyAuthority,
        ) or not isinstance(
            capability,
            SettledExperienceConsumerCapability,
        ):
            raise TypeError(
                "THING continuity requires typed settled custody"
            )
        view = custody_authority.open_child(capability)
        contacted = self._contact_object_id(view.world_observation)
        if contacted is None:
            raise ValueError(
                "THING continuity requires one contacted entity"
            )
        return self._entity_continuity(contacted)
    def verify_physical_surface_continuity_witness(
        self,
        witness: PhysicalSurfaceContinuityWitness,
    ) -> None:
        if not isinstance(
            witness,
            PhysicalSurfaceContinuityWitness,
        ):
            raise TypeError(
                "physical surface continuity witness is not typed"
            )
        for digest, label in (
            (witness.settlement_receipt_sha256, "surface settlement"),
            (
                witness.settlement_structural_fingerprint,
                "surface structural fingerprint",
            ),
            (
                witness.world_observation_receipt_sha256,
                "surface world observation",
            ),
            (
                witness.entity_continuity_hmac_sha256,
                "surface entity continuity",
            ),
            (
                witness.foveal_scan_receipt_sha256,
                "surface foveal scan",
            ),
            (
                witness.foveal_observation_receipt_sha256,
                "surface foveal observation",
            ),
            (witness.authority_hmac_sha256, "surface witness HMAC"),
            (witness.authority_receipt_sha256, "surface witness authority"),
        ):
            _sha(digest, label)
        if (
            isinstance(witness.world_revision, bool)
            or not isinstance(witness.world_revision, int)
            or witness.world_revision < 0
        ):
            raise ValueError("surface witness world revision changed")
        unsigned = witness.payload()
        expected = hmac.new(
            self._partition_key,
            _PHYSICAL_SURFACE_CONTINUITY_DOMAIN + _canonical(unsigned),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                witness.authority_hmac_sha256,
            )
            or witness.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": unsigned,
            })
        ):
            raise ValueError(
                "physical surface continuity witness authority changed"
            )

    def physical_surface_continuity_witness(
        self,
        *,
        settlement,
        world_observation,
        foveal_authority,
        foveal_observation,
    ) -> PhysicalSurfaceContinuityWitness:
        from dsf_ai_service.substrate.w1_physical_foveal_observation import (
            PhysicalFovealObservation,
            PhysicalFovealObservationAuthority,
            _surface_sha256,
        )
        if (
            not isinstance(
                foveal_authority,
                PhysicalFovealObservationAuthority,
            )
            or not isinstance(
                foveal_observation,
                PhysicalFovealObservation,
            )
        ):
            raise TypeError(
                "physical surface continuity requires typed foveal evidence"
            )
        self._world.verify_observation_snapshot(world_observation)
        foveal_authority.verify_settlement(
            foveal_observation,
            settlement,
        )
        plan = foveal_observation.scan_plan
        if plan.world_revision != world_observation.revision:
            raise ValueError(
                "physical surface continuity crossed world revision"
            )
        matches = tuple(
            item
            for item in world_observation.objects
            if (
                item.position == plan.target_position
                and item.radius_mm == plan.target_radius_mm
                and item.optical_surface is not None
                and _surface_sha256(item.optical_surface)
                == plan.surface_sha256
            )
        )
        if len(matches) != 1:
            raise ValueError(
                "foveal evidence does not resolve one physical surface"
            )
        provisional = PhysicalSurfaceContinuityWitness(
            settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                settlement.structural_fingerprint
            ),
            world_observation_receipt_sha256=(
                world_observation.authority_receipt_sha256
            ),
            world_revision=world_observation.revision,
            entity_continuity_hmac_sha256=(
                self._entity_continuity(matches[0].object_id)
            ),
            foveal_scan_receipt_sha256=(
                plan.authority_receipt_sha256
            ),
            foveal_observation_receipt_sha256=(
                foveal_observation.authority_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._partition_key,
            _PHYSICAL_SURFACE_CONTINUITY_DOMAIN
            + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        witness = PhysicalSurfaceContinuityWitness(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if not name.startswith("authority_")
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify_physical_surface_continuity_witness(witness)
        return witness



    def partition_from_physical_surface(
        self,
        *,
        settlement,
        world_observation,
        foveal_authority,
        foveal_observation,
        prior: ThingEncounterPartition | None = None,
    ) -> tuple[
        ThingEncounterPartition,
        PhysicalSurfaceContinuityWitness,
    ]:
        if prior is not None:
            if not isinstance(prior, ThingEncounterPartition):
                raise TypeError("prior THING partition is not typed")
            self.verify(prior)
        witness = self.physical_surface_continuity_witness(
            settlement=settlement,
            world_observation=world_observation,
            foveal_authority=foveal_authority,
            foveal_observation=foveal_observation,
        )
        roots = full_field_sensory_roots(settlement)
        if len(roots) > self._max_roots:
            raise RuntimeError(
                "physical surface partition root capacity exhausted"
            )
        if (
            prior is not None
            and (
                prior.settlement_receipt_sha256
                == witness.settlement_receipt_sha256
                or prior.physical_surface_observation_receipt_sha256
                == witness.foveal_observation_receipt_sha256
            )
        ):
            exact_replay = (
                prior.settlement_receipt_sha256
                == witness.settlement_receipt_sha256
                and prior.settlement_structural_fingerprint
                == witness.settlement_structural_fingerprint
                and prior.world_observation_receipt_sha256
                == witness.world_observation_receipt_sha256
                and prior.world_revision == witness.world_revision
                and prior.entity_continuity_hmac_sha256
                == witness.entity_continuity_hmac_sha256
                and prior.physical_surface_observation_receipt_sha256
                == witness.foveal_observation_receipt_sha256
                and prior.execution_receipt_sha256 is None
                and not any((
                    prior.source_occurrence_id,
                    prior.parent_custody_receipt_sha256,
                    prior.thing_custody_capability_receipt_sha256,
                ))
                and prior.entity_root_keys
                == _participating_root_keys(roots)
                and prior.full_field_roots == roots
            )
            if not exact_replay:
                raise ValueError(
                    "physical surface encounter receipt collision"
                )
            return prior, witness
        provisional = ThingEncounterPartition(
            source_occurrence_id=None,
            parent_custody_receipt_sha256=None,
            thing_custody_capability_receipt_sha256=None,
            settlement_receipt_sha256=(
                witness.settlement_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                witness.settlement_structural_fingerprint
            ),
            world_observation_receipt_sha256=(
                witness.world_observation_receipt_sha256
            ),
            execution_receipt_sha256=None,
            world_revision=witness.world_revision,
            entity_continuity_hmac_sha256=(
                witness.entity_continuity_hmac_sha256
            ),
            prior_partition_receipt_sha256=(
                prior.authority_receipt_sha256
                if prior is not None
                else None
            ),
            entity_root_keys=_participating_root_keys(roots),
            full_field_roots=roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
            physical_surface_observation_receipt_sha256=(
                witness.foveal_observation_receipt_sha256
            ),
        )
        signature = hmac.new(
            self._partition_key,
            _PARTITION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        partition = ThingEncounterPartition(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if not name.startswith("authority_")
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify(partition)
        return partition, witness

    def verify(self, value: ThingEncounterPartition) -> None:
        """Verify multisensory participation and causal entity continuity."""

        if not isinstance(value, ThingEncounterPartition):
            raise TypeError("THING encounter partition is not typed")
        for digest, label in (
            (value.settlement_receipt_sha256, "partition settlement"),
            (
                value.settlement_structural_fingerprint,
                "partition structural fingerprint",
            ),
            (
                value.world_observation_receipt_sha256,
                "partition world observation",
            ),
            (
                value.entity_continuity_hmac_sha256,
                "partition physical continuity",
            ),
            (value.authority_hmac_sha256, "partition HMAC"),
            (value.authority_receipt_sha256, "partition authority"),
        ):
            _sha(digest, label)
        physical_receipt = (
            value.physical_surface_observation_receipt_sha256
        )
        if (value.execution_receipt_sha256 is None) == (
            physical_receipt is None
        ):
            raise ValueError(
                "THING partition requires exactly one physical cause"
            )
        if value.execution_receipt_sha256 is not None:
            _sha(
                value.execution_receipt_sha256,
                "partition execution",
            )
        else:
            _sha(
                physical_receipt,
                "partition physical surface observation",
            )
        if value.prior_partition_receipt_sha256 is not None:
            _sha(
                value.prior_partition_receipt_sha256,
                "prior partition authority",
            )
        custody_values = (
            value.source_occurrence_id,
            value.parent_custody_receipt_sha256,
            value.thing_custody_capability_receipt_sha256,
        )
        if any(item is not None for item in custody_values):
            if any(item is None for item in custody_values):
                raise ValueError(
                    "THING partition split settled custody authority"
                )
            for digest, label in zip(
                custody_values,
                (
                    "partition source occurrence",
                    "partition parent custody",
                    "partition THING custody capability",
                ),
                strict=True,
            ):
                _sha(digest, label)
        if physical_receipt is not None and any(
            item is not None for item in custody_values
        ):
            raise ValueError(
                "physical surface partition cannot invent action custody"
            )

        if (
            isinstance(value.world_revision, bool)
            or not isinstance(value.world_revision, int)
            or value.world_revision < (0 if physical_receipt is not None else 1)
            or not value.full_field_roots
            or len(value.full_field_roots) > self._max_roots
        ):
            raise ValueError("THING encounter partition extent changed")
        for root in value.full_field_roots:
            root.verify()
        if physical_receipt is None and all(
            item is None for item in custody_values
        ):
            expected_keys = tuple(sorted(
                root.route_key
                for root in value.full_field_roots
                if root.sense == "touch"
            ))
        else:
            expected_keys = _participating_root_keys(value.full_field_roots)
        if (
            not value.entity_root_keys
            or value.entity_root_keys != expected_keys
        ):
            raise ValueError(
                "THING encounter lost symmetric sensory participation"
            )
        payload = value.payload()
        signature = hmac.new(
            self._partition_key,
            _PARTITION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(signature, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("THING encounter partition authority changed")

    def partition_from_custody(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        capability: SettledExperienceConsumerCapability,
        prior: ThingEncounterPartition | None = None,
    ) -> ThingEncounterPartition:
        if not isinstance(
            custody_authority,
            SettledExperienceCustodyAuthority,
        ):
            raise TypeError(
                "THING partition requires settled-experience custody"
            )
        if not isinstance(
            capability,
            SettledExperienceConsumerCapability,
        ):
            raise TypeError(
                "THING partition requires a typed custody capability"
            )
        if capability.consumer_id != THING_MOSAIC_CONSUMER_ID:
            raise ValueError(
                "THING partition requires its own custody capability"
            )
        view = custody_authority.open_child(capability)
        execution = view.world_execution
        if execution is None:
            raise ValueError(
                "THING partition requires applied-execution custody"
            )
        settlement = view.causal_settlement
        counter = view.occurrence_counter
        if (
            counter.source_occurrence_id != view.source_occurrence_id
            or counter.custody_count != 1
            or counter.source_transduction_lineage_count != 1
            or counter.full_field_build_lineage_count != 1
            or counter.causal_settlement_lineage_count != 1
            or capability.parent_custody_receipt_sha256
            != view.parent_custody_receipt_sha256
        ):
            raise ValueError(
                "THING partition requires one complete settled occurrence"
            )

        contact_after = self._contact_object_id(execution.after)
        contact_before = self._contact_object_id(execution.before)
        if contact_after is None:
            raise ValueError("THING partition has no contacted entity")
        continuity = self._entity_continuity(contact_after)
        if prior is None:
            if contact_before is not None:
                raise ValueError(
                    "THING genesis lacks a new reciprocal hold transition"
                )
            prior_receipt = None
        else:
            self.verify(prior)
            if (
                contact_before != contact_after
                or continuity != prior.entity_continuity_hmac_sha256
                or prior.world_revision != execution.before.revision
                or prior.world_observation_receipt_sha256
                != execution.before.authority_receipt_sha256
            ):
                raise ValueError(
                    "THING continuation left its exact physical chain"
                )
            prior_receipt = prior.authority_receipt_sha256

        roots = full_field_sensory_roots(settlement)
        if len(roots) > self._max_roots:
            raise RuntimeError("THING partition root capacity exhausted")
        participating_keys = _participating_root_keys(roots)
        provisional = ThingEncounterPartition(
            source_occurrence_id=view.source_occurrence_id,
            parent_custody_receipt_sha256=(
                view.parent_custody_receipt_sha256
            ),
            thing_custody_capability_receipt_sha256=(
                capability.authority_receipt_sha256
            ),
            settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                settlement.structural_fingerprint
            ),
            world_observation_receipt_sha256=(
                execution.after.authority_receipt_sha256
            ),
            execution_receipt_sha256=(
                execution.authority_receipt_sha256
            ),
            world_revision=execution.after.revision,
            entity_continuity_hmac_sha256=continuity,
            prior_partition_receipt_sha256=prior_receipt,
            entity_root_keys=participating_keys,
            full_field_roots=roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._partition_key,
            _PARTITION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        partition = ThingEncounterPartition(
            source_occurrence_id=provisional.source_occurrence_id,
            parent_custody_receipt_sha256=(
                provisional.parent_custody_receipt_sha256
            ),
            thing_custody_capability_receipt_sha256=(
                provisional.thing_custody_capability_receipt_sha256
            ),
            settlement_receipt_sha256=(
                provisional.settlement_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                provisional.settlement_structural_fingerprint
            ),
            world_observation_receipt_sha256=(
                provisional.world_observation_receipt_sha256
            ),
            execution_receipt_sha256=(
                provisional.execution_receipt_sha256
            ),
            world_revision=provisional.world_revision,
            entity_continuity_hmac_sha256=(
                provisional.entity_continuity_hmac_sha256
            ),
            prior_partition_receipt_sha256=prior_receipt,
            entity_root_keys=provisional.entity_root_keys,
            full_field_roots=provisional.full_field_roots,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify(partition)
        return partition


__all__ = (
    "CustodiedW1ContactThingEncounterAuthority",
    "PhysicalSurfaceContinuityWitness",
    "PHYSICAL_SURFACE_CONTINUITY_SCHEMA",
    "THING_MOSAIC_CONSUMER_ID",
)
