from __future__ import annotations

import hashlib
import json

import pytest

from dsf_ai_service.substrate.durable_sensed_consequence import (
    DurableSensedConsequenceOwner,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    L6Disposition,
    MechanismAvailability,
    MechanismKind,
    MountedMechanismSpec,
    WholeOrganismEpisodeAuthority,
    create_mounted_mechanism_manifest,
)
from tests.test_whole_organism_thing_mosaic_learning import (
    EPISODE_KEY,
    L6_RECEIPT,
    TOPOLOGY_RECEIPT,
    _authorization_settlement,
    _manifest,
)
from tests.test_whole_organism_recovery_state import _settlement


KEY = b"durable-sensed-consequence-test-key"


def _authority_and_capabilities():
    base = _manifest()
    parents = tuple(sorted(v.mechanism_id for v in base.mechanisms))
    body = MountedMechanismSpec(
        mechanism_id="state:internal-physical-chemical",
        kind=MechanismKind.STATEFUL,
        availability=MechanismAvailability.AVAILABLE,
        evidence_schema="test.sensed.body.v1",
        parent_mechanism_ids=parents,
        binds_full_field_roots=True,
    )
    recovery = MountedMechanismSpec(
        mechanism_id="state:recovery",
        kind=MechanismKind.STATEFUL,
        availability=MechanismAvailability.AVAILABLE,
        evidence_schema="test.sensed.recovery.v1",
        parent_mechanism_ids=tuple(sorted((*parents, body.mechanism_id))),
        binds_full_field_roots=True,
    )
    manifest = create_mounted_mechanism_manifest(
        authority_key=EPISODE_KEY,
        manifest_id="durable-sensed-consequence-manifest",
        topology_authority_receipt_sha256=TOPOLOGY_RECEIPT,
        mechanisms=(*base.mechanisms, body, recovery),
    )
    authority = WholeOrganismEpisodeAuthority(
        authority_key=EPISODE_KEY, manifest=manifest,
        max_episodes=8, max_state_bytes=64 * 1024 * 1024,
    )

    def contributions(draft):
        values = []
        for spec in authority.manifest.mechanisms:
            capability = authority.mechanism_capability(
                draft, spec.mechanism_id
            )
            if spec.kind is MechanismKind.RECEPTOR_FAMILY:
                values.append(authority.prepare_receptor_contribution(
                    draft, capability
                ))
            else:
                values.append(authority.prepare_quiescent_contribution(
                    draft, capability,
                    quiescent_state={"mounted": spec.mechanism_id},
                    quiescent_authority_receipt_sha256=hashlib.sha256(
                        spec.mechanism_id.encode()
                    ).hexdigest(),
                ))
        return tuple(values)

    authorization_draft = authority.begin_action_authorization(
        chain_id="one-action-chain",
        settlement=_authorization_settlement(),
        action_authority_receipt_sha256=hashlib.sha256(b"action").hexdigest(),
    )
    authorization = authority.resolve(
        authorization_draft, contributions(authorization_draft)
    )
    consequence_draft = authority.begin_consequence(
        authorization=authorization.capability,
        settlement=_settlement("sensed-consequence", negative_space=False),
        action_execution_receipt_sha256=hashlib.sha256(
            b"execution"
        ).hexdigest(),
        l6_disposition=L6Disposition.SETTLED,
        l6_authority_receipt_sha256=L6_RECEIPT,
    )
    consequence = authority.resolve(
        consequence_draft, contributions(consequence_draft)
    )
    return authority, authorization.capability, consequence.capability


def test_complete_consequence_is_durable_atomic_and_cold_restorable():
    authority, authorization, consequence = _authority_and_capabilities()
    owner = DurableSensedConsequenceOwner(
        authority_key=KEY, episode_authority=authority
    )
    genesis = owner.snapshot_encoded()
    with pytest.raises(PermissionError):
        owner.prepare(authorization)

    prepared = owner.prepare(consequence)
    assert prepared.staged[0].episode_record_json
    assert prepared.staged[0].body_contribution_json
    assert prepared.staged[0].recovery_contribution_json
    undo = owner.commit(prepared)
    encoded = owner.snapshot_encoded()
    cold = DurableSensedConsequenceOwner.restore_encoded(
        authority_key=KEY, episode_authority=authority, encoded=encoded
    )
    assert cold.snapshot_encoded() == encoded
    owner.rollback(undo)
    assert owner.snapshot_encoded() == genesis

    raw = json.loads(encoded)
    raw["body"]["records"][0]["episode_record_json"] = "{}"
    tampered = json.dumps(
        raw, separators=(",", ":"), sort_keys=True
    ).encode()
    with pytest.raises(ValueError):
        DurableSensedConsequenceOwner.restore_encoded(
            authority_key=KEY, episode_authority=authority, encoded=tampered
        )


def test_capacity_and_duplicate_fail_without_mutation():
    authority, _authorization, consequence = _authority_and_capabilities()
    owner = DurableSensedConsequenceOwner(
        authority_key=KEY, episode_authority=authority, max_records=1
    )
    owner.commit(owner.prepare(consequence))
    before = owner.snapshot_encoded()
    with pytest.raises(ValueError, match="already retained"):
        owner.prepare(consequence)
    assert owner.snapshot_encoded() == before
