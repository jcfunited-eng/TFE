"""Checked repository provenance for real W1 vocal pressure candidates.

Filenames and repository prose establish source provenance only.  They are
never forwarded as perceptual identity or learned meaning.  The admitted
sensory value is exact decoded mono PCM16 pressure plus an authority receipt
that binds the repository commit, Git blob, file digest, decode contract, and
decoded PCM digest.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    MIN_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
)


W1_RECORDED_VOCAL_PROVENANCE_SCHEMA = (
    "guala.w1.recorded_vocal_provenance.v1"
)
W1_RECORDED_VOCAL_MANIFEST_SCHEMA = (
    "guala.w1.recorded_vocal_provenance_manifest.v1"
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


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _sha1(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase Git SHA-1 identity")
    return value


def _relative_path(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
    ):
        raise ValueError(f"{name} is not a canonical relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ValueError(f"{name} escaped the repository")
    return value


def _decode_pcm(path: Path) -> bytes:
    completed = subprocess.run(
        (
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            str(VOCAL_SAMPLE_RATE_HZ),
            "-f",
            "s16le",
            "-",
        ),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result = completed.stdout
    if (
        not result
        or len(result) % 2
        or not MIN_VOCAL_SAMPLE_COUNT
        <= len(result) // 2
        <= MAX_VOCAL_SAMPLE_COUNT
    ):
        raise ValueError(
            "recorded vocal decode left the physical PCM boundary"
        )
    return result


def _git_blob(
    *,
    repository_root: Path,
    commit: str,
    relative_path: str,
) -> str:
    completed = subprocess.run(
        (
            "git",
            "-C",
            str(repository_root),
            "rev-parse",
            f"{commit}:{relative_path}",
        ),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


@dataclass(frozen=True, slots=True)
class W1RecordedVocalProvenance:
    repository_commit: str
    repository_path: str
    git_blob_sha1: str
    file_sha256: str
    decoded_pcm_s16le_sha256: str
    decoded_sample_count: int
    repository_authority_sha256s: tuple[str, ...]
    manifest_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "decoded_channels": 1,
            "decoded_pcm_s16le_sha256": (
                self.decoded_pcm_s16le_sha256
            ),
            "decoded_sample_count": self.decoded_sample_count,
            "decoded_sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "file_sha256": self.file_sha256,
            "git_blob_sha1": self.git_blob_sha1,
            "manifest_sha256": self.manifest_sha256,
            "repository_authority_sha256s": list(
                self.repository_authority_sha256s
            ),
            "repository_commit": self.repository_commit,
            "repository_path": self.repository_path,
            "schema": W1_RECORDED_VOCAL_PROVENANCE_SCHEMA,
        }

    def verify(self, pcm_s16le: bytes) -> None:
        _sha1(self.repository_commit, "recorded vocal repository commit")
        _relative_path(
            self.repository_path, "recorded vocal repository path"
        )
        _sha1(self.git_blob_sha1, "recorded vocal Git blob")
        _sha256(self.file_sha256, "recorded vocal file")
        _sha256(
            self.decoded_pcm_s16le_sha256,
            "recorded vocal decoded PCM",
        )
        _sha256(self.manifest_sha256, "recorded vocal manifest")
        _sha256(
            self.authority_receipt_sha256,
            "recorded vocal provenance authority",
        )
        for value in self.repository_authority_sha256s:
            _sha256(value, "recorded vocal repository authority")
        if (
            not isinstance(pcm_s16le, bytes)
            or len(pcm_s16le) % 2
            or len(pcm_s16le) // 2 != self.decoded_sample_count
            or hashlib.sha256(pcm_s16le).hexdigest()
            != self.decoded_pcm_s16le_sha256
            or self.authority_receipt_sha256
            != hashlib.sha256(_canonical(self.payload())).hexdigest()
        ):
            raise ValueError("recorded vocal provenance authority changed")


@dataclass(frozen=True, slots=True)
class W1RecordedVocalPressure:
    provenance: W1RecordedVocalProvenance
    pcm_s16le: bytes

    def verify(self) -> None:
        self.provenance.verify(self.pcm_s16le)
        if (
            len(self.framed_pcm_s16le) // 2
            > MAX_VOCAL_SAMPLE_COUNT
            or len(self.framed_pcm_s16le) // 2
            % OBSERVATION_HOP_SAMPLES
        ):
            raise ValueError(
                "recorded vocal framing left its physical boundary"
            )

    @property
    def zero_tail_sample_count(self) -> int:
        sample_count = len(self.pcm_s16le) // 2
        return (-sample_count) % OBSERVATION_HOP_SAMPLES

    @property
    def framed_pcm_s16le(self) -> bytes:
        return self.pcm_s16le + (
            b"\0\0" * self.zero_tail_sample_count
        )

    @property
    def framing_receipt_sha256(self) -> str:
        return hashlib.sha256(_canonical({
            "decoded_pcm_s16le_sha256": (
                self.provenance.decoded_pcm_s16le_sha256
            ),
            "framed_pcm_s16le_sha256": hashlib.sha256(
                self.framed_pcm_s16le
            ).hexdigest(),
            "observation_hop_samples": OBSERVATION_HOP_SAMPLES,
            "provenance_receipt_sha256": (
                self.provenance.authority_receipt_sha256
            ),
            "schema": "guala.w1.recorded_vocal_zero_tail_framing.v1",
            "zero_tail_sample_count": self.zero_tail_sample_count,
        })).hexdigest()


def load_checked_w1_recorded_vocals(
    *,
    repository_root: Path,
    manifest_path: Path,
) -> tuple[W1RecordedVocalPressure, ...]:
    """Load every manifest asset or reject the complete candidate set."""

    root = repository_root.resolve(strict=True)
    path = manifest_path.resolve(strict=True)
    try:
        manifest = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "recorded vocal manifest is not canonical JSON"
        ) from error
    if (
        not isinstance(manifest, Mapping)
        or set(manifest)
        != {
            "assets",
            "decode_contract",
            "repository_authorities",
            "repository_commit",
            "schema",
        }
        or manifest.get("schema") != W1_RECORDED_VOCAL_MANIFEST_SCHEMA
        or not isinstance(manifest.get("assets"), list)
        or not manifest["assets"]
        or not isinstance(
            manifest.get("repository_authorities"), list
        )
        or not isinstance(manifest.get("decode_contract"), Mapping)
        or manifest["decode_contract"]
        != {
            "channels": 1,
            "ffmpeg_sample_format": "s16le",
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
        }
    ):
        raise ValueError("recorded vocal manifest changed")
    commit = _sha1(
        manifest.get("repository_commit"),
        "recorded vocal manifest commit",
    )
    manifest_sha = hashlib.sha256(_canonical(manifest)).hexdigest()
    authority_by_path: dict[str, str] = {}
    for raw in manifest["repository_authorities"]:
        if (
            not isinstance(raw, Mapping)
            or set(raw) != {"git_blob_sha1", "path", "sha256"}
        ):
            raise ValueError("recorded vocal repository authority changed")
        relative = _relative_path(
            raw.get("path"), "recorded vocal authority path"
        )
        digest = _sha256(
            raw.get("sha256"), "recorded vocal authority digest"
        )
        authority_blob = _sha1(
            raw.get("git_blob_sha1"),
            "recorded vocal authority Git blob",
        )
        authority_path = (root / relative).resolve(strict=True)
        if (
            root not in authority_path.parents
            or hashlib.sha256(authority_path.read_bytes()).hexdigest()
            != digest
            or _git_blob(
                repository_root=root,
                commit=commit,
                relative_path=relative,
            )
            != authority_blob
            or relative in authority_by_path
        ):
            raise ValueError("recorded vocal repository authority changed")
        authority_by_path[relative] = digest
    results = []
    used_paths: set[str] = set()
    used_blobs: set[str] = set()
    for raw in manifest["assets"]:
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != {
                "decoded_pcm_s16le_sha256",
                "decoded_sample_count",
                "file_sha256",
                "git_blob_sha1",
                "path",
                "repository_authorities",
            }
            or not isinstance(raw.get("repository_authorities"), list)
            or not raw["repository_authorities"]
        ):
            raise ValueError("recorded vocal asset record changed")
        relative = _relative_path(
            raw.get("path"), "recorded vocal asset path"
        )
        blob = _sha1(raw.get("git_blob_sha1"), "recorded vocal asset blob")
        file_sha = _sha256(
            raw.get("file_sha256"), "recorded vocal asset file"
        )
        pcm_sha = _sha256(
            raw.get("decoded_pcm_s16le_sha256"),
            "recorded vocal asset PCM",
        )
        sample_count = raw.get("decoded_sample_count")
        if (
            isinstance(sample_count, bool)
            or not isinstance(sample_count, int)
            or not MIN_VOCAL_SAMPLE_COUNT
            <= sample_count
            <= MAX_VOCAL_SAMPLE_COUNT
            or relative in used_paths
            or blob in used_blobs
        ):
            raise ValueError("recorded vocal asset extent changed")
        authority_digests = tuple(
            authority_by_path.get(value, "")
            for value in raw["repository_authorities"]
        )
        if (
            any(not value for value in authority_digests)
            or len(authority_digests) != len(set(authority_digests))
        ):
            raise ValueError(
                "recorded vocal asset authority reference changed"
            )
        asset_path = (root / relative).resolve(strict=True)
        if root not in asset_path.parents:
            raise ValueError("recorded vocal asset escaped repository")
        file_bytes = asset_path.read_bytes()
        if (
            hashlib.sha256(file_bytes).hexdigest() != file_sha
            or _git_blob(
                repository_root=root,
                commit=commit,
                relative_path=relative,
            )
            != blob
        ):
            raise ValueError("recorded vocal repository asset changed")
        pcm = _decode_pcm(asset_path)
        provenance = W1RecordedVocalProvenance(
            repository_commit=commit,
            repository_path=relative,
            git_blob_sha1=blob,
            file_sha256=file_sha,
            decoded_pcm_s16le_sha256=pcm_sha,
            decoded_sample_count=sample_count,
            repository_authority_sha256s=authority_digests,
            manifest_sha256=manifest_sha,
            authority_receipt_sha256="0" * 64,
        )
        provenance = W1RecordedVocalProvenance(
            repository_commit=provenance.repository_commit,
            repository_path=provenance.repository_path,
            git_blob_sha1=provenance.git_blob_sha1,
            file_sha256=provenance.file_sha256,
            decoded_pcm_s16le_sha256=(
                provenance.decoded_pcm_s16le_sha256
            ),
            decoded_sample_count=provenance.decoded_sample_count,
            repository_authority_sha256s=(
                provenance.repository_authority_sha256s
            ),
            manifest_sha256=provenance.manifest_sha256,
            authority_receipt_sha256=hashlib.sha256(
                _canonical(provenance.payload())
            ).hexdigest(),
        )
        result = W1RecordedVocalPressure(provenance, pcm)
        result.verify()
        results.append(result)
        used_paths.add(relative)
        used_blobs.add(blob)
    return tuple(results)


__all__ = [
    "W1RecordedVocalPressure",
    "W1RecordedVocalProvenance",
    "load_checked_w1_recorded_vocals",
]
