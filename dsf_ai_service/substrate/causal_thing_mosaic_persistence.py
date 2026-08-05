"""Authenticated cold restoration for the new causal THING mosaic owner."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Mapping

from dsf_ai_service.substrate.causal_thing_mosaic import (
    ENVELOPE_SCHEMA,
    MOSAIC_SCHEMA,
    PARTITION_SCHEMA,
    PROFILE_SCHEMA,
    ROOT_SCHEMA,
    STATE_SCHEMA,
    _STATE_DOMAIN,
    _canonical,
    CausalThingMosaic,
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
    FullFieldSensoryRoot,
    ThingEncounterPartition,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
)


def _profile_from_record(value: object) -> CausalThingMosaicProfile:
    expected = {
        "authority_receipt_sha256",
        "max_mosaics",
        "max_partitions_per_mosaic",
        "max_roots_per_partition",
        "max_routes",
        "max_state_bytes",
        "profile_id",
        "schema",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != PROFILE_SCHEMA
    ):
        raise ValueError("THING mosaic persisted profile changed")
    profile = CausalThingMosaicProfile(
        profile_id=value.get("profile_id"),
        max_mosaics=value.get("max_mosaics"),
        max_partitions_per_mosaic=value.get(
            "max_partitions_per_mosaic"
        ),
        max_roots_per_partition=value.get("max_roots_per_partition"),
        max_routes=value.get("max_routes"),
        max_state_bytes=value.get("max_state_bytes"),
        authority_receipt_sha256=value.get("authority_receipt_sha256"),
    )
    profile.verify()
    if profile.record() != value:
        raise ValueError("THING mosaic persisted profile is not canonical")
    return profile


def _root_from_record(value: object) -> FullFieldSensoryRoot:
    expected = {
        "full_evidence_json",
        "physical_value_sha256",
        "schema",
        "sense",
        "topology_index",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != ROOT_SCHEMA
    ):
        raise ValueError("THING mosaic persisted root changed")
    root = FullFieldSensoryRoot(
        sense=value.get("sense"),
        topology_index=value.get("topology_index"),
        physical_value_sha256=value.get("physical_value_sha256"),
        full_evidence_json=value.get("full_evidence_json"),
    )
    root.verify()
    if root.record() != value:
        raise ValueError("THING mosaic persisted root is not canonical")
    return root


def _partition_from_record(
    value: object,
    *,
    authority: CustodiedW1ContactThingEncounterAuthority,
) -> ThingEncounterPartition:
    expected = {
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "entity_continuity_hmac_sha256",
        "entity_root_keys",
        "execution_receipt_sha256",
        "full_field_roots",
        "prior_partition_receipt_sha256",
        "source_occurrence_id",
        "parent_custody_receipt_sha256",
        "thing_custody_capability_receipt_sha256",
        "schema",
        "settlement_receipt_sha256",
        "settlement_structural_fingerprint",
        "world_observation_receipt_sha256",
        "world_revision",
    }
    physical_expected = expected | {
        "physical_surface_observation_receipt_sha256"
    }
    if (
        not isinstance(value, Mapping)
        or set(value) not in {frozenset(expected), frozenset(physical_expected)}
        or value.get("schema") != PARTITION_SCHEMA
        or not isinstance(value.get("entity_root_keys"), list)
        or not isinstance(value.get("full_field_roots"), list)
    ):
        raise ValueError("THING mosaic persisted partition changed")
    entity_root_keys = tuple(
        tuple(item) for item in value["entity_root_keys"]
    )
    if any(
        len(item) != 2
        or not all(isinstance(part, str) for part in item)
        for item in entity_root_keys
    ):
        raise ValueError("THING mosaic persisted entity roots changed")
    partition = ThingEncounterPartition(
        source_occurrence_id=value.get("source_occurrence_id"),
        parent_custody_receipt_sha256=value.get(
            "parent_custody_receipt_sha256"
        ),
        thing_custody_capability_receipt_sha256=value.get(
            "thing_custody_capability_receipt_sha256"
        ),
        settlement_receipt_sha256=value.get(
            "settlement_receipt_sha256"
        ),
        settlement_structural_fingerprint=value.get(
            "settlement_structural_fingerprint"
        ),
        world_observation_receipt_sha256=value.get(
            "world_observation_receipt_sha256"
        ),
        execution_receipt_sha256=value.get("execution_receipt_sha256"),
        world_revision=value.get("world_revision"),
        entity_continuity_hmac_sha256=value.get(
            "entity_continuity_hmac_sha256"
        ),
        prior_partition_receipt_sha256=value.get(
            "prior_partition_receipt_sha256"
        ),
        entity_root_keys=entity_root_keys,
        full_field_roots=tuple(
            _root_from_record(item) for item in value["full_field_roots"]
        ),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
        authority_receipt_sha256=value.get("authority_receipt_sha256"),
        physical_surface_observation_receipt_sha256=value.get(
            "physical_surface_observation_receipt_sha256"
        ),
    )
    custody_values = (
        partition.source_occurrence_id,
        partition.parent_custody_receipt_sha256,
        partition.thing_custody_capability_receipt_sha256,
    )
    if (
        partition.physical_surface_observation_receipt_sha256 is None
        and any(value is None for value in custody_values)
    ):
        raise ValueError(
            "THING mosaic legacy partition lacks settled custody; "
            "authenticated migration is required"
        )
    if (
        partition.physical_surface_observation_receipt_sha256 is not None
        and any(value is not None for value in custody_values)
    ):
        raise ValueError(
            "THING mosaic physical surface partition invented custody"
        )
    authority.verify(partition)
    if partition.record() != value:
        raise ValueError("THING mosaic persisted partition is not canonical")
    return partition


def _mosaic_from_record(
    value: object,
    *,
    owner: CausalThingMosaicOwner,
    partition_authority: CustodiedW1ContactThingEncounterAuthority,
) -> CausalThingMosaic:
    expected = {
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "partitions",
        "schema",
        "thing_id",
        "version",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != MOSAIC_SCHEMA
        or not isinstance(value.get("partitions"), list)
    ):
        raise ValueError("THING mosaic persisted record changed")
    partitions = tuple(
        _partition_from_record(
            item,
            authority=partition_authority,
        )
        for item in value["partitions"]
    )
    if not partitions:
        raise ValueError("THING mosaic persisted without an encounter")
    if (
        partitions[0].prior_partition_receipt_sha256 is not None
        or any(
            current.prior_partition_receipt_sha256
            != prior.authority_receipt_sha256
            for prior, current in zip(partitions, partitions[1:])
        )
        or any(
            current.entity_continuity_hmac_sha256
            != partitions[0].entity_continuity_hmac_sha256
            for current in partitions[1:]
        )
    ):
        raise ValueError("THING mosaic persisted continuity chain changed")
    thing_id = value.get("thing_id")
    expected_thing_id = hmac.new(
        owner._mosaic_key,
        b"guala-causal-thing-id-v1\0"
        + bytes.fromhex(partitions[0].authority_receipt_sha256),
        hashlib.sha256,
    ).hexdigest()
    if thing_id != expected_thing_id:
        raise ValueError("THING mosaic persisted stable identity changed")
    if value.get("version") != len(partitions) - 1:
        raise ValueError("THING mosaic persisted version changed")
    expected_mosaic = owner._seal(
        thing_id=thing_id,
        version=value["version"],
        partitions=partitions,
    )
    if expected_mosaic.record() != value:
        raise ValueError("THING mosaic persisted authority changed")
    return expected_mosaic


def restore_causal_thing_mosaic_owner(
    *,
    authority_key: bytes | str,
    partition_authority: CustodiedW1ContactThingEncounterAuthority,
    encoded: bytes,
) -> CausalThingMosaicOwner:
    """Restore only after every profile, root, partition, chain, and HMAC verifies."""

    if not isinstance(
        partition_authority,
        CustodiedW1ContactThingEncounterAuthority,
    ):
        raise TypeError(
            "THING mosaic restore requires custody-native partition "
            "authority"
        )
    if not isinstance(encoded, bytes):
        raise TypeError("THING mosaic state must be immutable bytes")
    try:
        envelope = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("THING mosaic state is unreadable") from error
    if (
        not isinstance(envelope, Mapping)
        or set(envelope) != {"body", "schema", "state_hmac_sha256"}
        or envelope.get("schema") != ENVELOPE_SCHEMA
        or _canonical(envelope) != encoded
        or not isinstance(envelope.get("body"), Mapping)
    ):
        raise ValueError("THING mosaic state envelope changed")
    body = envelope["body"]
    if (
        set(body) != {"mosaics", "profile", "schema"}
        or body.get("schema") != STATE_SCHEMA
        or not isinstance(body.get("mosaics"), list)
    ):
        raise ValueError("THING mosaic state body changed")
    profile = _profile_from_record(body.get("profile"))
    if len(encoded) > profile.max_state_bytes:
        raise ValueError("THING mosaic state exceeds its byte capacity")
    owner = CausalThingMosaicOwner(
        authority_key=authority_key,
        profile=profile,
        partition_authority=partition_authority,
    )
    expected_hmac = hmac.new(
        owner._state_key,
        _STATE_DOMAIN + _canonical(body),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(
        expected_hmac,
        str(envelope["state_hmac_sha256"]),
    ):
        raise ValueError("THING mosaic state authority changed")
    restored: dict[str, CausalThingMosaic] = {}
    partition_receipts: set[str] = set()
    continuity_receipts: set[str] = set()
    for raw_mosaic in body["mosaics"]:
        mosaic = _mosaic_from_record(
            raw_mosaic,
            owner=owner,
            partition_authority=partition_authority,
        )
        if mosaic.thing_id in restored:
            raise ValueError("THING mosaic state repeats a stable identity")
        receipts = {
            value.authority_receipt_sha256 for value in mosaic.partitions
        }
        if partition_receipts.intersection(receipts):
            raise ValueError("THING mosaic state reuses an encounter partition")
        continuity = mosaic.partitions[0].entity_continuity_hmac_sha256
        if continuity in continuity_receipts:
            raise ValueError("THING mosaic state duplicates physical continuity")
        partition_receipts.update(receipts)
        continuity_receipts.add(continuity)
        restored[mosaic.thing_id] = mosaic
    if len(restored) > profile.max_mosaics:
        raise ValueError("THING mosaic state exceeds mosaic capacity")
    owner._routes(restored)
    owner._mosaics = restored
    if owner.snapshot_encoded() != encoded:
        raise ValueError("THING mosaic cold restoration changed state bytes")
    return owner


__all__ = ("restore_causal_thing_mosaic_owner",)
