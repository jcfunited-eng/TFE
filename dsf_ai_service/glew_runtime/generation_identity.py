"""Unified generation identity binding over three independent GLEW checkpoints.

Step 4 of
``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
(sections 9.5 and 12) requires "production persistence for learned bindings
and recall episodes under one new generation identity."  A prior
investigation found three real, independently tested, and mutually unaware
checkpoint mechanisms in this repository:

* ``genesis.py`` -- ``create_clean_genesis`` / ``restore_clean_genesis``.
  Identity is an RFC 4122 UUIDv4 ``identity`` string, a deterministic
  ``generation_uuid`` derived from ``identity`` plus the exact executable
  profile digest, and an integer ``tick`` that ``restore_clean_genesis``
  hard-rejects unless it is exactly zero.
* ``expression_learning.py`` -- ``learned_binding_checkpoint_payload`` /
  ``restore_learned_binding_checkpoint``.  A bespoke HMAC-SHA256 envelope
  keyed only by its own ``checkpoint_id`` / ``key_id`` -- no UUID, no tick,
  no reference to genesis.
* ``recall_story_episode_archive.py`` -- ``recall_story_archive_checkpoint_payload``
  / ``restore_recall_story_archive_checkpoint``.  The same bespoke
  HMAC-SHA256 envelope pattern, again keyed only by its own
  ``checkpoint_id`` / ``key_id`` -- no UUID, no tick, no reference to the
  other two.

None of the three mechanisms references any of the others, and this module
does not change that: each of the three checkpoint mechanisms remains
independently valid, independently restorable, and independently tested
exactly as it is today.  This module only *composes* the three
already-verified identifiers into one additional, real, content-addressed
receipt -- :class:`GenerationIdentityBinding` -- that answers the concrete
production question "did I just restore genesis generation A's topology
alongside a learning checkpoint (or recall archive) that actually belongs to
generation B?"  :func:`verify_generation_identity_binding` raises the moment
any one of the three restored identifiers disagrees with what was originally
bound.

Honesty note on genesis's ``tick`` (Step 4 handoff item 4): the ``tick``
this module records and compares is the
``dsf_ai_service.substrate.immutable_generation_store`` checkpoint-revision
counter that ``create_clean_genesis`` / ``restore_clean_genesis`` thread
through unchanged.  It is a birth-certificate revision number for the
immutable, empty-topology clean-genesis artifact -- today it is
contractually always ``0``, because ``restore_clean_genesis`` hard-rejects
any other value and a clean genesis is, by the contract in ``genesis.py``'s
own module docstring, never re-committed.  That is a *different* concept
from GLEW's own physical/structural time (the genesis payload's own
``structural_time`` -> ``gate_count``), and it is a *third*, unrelated
concept from whatever turn-progression counter a live, learning-and-recalling
generation will eventually need.  As of this investigation, neither
``mount_six_lane_runtime`` (``six_lane_runtime_mount.py``) nor
``story_chemistry.py`` (the "six-lane runtime" Step 3 built) has any tick,
revision, or generation-progression concept of its own at all.  There is
therefore nothing on that side to unify genesis's tick with yet: this module
records and compares genesis's tick honestly (as evidence that the same
immutable genesis revision was restored), but it does not attempt to
reconcile "genesis tick" with a "six-lane runtime tick" -- that
reconciliation is deferred, not because it is difficult, but because one
side of it does not exist yet.  See the accompanying implementation report
for the full reasoning.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from .model import ReceiptError, receipt_sha256, require_identifier, sha256_digest


GENERATION_IDENTITY_BINDING_SCHEMA = "glew.identity.generation_binding.v1"


def _canonical_json(value: Any) -> bytes:
    """Canonicalize exactly as ``genesis.py``'s own ``_canonical_json`` does.

    Genesis is the "outermost" identity in this composition (its identity and
    generation_uuid are the anchor the learning and archive checkpoints are
    bound to), so this receipt uses genesis's own two-space-indented,
    trailing-newline, ``sort_keys``, non-ASCII-preserving canonicalization
    style rather than either of the other two modules' compact
    ``separators=(",", ":")`` style.
    """

    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ReceiptError(
            f"generation identity binding value is not canonical JSON: {error}"
        ) from error


def _validate_genesis_identity(value: str) -> str:
    require_identifier(value, "bound genesis identity")
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError) as error:
        raise ReceiptError(
            "bound genesis identity is not a canonical UUID"
        ) from error
    if str(parsed) != value or parsed.version != 4:
        raise ReceiptError("bound genesis identity is not a canonical UUIDv4")
    return value


def _validate_genesis_generation_uuid(value: str) -> str:
    require_identifier(value, "bound genesis generation_uuid")
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError) as error:
        raise ReceiptError(
            "bound genesis generation_uuid is not a canonical UUID"
        ) from error
    # Note: genesis.py's own deterministic generation_uuid
    # (``_deterministic_generation_uuid``) forces the RFC-4122 variant bits
    # but sets the version nibble to 8, not 4 -- it is a content-derived
    # (version-8) UUID, not a UUIDv4.  ``restore_clean_genesis`` itself never
    # checks the generation_uuid's version, only that it is byte-identical to
    # the recomputed identity-derived value.  Enforcing version 4 here would
    # therefore reject every real genesis_generation_uuid this codebase has
    # ever produced, so only canonical-string form is required.
    if str(parsed) != value:
        raise ReceiptError("bound genesis generation_uuid is not canonical")
    return value


def _validate_genesis_tick(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReceiptError("bound genesis tick must be an integer")
    if value < 0:
        raise ReceiptError("bound genesis tick cannot be negative")
    return value


def generation_identity_binding_receipt_payload(
    *,
    genesis_identity: str,
    genesis_generation_uuid: str,
    genesis_tick: int,
    learning_checkpoint_id: str,
    archive_checkpoint_id: str,
) -> bytes:
    """Exact canonical bytes bound by one :class:`GenerationIdentityBinding`."""

    _validate_genesis_identity(genesis_identity)
    _validate_genesis_generation_uuid(genesis_generation_uuid)
    _validate_genesis_tick(genesis_tick)
    require_identifier(learning_checkpoint_id, "bound learning checkpoint id")
    require_identifier(archive_checkpoint_id, "bound archive checkpoint id")
    return _canonical_json(
        {
            "archive_checkpoint_id": archive_checkpoint_id,
            "genesis_generation_uuid": genesis_generation_uuid,
            "genesis_identity": genesis_identity,
            "genesis_tick": genesis_tick,
            "learning_checkpoint_id": learning_checkpoint_id,
            "schema": GENERATION_IDENTITY_BINDING_SCHEMA,
        }
    )


@dataclass(frozen=True, slots=True)
class GenerationIdentityBinding:
    """One receipted binding of a genesis identity to two sibling checkpoints.

    This does not own, restore, or duplicate any of the three underlying
    mechanisms' own state.  It only records their already-verified
    identifiers and content-addresses that record so a later restart can
    detect a mismatched combination.
    """

    genesis_identity: str
    genesis_generation_uuid: str
    genesis_tick: int
    learning_checkpoint_id: str
    archive_checkpoint_id: str
    receipt_sha256: str
    receipt_payload: bytes

    def payload(self) -> bytes:
        return generation_identity_binding_receipt_payload(
            genesis_identity=self.genesis_identity,
            genesis_generation_uuid=self.genesis_generation_uuid,
            genesis_tick=self.genesis_tick,
            learning_checkpoint_id=self.learning_checkpoint_id,
            archive_checkpoint_id=self.archive_checkpoint_id,
        )

    def verify(self) -> None:
        sha256_digest(self.receipt_sha256, "generation identity binding receipt")
        expected = self.payload()
        if (
            self.receipt_payload != expected
            or receipt_sha256(expected) != self.receipt_sha256
        ):
            raise ReceiptError(
                "generation identity binding differs from its exact receipt"
            )


def bind_generation_identity(
    *,
    genesis_identity: str,
    genesis_generation_uuid: str,
    genesis_tick: int,
    learning_checkpoint_id: str,
    archive_checkpoint_id: str,
) -> GenerationIdentityBinding:
    """Bind one genesis identity triple to one learning and one archive id.

    Every sub-identity is validated with the same real rule its owning
    module already enforces -- ``require_identifier`` (from ``model.py``,
    the exact helper both ``expression_learning.py`` and
    ``recall_story_episode_archive.py`` call on their own ``checkpoint_id``
    inputs) for the two checkpoint ids, and genesis's own canonical-UUID
    rules for ``genesis_identity`` / ``genesis_generation_uuid`` (see the
    module docstring for why the two UUID checks differ).  This function
    does not itself create, restore, or mutate any genesis root, learned
    state, or archive -- callers must have already produced each of the
    three identifiers through their own real, unmodified construction path.
    """

    payload = generation_identity_binding_receipt_payload(
        genesis_identity=genesis_identity,
        genesis_generation_uuid=genesis_generation_uuid,
        genesis_tick=genesis_tick,
        learning_checkpoint_id=learning_checkpoint_id,
        archive_checkpoint_id=archive_checkpoint_id,
    )
    binding = GenerationIdentityBinding(
        genesis_identity=genesis_identity,
        genesis_generation_uuid=genesis_generation_uuid,
        genesis_tick=genesis_tick,
        learning_checkpoint_id=learning_checkpoint_id,
        archive_checkpoint_id=archive_checkpoint_id,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    binding.verify()
    return binding


def verify_generation_identity_binding(
    binding: GenerationIdentityBinding,
    *,
    restored_genesis_identity: str,
    restored_genesis_generation_uuid: str,
    restored_genesis_tick: int,
    restored_learning_checkpoint_id: str,
    restored_archive_checkpoint_id: str,
) -> None:
    """Reject a restart that mixes generations.

    Raises :class:`ReceiptError` if the binding's own receipt no longer
    matches its recorded fields (a tampered binding), or if any one of the
    five identifiers actually restored from the three independent mechanisms
    differs from what this binding originally recorded.  A caller that
    restored genesis generation A's topology alongside a learning checkpoint
    or recall archive from generation B must have this raise before that
    combination is trusted.
    """

    if not isinstance(binding, GenerationIdentityBinding):
        raise ReceiptError(
            "generation identity verification requires a real generation "
            "identity binding"
        )
    binding.verify()
    if binding.genesis_identity != restored_genesis_identity:
        raise ReceiptError(
            "restored genesis identity does not match the bound generation "
            "identity"
        )
    if binding.genesis_generation_uuid != restored_genesis_generation_uuid:
        raise ReceiptError(
            "restored genesis generation_uuid does not match the bound "
            "generation identity"
        )
    if binding.genesis_tick != restored_genesis_tick:
        raise ReceiptError(
            "restored genesis tick does not match the bound generation "
            "identity"
        )
    if binding.learning_checkpoint_id != restored_learning_checkpoint_id:
        raise ReceiptError(
            "restored learning checkpoint id does not match the bound "
            "generation identity"
        )
    if binding.archive_checkpoint_id != restored_archive_checkpoint_id:
        raise ReceiptError(
            "restored archive checkpoint id does not match the bound "
            "generation identity"
        )


__all__ = [
    "GENERATION_IDENTITY_BINDING_SCHEMA",
    "GenerationIdentityBinding",
    "bind_generation_identity",
    "generation_identity_binding_receipt_payload",
    "verify_generation_identity_binding",
]
