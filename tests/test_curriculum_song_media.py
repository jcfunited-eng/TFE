from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path

from dsf_ai_service import native_production_app as production


ROOT = Path(__file__).resolve().parents[1]
SONG_ROOT = ROOT / "guala_curriculum" / "songs"
MANIFEST_PATH = SONG_ROOT / "song_experience_manifest-v1.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_song_media_are_exact_bounded_physical_waveforms() -> None:
    manifest = json.loads(MANIFEST_PATH.read_bytes())
    assert manifest["schema"] == (
        "guala.external_tutor_song_experience_manifest.v1"
    )
    assert manifest["authority_boundary"] == {
        "external_tutor_media": True,
        "glyph_identity_authority": False,
        "meaning_authority": False,
        "recognition_authority": False,
        "transcript_authority": False,
        "word_authority": False,
    }
    assert manifest["sample_format"] == {
        "channels": 1,
        "encoding": "pcm_s16le",
        "sample_rate_hz": 16_000,
    }
    assert len(manifest["experiences"]) == 3
    for experience in manifest["experiences"]:
        audio = experience["audio"]
        path = ROOT / audio["path"]
        assert path.parent == SONG_ROOT
        assert _sha256(path) == audio["sha256"]
        with wave.open(str(path), "rb") as source:
            assert source.getnchannels() == 1
            assert source.getsampwidth() == 2
            assert source.getframerate() == 16_000
            assert source.getnframes() == audio["sample_count"]
        assert audio["sample_count"] <= 16_000 * 60


def test_counting_song_visual_intervals_cover_the_waveform_exactly() -> None:
    manifest = json.loads(MANIFEST_PATH.read_bytes())
    by_id = {
        item["experience_id"]: item
        for item in manifest["experiences"]
    }
    expected_sequences = {
        "count-up-one-to-ten-v1": [
            f"W1-optical-surface-{index:02d}"
            for index in range(27, 37)
        ],
        "count-down-ten-to-one-v1": [
            f"W1-optical-surface-{index:02d}"
            for index in range(36, 26, -1)
        ],
    }
    for experience_id, object_ids in expected_sequences.items():
        experience = by_id[experience_id]
        visual = experience["visual_program"]
        assert visual["alignment_claim"] == (
            "exact_sample_interval_surface_sequence"
        )
        slots = visual["slots"]
        assert [slot["object_id"] for slot in slots] == object_ids
        assert [slot["first_sample_index"] for slot in slots] == [
            index * 19_200 for index in range(10)
        ]
        assert {slot["sample_count"] for slot in slots} == {19_200}
        assert (
            slots[-1]["first_sample_index"]
            + slots[-1]["sample_count"]
            == experience["audio"]["sample_count"]
        )


def test_alphabet_song_does_not_claim_unverified_per_letter_timing() -> None:
    manifest = json.loads(MANIFEST_PATH.read_bytes())
    alphabet = next(
        item
        for item in manifest["experiences"]
        if item["experience_id"] == "alphabet-song-cc-by-sa-3.0-v1"
    )
    visual = alphabet["visual_program"]
    assert visual["alignment_claim"] == (
        "simultaneous_alphabet_surface_set_only"
    )
    assert visual["per_letter_timing_authority"] is False
    assert visual["object_ids"] == [
        f"W1-optical-surface-{index:02d}"
        for index in range(1, 27)
    ]


def test_song_builders_keep_one_joint_bounded_shared_clock() -> None:
    expected = {
        "alphabet-song-cc-by-sa-3.0-v1": (
            "simultaneous_alphabet_surface_set_only",
            98,
        ),
        "count-up-one-to-ten-v1": (
            "exact_sample_interval_surface_sequence",
            50,
        ),
        "count-down-ten-to-one-v1": (
            "exact_sample_interval_surface_sequence",
            50,
        ),
    }
    for song_id, (claim, expected_hops) in expected.items():
        experience = production._read_manifest_song(song_id)
        episodes, observed_claim = production._song_lesson_hop_episodes(
            song_id,
            experience,
        )
        assert observed_claim == claim
        assert len(episodes) == expected_hops
        for episode, intervals in episodes:
            assert episode.port_count == production.LESSON_PORT_COUNT
            assert episode.occurrence_count == 1
            assert intervals == [
                (
                    (
                        experience["audio"]["sample_count"] * 1000
                        + production.COCHLEAR_SAMPLE_RATE_HZ
                        - 1
                    )
                    // production.COCHLEAR_SAMPLE_RATE_HZ,
                    1000,
                )
            ]


def test_alphabet_song_surface_set_is_simultaneous_and_bounded() -> None:
    roster = production._alphabet_song_surface_set_luminance()
    assert len(roster) == production.CARD_SURFACE_PORT_COUNT
    assert all(0.0 <= value <= 1.0 for value in roster)
    assert all(value > 0.0 for value in roster[:26])
    assert roster[26] == 0.0


def test_song_receipt_is_fixed_digest_checked_custody(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    receipt = {
        "schema": production.SONG_LESSON_RECEIPT_SCHEMA,
        "song_id": "count-up-one-to-ten-v1",
        "successor_organism_tick": 12,
        "transport_metadata_only": True,
    }
    receipt["receipt_sha256"] = production._lesson_receipt_digest(receipt)
    production._persist_song_lesson_receipt(receipt)
    assert production._load_song_lesson_receipt() == receipt
    assert (tmp_path / production.SONG_LESSON_RECEIPT_FILE).stat().st_size < 32_768


def test_song_routes_and_invitation_identity_are_explicit() -> None:
    paths = {route.path for route in production.app.routes}
    assert production.CURRICULUM_INVITE_SONG_ENDPOINT in paths
    assert production.CURRICULUM_TEACH_SONG_ENDPOINT in paths
    invitation = {
        "schema": production.CURRICULUM_INVITATION_SCHEMA,
        "experience_kind": "song",
        "experience_id": "count-up-one-to-ten-v1",
        "song_id": "count-up-one-to-ten-v1",
        "outcome": "presentable",
        "presentation_eligible": True,
    }
    invitation["invitation_receipt_sha256"] = production._receipt(invitation)
    production._curriculum_invitation = invitation
    assert production._validated_curriculum_experience_invitation(
        "song",
        "count-up-one-to-ten-v1",
        invitation["invitation_receipt_sha256"],
    ) == invitation
    production._curriculum_invitation = None


def test_song_receipt_follows_one_committed_native_transaction(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    production._restored = None
    production._admission = None
    production._boot_error = None
    production._public_observation_body = None
    production._public_observation_etag = None
    production._last_transition_evidence = None
    production._last_song_lesson_receipt = None
    production._last_song_lesson_receipt_error = None
    production._startup()
    song_id = "count-up-one-to-ten-v1"
    experience = production._read_manifest_song(song_id)
    episodes, claim = production._song_lesson_hop_episodes(song_id, experience)
    invitation = {
        "schema": production.CURRICULUM_INVITATION_SCHEMA,
        "experience_kind": "song",
        "experience_id": song_id,
        "song_id": song_id,
        "outcome": "presentable",
        "presentation_eligible": True,
    }
    invitation["invitation_receipt_sha256"] = production._receipt(invitation)
    production._curriculum_invitation = invitation
    result = production._perform_song_lesson_intake(
        episodes[:1],
        song_id,
        experience,
        claim,
        invitation["invitation_receipt_sha256"],
    )
    assert result["persisted"]["state_sha256"] != result["persisted"][
        "predecessor_state_sha256"
    ]
    assert result["durable_receipt"]["available"] is True
    assert result["durable_receipt"]["song_id"] == song_id
    assert result["durable_receipt"]["hop_count"] == 1
    assert production._load_song_lesson_receipt()["receipt_sha256"] == result[
        "durable_receipt"
    ]["receipt_sha256"]
    production._restored = None
    production._admission = None
    production._boot_error = None
    production._curriculum_invitation = None
