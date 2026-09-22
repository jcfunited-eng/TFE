"""Exact action deliberation through causally continuous THING mosaics.

The causal action cycle retains complete learned trigger/action/outcome
evidence, but its native lookup is deliberately exact to one whole-field
structural fingerprint.  A different lived view of the same physical entity
therefore cannot reuse that relation by itself.

This authority supplies only the missing lawful bridge.  A current sensory
settlement must first evoke exactly one already-experienced THING through the
reciprocal mosaic owner.  A learned action relation is eligible only when its
authenticated trigger settlement is one of that same THING's retained
physical encounter partitions.  The complete trigger and outcome perception
witnesses remain attached; the THING id is an index backed by the physical
continuity chain, never a replacement for the field.

No signal comparison, threshold, score, vote, label, chi identity, Atlas,
grammar, text, or ML operation participates.  Unknown and conflicting
relations stop explicitly.  This is a read-only derivation over bounded owners
and creates no second lifetime memory.

Admission also requires the current authenticated recognition-attention state
and current embodied perspective boundary.  Their exact receipts remain in
the resolution.  They may reject stale, unresolved, or cross-context custody;
they never rank candidates or choose content.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    CausalActionCycle,
    PerceptionWitness,
    VerifiedActionRelationEvidence,
)
from dsf_ai_service.substrate.causal_recognition_attention import (
    CausalRecognitionAttentionOwner,
    CausalRecognitionAttentionState,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalClass,
    CausalThingReciprocalEvocation,
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.embodied_other_perspective import (
    EmbodiedOtherPerspectiveOwner,
    OtherBodyPerspectiveModel,
    SelfWorldState,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


CANDIDATE_SCHEMA = "guala.causal_thing.action_candidate.v1"
RESOLUTION_SCHEMA = "guala.causal_thing.action_resolution.v2"
STATUS_SCHEMA = "guala.causal_thing.action_deliberation.status.v1"

_RESOLUTION_DOMAIN = b"guala-causal-thing-action-resolution-v2\0"
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
        raise ValueError("THING action deliberation key changed")
    return hashlib.sha256(
        b"guala-causal-thing-action-deliberation-v1\0" + raw
    ).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class CausalThingActionCandidate:
    thing_id: str
    thing_class_receipt_sha256: str
    trigger_partition_receipt_sha256: str
    binding_id: str
    action: ActionCommand
    trigger_witness: PerceptionWitness
    outcome_witness: PerceptionWitness
    latest_closure_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action": self.action.as_record(),
            "binding_id": self.binding_id,
            "latest_closure_receipt_sha256": (
                self.latest_closure_receipt_sha256
            ),
            "outcome_witness": self.outcome_witness.as_record(),
            "schema": CANDIDATE_SCHEMA,
            "thing_class_receipt_sha256": (
                self.thing_class_receipt_sha256
            ),
            "thing_id": self.thing_id,
            "trigger_partition_receipt_sha256": (
                self.trigger_partition_receipt_sha256
            ),
            "trigger_witness": self.trigger_witness.as_record(),
        }


@dataclass(frozen=True, slots=True)
class CausalThingActionResolution:
    state: str
    current_settlement_receipt_sha256: str
    recognition_attention_receipt_sha256: str
    attention_context_receipt_sha256: str
    focused_relation_receipt_sha256: str
    self_world_state_receipt_sha256: str
    world_observation_receipt_sha256: str
    perspective_model_receipt_sha256s: tuple[str, ...]
    evocation: CausalThingReciprocalEvocation
    candidates: tuple[CausalThingActionCandidate, ...]
    selected: CausalThingActionCandidate | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "candidate_records": [
                value.payload() for value in self.candidates
            ],
            "current_settlement_receipt_sha256": (
                self.current_settlement_receipt_sha256
            ),
            "recognition_attention_receipt_sha256": (
                self.recognition_attention_receipt_sha256
            ),
            "attention_context_receipt_sha256": (
                self.attention_context_receipt_sha256
            ),
            "focused_relation_receipt_sha256": (
                self.focused_relation_receipt_sha256
            ),
            "self_world_state_receipt_sha256": (
                self.self_world_state_receipt_sha256
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "perspective_model_receipt_sha256s": list(
                self.perspective_model_receipt_sha256s
            ),
            "evocation_receipt_sha256": (
                self.evocation.authority_receipt_sha256
            ),
            "schema": RESOLUTION_SCHEMA,
            "selected_binding_id": (
                self.selected.binding_id
                if self.selected is not None
                else None
            ),
            "state": self.state,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class CausalThingActionDeliberationOwner:
    """Resolve learned full-field actions through exact THING continuity."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        reciprocal_owner: CausalThingReciprocalMosaicOwner,
        action_cycle: CausalActionCycle,
        max_candidates: int,
    ) -> None:
        if not isinstance(
            reciprocal_owner,
            CausalThingReciprocalMosaicOwner,
        ):
            raise TypeError(
                "THING action deliberation requires reciprocal mosaics"
            )
        if not isinstance(action_cycle, CausalActionCycle):
            raise TypeError(
                "THING action deliberation requires the causal action cycle"
            )
        if (
            isinstance(max_candidates, bool)
            or not isinstance(max_candidates, int)
            or max_candidates <= 0
        ):
            raise ValueError(
                "THING action deliberation capacity must be positive"
            )
        self._resolution_key = hashlib.sha256(
            _RESOLUTION_DOMAIN + _key(authority_key)
        ).digest()
        self._reciprocal = reciprocal_owner
        self._actions = action_cycle
        self._max_candidates = max_candidates

    def _trigger_partition(
        self,
        thing_class: CausalThingReciprocalClass,
        evidence: VerifiedActionRelationEvidence,
    ) -> str | None:
        return self._reciprocal.retained_trigger_partition(
            thing_class,
            evidence.trigger_witness.settlement_receipt_sha256,
        )

    @staticmethod
    def _candidate(
        *,
        thing_class: CausalThingReciprocalClass,
        partition_receipt: str,
        evidence: VerifiedActionRelationEvidence,
    ) -> CausalThingActionCandidate:
        if (
            evidence.status == "revoked"
            or evidence.outcome_witness is None
            or evidence.latest_closure_receipt_sha256 is None
        ):
            raise ValueError(
                "THING action candidate lacks a completed live relation"
            )
        evidence.action.verify(
            max_command_bytes=4_096,
        )
        for value, label in (
            (thing_class.thing_id, "THING action id"),
            (
                thing_class.authority_receipt_sha256,
                "THING action class",
            ),
            (partition_receipt, "THING action partition"),
            (evidence.binding_id, "THING action binding"),
            (
                evidence.latest_closure_receipt_sha256,
                "THING action closure",
            ),
        ):
            _sha(value, label)
        return CausalThingActionCandidate(
            thing_id=thing_class.thing_id,
            thing_class_receipt_sha256=(
                thing_class.authority_receipt_sha256
            ),
            trigger_partition_receipt_sha256=partition_receipt,
            binding_id=evidence.binding_id,
            action=evidence.action,
            trigger_witness=evidence.trigger_witness,
            outcome_witness=evidence.outcome_witness,
            latest_closure_receipt_sha256=(
                evidence.latest_closure_receipt_sha256
            ),
        )

    def _seal(
        self,
        *,
        state: str,
        settlement: CausalExperienceSettlement,
        attention_state: CausalRecognitionAttentionState,
        self_world_state: SelfWorldState,
        perspective_models: tuple[OtherBodyPerspectiveModel, ...],
        evocation: CausalThingReciprocalEvocation,
        candidates: tuple[CausalThingActionCandidate, ...],
        selected: CausalThingActionCandidate | None,
    ) -> CausalThingActionResolution:
        provisional = CausalThingActionResolution(
            state=state,
            current_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            recognition_attention_receipt_sha256=(
                attention_state.authority_receipt_sha256
            ),
            attention_context_receipt_sha256=(
                attention_state.context.authority_receipt_sha256
            ),
            focused_relation_receipt_sha256=(
                attention_state.focused_relation_receipt_sha256
            ),
            self_world_state_receipt_sha256=(
                self_world_state.authority_receipt_sha256
            ),
            world_observation_receipt_sha256=(
                self_world_state.world_observation_receipt_sha256
            ),
            perspective_model_receipt_sha256s=tuple(sorted(
                value.authority_receipt_sha256
                for value in perspective_models
            )),
            evocation=evocation,
            candidates=candidates,
            selected=selected,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._resolution_key,
            _RESOLUTION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return CausalThingActionResolution(
            state=provisional.state,
            current_settlement_receipt_sha256=(
                provisional.current_settlement_receipt_sha256
            ),
            recognition_attention_receipt_sha256=(
                provisional.recognition_attention_receipt_sha256
            ),
            attention_context_receipt_sha256=(
                provisional.attention_context_receipt_sha256
            ),
            focused_relation_receipt_sha256=(
                provisional.focused_relation_receipt_sha256
            ),
            self_world_state_receipt_sha256=(
                provisional.self_world_state_receipt_sha256
            ),
            world_observation_receipt_sha256=(
                provisional.world_observation_receipt_sha256
            ),
            perspective_model_receipt_sha256s=(
                provisional.perspective_model_receipt_sha256s
            ),
            evocation=provisional.evocation,
            candidates=provisional.candidates,
            selected=provisional.selected,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _discover_eligible_completed(
        self,
        settlement: CausalExperienceSettlement,
        *,
        cue_senses: tuple[str, ...],
    ) -> tuple[
        CausalThingReciprocalEvocation,
        tuple[CausalThingActionCandidate, ...],
        bool,
    ]:
        """Return exact completed candidates without choosing among them."""

        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "THING action discovery requires a causal settlement"
            )
        settlement.verify()
        evocation = self._reciprocal.evoke(
            settlement,
            cue_senses=cue_senses,
        )
        if evocation.state != "unique" or evocation.candidate is None:
            return evocation, (), False
        thing_class = evocation.candidate
        candidates = []
        incomplete = False
        for evidence in self._actions.verified_relation_evidence():
            partition = self._trigger_partition(thing_class, evidence)
            if partition is None or evidence.status == "revoked":
                continue
            if (
                evidence.outcome_witness is None
                or evidence.latest_closure_receipt_sha256 is None
            ):
                incomplete = True
                continue
            candidates.append(self._candidate(
                thing_class=thing_class,
                partition_receipt=partition,
                evidence=evidence,
            ))
        ordered = tuple(sorted(
            candidates,
            key=lambda value: (
                value.action.authority_receipt_sha256,
                value.binding_id,
            ),
        ))
        if len(ordered) > self._max_candidates:
            raise RuntimeError(
                "THING action deliberation candidate capacity exhausted"
            )
        return evocation, ordered, incomplete

    def eligible_completed_closure_receipts(
        self,
        settlement: CausalExperienceSettlement,
        *,
        cue_senses: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Expose exact eligible closures without preference or mutation."""

        _evocation, candidates, _incomplete = (
            self._discover_eligible_completed(
                settlement,
                cue_senses=cue_senses,
            )
        )
        return tuple(sorted(
            value.latest_closure_receipt_sha256
            for value in candidates
        ))

    def resolve(
        self,
        settlement: CausalExperienceSettlement,
        *,
        cue_senses: tuple[str, ...],
        recognition_attention_owner: CausalRecognitionAttentionOwner,
        attention_state: CausalRecognitionAttentionState | None,
        perspective_owner: EmbodiedOtherPerspectiveOwner,
        self_world_state: SelfWorldState | None,
        perspective_models: tuple[OtherBodyPerspectiveModel, ...],
    ) -> CausalThingActionResolution | None:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "THING action deliberation requires a causal settlement"
            )
        settlement.verify()
        if not isinstance(
            recognition_attention_owner,
            CausalRecognitionAttentionOwner,
        ):
            raise TypeError(
                "THING action deliberation requires recognition attention authority"
            )
        if not isinstance(
            perspective_owner,
            EmbodiedOtherPerspectiveOwner,
        ):
            raise TypeError(
                "THING action deliberation requires perspective authority"
            )
        if (
            attention_state is None
            or attention_state.recognition_state != "settled"
            or attention_state.attention_state != "focused_action"
            or attention_state.focused_relation_receipt_sha256 is None
        ):
            return None
        if recognition_attention_owner.state != attention_state:
            raise ValueError(
                "THING action recognition attention is not current"
            )
        if (
            self_world_state is None
            or perspective_owner.self_world_state != self_world_state
            or perspective_owner.models != perspective_models
        ):
            raise ValueError(
                "THING action perspective custody is not current"
            )
        context = attention_state.context
        if (
            context.context_id
            != "live-observation:" + settlement.authority_receipt_sha256
            or context.source_time_start != settlement.source_time_start
            or context.source_time_end != settlement.source_time_end
            or context.current_full_field_roots
            != full_field_sensory_roots(settlement)
        ):
            raise ValueError(
                "THING action attention names another settlement"
            )
        try:
            causal_context = json.loads(context.causal_context_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                "THING action attention causal context is unreadable"
            ) from error
        if (
            not isinstance(causal_context, dict)
            or causal_context.get("world_observation_receipt_sha256")
            != self_world_state.world_observation_receipt_sha256
        ):
            raise ValueError(
                "THING action perspective names another organism context"
            )
        evocation, ordered, incomplete = self._discover_eligible_completed(
            settlement,
            cue_senses=cue_senses,
        )
        if evocation.state != "unique" or evocation.candidate is None:
            return self._seal(
                state=(
                    "cue_ambiguous"
                    if evocation.state == "ambiguous"
                    else "cue_unresolved"
                ),
                settlement=settlement,
                attention_state=attention_state,
                self_world_state=self_world_state,
                perspective_models=perspective_models,
                evocation=evocation,
                candidates=(),
                selected=None,
            )
        thing_class = evocation.candidate
        if (
            attention_state.recognized_thing_mosaic_receipt_sha256
            != thing_class.thing_mosaic_receipt_sha256
        ):
            return self._seal(
                state="attention_thing_mismatch",
                settlement=settlement,
                attention_state=attention_state,
                self_world_state=self_world_state,
                perspective_models=perspective_models,
                evocation=evocation,
                candidates=(),
                selected=None,
            )
        selected = ordered[0] if len(ordered) == 1 else None
        if (
            selected is not None
            and selected.latest_closure_receipt_sha256
            != attention_state.focused_relation_receipt_sha256
        ):
            selected = None
            state = "attention_relation_mismatch"
        else:
            state = (
                "ready"
                if selected is not None
                else "action_ambiguous"
                if ordered
                else "outcome_unknown"
                if incomplete
                else "action_unknown"
            )
        return self._seal(
            state=state,
            settlement=settlement,
            attention_state=attention_state,
            self_world_state=self_world_state,
            perspective_models=perspective_models,
            evocation=evocation,
            candidates=ordered,
            selected=selected,
        )

    def verify_resolution(
        self,
        value: CausalThingActionResolution,
    ) -> None:
        if not isinstance(value, CausalThingActionResolution):
            raise TypeError("THING action resolution is not typed")
        self._reciprocal.verify_evocation(value.evocation)
        for digest, label in (
            (
                value.current_settlement_receipt_sha256,
                "THING action current settlement",
            ),
            (
                value.evocation.authority_receipt_sha256,
                "THING action evocation",
            ),
            (
                value.recognition_attention_receipt_sha256,
                "THING action recognition attention",
            ),
            (
                value.attention_context_receipt_sha256,
                "THING action attention context",
            ),
            (
                value.focused_relation_receipt_sha256,
                "THING action focused relation",
            ),
            (
                value.self_world_state_receipt_sha256,
                "THING action self-world state",
            ),
            (
                value.world_observation_receipt_sha256,
                "THING action world observation",
            ),
            (value.authority_hmac_sha256, "THING action resolution HMAC"),
            (
                value.authority_receipt_sha256,
                "THING action resolution authority",
            ),
        ):
            _sha(digest, label)
        if value.perspective_model_receipt_sha256s != tuple(sorted(
            set(value.perspective_model_receipt_sha256s)
        )):
            raise ValueError(
                "THING action perspective model custody changed"
            )
        for receipt in value.perspective_model_receipt_sha256s:
            _sha(receipt, "THING action perspective model")
        if (
            len(value.candidates) > self._max_candidates
            or (
                value.state == "ready"
                and (
                    len(value.candidates) != 1
                    or value.selected != value.candidates[0]
                )
            )
            or (
                value.state != "ready"
                and value.selected is not None
            )
        ):
            raise ValueError("THING action resolution extent changed")
        expected = hmac.new(
            self._resolution_key,
            _RESOLUTION_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("THING action resolution authority changed")

    def verify_current_resolution(
        self,
        settlement: CausalExperienceSettlement,
        value: CausalThingActionResolution,
        *,
        recognition_attention_owner: CausalRecognitionAttentionOwner,
        attention_state: CausalRecognitionAttentionState,
        perspective_owner: EmbodiedOtherPerspectiveOwner,
        self_world_state: SelfWorldState,
        perspective_models: tuple[OtherBodyPerspectiveModel, ...],
    ) -> None:
        """Reject a valid but stale relation before it can authorize action."""

        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "current THING action resolution requires a settlement"
            )
        settlement.verify()
        self.verify_resolution(value)
        if (
            value.current_settlement_receipt_sha256
            != settlement.authority_receipt_sha256
        ):
            raise ValueError(
                "THING action resolution names another current settlement"
            )
        current = self.resolve(
            settlement,
            cue_senses=value.evocation.cue_senses,
            recognition_attention_owner=recognition_attention_owner,
            attention_state=attention_state,
            perspective_owner=perspective_owner,
            self_world_state=self_world_state,
            perspective_models=perspective_models,
        )
        if current is None or current != value:
            raise ValueError(
                "THING action resolution is no longer current"
            )

    def status(self) -> dict[str, object]:
        return {
            "full_field_witnesses_retained": True,
            "max_candidates": self._max_candidates,
            "reduced_approximation": False,
            "schema": STATUS_SCHEMA,
            "signal_matching": False,
            "state_bytes": 0,
            "unseen_variant_guessing": False,
        }


__all__ = (
    "CausalThingActionCandidate",
    "CausalThingActionDeliberationOwner",
    "CausalThingActionResolution",
)
