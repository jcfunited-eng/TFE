from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path


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
