from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import math
import struct
import wave

import pytest

from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


_API_KEY = "production-test-auditory-authority-key"


def _tone_wav() -> bytes:
    rate = 16_000
    values = [
        int(8_000 * math.sin(2.0 * math.pi * 440.0 * index / rate))
        for index in range(rate)
    ]
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(struct.pack(f"<{len(values)}h", *values))
    return payload.getvalue()


def _mounted_experience(monkeypatch, boundary: str):
    monkeypatch.delenv("GUALALOOM_API_KEY", raising=False)
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    receipt = engine.process_sound_frame(
        _tone_wav(),
        source_anchor_ns=1_000_000_000,
        source_time_end_ns=2_000_000_000,
        auditory_event_boundary=boundary,
    )
    assert receipt["accepted"] is True
    experience = engine._latest_auditory_l5_experience
    experience.verify()
    return engine, experience


@pytest.fixture
def auditory_experience(monkeypatch):
    engine, experience = _mounted_experience(monkeypatch, "utterance")
    try:
        yield experience
    finally:
        engine.shutdown()


def _authority() -> AuditoryTutorAuthority:
    return AuditoryTutorAuthority(api_key=_API_KEY, required=True)


def _receipt(authority, experience, *, label="  hello   guala  "):
    return authority.issue(
        experience_id=experience.experience_id,
        kind="spoken_form",
        tutor_label=label,
        nonce="ab" * 32,
        issued_at_unix_ns=1_750_000_000_000_000_000,
    )


def test_receipt_binds_exact_experience_kind_canonical_label_nonce_and_time(
    auditory_experience,
) -> None:
    authority = _authority()
    receipt = _receipt(authority, auditory_experience)

    assert receipt.tutor_label == "hello guala"
    assert receipt.nonce == "ab" * 32
    assert receipt.issued_at_unix_ns == 1_750_000_000_000_000_000
    authority.verify(
        receipt.as_dict(),
        experience_id=auditory_experience.experience_id,
        kind="spoken_form",
        tutor_label="hello guala",
    )

    mutations = {
        "experience_id": "0" * 64,
        "kind": "source_continuity",
        "tutor_label": "different",
        "nonce": "cd" * 32,
        "issued_at_unix_ns": receipt.issued_at_unix_ns + 1,
    }
    for field, changed in mutations.items():
        payload = receipt.as_dict()
        payload[field] = changed
        with pytest.raises(ValueError):
            authority.verify(
                payload,
                experience_id=payload["experience_id"],
                kind=payload["kind"],
                tutor_label=payload["tutor_label"],
            )


def test_live_owner_rejects_ambient_even_with_valid_gateway_hmac(
    monkeypatch,
) -> None:
    engine, ambient = _mounted_experience(monkeypatch, "ambient")
    try:
        authority = _authority()
        owner = AuditoryReciprocityOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=authority,
        )
        receipt = _receipt(authority, ambient, label="ambient must not teach")
        with pytest.raises(ValueError, match="verified utterance boundary"):
            owner.teach(
                ambient,
                kind=AuditoryReciprocityKind.SPOKEN_FORM,
                tutor_label="ambient must not teach",
                authority_receipt=receipt,
            )
        assert owner.status()["reinforcements"]["spoken_form"] == 0
    finally:
        engine.shutdown()


def test_production_owner_requires_receipt_and_rejects_nonce_replay(
    auditory_experience,
) -> None:
    authority = _authority()
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=authority,
    )

    with pytest.raises(RuntimeError, match="requires authenticated"):
        owner.teach(
            auditory_experience,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label="hello guala",
        )

    receipt = _receipt(authority, auditory_experience)
    learned = owner.teach(
        auditory_experience,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        tutor_label="hello guala",
        authority_receipt=receipt.as_dict(),
    )
    assert learned.reinforcement_count == 1
    assert learned.authority_receipts == (receipt,)

    with pytest.raises(RuntimeError, match="nonce was already used"):
        owner.teach(
            auditory_experience,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label="hello guala",
            authority_receipt=receipt.as_dict(),
        )
    assert owner.status()["reinforcements"]["spoken_form"] == 1


def test_required_snapshot_restore_verifies_authority_and_restores_replay_guard(
    auditory_experience,
) -> None:
    authority = _authority()
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=authority,
    )
    receipt = _receipt(authority, auditory_experience)
    owner.teach(
        auditory_experience,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        tutor_label="hello guala",
        authority_receipt=receipt,
    )

    snapshot = owner.snapshot()
    learned_snapshot = snapshot["classes"][0]
    assert len(learned_snapshot["authority_receipts"]) == 1
    assert len(learned_snapshot["admission_receipts"]) == 1
    admission = learned_snapshot["admission_receipts"][0]
    assert admission["event_boundary"] == "utterance"
    l5_payload = json.loads(base64.b64decode(
        admission["l5_authority_payload_base64"], validate=True
    ))
    assert l5_payload["event_boundary"] == "utterance"
    assert l5_payload["experience_id"] == auditory_experience.experience_id

    encoded = owner.encoded_snapshot()
    restored = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=_authority(),
    )
    restored.restore_encoded(encoded)
    assert restored.status()["tutor_authority_nonce_count"] == 1
    assert restored.recognize(
        auditory_experience,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
    ).tutor_label == "hello guala"
    with pytest.raises(RuntimeError, match="nonce was already used"):
        restored.teach(
            auditory_experience,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label="hello guala",
            authority_receipt=receipt,
        )

    wrong_key = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority(
            api_key="wrong-production-key", required=True
        ),
    )
    with pytest.raises(ValueError, match="HMAC is invalid"):
        wrong_key.restore_encoded(encoded)


def test_repeated_authorized_structure_restores_distinct_l5_admissions(
    monkeypatch,
) -> None:
    engine, first = _mounted_experience(monkeypatch, "utterance")
    try:
        authority = _authority()
        owner = AuditoryReciprocityOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=authority,
        )
        owner.teach(
            first,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label="repeated form",
            authority_receipt=_receipt(
                authority, first, label="repeated form"
            ),
        )
        engine.process_sound_frame(
            _tone_wav(),
            source_anchor_ns=3_000_000_000,
            source_time_end_ns=4_000_000_000,
            auditory_event_boundary="utterance",
        )
        second = engine._latest_auditory_l5_experience
        assert second.experience_id != first.experience_id
        second_receipt = authority.issue(
            experience_id=second.experience_id,
            kind="spoken_form",
            tutor_label="repeated form",
            nonce="cd" * 32,
            issued_at_unix_ns=1_750_000_000_000_000_001,
        )
        learned = owner.teach(
            second,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label="repeated form",
            authority_receipt=second_receipt,
        )
        assert learned.reinforcement_count == 2
        assert len(learned.branches) == 1
        assert len(learned.admission_receipts) == 2

        restored = AuditoryReciprocityOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=_authority(),
        )
        restored.restore_encoded(owner.encoded_snapshot())
        assert restored.status()["reinforcements"]["spoken_form"] == 2
        assert restored.status()["tutor_authority_nonce_count"] == 2
    finally:
        engine.shutdown()


def test_restore_rejects_changed_l5_boundary_and_changed_witness(
    auditory_experience,
) -> None:
    authority = _authority()
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=authority,
    )
    owner.teach(
        auditory_experience,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        tutor_label="sealed evidence",
        authority_receipt=_receipt(
            authority, auditory_experience, label="sealed evidence"
        ),
    )
    original = owner.snapshot()

    changed_boundary = copy.deepcopy(original)
    admission = changed_boundary["classes"][0]["admission_receipts"][0]
    payload = json.loads(base64.b64decode(
        admission["l5_authority_payload_base64"], validate=True
    ))
    payload["event_boundary"] = "ambient"
    changed_bytes = json.dumps(
        payload, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    admission["l5_authority_payload_base64"] = base64.b64encode(
        changed_bytes
    ).decode("ascii")
    admission["l5_authority_receipt_sha256"] = hashlib.sha256(
        changed_bytes
    ).hexdigest()
    with pytest.raises(ValueError, match="admission HMAC is invalid"):
        AuditoryReciprocityOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=_authority(),
        ).restore(changed_boundary)

    changed_witness = copy.deepcopy(original)
    branch = changed_witness["classes"][0]["branches"][0]
    packed = bytearray(base64.b64decode(
        branch["packed_samples"][0], validate=True
    ))
    packed[0] ^= 1
    branch["packed_samples"][0] = base64.b64encode(packed).decode("ascii")
    with pytest.raises(ValueError, match="persisted witness structural field"):
        AuditoryReciprocityOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=_authority(),
        ).restore(changed_witness)

    missing_admission = copy.deepcopy(original)
    missing_admission["classes"][0]["admission_receipts"] = []
    with pytest.raises(ValueError, match="lacks tutor admission authority"):
        AuditoryReciprocityOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=_authority(),
        ).restore(missing_admission)


def test_explicit_unrequired_owner_is_isolated_from_required_snapshots(
    auditory_experience,
) -> None:
    development = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    development.teach(
        auditory_experience,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        tutor_label="development only",
    )
    restored_development = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    restored_development.restore_encoded(development.encoded_snapshot())
    assert restored_development.status()["tutor_authority_required"] is False

    production = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=_authority(),
    )
    with pytest.raises(ValueError, match="capacity or authority changed"):
        production.restore_encoded(development.encoded_snapshot())


def test_environment_key_enables_required_mode(monkeypatch) -> None:
    monkeypatch.setenv("GUALALOOM_API_KEY", _API_KEY)
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None
    )
    assert owner.status()["tutor_authority_required"] is True
