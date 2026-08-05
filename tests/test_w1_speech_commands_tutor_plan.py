from __future__ import annotations

import json
from pathlib import Path

import pytest

from dsf_ai_service.substrate.w1_speech_commands_tutor_plan import (
    load_w1_speech_command_tutor_plan,
)


ROOT = Path(__file__).resolve().parents[1]
ASSETS = (
    ROOT / "dsf_ai_service" / "curriculum" / "assets"
    / "speech_commands"
)
MANIFEST = (
    ROOT / "dsf_ai_service" / "curriculum"
    / "speech_commands_subset_manifest.json"
)
KEY = b"W1-speech-command-tutor-plan-test-key"


def test_bounded_plan_separates_lessons_from_fresh_challenges():
    plan = load_w1_speech_command_tutor_plan(
        authority_key=KEY,
        asset_root=ASSETS,
        manifest_path=MANIFEST,
    )

    assert len(plan) == 26
    assert len({
        value.speaker_sha256_prefix for value in plan
    }) == 26
    by_command = {
        command: tuple(
            value for value in plan
            if value.tutor_command == command
        )
        for command in (
            "down", "go", "left", "no",
            "right", "stop", "up", "yes",
        )
    }
    for command, examples in by_command.items():
        expected = (
            {"lesson_1", "lesson_2", "lesson_3", "fresh_challenge"}
            if command in {"down", "stop"}
            else {"lesson_1", "lesson_2", "fresh_challenge"}
        )
        assert {value.tutor_role for value in examples} == expected
        assert len({
            value.speaker_sha256_prefix for value in examples
        }) == len(expected)
    assert all(
        len(value.pressure.pcm_s16le) == 32_000 for value in plan
    )
    assert all(
        not hasattr(value.pressure, "tutor_command")
        and not hasattr(value.pressure, "tutor_role")
        and not hasattr(value.pressure, "speaker_sha256_prefix")
        and not hasattr(value.pressure, "label")
        and not hasattr(value.pressure, "transcript")
        and not hasattr(value.pressure, "meaning")
        for value in plan
    )


def test_tutor_manifest_or_attribution_tamper_is_rejected(tmp_path):
    manifest = json.loads(MANIFEST.read_bytes())
    manifest["assets"][0]["file_sha256"] = "0" * 64
    altered = tmp_path / "altered-speech-commands.json"
    altered.write_text(json.dumps(
        manifest,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ))
    with pytest.raises(ValueError, match="file changed"):
        load_w1_speech_command_tutor_plan(
            authority_key=KEY,
            asset_root=ASSETS,
            manifest_path=altered,
        )

    manifest = json.loads(MANIFEST.read_bytes())
    manifest["attribution_sha256"] = "0" * 64
    altered = tmp_path / "altered-attribution.json"
    altered.write_text(json.dumps(
        manifest,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ))
    with pytest.raises(ValueError, match="attribution changed"):
        load_w1_speech_command_tutor_plan(
            authority_key=KEY,
            asset_root=ASSETS,
            manifest_path=altered,
        )

    manifest = json.loads(MANIFEST.read_bytes())
    manifest["assets"][3]["tutor_role"] = "lesson_3"
    altered = tmp_path / "altered-role.json"
    altered.write_text(json.dumps(
        manifest,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ))
    with pytest.raises(
        ValueError, match="sources are not independent"
    ):
        load_w1_speech_command_tutor_plan(
            authority_key=KEY,
            asset_root=ASSETS,
            manifest_path=altered,
        )
