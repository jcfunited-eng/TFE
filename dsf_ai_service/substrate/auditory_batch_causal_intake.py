"""Authenticated causal intake for one live ordered auditory terminal batch.

The authority in this module is stateless.  It can issue a durable receipt only
while the terminal registry still owns one complete live batch claim and only
when that batch, its incremental advance, its ordered token sequence, the
current joint auditory settlement, and the immutable six-sense causal
settlement agree exactly.

The receipt carries authority links and physical intervals only.  It has no
tutor label, transcript, source or agent identity, routing chi, Atlas value,
semantic score, compatibility token, or retained index.  A release whose
physical interval crosses the current causal settlement is reported explicitly
and is never collapsed into a fabricated single-settlement episode.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.model import require_fraction, sha256_digest
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryIncrementalAdvance,
    AuditoryIncrementalTerminalBatchClaim,
    AuditoryIncrementalTerminalRegistry,
)
from dsf_ai_service.substrate.auditory_pcm_stream import PCM_SAMPLE_RATE_HZ
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.auditory_token_sequence import (
    AuditoryTokenSequenceAuthority,
    AuditoryTokenSequenceReceipt,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


AUDITORY_BATCH_CAUSAL_INTAKE_SCHEMA = (
    "guala.auditory.batch_causal_intake.v1"
)
_INTAKE_KEY_DOMAIN = b"guala.auditory.batch_causal_intake.v1\0"
MAX_IDENTIFIER_BYTES = 256
MAX_INTAKE_BYTES = 4 * 1024 * 1024


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
        raise ValueError("auditory causal intake key must be bytes or text")
    if len(result) < 32 or len(result) > 4096:
        raise ValueError("auditory causal intake key has an invalid boundary")
    return result


def _sign(key: bytes, value: object) -> str:
    return hmac.new(key, _canonical(value), hashlib.sha256).hexdigest()


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES
    ):
        raise ValueError(f"{name} must be a bounded canonical identifier")
    return value


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "auditory causal intake exact time")
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator_text, denominator_text = value.split("/", 1)
    if (
        not numerator_text
        or not denominator_text
        or not numerator_text.lstrip("-").isdigit()
        or not denominator_text.isdigit()
        or int(denominator_text) <= 0
    ):
        raise ValueError(f"{name} is not an exact fraction")
    result = Fraction(int(numerator_text), int(denominator_text))
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class AuditoryBatchCausalEntryLink:
    ordinal: int
    sub_event_id: str
    source_sample_start: int
    source_sample_end: int
    source_time_start: Fraction
    source_time_end: Fraction
    structural_fingerprint: str
    terminal_authority_receipt_sha256: str
    l5_authority_receipt_sha256: str

    def as_record(self) -> dict[str, object]:
        return {
            "l5_authority_receipt_sha256": self.l5_authority_receipt_sha256,
            "ordinal": self.ordinal,
            "source_sample_end": self.source_sample_end,
            "source_sample_start": self.source_sample_start,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "structural_fingerprint": self.structural_fingerprint,
            "sub_event_id": self.sub_event_id,
            "terminal_authority_receipt_sha256": (
                self.terminal_authority_receipt_sha256
            ),
        }

    @classmethod
    def from_record(
        cls, record: object
    ) -> "AuditoryBatchCausalEntryLink":
        expected = {
            "l5_authority_receipt_sha256",
            "ordinal",
            "source_sample_end",
            "source_sample_start",
            "source_time_end",
            "source_time_start",
            "structural_fingerprint",
            "sub_event_id",
            "terminal_authority_receipt_sha256",
        }
        if not isinstance(record, Mapping) or set(record) != expected:
            raise ValueError("auditory causal intake entry fields changed")
        return cls(
            ordinal=record.get("ordinal"),
            sub_event_id=record.get("sub_event_id"),
            source_sample_start=record.get("source_sample_start"),
            source_sample_end=record.get("source_sample_end"),
            source_time_start=_fraction_from_text(
                record.get("source_time_start"), "intake entry start"
            ),
            source_time_end=_fraction_from_text(
                record.get("source_time_end"), "intake entry end"
            ),
            structural_fingerprint=record.get("structural_fingerprint"),
            terminal_authority_receipt_sha256=record.get(
                "terminal_authority_receipt_sha256"
            ),
            l5_authority_receipt_sha256=record.get(
                "l5_authority_receipt_sha256"
            ),
        )


def _intake_payload(
    *,
    advance_authority_receipt_sha256: str,
    batch_authority_receipt_sha256: str,
    token_sequence_id: str,
    token_sequence_authority_hmac_sha256: str,
    joint_settlement_authority_receipt_sha256: str,
    causal_settlement_authority_receipt_sha256: str,
    assembly_id: str,
    stream_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    entries: tuple[AuditoryBatchCausalEntryLink, ...],
) -> dict[str, object]:
    return {
        "advance_authority_receipt_sha256": (
            advance_authority_receipt_sha256
        ),
        "assembly_id": assembly_id,
        "batch_authority_receipt_sha256": batch_authority_receipt_sha256,
        "causal_settlement_authority_receipt_sha256": (
            causal_settlement_authority_receipt_sha256
        ),
        "entries": [value.as_record() for value in entries],
        "joint_settlement_authority_receipt_sha256": (
            joint_settlement_authority_receipt_sha256
        ),
        "schema": AUDITORY_BATCH_CAUSAL_INTAKE_SCHEMA,
        "source_time_end": _fraction_text(source_time_end),
        "source_time_start": _fraction_text(source_time_start),
        "stream_id": stream_id,
        "token_sequence_authority_hmac_sha256": (
            token_sequence_authority_hmac_sha256
        ),
        "token_sequence_id": token_sequence_id,
    }


@dataclass(frozen=True, slots=True)
class AuditoryBatchCausalIntakeReceipt:
    intake_id: str
    advance_authority_receipt_sha256: str
    batch_authority_receipt_sha256: str
    token_sequence_id: str
    token_sequence_authority_hmac_sha256: str
    joint_settlement_authority_receipt_sha256: str
    causal_settlement_authority_receipt_sha256: str
    assembly_id: str
    stream_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    entries: tuple[AuditoryBatchCausalEntryLink, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return _intake_payload(
            advance_authority_receipt_sha256=(
                self.advance_authority_receipt_sha256
            ),
            batch_authority_receipt_sha256=(
                self.batch_authority_receipt_sha256
            ),
            token_sequence_id=self.token_sequence_id,
            token_sequence_authority_hmac_sha256=(
                self.token_sequence_authority_hmac_sha256
            ),
            joint_settlement_authority_receipt_sha256=(
                self.joint_settlement_authority_receipt_sha256
            ),
            causal_settlement_authority_receipt_sha256=(
                self.causal_settlement_authority_receipt_sha256
            ),
            assembly_id=self.assembly_id,
            stream_id=self.stream_id,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            entries=self.entries,
        )

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "intake_id": self.intake_id,
        }

    @classmethod
    def from_record(
        cls, record: object
    ) -> "AuditoryBatchCausalIntakeReceipt":
        expected = {
            "advance_authority_receipt_sha256",
            "assembly_id",
            "authority_hmac_sha256",
            "batch_authority_receipt_sha256",
            "causal_settlement_authority_receipt_sha256",
            "entries",
            "intake_id",
            "joint_settlement_authority_receipt_sha256",
            "schema",
            "source_time_end",
            "source_time_start",
            "stream_id",
            "token_sequence_authority_hmac_sha256",
            "token_sequence_id",
        }
        if (
            not isinstance(record, Mapping)
            or set(record) != expected
            or record.get("schema") != AUDITORY_BATCH_CAUSAL_INTAKE_SCHEMA
        ):
            raise ValueError("auditory causal intake record fields changed")
        raw_entries = record.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError("auditory causal intake entries changed")
        return cls(
            intake_id=record.get("intake_id"),
            advance_authority_receipt_sha256=record.get(
                "advance_authority_receipt_sha256"
            ),
            batch_authority_receipt_sha256=record.get(
                "batch_authority_receipt_sha256"
            ),
            token_sequence_id=record.get("token_sequence_id"),
            token_sequence_authority_hmac_sha256=record.get(
                "token_sequence_authority_hmac_sha256"
            ),
            joint_settlement_authority_receipt_sha256=record.get(
                "joint_settlement_authority_receipt_sha256"
            ),
            causal_settlement_authority_receipt_sha256=record.get(
                "causal_settlement_authority_receipt_sha256"
            ),
            assembly_id=record.get("assembly_id"),
            stream_id=record.get("stream_id"),
            source_time_start=_fraction_from_text(
                record.get("source_time_start"), "intake source start"
            ),
            source_time_end=_fraction_from_text(
                record.get("source_time_end"), "intake source end"
            ),
            entries=tuple(
                AuditoryBatchCausalEntryLink.from_record(value)
                for value in raw_entries
            ),
            authority_hmac_sha256=record.get("authority_hmac_sha256"),
        )


@dataclass(frozen=True, slots=True)
class AuditoryBatchCausalIntakeAdmission:
    state: str
    reason: str
    intake: AuditoryBatchCausalIntakeReceipt | None


class AuditoryBatchCausalIntakeAuthority:
    """Issues receipts from live authority graphs without retaining state."""

    def __init__(self, *, authority_key: bytes | str) -> None:
        root = hashlib.sha256(_key(authority_key)).digest()
        self._intake_key = hashlib.sha256(
            _INTAKE_KEY_DOMAIN + root
        ).digest()

    @property
    def retained_intake_count(self) -> int:
        return 0

    @staticmethod
    def _verify_entry(value: AuditoryBatchCausalEntryLink) -> None:
        if not isinstance(value, AuditoryBatchCausalEntryLink):
            raise TypeError("auditory causal intake entry is untyped")
        if (
            isinstance(value.ordinal, bool)
            or not isinstance(value.ordinal, int)
            or value.ordinal < 0
            or isinstance(value.source_sample_start, bool)
            or not isinstance(value.source_sample_start, int)
            or value.source_sample_start < 0
            or isinstance(value.source_sample_end, bool)
            or not isinstance(value.source_sample_end, int)
            or value.source_sample_end <= value.source_sample_start
        ):
            raise ValueError("auditory causal intake entry interval changed")
        require_fraction(value.source_time_start, "intake entry start")
        require_fraction(value.source_time_end, "intake entry end")
        if (
            value.source_time_end <= value.source_time_start
            or value.source_time_end - value.source_time_start
            != Fraction(
                value.source_sample_end - value.source_sample_start,
                PCM_SAMPLE_RATE_HZ,
            )
        ):
            raise ValueError("auditory causal intake entry clocks disagree")
        for digest, name in (
            (value.sub_event_id, "sub-event"),
            (value.structural_fingerprint, "structural fingerprint"),
            (value.terminal_authority_receipt_sha256, "terminal receipt"),
            (value.l5_authority_receipt_sha256, "L5 receipt"),
        ):
            sha256_digest(digest, f"auditory causal intake {name}")

    def verify_intake(
        self, value: AuditoryBatchCausalIntakeReceipt
    ) -> None:
        if not isinstance(value, AuditoryBatchCausalIntakeReceipt):
            raise TypeError("auditory causal intake receipt is untyped")
        _identifier(value.assembly_id, "auditory causal intake assembly")
        _identifier(value.stream_id, "auditory causal intake stream")
        require_fraction(value.source_time_start, "intake source start")
        require_fraction(value.source_time_end, "intake source end")
        if value.source_time_end <= value.source_time_start:
            raise ValueError("auditory causal intake interval changed")
        for digest, name in (
            (value.intake_id, "identity"),
            (value.advance_authority_receipt_sha256, "advance receipt"),
            (value.batch_authority_receipt_sha256, "batch receipt"),
            (value.token_sequence_id, "token sequence"),
            (value.token_sequence_authority_hmac_sha256, "sequence HMAC"),
            (
                value.joint_settlement_authority_receipt_sha256,
                "joint settlement receipt",
            ),
            (
                value.causal_settlement_authority_receipt_sha256,
                "causal settlement receipt",
            ),
            (value.authority_hmac_sha256, "authority HMAC"),
        ):
            sha256_digest(digest, f"auditory causal intake {name}")
        if not value.entries:
            raise ValueError("auditory causal intake has no entries")
        prior: AuditoryBatchCausalEntryLink | None = None
        for ordinal, entry in enumerate(value.entries):
            self._verify_entry(entry)
            if entry.ordinal != ordinal:
                raise ValueError("auditory causal intake order changed")
            if prior is not None and (
                entry.source_sample_start < prior.source_sample_end
                or entry.source_time_start < prior.source_time_end
            ):
                raise ValueError("auditory causal intake physical order changed")
            prior = entry
        payload = value.payload()
        if len(_canonical(value.as_record())) > MAX_INTAKE_BYTES:
            raise ValueError("auditory causal intake exceeds its byte boundary")
        if value.intake_id != _digest(payload):
            raise ValueError("auditory causal intake identity changed")
        if not hmac.compare_digest(
            value.authority_hmac_sha256,
            _sign(self._intake_key, payload),
        ):
            raise ValueError("auditory causal intake authority changed")

    def verify_for_episode(
        self,
        *,
        intake: AuditoryBatchCausalIntakeReceipt,
        sequence: AuditoryTokenSequenceReceipt,
        settlement: CausalExperienceSettlement,
    ) -> None:
        self.verify_intake(intake)
        if not isinstance(sequence, AuditoryTokenSequenceReceipt):
            raise TypeError("auditory causal episode sequence is untyped")
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("auditory causal episode settlement is untyped")
        if (
            intake.token_sequence_id != sequence.sequence_id
            or intake.token_sequence_authority_hmac_sha256
            != sequence.authority_hmac_sha256
            or intake.causal_settlement_authority_receipt_sha256
            != settlement.authority_receipt_sha256
            or intake.assembly_id != settlement.assembly_id
            or intake.stream_id != sequence.stream_id
            or intake.source_time_start != settlement.source_time_start
            or intake.source_time_end != settlement.source_time_end
            or len(intake.entries) != len(sequence.occurrences)
        ):
            raise ValueError("auditory causal intake names another episode")
        for link, occurrence in zip(
            intake.entries, sequence.occurrences, strict=True
        ):
            if (
                link.ordinal != occurrence.ordinal
                or link.sub_event_id != occurrence.sub_event_id
                or link.source_sample_start
                != occurrence.source_sample_start
                or link.source_sample_end != occurrence.source_sample_end
                or link.source_time_start != occurrence.source_time_start
                or link.source_time_end != occurrence.source_time_end
                or link.structural_fingerprint
                != occurrence.structural_fingerprint
                or link.terminal_authority_receipt_sha256
                != occurrence.terminal_authority_receipt_sha256
                or link.l5_authority_receipt_sha256
                != occurrence.l5_authority_receipt_sha256
            ):
                raise ValueError(
                    "auditory causal intake occurrence link changed"
                )

    def bind(
        self,
        *,
        registry: AuditoryIncrementalTerminalRegistry,
        claim: AuditoryIncrementalTerminalBatchClaim,
        advance: AuditoryIncrementalAdvance,
        token_authority: AuditoryTokenSequenceAuthority,
        sequence: AuditoryTokenSequenceReceipt,
        joint_settlement: AuditoryStreamSettlementReceipt,
        causal_settlement: CausalExperienceSettlement,
    ) -> AuditoryBatchCausalIntakeAdmission:
        if not isinstance(registry, AuditoryIncrementalTerminalRegistry):
            raise TypeError("auditory causal intake requires terminal registry")
        if not isinstance(claim, AuditoryIncrementalTerminalBatchClaim):
            raise TypeError("auditory causal intake requires a live batch claim")
        if not isinstance(advance, AuditoryIncrementalAdvance):
            raise TypeError("auditory causal intake requires an advance")
        if not isinstance(token_authority, AuditoryTokenSequenceAuthority):
            raise TypeError("auditory causal intake requires token authority")
        if not isinstance(sequence, AuditoryTokenSequenceReceipt):
            raise TypeError("auditory causal intake requires a token sequence")
        if not isinstance(joint_settlement, AuditoryStreamSettlementReceipt):
            raise TypeError("auditory causal intake requires a joint settlement")
        if not isinstance(causal_settlement, CausalExperienceSettlement):
            raise TypeError("auditory causal intake requires a causal settlement")

        batch = registry.verify_batch_claim(claim)
        advance.verify()
        token_authority.verify_sequence(sequence)
        joint_settlement.verify()
        causal_settlement.verify()
        if batch.advance_authority_receipt_sha256 != advance.authority_receipt_sha256:
            raise ValueError("auditory causal batch names another advance")
        if tuple(value.event for value in batch.entries) != advance.released_terminals:
            raise ValueError("auditory causal advance release changed")
        if (
            joint_settlement.stream_id != sequence.stream_id
            or any(
                entry.event.stream_id != sequence.stream_id
                for entry in batch.entries
            )
        ):
            raise ValueError("auditory causal intake crosses stream epochs")
        if (
            joint_settlement.assembly_id != causal_settlement.assembly_id
            or joint_settlement.causal_settlement_authority_receipt_sha256
            != causal_settlement.authority_receipt_sha256
            or joint_settlement.source_time_start
            != causal_settlement.source_time_start
            or joint_settlement.source_time_end
            != causal_settlement.source_time_end
        ):
            raise ValueError("auditory causal joint settlement changed")
        if len(batch.entries) != len(sequence.occurrences):
            raise ValueError("auditory causal intake cardinality changed")

        links = []
        evidence_receipts: set[str] = set()
        for ordinal, (entry, occurrence) in enumerate(
            zip(batch.entries, sequence.occurrences, strict=True)
        ):
            event = entry.event
            auditory_l5 = entry.auditory_l5
            expected_sub_event_id = _digest({
                "l5_authority_receipt_sha256": (
                    auditory_l5.authority_receipt_sha256
                ),
                "source_sample_end": event.source_sample_end,
                "source_sample_start": event.source_sample_start,
                "stream_id": event.stream_id,
                "structural_fingerprint": event.structural_fingerprint,
                "terminal_authority_receipt_sha256": (
                    event.authority_receipt_sha256
                ),
            })
            evidence_receipts.update(event.joint_settlement_receipt_sha256s)
            if (
                joint_settlement.authority_receipt_sha256
                not in event.joint_settlement_receipt_sha256s
            ):
                raise ValueError(
                    "auditory terminal lacks current joint settlement evidence"
                )
            if (
                occurrence.ordinal != ordinal
                or occurrence.sub_event_id != expected_sub_event_id
                or occurrence.source_sample_start != event.source_sample_start
                or occurrence.source_sample_end != event.source_sample_end
                or occurrence.source_time_start
                != auditory_l5.source_time_start
                or occurrence.source_time_end != auditory_l5.source_time_end
                or occurrence.structural_fingerprint
                != event.structural_fingerprint
                or occurrence.terminal_authority_receipt_sha256
                != event.authority_receipt_sha256
                or occurrence.l5_authority_receipt_sha256
                != auditory_l5.authority_receipt_sha256
            ):
                raise ValueError(
                    "auditory causal batch and token occurrence disagree"
                )
            links.append(AuditoryBatchCausalEntryLink(
                ordinal=ordinal,
                sub_event_id=occurrence.sub_event_id,
                source_sample_start=occurrence.source_sample_start,
                source_sample_end=occurrence.source_sample_end,
                source_time_start=occurrence.source_time_start,
                source_time_end=occurrence.source_time_end,
                structural_fingerprint=occurrence.structural_fingerprint,
                terminal_authority_receipt_sha256=(
                    occurrence.terminal_authority_receipt_sha256
                ),
                l5_authority_receipt_sha256=(
                    occurrence.l5_authority_receipt_sha256
                ),
            ))

        if any(
            link.source_time_start < causal_settlement.source_time_start
            or link.source_time_end > causal_settlement.source_time_end
            for link in links
        ):
            reason = (
                "multi_settlement_window_required"
                if len(evidence_receipts) > 1
                else "current_causal_window_incomplete"
            )
            return AuditoryBatchCausalIntakeAdmission(
                state="unknown", reason=reason, intake=None
            )

        immutable_links = tuple(links)
        payload = _intake_payload(
            advance_authority_receipt_sha256=(
                advance.authority_receipt_sha256
            ),
            batch_authority_receipt_sha256=(
                batch.authority_receipt_sha256
            ),
            token_sequence_id=sequence.sequence_id,
            token_sequence_authority_hmac_sha256=(
                sequence.authority_hmac_sha256
            ),
            joint_settlement_authority_receipt_sha256=(
                joint_settlement.authority_receipt_sha256
            ),
            causal_settlement_authority_receipt_sha256=(
                causal_settlement.authority_receipt_sha256
            ),
            assembly_id=causal_settlement.assembly_id,
            stream_id=sequence.stream_id,
            source_time_start=causal_settlement.source_time_start,
            source_time_end=causal_settlement.source_time_end,
            entries=immutable_links,
        )
        intake = AuditoryBatchCausalIntakeReceipt(
            intake_id=_digest(payload),
            advance_authority_receipt_sha256=(
                advance.authority_receipt_sha256
            ),
            batch_authority_receipt_sha256=(
                batch.authority_receipt_sha256
            ),
            token_sequence_id=sequence.sequence_id,
            token_sequence_authority_hmac_sha256=(
                sequence.authority_hmac_sha256
            ),
            joint_settlement_authority_receipt_sha256=(
                joint_settlement.authority_receipt_sha256
            ),
            causal_settlement_authority_receipt_sha256=(
                causal_settlement.authority_receipt_sha256
            ),
            assembly_id=causal_settlement.assembly_id,
            stream_id=sequence.stream_id,
            source_time_start=causal_settlement.source_time_start,
            source_time_end=causal_settlement.source_time_end,
            entries=immutable_links,
            authority_hmac_sha256=_sign(self._intake_key, payload),
        )
        self.verify_for_episode(
            intake=intake,
            sequence=sequence,
            settlement=causal_settlement,
        )
        return AuditoryBatchCausalIntakeAdmission(
            state="unique", reason="causal_intake_authenticated", intake=intake
        )


__all__ = (
    "AUDITORY_BATCH_CAUSAL_INTAKE_SCHEMA",
    "AuditoryBatchCausalEntryLink",
    "AuditoryBatchCausalIntakeAdmission",
    "AuditoryBatchCausalIntakeAuthority",
    "AuditoryBatchCausalIntakeReceipt",
)
