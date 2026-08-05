"""Typed provider boundary for an isolated whole-organism consequence.

The present whole-organism episode owner accepts caller-provided state payloads.
This boundary therefore does not treat its capability as physical provider
truth by itself.  It binds one completed learning capability to live settled
W1 custody, the exact causal settlement, complete multisensory roots, and a
verified two-ear receptor settlement.

This owner deliberately has no persistence API.  Its status reports that
fact.  It is an isolated typed dependency, not the cold-restorable production
provider required for a production-speech claim.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field

from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    DownstreamAuthority,
    WholeOrganismEpisodeAuthority,
    WholeOrganismEpisodeCapability,
    WholeOrganismEpisodePhase,
)


PROVIDER_AUTHENTICATED_CONSEQUENCE_CONSUMER_ID = (
    "provider-authenticated-whole-organism-consequence"
)
PROVIDER_AUTHENTICATED_CONSEQUENCE_SCHEMA = (
    "guala.provider_authenticated_whole_organism_consequence.v1"
)

_DOMAIN = b"guala-provider-authenticated-whole-organism-consequence-v1\0"
_CONSTRUCTION_AUTHORITY = object()
_HEX = frozenset("0123456789abcdef")


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
        raise ValueError("provider consequence authority key changed")
    return raw


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


@dataclass(frozen=True, slots=True)
class ProviderAuthenticatedWholeOrganismConsequence:
    whole_episode_receipt_sha256: str
    settled_custody_receipt_sha256: str
    settled_capability_receipt_sha256: str
    causal_settlement_receipt_sha256: str
    binaural_receptor_settlement_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _whole_capability: WholeOrganismEpisodeCapability = field(
        repr=False,
        compare=False,
    )
    _custody_authority: SettledExperienceCustodyAuthority = field(
        repr=False,
        compare=False,
    )
    _custody_capability: SettledExperienceConsumerCapability = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "binaural_receptor_settlement_receipt_sha256": (
                self.binaural_receptor_settlement_receipt_sha256
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "schema": PROVIDER_AUTHENTICATED_CONSEQUENCE_SCHEMA,
            "settled_capability_receipt_sha256": (
                self.settled_capability_receipt_sha256
            ),
            "settled_custody_receipt_sha256": (
                self.settled_custody_receipt_sha256
            ),
            "whole_episode_receipt_sha256": (
                self.whole_episode_receipt_sha256
            ),
        }


class ProviderAuthenticatedWholeOrganismConsequenceOwner:
    """Bind a completed episode to live W1 provider custody."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        whole_organism_owner: WholeOrganismEpisodeAuthority,
    ) -> None:
        if not isinstance(
            whole_organism_owner,
            WholeOrganismEpisodeAuthority,
        ):
            raise TypeError(
                "provider consequence requires whole-organism authority"
            )
        self._key = hashlib.sha256(_DOMAIN + _key(authority_key)).digest()
        self._whole = whole_organism_owner
        self._owner_authority = object()

    def authenticate(
        self,
        *,
        whole_organism_capability: WholeOrganismEpisodeCapability,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> ProviderAuthenticatedWholeOrganismConsequence:
        if (
            not isinstance(
                custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                custody_capability,
                SettledExperienceConsumerCapability,
            )
            or custody_capability.consumer_id
            != PROVIDER_AUTHENTICATED_CONSEQUENCE_CONSUMER_ID
        ):
            raise ValueError(
                "provider consequence lacks dedicated settled custody"
            )
        episode = self._whole.require(
            whole_organism_capability,
            DownstreamAuthority.LEARNING,
        )
        if episode.phase is not WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED:
            raise ValueError(
                "provider consequence is not a completed consequence"
            )
        view = custody_authority.open_child(custody_capability)
        receptors = view.binaural_receptor_settlement
        if receptors is None:
            raise ValueError(
                "provider consequence lacks two-ear receptor settlement"
            )
        receptors.verify()
        roots = full_field_sensory_roots(view.causal_settlement)
        if (
            len({root.sense for root in roots}) < 2
            or episode.settlement_authority_receipt_sha256
            != view.causal_settlement.authority_receipt_sha256
            or episode.full_field_roots != roots
            or receptors.upstream_causal_settlement_receipt_sha256
            != view.causal_settlement.authority_receipt_sha256
        ):
            raise ValueError(
                "provider consequence lost complete live W1 evidence"
            )
        provisional = ProviderAuthenticatedWholeOrganismConsequence(
            whole_episode_receipt_sha256=(
                episode.authority_receipt_sha256
            ),
            settled_custody_receipt_sha256=(
                view.parent_custody_receipt_sha256
            ),
            settled_capability_receipt_sha256=(
                custody_capability.authority_receipt_sha256
            ),
            causal_settlement_receipt_sha256=(
                view.causal_settlement.authority_receipt_sha256
            ),
            binaural_receptor_settlement_receipt_sha256=(
                receptors.authority_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
            _whole_capability=whole_organism_capability,
            _custody_authority=custody_authority,
            _custody_capability=custody_capability,
            _owner_authority=self._owner_authority,
            _construction_authority=_CONSTRUCTION_AUTHORITY,
        )
        signature = hmac.new(
            self._key,
            _DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = ProviderAuthenticatedWholeOrganismConsequence(
            whole_episode_receipt_sha256=(
                provisional.whole_episode_receipt_sha256
            ),
            settled_custody_receipt_sha256=(
                provisional.settled_custody_receipt_sha256
            ),
            settled_capability_receipt_sha256=(
                provisional.settled_capability_receipt_sha256
            ),
            causal_settlement_receipt_sha256=(
                provisional.causal_settlement_receipt_sha256
            ),
            binaural_receptor_settlement_receipt_sha256=(
                provisional
                .binaural_receptor_settlement_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
            _whole_capability=whole_organism_capability,
            _custody_authority=custody_authority,
            _custody_capability=custody_capability,
            _owner_authority=self._owner_authority,
            _construction_authority=_CONSTRUCTION_AUTHORITY,
        )
        self.verify(result)
        return result

    def verify(
        self,
        capability: ProviderAuthenticatedWholeOrganismConsequence,
    ):
        if (
            not isinstance(
                capability,
                ProviderAuthenticatedWholeOrganismConsequence,
            )
            or capability._construction_authority
            is not _CONSTRUCTION_AUTHORITY
            or capability._owner_authority is not self._owner_authority
        ):
            raise ValueError("provider consequence capability changed")
        for value, name in (
            (
                capability.whole_episode_receipt_sha256,
                "provider whole episode",
            ),
            (
                capability.settled_custody_receipt_sha256,
                "provider settled custody",
            ),
            (
                capability.settled_capability_receipt_sha256,
                "provider settled capability",
            ),
            (
                capability.causal_settlement_receipt_sha256,
                "provider causal settlement",
            ),
            (
                capability
                .binaural_receptor_settlement_receipt_sha256,
                "provider receptor settlement",
            ),
            (capability.authority_hmac_sha256, "provider capability HMAC"),
            (
                capability.authority_receipt_sha256,
                "provider capability authority",
            ),
        ):
            _sha(value, name)
        episode = self._whole.require(
            capability._whole_capability,
            DownstreamAuthority.LEARNING,
        )
        view = capability._custody_authority.open_child(
            capability._custody_capability
        )
        receptors = view.binaural_receptor_settlement
        if (
            episode.phase
            is not WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED
            or receptors is None
        ):
            raise ValueError("provider consequence lost live evidence")
        receptors.verify()
        roots = full_field_sensory_roots(view.causal_settlement)
        expected_hmac = hmac.new(
            self._key,
            _DOMAIN + _canonical(capability.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            len({root.sense for root in roots}) < 2
            or episode.authority_receipt_sha256
            != capability.whole_episode_receipt_sha256
            or episode.settlement_authority_receipt_sha256
            != capability.causal_settlement_receipt_sha256
            or episode.full_field_roots != roots
            or view.parent_custody_receipt_sha256
            != capability.settled_custody_receipt_sha256
            or capability._custody_capability.authority_receipt_sha256
            != capability.settled_capability_receipt_sha256
            or receptors.authority_receipt_sha256
            != capability.binaural_receptor_settlement_receipt_sha256
            or receptors.upstream_causal_settlement_receipt_sha256
            != capability.causal_settlement_receipt_sha256
            or not hmac.compare_digest(
                expected_hmac,
                capability.authority_hmac_sha256,
            )
            or capability.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": capability.payload(),
            })
        ):
            raise ValueError("provider consequence authority changed")
        return episode, view, receptors

    def status(self) -> dict[str, object]:
        return {
            "cold_restorable": False,
            "production_authority": False,
            "schema": (
                "guala.provider_authenticated_whole_organism_"
                "consequence.status.v1"
            ),
            "typed_live_provider_binding": True,
        }


__all__ = (
    "PROVIDER_AUTHENTICATED_CONSEQUENCE_CONSUMER_ID",
    "ProviderAuthenticatedWholeOrganismConsequence",
    "ProviderAuthenticatedWholeOrganismConsequenceOwner",
)
