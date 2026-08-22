from __future__ import annotations

import hashlib
import json
from pathlib import Path
import wave


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "guala_curriculum/card_experience_manifest-v1.json"
SCHEMA = "guala.external_tutor_card_experience_manifest.v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_complete_card_roster_is_exact_physical_external_tutoring() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert value["schema"] == SCHEMA
    assert value["approved_experience_count"] == 61
    assert value["authority_boundary"] == {
        "external_tutor_pairing": True,
        "internal_identity_authority": False,
        "internal_meaning_authority": False,
        "internal_pronunciation_authority": False,
        "internal_recognition_authority": False,
    }
    assert value["sample_format"] == {
        "channels": 1,
        "encoding": "pcm_s16le",
        "sample_rate_hz": 16_000,
    }

    experiences = value["experiences"]
    assert [item["experience_id"] for item in experiences] == [
        *(f"alphabet-{chr(ord('a') + index)}" for index in range(26)),
        *(f"number-{number:02d}" for number in range(0, 11)),
        "word-mama",
        "word-dada",
        "word-ball",
        "word-cup",
        "word-dog",
        "word-cat",
        "word-sun",
        "word-moon",
        "word-tree",
        "word-water",
        "word-milk",
        "word-shoe",
        "word-hand",
        "word-eye",
        "word-book",
        "word-car",
        "word-bed",
        "word-door",
        "word-apple",
        "word-banana",
        "word-chair",
        "word-hat",
        "word-fish",
        "word-bird",
    ]
    assert [item["surface"]["object_id"] for item in experiences] == [
        *(f"W1-optical-surface-{ordinal:02d}" for ordinal in range(1, 27)),
        "W1-optical-surface-61",
        *(f"W1-optical-surface-{ordinal:02d}" for ordinal in range(27, 61)),
    ]
    assert sum(item["presentation_milliseconds"] for item in experiences) == 915_000
    assert all(item["presentation_milliseconds"] == 15_000 for item in experiences)

    card_paths: set[str] = set()
    audio_paths: list[str] = []
    for experience in experiences:
        surface = experience["surface"]
        assert surface["path"] not in card_paths
        card_paths.add(surface["path"])

        card_path = ROOT / surface["path"]
        assert card_path.is_file()
        assert _sha256(card_path) == surface["sha256"]

        tutor_audio = experience.get("tutor_audio")
        if tutor_audio is None:
            assert experience["experience_id"].startswith("word-")
            continue
        audio_paths.append(tutor_audio["path"])
        audio_path = ROOT / tutor_audio["path"]
        assert audio_path.is_file()
        assert _sha256(audio_path) == tutor_audio["sha256"]

        with wave.open(str(audio_path), "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 16_000
            assert wav.getnframes() == tutor_audio["sample_count"]

    assert sum("number-00" in value for value in card_paths) == 1
    assert sum("number-00" in value for value in audio_paths) == 1
    assert len(audio_paths) == 38
    assert audio_paths.count("guala_curriculum/audio/a-apple-tutor-v1.wav") == 2
    assert len(set(audio_paths)) == 37
