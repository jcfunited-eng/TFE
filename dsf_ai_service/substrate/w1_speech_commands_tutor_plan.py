"""Authenticated external tutor plan for bounded real speech commands.

Command, source-speaker, and lesson/challenge role are tutor-only metadata used
to schedule causally matching W1 scenes.  The substrate-facing pressure record
contains none of them.  It binds only exact PCM and source provenance.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


W1_SPEECH_PRESSURE_SCHEMA = "guala.w1.tutored_speech_pressure.v1"
W1_SPEECH_TUTOR_EXAMPLE_SCHEMA = (
    "guala.w1.speech_command_tutor_example.v3"
)
W1_SPEECH_COMMANDS_MANIFEST_SCHEMA = (
    "guala.w1.speech_commands_subset_manifest.v3"
)
_PRESSURE_DOMAIN = b"guala-w1-tutored-speech-pressure-v1\0"
_TUTOR_DOMAIN = b"guala-w1-speech-command-tutor-example-v3\0"
_COMMANDS = ("down", "go", "left", "no", "right", "stop", "up", "yes")
_TUTOR_ROLES = (
    "lesson_1", "lesson_2", "lesson_3", "fresh_challenge"
)
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("W1 speech tutor key is not typed")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 speech tutor key boundary changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


@dataclass(frozen=True, slots=True)
class W1TutoredSpeechPressure:
    pcm_s16le: bytes
    pcm_sha256: str
    sample_count: int
    source_file_sha256: str
    source_archive_sha256: str
    manifest_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "channels": 1,
            "manifest_sha256": self.manifest_sha256,
            "pcm_sha256": self.pcm_sha256,
            "sample_count": self.sample_count,
            "sample_rate_hz": 16_000,
            "sample_width_bytes": 2,
            "schema": W1_SPEECH_PRESSURE_SCHEMA,
            "source_archive_sha256": self.source_archive_sha256,
            "source_file_sha256": self.source_file_sha256,
        }

    def verify(self, authority_key: bytes | str) -> None:
        for value, name in (
            (self.pcm_sha256, "W1 tutored PCM"),
            (self.source_file_sha256, "W1 tutor source file"),
            (self.source_archive_sha256, "W1 tutor source archive"),
            (self.manifest_sha256, "W1 tutor manifest"),
            (self.authority_hmac_sha256, "W1 tutor pressure HMAC"),
            (
                self.authority_receipt_sha256,
                "W1 tutor pressure authority",
            ),
        ):
            _sha256(value, name)
        root = hashlib.sha256(_key(authority_key)).digest()
        pressure_key = hashlib.sha256(
            _PRESSURE_DOMAIN + root
        ).digest()
        signature = hmac.new(
            pressure_key,
            _PRESSURE_DOMAIN + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not isinstance(self.pcm_s16le, bytes)
            or isinstance(self.sample_count, bool)
            or not isinstance(self.sample_count, int)
            or self.sample_count <= 0
            or len(self.pcm_s16le) != self.sample_count * 2
            or hashlib.sha256(self.pcm_s16le).hexdigest()
            != self.pcm_sha256
            or not hmac.compare_digest(
                signature, self.authority_hmac_sha256
            )
            or self.authority_receipt_sha256
            != hashlib.sha256(_canonical({
                "authority_hmac_sha256": signature,
                "payload": self.payload(),
            })).hexdigest()
        ):
            raise ValueError("W1 tutored pressure authority changed")


@dataclass(frozen=True, slots=True)
class W1SpeechCommandTutorExample:
    tutor_command: str
    tutor_role: str
    speaker_sha256_prefix: str
    pressure: W1TutoredSpeechPressure
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "pressure_authority_receipt_sha256": (
                self.pressure.authority_receipt_sha256
            ),
            "schema": W1_SPEECH_TUTOR_EXAMPLE_SCHEMA,
            "speaker_sha256_prefix": self.speaker_sha256_prefix,
            "tutor_command": self.tutor_command,
            "tutor_role": self.tutor_role,
        }

    def verify(self, authority_key: bytes | str) -> None:
        self.pressure.verify(authority_key)
        if (
            self.tutor_command not in _COMMANDS
            or self.tutor_role not in _TUTOR_ROLES
            or not isinstance(self.speaker_sha256_prefix, str)
            or len(self.speaker_sha256_prefix) != 8
            or any(
                value not in _HEX
                for value in self.speaker_sha256_prefix
            )
        ):
            raise ValueError("W1 speech tutor metadata changed")
        root = hashlib.sha256(_key(authority_key)).digest()
        tutor_key = hashlib.sha256(_TUTOR_DOMAIN + root).digest()
        signature = hmac.new(
            tutor_key,
            _TUTOR_DOMAIN + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature, self.authority_hmac_sha256
            )
            or self.authority_receipt_sha256
            != hashlib.sha256(_canonical({
                "authority_hmac_sha256": signature,
                "payload": self.payload(),
            })).hexdigest()
        ):
            raise ValueError("W1 speech tutor authority changed")


def _load_manifest(
    *,
    root: Path,
    manifest_file: Path,
) -> Mapping[str, object]:
    try:
        manifest = json.loads(manifest_file.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "W1 speech commands manifest is unreadable"
        ) from error
    if (
        not isinstance(manifest, Mapping)
        or set(manifest)
        != {
            "assets",
            "attribution_path",
            "attribution_sha256",
            "channels",
            "commands",
            "license_spdx",
            "sample_rate_hz",
            "sample_width_bytes",
            "schema",
            "source_archive_bytes",
            "source_archive_sha256",
            "source_url",
        }
        or manifest.get("schema")
        != W1_SPEECH_COMMANDS_MANIFEST_SCHEMA
        or manifest.get("commands") != list(_COMMANDS)
        or manifest.get("channels") != 1
        or manifest.get("sample_rate_hz") != 16_000
        or manifest.get("sample_width_bytes") != 2
        or manifest.get("license_spdx") != "CC-BY-4.0"
        or manifest.get("source_archive_bytes") != 182_082_353
        or manifest.get("source_archive_sha256")
        != "49650f2341b26d886b46b3f4fb8fed59e30300b17550f1ee4a768b3106cf93a0"
        or manifest.get("source_url")
        != (
            "http://storage.googleapis.com/download.tensorflow.org/"
            "data/mini_speech_commands.zip"
        )
        or not isinstance(manifest.get("assets"), list)
        or len(manifest["assets"]) != 26
    ):
        raise ValueError("W1 speech commands manifest changed")
    attribution_path = root / manifest.get("attribution_path", "")
    if (
        not attribution_path.is_file()
        or hashlib.sha256(attribution_path.read_bytes()).hexdigest()
        != _sha256(
            manifest.get("attribution_sha256"),
            "W1 speech commands attribution",
        )
    ):
        raise ValueError("W1 speech commands attribution changed")
    return manifest


def _load_pcm(
    *,
    root: Path,
    relative: str,
    expected_file_sha256: str,
) -> bytes:
    file_path = (root / relative).resolve(strict=True)
    if root not in file_path.parents:
        raise ValueError("W1 speech command asset escaped its root")
    file_bytes = file_path.read_bytes()
    if hashlib.sha256(file_bytes).hexdigest() != expected_file_sha256:
        raise ValueError("W1 speech command file changed")
    try:
        with wave.open(str(file_path), "rb") as wav:
            if (
                wav.getnchannels() != 1
                or wav.getsampwidth() != 2
                or wav.getframerate() != 16_000
                or wav.getnframes() != 16_000
                or wav.getcomptype() != "NONE"
            ):
                raise ValueError(
                    "W1 speech command WAV boundary changed"
                )
            return wav.readframes(wav.getnframes())
    except wave.Error as error:
        raise ValueError(
            "W1 speech command WAV is unreadable"
        ) from error


def load_w1_speech_command_tutor_plan(
    *,
    authority_key: bytes | str,
    asset_root: Path,
    manifest_path: Path,
) -> tuple[W1SpeechCommandTutorExample, ...]:
    """Load two source-disjoint lessons and one fresh challenge per relation."""

    root_key = hashlib.sha256(_key(authority_key)).digest()
    pressure_key = hashlib.sha256(_PRESSURE_DOMAIN + root_key).digest()
    tutor_key = hashlib.sha256(_TUTOR_DOMAIN + root_key).digest()
    root = asset_root.resolve(strict=True)
    manifest_file = manifest_path.resolve(strict=True)
    manifest = _load_manifest(root=root, manifest_file=manifest_file)
    manifest_sha = hashlib.sha256(_canonical(manifest)).hexdigest()
    archive_sha = manifest["source_archive_sha256"]
    required_roles = {
        command: (
            frozenset(_TUTOR_ROLES)
            if command in {"down", "stop"}
            else frozenset(("lesson_1", "lesson_2", "fresh_challenge"))
        )
        for command in _COMMANDS
    }
    role_counts = {
        command: {role: 0 for role in required_roles[command]}
        for command in _COMMANDS
    }
    speakers: set[str] = set()
    paths: set[str] = set()
    results = []
    for raw in manifest["assets"]:
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != {
                "command",
                "file_sha256",
                "frame_count",
                "path",
                "speaker_sha256_prefix",
                "tutor_role",
            }
            or raw.get("command") not in _COMMANDS
            or raw.get("tutor_role")
            not in required_roles.get(raw.get("command"), frozenset())
            or raw.get("frame_count") != 16_000
        ):
            raise ValueError("W1 speech command asset record changed")
        command = raw["command"]
        role = raw["tutor_role"]
        relative = raw.get("path")
        speaker = raw.get("speaker_sha256_prefix")
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or Path(relative).parts[0] != command
            or relative in paths
            or not isinstance(speaker, str)
            or speaker in speakers
            or len(speaker) != 8
            or any(value not in _HEX for value in speaker)
            or not Path(relative).name.startswith(
                f"{speaker}_nohash_"
            )
            or role_counts[command][role]
        ):
            raise ValueError(
                "W1 speech command sources are not independent"
            )
        file_sha = _sha256(
            raw.get("file_sha256"),
            "W1 speech command file",
        )
        pcm = _load_pcm(
            root=root,
            relative=relative,
            expected_file_sha256=file_sha,
        )
        pressure_payload = {
            "channels": 1,
            "manifest_sha256": manifest_sha,
            "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            "sample_count": 16_000,
            "sample_rate_hz": 16_000,
            "sample_width_bytes": 2,
            "schema": W1_SPEECH_PRESSURE_SCHEMA,
            "source_archive_sha256": archive_sha,
            "source_file_sha256": file_sha,
        }
        pressure_signature = hmac.new(
            pressure_key,
            _PRESSURE_DOMAIN + _canonical(pressure_payload),
            hashlib.sha256,
        ).hexdigest()
        pressure = W1TutoredSpeechPressure(
            pcm_s16le=pcm,
            pcm_sha256=pressure_payload["pcm_sha256"],
            sample_count=16_000,
            source_file_sha256=file_sha,
            source_archive_sha256=archive_sha,
            manifest_sha256=manifest_sha,
            authority_hmac_sha256=pressure_signature,
            authority_receipt_sha256=hashlib.sha256(_canonical({
                "authority_hmac_sha256": pressure_signature,
                "payload": pressure_payload,
            })).hexdigest(),
        )
        tutor_payload = {
            "pressure_authority_receipt_sha256": (
                pressure.authority_receipt_sha256
            ),
            "schema": W1_SPEECH_TUTOR_EXAMPLE_SCHEMA,
            "speaker_sha256_prefix": speaker,
            "tutor_command": command,
            "tutor_role": role,
        }
        tutor_signature = hmac.new(
            tutor_key,
            _TUTOR_DOMAIN + _canonical(tutor_payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1SpeechCommandTutorExample(
            tutor_command=command,
            tutor_role=role,
            speaker_sha256_prefix=speaker,
            pressure=pressure,
            authority_hmac_sha256=tutor_signature,
            authority_receipt_sha256=hashlib.sha256(_canonical({
                "authority_hmac_sha256": tutor_signature,
                "payload": tutor_payload,
            })).hexdigest(),
        )
        result.verify(authority_key)
        results.append(result)
        paths.add(relative)
        speakers.add(speaker)
        role_counts[command][role] += 1
    if (
        any(
            set(role_counts[command]) != required_roles[command]
            or any(count != 1 for count in role_counts[command].values())
            for command in _COMMANDS
        )
        or len(speakers) != 26
    ):
        raise ValueError(
            "W1 speech tutor lacks source-disjoint lesson/challenge roles"
        )
    return tuple(results)


__all__ = [
    "W1SpeechCommandTutorExample",
    "W1TutoredSpeechPressure",
    "load_w1_speech_command_tutor_plan",
]
