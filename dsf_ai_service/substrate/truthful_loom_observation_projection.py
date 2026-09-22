"""Fail-closed projection boundary for Loom observation surfaces.

This component projects typed runtime evidence; it does not infer runtime
state from planning documents, labels, transcripts, or compatibility status.

No speech-to-text or model output is admitted. Tutor text may appear only as a
designation. Discrete browser channels remain hardware-unproven. An
architecture contract is inactive unless a live runtime authority receipt is
supplied with ``wired=True``. Auditory structure may be projected only from a
verified recurrent-q result, and that result establishes no word, speaker,
kind, lexical meaning, or L6 certainty.

The projection is bounded and HMAC receipted.  It evaluates no DSF field and
does not flatten one; verified causal occurrences retain their complete field
authority outside this view.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.substrate.auditory_live_motif import (
    AuditoryLiveMotifCompactReceipt,
    AuditoryLiveMotifResult,
)
from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    AcceptedBrowserBinauralPCMChunk,
)


TRUTHFUL_LOOM_PROJECTION_SCHEMA = (
    "guala.truthful_loom_observation_projection.v2"
)
TRUTHFUL_LOOM_PROJECTION_DOMAIN = (
    b"guala-truthful-loom-observation-projection-v2\0"
)
MAX_BOUNDARY_OBSERVATIONS = 16
MAX_DESIGNATIONS = 16
MAX_RUNTIME_COMPONENTS = 64
MAX_DISPLAY_TEXT_BYTES = 4_096
CAUSAL_THING_LOOM_SCHEMA = (
    "guala.truthful_loom.causal_thing_observation.v1"
)
CAUSAL_THING_LOOM_DOMAIN = (
    b"guala-truthful-loom-causal-thing-observation-v1\0"
)
MAX_CAUSAL_THING_SUMMARIES = 64
SIGHT_ARTICULATORY_LOOM_SCHEMA = (
    "guala.truthful_loom.sight_evoked_articulatory_observation.v1"
)
SIGHT_ARTICULATORY_LOOM_DOMAIN = (
    b"guala-truthful-loom-sight-evoked-articulatory-observation-v1\0"
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


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError("truthful Loom authority key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError(
            "truthful Loom authority key is outside its exact boundary"
        )
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _bounded_text(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > MAX_DISPLAY_TEXT_BYTES
    ):
        raise ValueError(f"{name} is outside its display boundary")
    return value


def _authenticated_state_hmac(
    encoded: bytes,
    *,
    schema: str,
    hmac_field: str,
    name: str,
) -> str:
    try:
        decoded = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{name} state is unreadable") from error
    if (
        not isinstance(decoded, Mapping)
        or decoded.get("schema") != schema
    ):
        raise ValueError(f"{name} state schema changed")
    return _sha256(decoded.get(hmac_field), f"{name} state HMAC")


def _authenticated_sensory_expansion_state_hmac(
    encoded: bytes,
) -> str:
    try:
        decoded = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "causal THING sensory expansion state is unreadable"
        ) from error
    if (
        not isinstance(decoded, Mapping)
        or set(decoded) != {"body", "schema", "state_hmac_sha256"}
        or decoded.get("schema")
        != "guala.causal_thing.sensory_expansion.state_hmac.v2"
        or _canonical(decoded) != encoded
    ):
        raise ValueError(
            "causal THING sensory expansion state schema changed"
        )
    body = decoded.get("body")
    if (
        not isinstance(body, Mapping)
        or set(body) != {"expansions", "limits", "schema"}
        or body.get("schema")
        != "guala.causal_thing.sensory_expansion.state.v2"
        or not isinstance(body.get("limits"), Mapping)
        or set(body["limits"])
        != {
            "max_expansions",
            "max_roots_per_expansion",
            "max_state_bytes",
        }
        or not isinstance(body.get("expansions"), list)
    ):
        raise ValueError(
            "causal THING sensory expansion v2 body changed"
        )
    required = {
        "admission_basis",
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "custody_capability_receipt_sha256",
        "full_field_roots",
        "grounding_contact_capability_receipt_sha256",
        "grounding_contact_custody_receipt_sha256",
        "grounding_contact_occurrence_id",
        "grounding_contact_settlement_receipt_sha256",
        "grounding_partition_receipt_sha256",
        "parent_custody_receipt_sha256",
        "prior_expansion_receipt_sha256s",
        "schema",
        "sequence",
        "settlement_receipt_sha256",
        "settlement_structural_fingerprint",
        "source_occurrence_id",
        "thing_id",
        "world_before_receipt_sha256",
        "world_execution_receipt_sha256",
        "world_observation_receipt_sha256",
        "world_revision",
    }
    for record in body["expansions"]:
        if (
            not isinstance(record, Mapping)
            or set(record) != required
            or record.get("schema")
            != "guala.causal_thing.sensory_expansion.v2"
        ):
            raise ValueError(
                "causal THING sensory expansion v2 record changed"
            )
        direct = (
            record.get("admission_basis")
            == "settled_known_sight_continuation"
        )
        world_values = (
            record.get("world_revision"),
            record.get("world_observation_receipt_sha256"),
            record.get("world_before_receipt_sha256"),
            record.get("world_execution_receipt_sha256"),
        )
        if direct != all(value is not None for value in world_values):
            raise ValueError(
                "causal THING sensory expansion v2 provenance changed"
            )
    return _sha256(
        decoded.get("state_hmac_sha256"),
        "causal THING sensory expansion state HMAC",
    )


def _causal_thing_projection_payload(
    *,
    thing_owner: CausalThingMosaicOwner,
    reciprocal_owner: CausalThingReciprocalMosaicOwner,
    sensory_expansion_owner: CausalThingSensoryExpansionOwner,
    autonomous_play_owner: AutonomousCausalPlayOwner,
    latest_settlement: CausalExperienceSettlement | None,
    latest_play: Mapping[str, object] | None,
) -> dict[str, object]:
    raise RuntimeError(
        "legacy Python THING/mosaic observation is permanently retired"
    )
    if not isinstance(thing_owner, CausalThingMosaicOwner):
        raise TypeError("Loom THING projection requires the typed THING owner")
    if not isinstance(
        reciprocal_owner,
        CausalThingReciprocalMosaicOwner,
    ):
        raise TypeError(
            "Loom THING projection requires the typed reciprocal owner"
        )
    if not isinstance(
        sensory_expansion_owner,
        CausalThingSensoryExpansionOwner,
    ):
        raise TypeError(
            "Loom THING projection requires the typed sensory expansion owner"
        )
    if not isinstance(autonomous_play_owner, AutonomousCausalPlayOwner):
        raise TypeError(
            "Loom THING projection requires the typed autonomous play owner"
        )

    initial_mosaic_state = thing_owner.snapshot_encoded()
    initial_expansion_state = sensory_expansion_owner.snapshot_encoded()
    initial_play_state = autonomous_play_owner.encoded_snapshot()
    mosaics = thing_owner.mosaics
    classes = reciprocal_owner.classes()
    expansions = sensory_expansion_owner.expansions
    if (
        len(mosaics) > MAX_CAUSAL_THING_SUMMARIES
        or len(classes) != len(mosaics)
    ):
        raise RuntimeError("Loom THING projection capacity changed")
    classes_by_id = {value.thing_id: value for value in classes}
    summaries = []
    for mosaic in mosaics:
        thing_class = classes_by_id.get(mosaic.thing_id)
        if (
            thing_class is None
            or thing_class.thing_mosaic_receipt_sha256
            != mosaic.authority_receipt_sha256
        ):
            raise ValueError("reciprocal THING class lost mosaic authority")
        expansion_receipts = sensory_expansion_owner.receipts_for_thing(
            mosaic.thing_id
        )
        summaries.append({
            "full_field_root_count": len(
                thing_class.full_field_roots
            ),
            "mosaic_authority_receipt_sha256": (
                mosaic.authority_receipt_sha256
            ),
            "partition_authority_receipt_sha256s": [
                value.authority_receipt_sha256
                for value in mosaic.partitions
            ],
            "reciprocal_class_authority_receipt_sha256": (
                thing_class.authority_receipt_sha256
            ),
            "sensory_expansion_authority_receipt_sha256s": list(
                expansion_receipts
            ),
            "thing_id": mosaic.thing_id,
            "version": mosaic.version,
        })

    if latest_settlement is None:
        live_resolution = {
            "authority_receipt_sha256": None,
            "candidate_thing_ids": [],
            "cue_senses": [],
            "selected_thing_id": None,
            "status": "not_observed",
        }
    else:
        if not isinstance(latest_settlement, CausalExperienceSettlement):
            raise TypeError(
                "Loom THING live resolution requires a typed settlement"
            )
        latest_settlement.verify()
        observed_senses = {
            value.sense
            for value in latest_settlement.interpretations
            if value.state == "observed"
        }
        cue_senses = tuple(
            value.value
            for value in SENSE_ORDER
            if value.value in observed_senses
        )
        if not cue_senses:
            live_resolution = {
                "authority_receipt_sha256": None,
                "candidate_thing_ids": [],
                "cue_senses": [],
                "selected_thing_id": None,
                "status": "unresolved",
            }
        else:
            evocation = reciprocal_owner.evoke(
                latest_settlement,
                cue_senses=cue_senses,
            )
            reciprocal_owner.verify_evocation(evocation)
            live_resolution = {
                "authority_receipt_sha256": (
                    evocation.authority_receipt_sha256
                ),
                "candidate_thing_ids": list(evocation.thing_ids),
                "cue_senses": list(evocation.cue_senses),
                "selected_thing_id": (
                    evocation.thing_ids[0]
                    if evocation.state == "unique"
                    else None
                ),
                "status": evocation.state,
            }

    play_state = json.loads(initial_play_state)
    play_hmac = _sha256(
        play_state.get("authority_hmac_sha256"),
        "autonomous play state HMAC",
    )
    play_growth = {
        "autonomous_play_state_hmac_sha256": play_hmac,
        "latest_play_record_sha256": None,
        "outcome_settlement_receipt_sha256": None,
        "partition_authority_receipt_sha256": None,
        "selected_thing_id": None,
        "status": "not_observed",
    }
    if latest_play is not None:
        if not isinstance(latest_play, Mapping):
            raise TypeError("Loom latest play observation must be a mapping")
        canonical_play = _canonical(latest_play)
        steps = latest_play.get("steps")
        if (
            latest_play.get("trigger") != "autonomous_play"
            or latest_play.get("dispatch_status") != "completed"
            or not isinstance(steps, list)
            or not steps
            or not isinstance(steps[-1], Mapping)
        ):
            play_growth["status"] = "not_completed"
            play_growth["latest_play_record_sha256"] = hashlib.sha256(
                canonical_play
            ).hexdigest()
        else:
            outcome_receipt = _sha256(
                steps[-1].get(
                    "outcome_settlement_receipt_sha256"
                ),
                "autonomous play outcome settlement",
            )
            matches = tuple(
                (mosaic.thing_id, partition.authority_receipt_sha256)
                for mosaic in mosaics
                for partition in mosaic.partitions
                if partition.settlement_receipt_sha256 == outcome_receipt
            )
            play_growth.update({
                "latest_play_record_sha256": hashlib.sha256(
                    canonical_play
                ).hexdigest(),
                "outcome_settlement_receipt_sha256": outcome_receipt,
                "status": (
                    "unique"
                    if len(matches) == 1
                    else "ambiguous"
                    if matches
                    else "unresolved"
                ),
            })
            if len(matches) == 1:
                play_growth.update({
                    "partition_authority_receipt_sha256": matches[0][1],
                    "selected_thing_id": matches[0][0],
                })

    if (
        thing_owner.snapshot_encoded() != initial_mosaic_state
        or sensory_expansion_owner.snapshot_encoded()
        != initial_expansion_state
        or autonomous_play_owner.encoded_snapshot()
        != initial_play_state
    ):
        raise RuntimeError(
            "causal THING owners changed during Loom observation"
        )
    mosaic_hmac = _authenticated_state_hmac(
        initial_mosaic_state,
        schema="guala.causal_thing_mosaic.state_hmac.v1",
        hmac_field="state_hmac_sha256",
        name="causal THING mosaic",
    )
    expansion_hmac = _authenticated_sensory_expansion_state_hmac(
        initial_expansion_state
    )
    return {
        "authorities": {
            "cognition": False,
            "decision": False,
            "meaning": False,
        },
        "durable_state": {
            "autonomous_play_state_hmac_sha256": play_hmac,
            "causal_thing_mosaic_state_hmac_sha256": mosaic_hmac,
            "mosaic_count": len(mosaics),
            "partition_count": sum(
                len(value.partitions) for value in mosaics
            ),
            "sensory_expansion_count": len(expansions),
            "sensory_expansion_state_hmac_sha256": expansion_hmac,
            "things": summaries,
        },
        "full_field_preserved_upstream": True,
        "latest_autonomous_play_partition_growth": play_growth,
        "live_resolution": live_resolution,
        "reduced_approximation": False,
        "schema": CAUSAL_THING_LOOM_SCHEMA,
        "status": "observed",
    }


def project_causal_thing_loom_observation(
    *,
    authority_key: bytes | str,
    thing_owner: CausalThingMosaicOwner,
    reciprocal_owner: CausalThingReciprocalMosaicOwner,
    sensory_expansion_owner: CausalThingSensoryExpansionOwner,
    autonomous_play_owner: AutonomousCausalPlayOwner,
    latest_settlement: CausalExperienceSettlement | None = None,
    latest_play: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Project authenticated owner state without interpreting cognition."""

    raise RuntimeError(
        "legacy Python THING/mosaic observation is permanently retired"
    )

    key = _key(authority_key)
    payload = _causal_thing_projection_payload(
        thing_owner=thing_owner,
        reciprocal_owner=reciprocal_owner,
        sensory_expansion_owner=sensory_expansion_owner,
        autonomous_play_owner=autonomous_play_owner,
        latest_settlement=latest_settlement,
        latest_play=latest_play,
    )
    signature = hmac.new(
        key,
        CAUSAL_THING_LOOM_DOMAIN + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    return {
        **payload,
        "authority_hmac_sha256": signature,
        "authority_receipt_sha256": _digest({
            "authority_hmac_sha256": signature,
            "payload": payload,
        }),
    }


def verify_causal_thing_loom_observation(
    value: Mapping[str, object],
    *,
    authority_key: bytes | str,
) -> None:
    """Verify the projection seal and its non-authoritative view contract."""

    if not isinstance(value, Mapping):
        raise TypeError("causal THING Loom projection must be a mapping")
    expected = {
        "authorities",
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "durable_state",
        "full_field_preserved_upstream",
        "latest_autonomous_play_partition_growth",
        "live_resolution",
        "reduced_approximation",
        "schema",
        "status",
    }
    if (
        set(value) != expected
        or value.get("schema") != CAUSAL_THING_LOOM_SCHEMA
        or value.get("status") != "observed"
        or value.get("authorities") != {
            "cognition": False,
            "decision": False,
            "meaning": False,
        }
        or value.get("full_field_preserved_upstream") is not True
        or value.get("reduced_approximation") is not False
    ):
        raise ValueError("causal THING Loom projection contract changed")
    payload = {
        key: value[key]
        for key in expected
        if key not in {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
        }
    }
    signature = hmac.new(
        _key(authority_key),
        CAUSAL_THING_LOOM_DOMAIN + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    if (
        not hmac.compare_digest(
            signature,
            value["authority_hmac_sha256"],
        )
        or value["authority_receipt_sha256"] != _digest({
            "authority_hmac_sha256": signature,
            "payload": payload,
        })
    ):
        raise ValueError("causal THING Loom projection authority changed")


def _sight_articulatory_projection_payload(
    response: SightEvokedArticulatoryResponse | None,
    *,
    source_authority_key: bytes | str,
) -> dict[str, object]:
    authorities = {
        "cognition": False,
        "decision": False,
        "label": False,
        "meaning": False,
        "word": False,
    }
    if response is None:
        return {
            "authorities": authorities,
            "emission_observed": False,
            "fresh_articulatory_synthesis_observed": False,
            "receipts": {
                "articulatory_custody_receipt_sha256": None,
                "binding_receipt_sha256": None,
                "cue_settlement_receipt_sha256": None,
                "emission_receipt_sha256": None,
                "evocation_receipt_sha256": None,
                "self_acoustic_receipt_sha256": None,
                "source_response_authority_receipt_sha256": None,
                "synthesis_receipt_sha256": None,
                "world_after_receipt_sha256": None,
                "world_before_receipt_sha256": None,
            },
            "response_state": None,
            "schema": SIGHT_ARTICULATORY_LOOM_SCHEMA,
            "status": "not_observed",
            "thing_ids": [],
        }
    verify_sight_evoked_articulatory_response(
        response,
        authority_key=source_authority_key,
    )
    executed = response.state == "executed"
    return {
        "authorities": authorities,
        "emission_observed": executed,
        "fresh_articulatory_synthesis_observed": executed,
        "receipts": {
            "articulatory_custody_receipt_sha256": (
                response.articulatory_custody_receipt_sha256
            ),
            "binding_receipt_sha256": response.binding_receipt_sha256,
            "cue_settlement_receipt_sha256": (
                response.cue_settlement_receipt_sha256
            ),
            "emission_receipt_sha256": (
                response.emission_receipt_sha256
            ),
            "evocation_receipt_sha256": (
                response.evocation_receipt_sha256
            ),
            "self_acoustic_receipt_sha256": (
                response.self_acoustic_receipt_sha256
            ),
            "source_response_authority_receipt_sha256": (
                response.authority_receipt_sha256
            ),
            "synthesis_receipt_sha256": (
                response.synthesis_receipt_sha256
            ),
            "world_after_receipt_sha256": (
                response.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                response.world_before_receipt_sha256
            ),
        },
        "response_state": response.state,
        "schema": SIGHT_ARTICULATORY_LOOM_SCHEMA,
        "status": "observed",
        "thing_ids": list(response.thing_ids),
    }


def project_sight_evoked_articulatory_loom_observation(
    *,
    authority_key: bytes | str,
    source_authority_key: bytes | str,
    response: SightEvokedArticulatoryResponse | None,
) -> dict[str, object]:
    """Project only a verified physical sight-to-articulation occurrence."""

    raise RuntimeError(
        "legacy sight-evoked articulation is permanently retired; "
        "native exact-field observation remains authoritative"
    )

    payload = _sight_articulatory_projection_payload(
        response,
        source_authority_key=source_authority_key,
    )
    signature = hmac.new(
        _key(authority_key),
        SIGHT_ARTICULATORY_LOOM_DOMAIN + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    return {
        **payload,
        "authority_hmac_sha256": signature,
        "authority_receipt_sha256": _digest({
            "authority_hmac_sha256": signature,
            "payload": payload,
        }),
    }


def verify_sight_evoked_articulatory_loom_observation(
    value: Mapping[str, object],
    *,
    authority_key: bytes | str,
) -> None:
    raise RuntimeError(
        "legacy sight-evoked articulation is permanently retired and cannot "
        "be restored"
    )
    if not isinstance(value, Mapping):
        raise TypeError(
            "sight articulatory Loom projection must be a mapping"
        )
    expected = {
        "authorities",
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "emission_observed",
        "fresh_articulatory_synthesis_observed",
        "receipts",
        "response_state",
        "schema",
        "status",
        "thing_ids",
    }
    authorities = {
        "cognition": False,
        "decision": False,
        "label": False,
        "meaning": False,
        "word": False,
    }
    receipts = value.get("receipts")
    act_fields = (
        "articulatory_custody_receipt_sha256",
        "binding_receipt_sha256",
        "emission_receipt_sha256",
        "self_acoustic_receipt_sha256",
        "synthesis_receipt_sha256",
    )
    if (
        set(value) != expected
        or value.get("schema") != SIGHT_ARTICULATORY_LOOM_SCHEMA
        or value.get("authorities") != authorities
        or value.get("status") not in {"observed", "not_observed"}
        or not isinstance(receipts, Mapping)
        or set(receipts) != {
            "articulatory_custody_receipt_sha256",
            "binding_receipt_sha256",
            "cue_settlement_receipt_sha256",
            "emission_receipt_sha256",
            "evocation_receipt_sha256",
            "self_acoustic_receipt_sha256",
            "source_response_authority_receipt_sha256",
            "synthesis_receipt_sha256",
            "world_after_receipt_sha256",
            "world_before_receipt_sha256",
        }
        or not isinstance(value.get("thing_ids"), list)
    ):
        raise ValueError(
            "sight articulatory Loom projection contract changed"
        )
    observed = value["status"] == "observed"
    executed = value.get("response_state") == "executed"
    occurrence_fields = (
        "cue_settlement_receipt_sha256",
        "evocation_receipt_sha256",
        "source_response_authority_receipt_sha256",
        "world_after_receipt_sha256",
        "world_before_receipt_sha256",
    )
    if (
        value.get("emission_observed") is not executed
        or value.get("fresh_articulatory_synthesis_observed")
        is not executed
        or (not observed and (
            value.get("response_state") is not None
            or value.get("thing_ids")
            or any(item is not None for item in receipts.values())
        ))
        or (
            observed
            and value.get("response_state")
            not in {"executed", "unresolved", "ambiguous", "unbound"}
        )
        or (
            observed and any(
                receipts[name] is None
                for name in occurrence_fields
            )
        )
        or (
            executed and (
                any(receipts[name] is None for name in act_fields)
                or len(value["thing_ids"]) != 1
                or receipts["world_before_receipt_sha256"]
                == receipts["world_after_receipt_sha256"]
            )
        )
        or (
            observed and not executed and (
                any(receipts[name] is not None for name in act_fields)
                or receipts["world_before_receipt_sha256"]
                != receipts["world_after_receipt_sha256"]
            )
        )
    ):
        raise ValueError(
            "sight articulatory Loom action claim changed"
        )
    for thing_id in value["thing_ids"]:
        _sha256(thing_id, "sight articulatory Loom THING")
    for name, receipt in receipts.items():
        if receipt is not None:
            _sha256(receipt, f"sight articulatory Loom {name}")
    payload = {
        key: value[key]
        for key in expected
        if key not in {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
        }
    }
    signature = hmac.new(
        _key(authority_key),
        SIGHT_ARTICULATORY_LOOM_DOMAIN + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    if (
        not hmac.compare_digest(
            signature,
            value["authority_hmac_sha256"],
        )
        or value["authority_receipt_sha256"] != _digest({
            "authority_hmac_sha256": signature,
            "payload": payload,
        })
    ):
        raise ValueError(
            "sight articulatory Loom projection authority changed"
        )


@dataclass(frozen=True, slots=True)
class LoomRuntimeComponentEvidence:
    component_id: str
    contract_schema: str
    wired: bool
    runtime_authority_receipt_sha256: str | None

    def verify(self) -> None:
        _bounded_text(self.component_id, "Loom runtime component id")
        _bounded_text(self.contract_schema, "Loom runtime contract schema")
        if not isinstance(self.wired, bool):
            raise TypeError("Loom runtime wired state must be boolean")
        if self.wired:
            if self.runtime_authority_receipt_sha256 is None:
                raise ValueError(
                    "wired Loom runtime component has no live authority"
                )
            _sha256(
                self.runtime_authority_receipt_sha256,
                "Loom runtime authority",
            )
        elif self.runtime_authority_receipt_sha256 is not None:
            raise ValueError(
                "inactive Loom contract cannot carry live authority"
            )

    def projection_record(self) -> dict[str, object]:
        self.verify()
        return {
            "cognition_authority": False,
            "component_id": self.component_id,
            "contract_schema": self.contract_schema,
            "runtime_authority_receipt_sha256": (
                self.runtime_authority_receipt_sha256
            ),
            "status": "active_runtime" if self.wired else "inactive_contract",
            "wired": self.wired,
        }


@dataclass(frozen=True, slots=True)
class TruthfulLoomObservationProjection:
    boundary_observations: tuple[Mapping[str, object], ...]
    designations: tuple[Mapping[str, object], ...]
    binaural_transport: Mapping[str, object]
    runtime_components: tuple[Mapping[str, object], ...]
    cognition: Mapping[str, object]
    meaning: Mapping[str, object]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "binaural_transport": dict(self.binaural_transport),
            "boundary_observations": [
                dict(value) for value in self.boundary_observations
            ],
            "cognition": dict(self.cognition),
            "designations": [
                dict(value) for value in self.designations
            ],
            "meaning": dict(self.meaning),
            "runtime_components": [
                dict(value) for value in self.runtime_components
            ],
            "schema": TRUTHFUL_LOOM_PROJECTION_SCHEMA,
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        if (
            len(self.boundary_observations)
            > MAX_BOUNDARY_OBSERVATIONS
            or len(self.designations) > MAX_DESIGNATIONS
            or len(self.runtime_components) > MAX_RUNTIME_COMPONENTS
        ):
            raise ValueError(
                "truthful Loom projection exceeded its bounded view"
            )
        for value in self.boundary_observations:
            if (
                set(value) != {
                    "causal_authority",
                    "cognition_authority",
                    "display_only",
                    "display_text",
                    "meaning_authority",
                    "observation_id",
                    "status",
                }
                or value["causal_authority"] is not False
                or value["cognition_authority"] is not False
                or value["display_only"] is not True
                or value["meaning_authority"] is not False
            ):
                raise ValueError(
                    "boundary observation crossed into cognition"
                )
        for value in self.designations:
            if (
                set(value) != {
                    "cognition_authority",
                    "designation_only",
                    "display_text",
                    "meaning_authority",
                }
                or value["cognition_authority"] is not False
                or value["designation_only"] is not True
                or value["meaning_authority"] is not False
            ):
                raise ValueError(
                    "tutor designation crossed into meaning"
                )
        if (
            set(self.binaural_transport) != {
                "cognition_admitted",
                "hardware_authority_proven",
                "status",
                "transport_receipt_sha256",
            }
            or self.binaural_transport["cognition_admitted"] is not False
        ):
            raise ValueError(
                "binaural transport crossed into cognition"
            )
        for value in self.runtime_components:
            active = value.get("status") == "active_runtime"
            if (
                value.get("cognition_authority") is not False
                or active != bool(value.get("wired"))
                or active
                != (
                    value.get("runtime_authority_receipt_sha256")
                    is not None
                )
            ):
                raise ValueError(
                    "inactive architecture appeared active"
                )
        expected_cognition_keys = {
            "activation_spans",
            "firing_motif_neuron_ids",
            "learning_state",
            "meaning_authority",
            "presemantic_authority",
            "q_result_authority_receipt_sha256",
            "source_experience_receipt_sha256",
            "source_receptor_event_receipt_sha256",
            "status",
            "transcript_authority",
        }
        if (
            set(self.cognition) != expected_cognition_keys
            or self.cognition["meaning_authority"] is not False
            or self.cognition["transcript_authority"] is not False
        ):
            raise ValueError(
                "observation projection fabricated cognition meaning"
            )
        if self.cognition["status"] == "not_observed":
            if (
                self.cognition["presemantic_authority"] is not False
                or self.cognition["activation_spans"] != []
                or self.cognition["firing_motif_neuron_ids"] != []
                or any(
                    self.cognition[key] is not None
                    for key in (
                        "learning_state",
                        "q_result_authority_receipt_sha256",
                        "source_experience_receipt_sha256",
                        "source_receptor_event_receipt_sha256",
                    )
                )
            ):
                raise ValueError("absent cognition carried authority")
        else:
            if (
                self.cognition["status"] not in {
                    "recurrent_q_pending_window",
                    "recurrent_q_observed",
                }
                or self.cognition["presemantic_authority"] is not True
                or not isinstance(
                    self.cognition["activation_spans"], list
                )
                or not isinstance(
                    self.cognition["firing_motif_neuron_ids"], list
                )
            ):
                raise ValueError(
                    "Loom recurrent-q state is not authoritative"
                )
            for name in (
                "q_result_authority_receipt_sha256",
                "source_experience_receipt_sha256",
                "source_receptor_event_receipt_sha256",
            ):
                _sha256(self.cognition[name], f"Loom recurrent-q {name}")
        if self.meaning != {
            "authority": False,
            "status": "not_established_by_observation_projection",
            "text": None,
        }:
            raise ValueError(
                "observation projection fabricated lexical meaning"
            )
        payload = self.payload()
        expected_hmac = hmac.new(
            key,
            TRUTHFUL_LOOM_PROJECTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError(
                "truthful Loom projection authority changed"
            )

    def as_record(self, authority_key: bytes | str) -> dict[str, object]:
        self.verify(authority_key)
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class TruthfulLoomObservationProjector:
    """Construct one bounded projection from typed active evidence."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
    ) -> None:
        self._key = _key(authority_key)

    def project(
        self,
        *,
        tutor_designations: tuple[str, ...] = (),
        browser_binaural_chunk: (
            AcceptedBrowserBinauralPCMChunk | None
        ) = None,
        runtime_components: tuple[
            LoomRuntimeComponentEvidence, ...
        ] = (),
        recurrent_q_result: (
            AuditoryLiveMotifResult
            | AuditoryLiveMotifCompactReceipt
            | None
        ) = None,
    ) -> TruthfulLoomObservationProjection:
        if (
            not isinstance(tutor_designations, tuple)
            or len(tutor_designations) > MAX_DESIGNATIONS
            or not isinstance(runtime_components, tuple)
            or len(runtime_components) > MAX_RUNTIME_COMPONENTS
        ):
            raise ValueError(
                "truthful Loom projection input exceeded its boundary"
            )
        observations = ()
        designations = tuple({
            "cognition_authority": False,
            "designation_only": True,
            "display_text": _bounded_text(
                value,
                "Loom tutor designation",
            ),
            "meaning_authority": False,
        } for value in tutor_designations)
        if browser_binaural_chunk is None:
            binaural = {
                "cognition_admitted": False,
                "hardware_authority_proven": False,
                "status": "not_observed",
                "transport_receipt_sha256": None,
            }
        else:
            if not isinstance(
                browser_binaural_chunk,
                AcceptedBrowserBinauralPCMChunk,
            ):
                raise TypeError(
                    "Loom binaural view requires typed transport evidence"
                )
            browser_binaural_chunk.verify()
            binaural = {
                "cognition_admitted": False,
                "hardware_authority_proven": False,
                "status": "discrete_transport_hardware_unproven",
                "transport_receipt_sha256": (
                    browser_binaural_chunk.receipt.receipt_sha256
                ),
            }
        component_records = []
        for value in runtime_components:
            if not isinstance(value, LoomRuntimeComponentEvidence):
                raise TypeError(
                    "Loom runtime projection requires typed evidence"
                )
            component_records.append(value.projection_record())
        components = tuple(component_records)
        cognition = {
            "activation_spans": [],
            "firing_motif_neuron_ids": [],
            "learning_state": None,
            "meaning_authority": False,
            "presemantic_authority": False,
            "q_result_authority_receipt_sha256": None,
            "source_experience_receipt_sha256": None,
            "source_receptor_event_receipt_sha256": None,
            "status": "not_observed",
            "transcript_authority": False,
        }
        if recurrent_q_result is not None:
            if isinstance(recurrent_q_result, AuditoryLiveMotifResult):
                recurrent_q_result.verify()
                q_record = recurrent_q_result.as_record()
            elif isinstance(
                recurrent_q_result,
                AuditoryLiveMotifCompactReceipt,
            ):
                recurrent_q_result.verify()
                q_record = recurrent_q_result.as_record()
            else:
                raise TypeError(
                    "Loom cognition requires a typed recurrent-q result"
                )
            pending = (
                q_record["firing_state"]
                == "awaiting_exact_window_composition"
            )
            cognition.update({
                "activation_spans": list(
                    q_record["activation_spans"]
                ),
                "firing_motif_neuron_ids": list(
                    q_record["firing_motif_neuron_ids"]
                ),
                "learning_state": q_record["learning_state"],
                "presemantic_authority": True,
                "q_result_authority_receipt_sha256": (
                    q_record["authority_receipt_sha256"]
                ),
                "source_experience_receipt_sha256": (
                    q_record["source_experience_receipt_sha256"]
                ),
                "source_receptor_event_receipt_sha256": (
                    q_record[
                        "source_receptor_event_receipt_sha256"
                    ]
                ),
                "status": (
                    "recurrent_q_pending_window"
                    if pending
                    else "recurrent_q_observed"
                ),
            })
        meaning = {
            "authority": False,
            "status": "not_established_by_observation_projection",
            "text": None,
        }
        draft = TruthfulLoomObservationProjection(
            boundary_observations=observations,
            designations=designations,
            binaural_transport=binaural,
            runtime_components=components,
            cognition=cognition,
            meaning=meaning,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = draft.payload()
        signature = hmac.new(
            self._key,
            TRUTHFUL_LOOM_PROJECTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = TruthfulLoomObservationProjection(
            boundary_observations=draft.boundary_observations,
            designations=draft.designations,
            binaural_transport=draft.binaural_transport,
            runtime_components=draft.runtime_components,
            cognition=draft.cognition,
            meaning=draft.meaning,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result.verify(self._key)
        return result


__all__ = [
    "CAUSAL_THING_LOOM_SCHEMA",
    "LoomRuntimeComponentEvidence",
    "MAX_BOUNDARY_OBSERVATIONS",
    "MAX_CAUSAL_THING_SUMMARIES",
    "MAX_DESIGNATIONS",
    "MAX_RUNTIME_COMPONENTS",
    "SIGHT_ARTICULATORY_LOOM_SCHEMA",
    "TRUTHFUL_LOOM_PROJECTION_SCHEMA",
    "TruthfulLoomObservationProjection",
    "TruthfulLoomObservationProjector",
    "project_causal_thing_loom_observation",
    "project_sight_evoked_articulatory_loom_observation",
    "verify_causal_thing_loom_observation",
    "verify_sight_evoked_articulatory_loom_observation",
]
