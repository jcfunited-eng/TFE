from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.substrate.causal_inquiry_tutor_authority import (
    CausalInquiryTutorAuthorizationAuthority,
    CausalInquiryTutorAuthorizationReceipt,
)


KEY = b"focused-external-inquiry-tutor-authority-key"
FOREIGN_KEY = b"foreign-external-inquiry-tutor-authority-key"
NEED = "1" * 64
OBSERVATION = "2" * 64
PROGRAM = "3" * 64
NONCE = b"\x04" * 32


def test_external_receipt_is_exact_label_free_and_verification_only():
    issuer = CausalInquiryTutorAuthorizationAuthority(
        authority_key=KEY
    )
    receipt = issuer.issue(
        need_receipt_sha256=NEED,
        world_observation_receipt_sha256=OBSERVATION,
        program_id=PROGRAM,
        nonce=NONCE,
    )
    verifier = issuer.verifier()
    verifier.verify(receipt)

    assert not hasattr(verifier, "issue")
    assert CausalInquiryTutorAuthorizationReceipt.from_record(
        receipt.record()
    ) == receipt
    assert set(receipt.payload()) == {
        "authorization_id",
        "need_receipt_sha256",
        "nonce_sha256",
        "program_id",
        "schema",
        "world_observation_receipt_sha256",
    }
    lowered = repr(receipt.record()).lower()
    for forbidden in (
        "tutor_id",
        "tutor_label",
        "word",
        "meaning",
        "label",
        "chi",
        "recognition",
    ):
        assert forbidden not in lowered


def test_foreign_tampered_and_malformed_authorizations_fail_closed():
    issuer = CausalInquiryTutorAuthorizationAuthority(
        authority_key=KEY
    )
    verifier = issuer.verifier()
    receipt = issuer.issue(
        need_receipt_sha256=NEED,
        world_observation_receipt_sha256=OBSERVATION,
        program_id=PROGRAM,
        nonce=NONCE,
    )
    foreign = CausalInquiryTutorAuthorizationAuthority(
        authority_key=FOREIGN_KEY
    ).issue(
        need_receipt_sha256=NEED,
        world_observation_receipt_sha256=OBSERVATION,
        program_id=PROGRAM,
        nonce=NONCE,
    )

    with pytest.raises(ValueError, match="authority changed"):
        verifier.verify(foreign)
    with pytest.raises(ValueError, match="authority changed"):
        verifier.verify(replace(receipt, program_id="4" * 64))
    with pytest.raises(ValueError, match="record changed"):
        CausalInquiryTutorAuthorizationReceipt.from_record({
            **receipt.record(),
            "tutor_label": "forbidden",
        })
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        issuer.issue(
            need_receipt_sha256=NEED,
            world_observation_receipt_sha256=OBSERVATION,
            program_id=PROGRAM,
            nonce=b"short",
        )
