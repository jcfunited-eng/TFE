"""Owner-bound execution of one experience-grown vocal causal relation.

The only public motor authority accepted here is a live
``ExperienceGrownVocalProgramCustody`` issued from the current authenticated
physical mosaic.  The caller cannot provide a program identity, waveform,
motor coordinate, cue sense, label, text, or meaning.

Preparation reopens the private settled-experience capability retained inside
the custody, requires that occurrence to be the immediate current world edge,
and recomputes the relation selection exactly.  The finalized fragment remains
the pressure authority.  The already-admitted articulatory program is then
synthesized and admitted to the existing atomic W1 self-hearing transaction.

PCM exists only inside the request-live prepared/committed capabilities.  No
PCM, prepared act, commit undo, or replay cursor has a persistence surface.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field, replace
from fractions import Fraction

from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryGeneratedEmission,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.experience_grown_vocal_causal_relation import (
    ExperienceGrownVocalCausalRelationOwner,
    ExperienceGrownVocalProgramCustody,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    PreparedW1SelfAcousticMount,
    W1ArticulatorySelfAcousticCommitUndo,
    W1PreparedArticulatoryCommitment,
    W1SelfAcousticMount,
    W1SelfAcousticPropagationAuthority,
)


ACT_RECEIPT_SCHEMA = (
    "guala.experience_grown_vocal_causal_act.receipt.v1"
)
STATUS_SCHEMA = "guala.experience_grown_vocal_causal_act.status.v1"

_RECEIPT_DOMAIN = b"guala-experience-grown-vocal-causal-act-receipt-v1\0"
_PREPARED_AUTHORITY = object()
_UNDO_AUTHORITY = object()
_COMMITTED_AUTHORITY = object()
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
        raise ValueError("vocal causal act authority key changed")
    return hashlib.sha256(
        b"guala-experience-grown-vocal-causal-act-owner-v1\0" + raw
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
class ExperienceGrownVocalCausalActReceipt:
    program_custody_receipt_sha256: str
    relation_receipt_sha256: str
    fragment_receipt_sha256: str
    program_id: str
    program_authority_receipt_sha256: str
    learned_pressure_sha256: str
    emitted_pressure_sha256: str
    synthesis_receipt_sha256: str
    emission_receipt_sha256: str
    self_acoustic_mount_receipt_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    world_execution_receipt_sha256: str
    causal_settlement_receipt_sha256: str
    binaural_l5_receipt_sha256: str
    receptor_settlement_receipt_sha256: str
    recurrent_q_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "binaural_l5_receipt_sha256": (
                self.binaural_l5_receipt_sha256
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "emission_receipt_sha256": self.emission_receipt_sha256,
            "emitted_pressure_sha256": self.emitted_pressure_sha256,
            "fragment_receipt_sha256": self.fragment_receipt_sha256,
            "learned_pressure_sha256": self.learned_pressure_sha256,
            "program_authority_receipt_sha256": (
                self.program_authority_receipt_sha256
            ),
            "program_custody_receipt_sha256": (
                self.program_custody_receipt_sha256
            ),
            "program_id": self.program_id,
            "receptor_settlement_receipt_sha256": (
                self.receptor_settlement_receipt_sha256
            ),
            "recurrent_q_receipt_sha256": (
                self.recurrent_q_receipt_sha256
            ),
            "relation_receipt_sha256": self.relation_receipt_sha256,
            "schema": ACT_RECEIPT_SCHEMA,
            "self_acoustic_mount_receipt_sha256": (
                self.self_acoustic_mount_receipt_sha256
            ),
            "synthesis_receipt_sha256": self.synthesis_receipt_sha256,
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class CommittedExperienceGrownVocalCausalAct:
    receipt: ExperienceGrownVocalCausalActReceipt
    pcm_s16le: bytes
    _program_custody: ExperienceGrownVocalProgramCustody = field(
        repr=False,
        compare=False,
    )
    _emission: ArticulatoryGeneratedEmission = field(
        repr=False,
        compare=False,
    )
    _mount: W1SelfAcousticMount = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


@dataclass(slots=True)
class _PreparedState:
    phase: str = "prepared"


@dataclass(frozen=True, slots=True)
class PreparedExperienceGrownVocalCausalAct:
    program_custody: ExperienceGrownVocalProgramCustody
    prepared_commitment: W1PreparedArticulatoryCommitment
    learned_pressure_sha256: str
    fragment_receipt_sha256: str
    _prepared_w1: PreparedW1SelfAcousticMount = field(
        repr=False,
        compare=False,
    )
    _state: _PreparedState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


@dataclass(slots=True)
class _UndoState:
    phase: str = "committed"


@dataclass(frozen=True, slots=True)
class ExperienceGrownVocalCausalActUndo:
    committed_act: CommittedExperienceGrownVocalCausalAct
    _prepared: PreparedExperienceGrownVocalCausalAct = field(
        repr=False,
        compare=False,
    )
    _w1_undo: W1ArticulatorySelfAcousticCommitUndo = field(
        repr=False,
        compare=False,
    )
    _state: _UndoState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


class ExperienceGrownVocalCausalActAuthority:
    """Execute only a request-live current-mosaic vocal program custody."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        relation_owner: ExperienceGrownVocalCausalRelationOwner,
        motor_owner: ArticulatorySelfVocalMotorOwner,
        acoustic_authority: W1SelfAcousticPropagationAuthority,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        if not isinstance(
            relation_owner,
            ExperienceGrownVocalCausalRelationOwner,
        ):
            raise TypeError(
                "vocal causal act requires relation custody"
            )
        if not isinstance(
            motor_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError("vocal causal act requires motor custody")
        if not isinstance(
            acoustic_authority,
            W1SelfAcousticPropagationAuthority,
        ):
            raise TypeError("vocal causal act requires W1 self-hearing")
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("vocal causal act requires W1 world custody")
        if (
            relation_owner._motor is not motor_owner
            or not acoustic_authority.owns_world(world_authority)
        ):
            raise ValueError(
                "vocal causal act crossed substrate ownership"
            )
        root = _key(authority_key)
        self._receipt_key = hashlib.sha256(
            _RECEIPT_DOMAIN + root
        ).digest()
        self._relations = relation_owner
        self._motor = motor_owner
        self._acoustic = acoustic_authority
        self._world = world_authority
        self._owner_authority = object()
        self._prepared: PreparedExperienceGrownVocalCausalAct | None = None
        self._undo: ExperienceGrownVocalCausalActUndo | None = None
        self._lock = threading.RLock()

    def _receipt(
        self,
        *,
        custody: ExperienceGrownVocalProgramCustody,
        fragment_receipt_sha256: str,
        learned_pressure_sha256: str,
        emission: ArticulatoryGeneratedEmission,
        mount: W1SelfAcousticMount,
    ) -> ExperienceGrownVocalCausalActReceipt:
        receipt = mount.receipt
        provisional = ExperienceGrownVocalCausalActReceipt(
            program_custody_receipt_sha256=(
                custody.authority_receipt_sha256
            ),
            relation_receipt_sha256=(
                custody.relation_receipt_sha256
            ),
            fragment_receipt_sha256=fragment_receipt_sha256,
            program_id=custody.program.program_id,
            program_authority_receipt_sha256=(
                custody.program.authority_receipt_sha256
            ),
            learned_pressure_sha256=learned_pressure_sha256,
            emitted_pressure_sha256=hashlib.sha256(
                emission.pcm_s16le
            ).hexdigest(),
            synthesis_receipt_sha256=(
                emission.synthesis.receipt.authority_receipt_sha256
            ),
            emission_receipt_sha256=(
                emission.emission_receipt.authority_receipt_sha256
            ),
            self_acoustic_mount_receipt_sha256=(
                receipt.authority_receipt_sha256
            ),
            world_before_receipt_sha256=(
                emission.execution_receipt
                .before.authority_receipt_sha256
            ),
            world_after_receipt_sha256=(
                emission.execution_receipt
                .after.authority_receipt_sha256
            ),
            world_execution_receipt_sha256=(
                emission.execution_receipt.authority_receipt_sha256
            ),
            causal_settlement_receipt_sha256=(
                receipt.causal_settlement_receipt_sha256
            ),
            binaural_l5_receipt_sha256=(
                receipt.binaural_l5_receipt_sha256
            ),
            receptor_settlement_receipt_sha256=(
                receipt.receptor_settlement_receipt_sha256
            ),
            recurrent_q_receipt_sha256=(
                receipt.observation_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._receipt_key,
            _RECEIPT_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return replace(
            provisional,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _verify_receipt(
        self,
        receipt: ExperienceGrownVocalCausalActReceipt,
    ) -> None:
        if not isinstance(
            receipt,
            ExperienceGrownVocalCausalActReceipt,
        ):
            raise TypeError("vocal causal act receipt is not typed")
        for value, label in (
            (
                receipt.program_custody_receipt_sha256,
                "vocal causal act program custody",
            ),
            (receipt.relation_receipt_sha256, "vocal causal relation"),
            (receipt.fragment_receipt_sha256, "vocal motor fragment"),
            (receipt.program_id, "vocal articulatory program"),
            (
                receipt.program_authority_receipt_sha256,
                "vocal articulatory program authority",
            ),
            (
                receipt.learned_pressure_sha256,
                "learned vocal pressure",
            ),
            (
                receipt.emitted_pressure_sha256,
                "emitted vocal pressure",
            ),
            (
                receipt.synthesis_receipt_sha256,
                "vocal synthesis",
            ),
            (receipt.emission_receipt_sha256, "vocal emission"),
            (
                receipt.self_acoustic_mount_receipt_sha256,
                "vocal self-hearing",
            ),
            (receipt.world_before_receipt_sha256, "world before"),
            (receipt.world_after_receipt_sha256, "world after"),
            (
                receipt.world_execution_receipt_sha256,
                "world execution",
            ),
            (
                receipt.causal_settlement_receipt_sha256,
                "self-heard causal settlement",
            ),
            (
                receipt.binaural_l5_receipt_sha256,
                "self-heard binaural L5",
            ),
            (
                receipt.receptor_settlement_receipt_sha256,
                "self-heard receptor settlement",
            ),
            (
                receipt.recurrent_q_receipt_sha256,
                "self-heard recurrent q",
            ),
            (receipt.authority_hmac_sha256, "vocal act HMAC"),
            (receipt.authority_receipt_sha256, "vocal act authority"),
        ):
            _sha(value, label)
        signature = hmac.new(
            self._receipt_key,
            _RECEIPT_DOMAIN + _canonical(receipt.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature,
                receipt.authority_hmac_sha256,
            )
            or receipt.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": receipt.payload(),
            })
            or receipt.learned_pressure_sha256
            != receipt.emitted_pressure_sha256
        ):
            raise ValueError("vocal causal act receipt changed")

    def _require_prepared(
        self,
        prepared: PreparedExperienceGrownVocalCausalAct,
    ) -> PreparedExperienceGrownVocalCausalAct:
        if (
            not isinstance(
                prepared,
                PreparedExperienceGrownVocalCausalAct,
            )
            or prepared._construction_authority
            is not _PREPARED_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
            or self._prepared is not prepared
            or prepared._state.phase != "prepared"
        ):
            raise ValueError(
                "prepared vocal causal act changed custody"
            )
        self._relations.verify_program_custody(
            prepared.program_custody
        )
        self._acoustic.verify_prepared_articulatory_commitment(
            prepared._prepared_w1,
            prepared.prepared_commitment,
        )
        if (
            prepared.prepared_commitment.pcm_sha256
            != prepared.learned_pressure_sha256
            or prepared.prepared_commitment.program_id
            != prepared.program_custody.program.program_id
        ):
            raise ValueError(
                "prepared vocal causal act changed learned pressure"
            )
        return prepared

    def prepare(
        self,
        program_custody: ExperienceGrownVocalProgramCustody,
    ) -> PreparedExperienceGrownVocalCausalAct:
        """Stage one exact learned act from typed current-mosaic custody."""

        if not isinstance(
            program_custody,
            ExperienceGrownVocalProgramCustody,
        ):
            raise TypeError(
                "vocal causal act requires typed program custody"
            )
        with self._lock:
            if self._prepared is not None or self._undo is not None:
                raise RuntimeError(
                    "vocal causal act transaction is already active"
                )
            self._relations.verify_program_custody(program_custody)
            view = self._relations.open_program_custody(
                program_custody
            )
            before = self._world.observation_snapshot()
            self._world.verify_observation_snapshot(before)
            if view.world_observation != before:
                raise ValueError(
                    "vocal program custody is not the immediate world edge"
                )
            reselection = self._relations.select(
                current_custody_authority=(
                    program_custody._current_custody_authority
                ),
                current_custody_capability=(
                    program_custody._current_custody_capability
                ),
            )
            self._relations.verify_selection(reselection)
            if (
                reselection.state != "ready"
                or reselection.program_custody != program_custody
            ):
                raise ValueError(
                    "vocal program custody no longer selects exactly"
                )
            fragment = self._relations.verified_program_fragment(
                program_custody
            )
            synthesis = self._motor.synthesize(
                program_id=program_custody.program.program_id,
                source_time_start=Fraction(
                    before.revision * MAX_VOCAL_SAMPLE_COUNT,
                    VOCAL_SAMPLE_RATE_HZ,
                ),
            )
            emitted_pressure = hashlib.sha256(
                synthesis.radiated_pcm_s16le
            ).hexdigest()
            if (
                synthesis.program != program_custody.program
                or emitted_pressure != fragment.pressure_sha256
            ):
                raise ValueError(
                    "learned program did not reproduce original pressure"
                )
            intent = _digest({
                "current_settlement_receipt_sha256": (
                    program_custody.current_settlement_receipt_sha256
                ),
                "fragment_receipt_sha256": (
                    fragment.authority_receipt_sha256
                ),
                "program_custody_receipt_sha256": (
                    program_custody.authority_receipt_sha256
                ),
                "schema": (
                    "guala.experience_grown_vocal_causal_act.intent.v1"
                ),
                "synthesis_receipt_sha256": (
                    synthesis.receipt.authority_receipt_sha256
                ),
                "world_before_receipt_sha256": (
                    before.authority_receipt_sha256
                ),
            })
            prepared_emission = self._motor.prepare_generated_emission(
                synthesis=synthesis,
                world_authority=self._world,
                causal_intent_receipt_sha256=intent,
            )
            prepared_w1 = self._acoustic.prepare_articulatory(
                prepared_emission,
                articulatory_owner=self._motor,
            )
            try:
                commitment = (
                    self._acoustic.prepared_articulatory_commitment(
                        prepared_w1
                    )
                )
                self._acoustic.verify_prepared_articulatory_commitment(
                    prepared_w1,
                    commitment,
                )
                if (
                    commitment.program_id
                    != program_custody.program.program_id
                    or commitment.pcm_sha256
                    != fragment.pressure_sha256
                    or commitment.world_before_receipt_sha256
                    != before.authority_receipt_sha256
                ):
                    raise ValueError(
                        "prepared vocal causal act crossed custody"
                    )
                prepared = PreparedExperienceGrownVocalCausalAct(
                    program_custody=program_custody,
                    prepared_commitment=commitment,
                    learned_pressure_sha256=fragment.pressure_sha256,
                    fragment_receipt_sha256=(
                        fragment.authority_receipt_sha256
                    ),
                    _prepared_w1=prepared_w1,
                    _state=_PreparedState(),
                    _owner_authority=self._owner_authority,
                    _construction_authority=_PREPARED_AUTHORITY,
                )
                self._prepared = prepared
                self._require_prepared(prepared)
                return prepared
            except BaseException:
                self._acoustic.discard_prepared_articulatory(
                    prepared_w1
                )
                raise

    def discard(
        self,
        prepared: PreparedExperienceGrownVocalCausalAct,
    ) -> None:
        with self._lock:
            current = self._require_prepared(prepared)
            self._acoustic.discard_prepared_articulatory(
                current._prepared_w1
            )
            current._state.phase = "discarded"
            self._prepared = None

    def commit(
        self,
        prepared: PreparedExperienceGrownVocalCausalAct,
    ) -> ExperienceGrownVocalCausalActUndo:
        """Commit body/world/W1 and retain the exact typed W1 undo."""

        with self._lock:
            current = self._require_prepared(prepared)
            w1_undo = None
            try:
                emission, mount, w1_undo = (
                    self._acoustic.commit_prepared_articulatory(
                        current._prepared_w1
                    )
                )
                self._motor.verify_generated_emission(
                    emission,
                    world_authority=self._world,
                )
                self._acoustic.verify_mount(mount)
                receipt = self._receipt(
                    custody=current.program_custody,
                    fragment_receipt_sha256=(
                        current.fragment_receipt_sha256
                    ),
                    learned_pressure_sha256=(
                        current.learned_pressure_sha256
                    ),
                    emission=emission,
                    mount=mount,
                )
                committed = CommittedExperienceGrownVocalCausalAct(
                    receipt=receipt,
                    pcm_s16le=bytes(emission.pcm_s16le),
                    _program_custody=current.program_custody,
                    _emission=emission,
                    _mount=mount,
                    _owner_authority=self._owner_authority,
                    _construction_authority=_COMMITTED_AUTHORITY,
                )
                self.verify_committed_act(committed)
            except BaseException:
                if w1_undo is not None:
                    self._acoustic.rollback_committed_articulatory(
                        w1_undo
                    )
                self._prepared = None
                current._state.phase = "rolled_back"
                raise
            current._state.phase = "committed"
            self._prepared = None
            undo = ExperienceGrownVocalCausalActUndo(
                committed_act=committed,
                _prepared=current,
                _w1_undo=w1_undo,
                _state=_UndoState(),
                _owner_authority=self._owner_authority,
                _construction_authority=_UNDO_AUTHORITY,
            )
            self._undo = undo
            return undo

    def _require_undo(
        self,
        undo: ExperienceGrownVocalCausalActUndo,
    ) -> ExperienceGrownVocalCausalActUndo:
        if (
            not isinstance(undo, ExperienceGrownVocalCausalActUndo)
            or undo._construction_authority is not _UNDO_AUTHORITY
            or undo._owner_authority is not self._owner_authority
            or self._undo is not undo
            or undo._state.phase != "committed"
            or undo._prepared._state.phase != "committed"
        ):
            raise ValueError("vocal causal act undo changed custody")
        self.verify_committed_act(undo.committed_act)
        if (
            self._world.observation_snapshot()
            .authority_receipt_sha256
            != undo.committed_act.receipt.world_after_receipt_sha256
        ):
            raise ValueError(
                "vocal causal act is no longer the current world edge"
            )
        return undo

    def rollback(
        self,
        undo: ExperienceGrownVocalCausalActUndo,
    ) -> None:
        with self._lock:
            current = self._require_undo(undo)
            self._acoustic.rollback_committed_articulatory(
                current._w1_undo
            )
            current._state.phase = "rolled_back"
            current._prepared._state.phase = "rolled_back"
            self._undo = None

    def finalize(
        self,
        undo: ExperienceGrownVocalCausalActUndo,
    ) -> CommittedExperienceGrownVocalCausalAct:
        """Release rollback custody only after external publication succeeds."""

        with self._lock:
            current = self._require_undo(undo)
            current._state.phase = "finalized"
            current._prepared._state.phase = "finalized"
            self._undo = None
            return current.committed_act

    def verify_committed_act(
        self,
        value: CommittedExperienceGrownVocalCausalAct,
    ) -> None:
        if (
            not isinstance(
                value,
                CommittedExperienceGrownVocalCausalAct,
            )
            or value._construction_authority is not _COMMITTED_AUTHORITY
            or value._owner_authority is not self._owner_authority
            or not isinstance(value.pcm_s16le, bytes)
            or not value.pcm_s16le
            or len(value.pcm_s16le) % 2
            or len(value.pcm_s16le)
            > MAX_VOCAL_SAMPLE_COUNT * 2
        ):
            raise ValueError("committed vocal causal act changed custody")
        self._verify_receipt(value.receipt)
        self._relations.verify_program_custody(
            value._program_custody
        )
        fragment = self._relations.verified_program_fragment(
            value._program_custody
        )
        self._motor.verify_generated_emission(
            value._emission,
            world_authority=self._world,
        )
        self._acoustic.verify_mount(value._mount)
        receipt = value.receipt
        emission = value._emission
        mount = value._mount
        if (
            hashlib.sha256(value.pcm_s16le).hexdigest()
            != receipt.emitted_pressure_sha256
            or value.pcm_s16le != emission.pcm_s16le
            or receipt.program_custody_receipt_sha256
            != value._program_custody.authority_receipt_sha256
            or receipt.relation_receipt_sha256
            != value._program_custody.relation_receipt_sha256
            or receipt.fragment_receipt_sha256
            != fragment.authority_receipt_sha256
            or receipt.program_id
            != value._program_custody.program.program_id
            or receipt.program_authority_receipt_sha256
            != value._program_custody.program.authority_receipt_sha256
            or receipt.learned_pressure_sha256
            != fragment.pressure_sha256
            or receipt.synthesis_receipt_sha256
            != emission.synthesis.receipt.authority_receipt_sha256
            or receipt.emission_receipt_sha256
            != emission.emission_receipt.authority_receipt_sha256
            or receipt.self_acoustic_mount_receipt_sha256
            != mount.receipt.authority_receipt_sha256
            or receipt.world_before_receipt_sha256
            != emission.execution_receipt
            .before.authority_receipt_sha256
            or receipt.world_after_receipt_sha256
            != emission.execution_receipt
            .after.authority_receipt_sha256
            or receipt.world_execution_receipt_sha256
            != emission.execution_receipt.authority_receipt_sha256
            or mount.receipt.motor_id != receipt.program_id
            or mount.receipt.self_vocal_emission_receipt_sha256
            != receipt.emission_receipt_sha256
            or mount.receipt.world_execution_receipt_sha256
            != receipt.world_execution_receipt_sha256
            or mount.receipt.causal_settlement_receipt_sha256
            != receipt.causal_settlement_receipt_sha256
            or mount.receipt.binaural_l5_receipt_sha256
            != receipt.binaural_l5_receipt_sha256
            or mount.receipt.receptor_settlement_receipt_sha256
            != receipt.receptor_settlement_receipt_sha256
            or mount.receipt.observation_receipt_sha256
            != receipt.recurrent_q_receipt_sha256
        ):
            raise ValueError(
                "committed vocal causal act changed physical linkage"
            )

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "accepts_caller_cue_senses": False,
                "accepts_caller_motor_parameters": False,
                "accepts_caller_program_id": False,
                "motor_derived_from_witness_field": True,
                "prepared": self._prepared is not None,
                "retained_pcm_bytes": 0,
                "retained_replay_receipts": 0,
                "rollback_pending": self._undo is not None,
                "schema": STATUS_SCHEMA,
                "stateful_persistence": False,
                "witness_full_dsf_field_preserved_upstream": True,
            }


__all__ = (
    "ACT_RECEIPT_SCHEMA",
    "STATUS_SCHEMA",
    "CommittedExperienceGrownVocalCausalAct",
    "ExperienceGrownVocalCausalActAuthority",
    "ExperienceGrownVocalCausalActReceipt",
    "ExperienceGrownVocalCausalActUndo",
    "PreparedExperienceGrownVocalCausalAct",
)
