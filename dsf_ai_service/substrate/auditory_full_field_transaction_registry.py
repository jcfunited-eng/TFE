"""Slim bounded authority for exact auditory full-field transactions.

This registry retains only physical continuity, the complete receptor event,
the already-prepared six-sense causal settlement, and request-local claims.
It contains no label, word, fingerprint, candidate, learned cell, score,
reciprocity branch, or recognition decision.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Callable

from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorFullFieldEvent,
    AuditoryVerifiedReceptorEventCapability,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryVerifiedSettlementCapability,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


AUDITORY_FULL_FIELD_TRANSACTION_SCHEMA = (
    "guala.auditory.full_field_transaction.v1"
)
AUDITORY_FULL_FIELD_CLAIM_SCHEMA = (
    "guala.auditory.full_field_transaction_claim.v1"
)
_CLAIM_AUTHORITY = object()


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


@dataclass(frozen=True, slots=True)
class AuditoryFullFieldTransaction:
    stream_id: str
    sequence: int
    full_field_event: AuditoryReceptorFullFieldEvent
    stream_settlement: AuditoryStreamSettlementReceipt
    prepared_causal_settlement: CausalExperienceSettlement
    transaction_id: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "full_field_event_receipt_sha256": (
                self.full_field_event.authority_receipt_sha256
            ),
            "prepared_causal_settlement_receipt_sha256": (
                self.prepared_causal_settlement.authority_receipt_sha256
            ),
            "schema": AUDITORY_FULL_FIELD_TRANSACTION_SCHEMA,
            "sequence": self.sequence,
            "stream_id": self.stream_id,
            "stream_settlement_receipt_sha256": (
                self.stream_settlement.authority_receipt_sha256
            ),
            "transaction_id": self.transaction_id,
        }

    def verify(self) -> None:
        self.full_field_event.verify()
        self.stream_settlement.verify()
        self.prepared_causal_settlement.verify()
        self._verify_receipt_linkage()

    def _verify_receipt_linkage(self) -> None:
        if (
            not isinstance(self.stream_id, str)
            or not self.stream_id
            or isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
            or self.stream_id != self.stream_settlement.stream_id
            or self.sequence != self.stream_settlement.sequence
            or self.full_field_event.auditory_l5_authority_receipt_sha256
            != self.stream_settlement.auditory_l5_authority_receipt_sha256
            or self.prepared_causal_settlement.assembly_id
            != self.stream_settlement.assembly_id
            or self.prepared_causal_settlement.source_time_start
            != self.stream_settlement.source_time_start
            or self.prepared_causal_settlement.source_time_end
            != self.stream_settlement.source_time_end
            or self.prepared_causal_settlement.authority_receipt_sha256
            != (
                self.stream_settlement
                .causal_settlement_authority_receipt_sha256
            )
        ):
            raise ValueError("auditory full-field transaction linkage changed")
        sha256_digest(self.transaction_id, "auditory transaction identity")
        sha256_digest(
            self.authority_receipt_sha256,
            "auditory transaction authority",
        )
        expected_id = _digest({
            "full_field_event_receipt_sha256": (
                self.full_field_event.authority_receipt_sha256
            ),
            "stream_settlement_receipt_sha256": (
                self.stream_settlement.authority_receipt_sha256
            ),
        })
        if (
            self.transaction_id != expected_id
            or _digest(self.payload()) != self.authority_receipt_sha256
        ):
            raise ValueError("auditory full-field transaction receipt changed")


@dataclass(frozen=True, slots=True)
class AuditoryFullFieldTransactionClaim:
    claim_id: str
    transaction: AuditoryFullFieldTransaction
    authority_receipt_sha256: str
    _construction_authority: object

    def payload(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "schema": AUDITORY_FULL_FIELD_CLAIM_SCHEMA,
            "transaction_authority_receipt_sha256": (
                self.transaction.authority_receipt_sha256
            ),
            "transaction_id": self.transaction.transaction_id,
        }

    def verify(self) -> None:
        if self._construction_authority is not _CLAIM_AUTHORITY:
            raise ValueError("auditory full-field claim lacks live authority")
        self.transaction.verify()
        sha256_digest(self.claim_id, "auditory transaction claim identity")
        sha256_digest(
            self.authority_receipt_sha256,
            "auditory transaction claim",
        )
        if (
            self.claim_id != _digest({
                "claim_for": self.transaction.authority_receipt_sha256,
            })
            or _digest(self.payload()) != self.authority_receipt_sha256
        ):
            raise ValueError("auditory full-field claim receipt changed")


class AuditoryFullFieldTransactionRegistry:
    """Finite transactional custody without an auditory classifier."""

    def __init__(
        self,
        *,
        max_streams: int,
        max_pending_per_stream: int,
        max_claims: int,
        log_event: Callable[..., None] | None = None,
    ) -> None:
        for value, name in (
            (max_streams, "streams"),
            (max_pending_per_stream, "pending transactions"),
            (max_claims, "claims"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"auditory transaction {name} must be positive")
        self._max_streams = max_streams
        self._max_pending_per_stream = max_pending_per_stream
        self._max_claims = max_claims
        self._pending: OrderedDict[
            str,
            list[AuditoryFullFieldTransaction],
        ] = OrderedDict()
        self._last_committed: OrderedDict[
            str,
            AuditoryStreamSettlementReceipt,
        ] = OrderedDict()
        self._claims: dict[str, AuditoryFullFieldTransactionClaim] = {}
        self._claim_by_transaction: dict[str, str] = {}
        self._committed = 0
        self._discarded = 0
        self._rolled_back_claims = 0
        self._log_event = log_event
        self._lock = threading.RLock()

    def stage(
        self,
        *,
        full_field_event: AuditoryReceptorFullFieldEvent,
        stream_settlement: AuditoryStreamSettlementReceipt,
        prepared_causal_settlement: CausalExperienceSettlement,
        verified_receptor_capability: (
            AuditoryVerifiedReceptorEventCapability | None
        ) = None,
        verified_settlement_capability: (
            AuditoryVerifiedSettlementCapability | None
        ) = None,
    ) -> AuditoryFullFieldTransaction:
        if not isinstance(full_field_event, AuditoryReceptorFullFieldEvent):
            raise TypeError("auditory transaction requires a receptor event")
        if not isinstance(stream_settlement, AuditoryStreamSettlementReceipt):
            raise TypeError("auditory transaction requires stream settlement")
        if not isinstance(
            prepared_causal_settlement,
            CausalExperienceSettlement,
        ):
            raise TypeError("auditory transaction requires causal settlement")
        transaction_id = _digest({
            "full_field_event_receipt_sha256": (
                full_field_event.authority_receipt_sha256
            ),
            "stream_settlement_receipt_sha256": (
                stream_settlement.authority_receipt_sha256
            ),
        })
        provisional = AuditoryFullFieldTransaction(
            stream_id=stream_settlement.stream_id,
            sequence=stream_settlement.sequence,
            full_field_event=full_field_event,
            stream_settlement=stream_settlement,
            prepared_causal_settlement=prepared_causal_settlement,
            transaction_id=transaction_id,
            authority_receipt_sha256="0" * 64,
        )
        transaction = replace(
            provisional,
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        if (
            verified_receptor_capability is None
            and verified_settlement_capability is None
        ):
            transaction.verify()
        elif (
            isinstance(
                verified_receptor_capability,
                AuditoryVerifiedReceptorEventCapability,
            )
            and isinstance(
                verified_settlement_capability,
                AuditoryVerifiedSettlementCapability,
            )
        ):
            verified_receptor_capability.verify_identity(
                full_field_event
            )
            verified_settlement_capability.verify_linkage(
                pcm_s16le=verified_settlement_capability.pcm_s16le,
                capture=verified_settlement_capability.capture,
                auditory_l5=verified_settlement_capability.auditory_l5,
                transport=verified_settlement_capability.transport,
                cochlear=verified_settlement_capability.cochlear,
                causal_settlement=prepared_causal_settlement,
                joint_settlement=stream_settlement,
            )
            transaction._verify_receipt_linkage()
        else:
            raise ValueError(
                "auditory transaction verified custody is incomplete"
            )
        with self._lock:
            stream_id = transaction.stream_id
            pending = self._pending.get(stream_id)
            prior = (
                pending[-1].stream_settlement
                if pending
                else self._last_committed.get(stream_id)
            )
            self._verify_continuity(transaction.stream_settlement, prior)
            if pending is None:
                if (
                    stream_id not in self._last_committed
                    and len(
                        set(self._pending).union(self._last_committed)
                    )
                    >= self._max_streams
                ):
                    raise RuntimeError(
                        "auditory transaction stream capacity exhausted"
                    )
                pending = []
                self._pending[stream_id] = pending
            if len(pending) >= self._max_pending_per_stream:
                raise RuntimeError(
                    "auditory pending transaction capacity exhausted"
                )
            if any(
                value.transaction_id == transaction.transaction_id
                for values in self._pending.values()
                for value in values
            ):
                raise ValueError("auditory transaction is duplicated")
            pending.append(transaction)
            self._pending.move_to_end(stream_id)
        return transaction

    @staticmethod
    def _verify_continuity(
        current: AuditoryStreamSettlementReceipt,
        prior: AuditoryStreamSettlementReceipt | None,
    ) -> None:
        if prior is None:
            if current.sequence != 0:
                raise ValueError(
                    "auditory transaction begins without sequence zero"
                )
            return
        if (
            current.sequence != prior.sequence + 1
            or current.first_sample_index
            != prior.first_sample_index + prior.sample_count
            or current.source_time_start != prior.source_time_end
            or current.prior_transport_receipt_sha256
            != prior.transport_receipt_sha256
            or current.prior_cochlear_state_receipt_sha256
            != prior.cochlear_receipt_sha256
        ):
            raise ValueError("auditory transaction continuity changed")

    def claim(
        self,
        transaction: AuditoryFullFieldTransaction,
    ) -> AuditoryFullFieldTransactionClaim:
        if not isinstance(transaction, AuditoryFullFieldTransaction):
            raise TypeError("auditory transaction claim requires transaction")
        with self._lock:
            mounted = self._mounted_transaction(transaction.transaction_id)
            if mounted is not transaction:
                raise ValueError("auditory transaction left registry custody")
            if transaction.transaction_id in self._claim_by_transaction:
                raise ValueError("auditory transaction is already claimed")
            if len(self._claims) >= self._max_claims:
                raise RuntimeError("auditory transaction claim capacity exhausted")
            claim_id = _digest({"claim_for": transaction.authority_receipt_sha256})
            provisional = AuditoryFullFieldTransactionClaim(
                claim_id=claim_id,
                transaction=transaction,
                authority_receipt_sha256="0" * 64,
                _construction_authority=_CLAIM_AUTHORITY,
            )
            claim = replace(
                provisional,
                authority_receipt_sha256=_digest(provisional.payload()),
            )
            self._claims[claim_id] = claim
            self._claim_by_transaction[transaction.transaction_id] = claim_id
            return claim

    def _mounted_transaction(
        self,
        transaction_id: str,
    ) -> AuditoryFullFieldTransaction | None:
        return next(
            (
                value
                for values in self._pending.values()
                for value in values
                if value.transaction_id == transaction_id
            ),
            None,
        )

    def verify_claim(
        self,
        claim: AuditoryFullFieldTransactionClaim,
    ) -> AuditoryFullFieldTransaction:
        if not isinstance(claim, AuditoryFullFieldTransactionClaim):
            raise TypeError("auditory transaction claim is not typed")
        with self._lock:
            if self._claims.get(claim.claim_id) is not claim:
                raise ValueError("auditory transaction claim is not live")
            if (
                self._mounted_transaction(
                    claim.transaction.transaction_id
                )
                is not claim.transaction
            ):
                raise ValueError("claimed auditory transaction left custody")
            return claim.transaction

    def full_field_from_claim(
        self,
        claim: AuditoryFullFieldTransactionClaim,
    ) -> AuditoryReceptorFullFieldEvent:
        return self.verify_claim(claim).full_field_event

    def prepared_settlement_from_claim(
        self,
        claim: AuditoryFullFieldTransactionClaim,
    ) -> CausalExperienceSettlement:
        return self.verify_claim(claim).prepared_causal_settlement

    def complete_claim(
        self,
        claim: AuditoryFullFieldTransactionClaim,
        *,
        commit_settlement: Callable[[], None],
    ) -> None:
        transaction = self.verify_claim(claim)
        if not callable(commit_settlement):
            raise TypeError("auditory transaction commit callback is required")
        with self._lock:
            pending = self._pending[transaction.stream_id]
            if not pending or pending[0] is not transaction:
                raise ValueError(
                    "auditory transactions must commit in causal order"
                )
            commit_settlement()
            pending.pop(0)
            if not pending:
                del self._pending[transaction.stream_id]
            self._last_committed[transaction.stream_id] = (
                transaction.stream_settlement
            )
            self._last_committed.move_to_end(transaction.stream_id)
            self._release_claim(claim)
            self._committed += 1
        if self._log_event is not None:
            self._log_event(
                "auditory_full_field_transaction_committed",
                stream_id=transaction.stream_id,
                sequence=transaction.sequence,
                transaction_id=transaction.transaction_id,
            )

    def rollback_claim(
        self,
        claim: AuditoryFullFieldTransactionClaim,
    ) -> None:
        self.verify_claim(claim)
        with self._lock:
            self._release_claim(claim)
            self._rolled_back_claims += 1

    def _release_claim(
        self,
        claim: AuditoryFullFieldTransactionClaim,
    ) -> None:
        del self._claims[claim.claim_id]
        del self._claim_by_transaction[claim.transaction.transaction_id]

    def discard(
        self,
        transaction: AuditoryFullFieldTransaction,
    ) -> None:
        if not isinstance(transaction, AuditoryFullFieldTransaction):
            raise TypeError("auditory discard requires transaction")
        with self._lock:
            mounted = self._mounted_transaction(transaction.transaction_id)
            if mounted is not transaction:
                raise ValueError("auditory transaction is not pending")
            if transaction.transaction_id in self._claim_by_transaction:
                raise ValueError("claimed auditory transaction cannot be discarded")
            pending = self._pending[transaction.stream_id]
            if pending[-1] is not transaction:
                raise ValueError(
                    "only the latest auditory transaction may be discarded"
                )
            pending.pop()
            if not pending:
                del self._pending[transaction.stream_id]
            self._discarded += 1

    def close_stream(self, stream_id: str) -> int:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("auditory transaction stream id is required")
        with self._lock:
            pending = self._pending.get(stream_id, ())
            if any(
                value.transaction_id in self._claim_by_transaction
                for value in pending
            ):
                raise ValueError(
                    "auditory stream has live transaction claims"
                )
            removed = len(pending)
            self._pending.pop(stream_id, None)
            self._last_committed.pop(stream_id, None)
            self._discarded += removed
            return removed

    def authority_counts(self) -> dict[str, int]:
        with self._lock:
            return {
                "in_flight_full_field_claims": len(self._claims),
                "pending_full_field_transactions": sum(
                    len(value) for value in self._pending.values()
                ),
            }

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "active_claims": len(self._claims),
                "active_streams": len(
                    set(self._pending).union(self._last_committed)
                ),
                "committed": self._committed,
                "discarded": self._discarded,
                "max_claims": self._max_claims,
                "max_pending_per_stream": self._max_pending_per_stream,
                "max_streams": self._max_streams,
                "pending_transactions": sum(
                    len(value) for value in self._pending.values()
                ),
                "rolled_back_claims": self._rolled_back_claims,
                "schema": "guala.auditory.full_field_transaction_status.v1",
                "semantic_authority": False,
                "transcript_authority": False,
            }


__all__ = (
    "AUDITORY_FULL_FIELD_CLAIM_SCHEMA",
    "AUDITORY_FULL_FIELD_TRANSACTION_SCHEMA",
    "AuditoryFullFieldTransaction",
    "AuditoryFullFieldTransactionClaim",
    "AuditoryFullFieldTransactionRegistry",
)
