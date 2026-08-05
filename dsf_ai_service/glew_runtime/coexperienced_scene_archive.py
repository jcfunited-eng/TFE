"""Six-lane-native archive of freshly-learned coexperienced scenes.

This module is storage, not cognition.  It answers
``docs/GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-20260714-v1.md`` section 6.1:
a content-addressed archive that stores, per learned scene, the learned
binding's identity plus the *deterministic reconstruction key* ``(scene_
task_id, scene_language_text)`` and nothing else.  It stores no field bytes,
no evidence, and no expression -- recall regenerates the evidence bit-for-bit
from the reconstruction key (design section 5) and *verifies* the regenerated
six-lane receipts against the binding, so storing the evidence would be
redundant and would risk drift.

Why this exists at all (not the five-sense ``RecallStoryEpisodeArchive``)
-------------------------------------------------------------------------
The design's section 3 proves, by direct code citation, that a five-sense
``RecallStoryEpisode``'s per-port sensory ``evidence_receipt_sha256`` can
never equal the *six-lane* sensory receipts a real learned ``MotifOutput
Binding`` carries (``closed_experience.prepare_closed_experience_evidence``
folds the whole-preparation support-floor / resonance digest into every
port's receipt, so a five-sense preparation and a six-lane preparation
produce different per-port receipts even for byte-identical streams).  This
archive is therefore keyed exactly like the five-sense archive's ``resolve``
contract -- ``(profile_binding_sha256, sorted(sensory_evidence_receipt_
sha256s))`` -- but on the *six-lane* receipts a real binding actually carries
(``expression_learning._sensory_receipts``), so a real learned binding can
resolve it.

Every checkpoint mirrors ``recall_story_episode_archive.py``'s existing
HMAC-signed format exactly (same ``authentication``/``body`` envelope, same
``_canonical_bytes`` ASCII canonicalization, same signature discipline).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Sequence

from .model import (
    ReceiptError,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)


COEXPERIENCED_SCENE_EPISODE_SCHEMA = "glew.recall.coexperienced_scene_episode.v1"
COEXPERIENCED_SCENE_ARCHIVE_SCHEMA = "glew.recall.coexperienced_scene_archive.v1"
COEXPERIENCED_SCENE_ARCHIVE_CHECKPOINT_SCHEMA = (
    "glew.recall.coexperienced_scene_archive_checkpoint.v1"
)
ARCHIVE_CHECKPOINT_ALGORITHM = "HMAC-SHA256"
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _canonical_bytes(value: object) -> bytes:
    """Mirror ``recall_story_episode_archive.py``'s own ``_canonical_bytes``
    exactly (``ensure_ascii=True`` + ASCII encoding), so this archive's
    checkpoint envelope is bit-for-bit the same shape the five-sense archive
    already ships -- and so a bound Unicode scalar (which may be non-ASCII or
    astral) canonicalizes to a fully reversible pure-ASCII ``\\uXXXX`` escape,
    keeping the content address deterministic across processes."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _strict_object_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ReceiptError("coexperienced scene checkpoint has a duplicate JSON field")
        result[key] = value
    return result


def _strict_json_object(payload: bytes, field_name: str) -> dict[str, object]:
    if not isinstance(payload, bytes) or not payload:
        raise ReceiptError(f"{field_name} bytes are absent")
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_strict_object_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ReceiptError(f"{field_name} contains a non-finite number")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{field_name} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise ReceiptError(f"{field_name} must be a JSON object")
    if _canonical_bytes(value) != payload:
        raise ReceiptError(f"{field_name} is not canonical JSON bytes")
    return value


def _expect_exact_keys(
    value: Mapping[str, object], expected: frozenset[str], field_name: str
) -> None:
    if frozenset(value) != expected:
        raise ReceiptError(f"{field_name} fields changed")


def _expect_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise ReceiptError(f"{field_name} must be a list")
    return value


def _hex_bytes(value: object, field_name: str) -> bytes:
    if not isinstance(value, str) or not value or value.lower() != value:
        raise ReceiptError(f"{field_name} must be nonempty lowercase hexadecimal")
    try:
        payload = bytes.fromhex(value)
    except ValueError as exc:
        raise ReceiptError(f"{field_name} is not hexadecimal") from exc
    if not payload or payload.hex() != value:
        raise ReceiptError(f"{field_name} is not canonical hexadecimal")
    return payload


def _require_one_scalar(text: object, field_name: str) -> str:
    if not isinstance(text, str) or len(text) != 1:
        raise ReceiptError(f"{field_name} must be exactly one Unicode scalar")
    return text


def _require_sorted_distinct_receipts(
    values: object, field_name: str
) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise ReceiptError(f"{field_name} must be a nonempty immutable tuple")
    for index, value in enumerate(values):
        sha256_digest(value, f"{field_name}[{index}]")
    if len(set(values)) != len(values):
        raise ReceiptError(f"{field_name} contains a duplicate receipt")
    if values != tuple(sorted(values)):
        raise ReceiptError(f"{field_name} must use canonical sorted digest order")
    return values


def coexperienced_scene_episode_receipt_payload(
    *,
    profile_binding_sha256: str,
    motif_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],
    coexperienced_scalar_text: str,
    scene_task_id: str,
    scene_language_text: str,
    engine_id: str,
) -> bytes:
    sha256_digest(profile_binding_sha256, "coexperienced scene profile binding")
    sha256_digest(motif_receipt_sha256, "coexperienced scene motif receipt")
    _require_sorted_distinct_receipts(
        sensory_evidence_receipt_sha256s,
        "coexperienced scene sensory evidence receipts",
    )
    _require_one_scalar(coexperienced_scalar_text, "coexperienced scalar text")
    _require_one_scalar(scene_language_text, "scene language text")
    require_identifier(scene_task_id, "coexperienced scene task id")
    require_identifier(engine_id, "coexperienced scene engine id")
    return _canonical_bytes(
        {
            "coexperienced_scalar_text": coexperienced_scalar_text,
            "engine_id": engine_id,
            "motif_receipt_sha256": motif_receipt_sha256,
            "profile_binding_sha256": profile_binding_sha256,
            "scene_language_text": scene_language_text,
            "scene_task_id": scene_task_id,
            "schema": COEXPERIENCED_SCENE_EPISODE_SCHEMA,
            "sensory_evidence_receipt_sha256s": list(
                sensory_evidence_receipt_sha256s
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class CoexperiencedSceneEpisode:
    """Bit-exact content-addressed closure of one learned coexperienced scene.

    Stores only the learned binding's identity plus the deterministic
    reconstruction key; no field/evidence bytes (design section 6.1 note)."""

    profile_binding_sha256: str
    motif_receipt_sha256: str
    sensory_evidence_receipt_sha256s: tuple[str, ...]
    coexperienced_scalar_text: str
    scene_task_id: str
    scene_language_text: str
    engine_id: str
    episode_receipt_sha256: str
    episode_receipt_payload: bytes

    @property
    def resolution_key(self) -> tuple[str, tuple[str, ...]]:
        return (
            self.profile_binding_sha256,
            tuple(sorted(self.sensory_evidence_receipt_sha256s)),
        )

    def verify(self) -> None:
        expected = coexperienced_scene_episode_receipt_payload(
            profile_binding_sha256=self.profile_binding_sha256,
            motif_receipt_sha256=self.motif_receipt_sha256,
            sensory_evidence_receipt_sha256s=(
                self.sensory_evidence_receipt_sha256s
            ),
            coexperienced_scalar_text=self.coexperienced_scalar_text,
            scene_task_id=self.scene_task_id,
            scene_language_text=self.scene_language_text,
            engine_id=self.engine_id,
        )
        if (
            self.episode_receipt_payload != expected
            or receipt_sha256(expected) != self.episode_receipt_sha256
        ):
            raise ReceiptError(
                "coexperienced scene episode differs from its content address"
            )


def create_coexperienced_scene_episode(
    *,
    profile_binding_sha256: str,
    motif_receipt_sha256: str,
    sensory_evidence_receipt_sha256s: tuple[str, ...],
    coexperienced_scalar_text: str,
    scene_task_id: str,
    scene_language_text: str,
    engine_id: str,
) -> CoexperiencedSceneEpisode:
    payload = coexperienced_scene_episode_receipt_payload(
        profile_binding_sha256=profile_binding_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        sensory_evidence_receipt_sha256s=sensory_evidence_receipt_sha256s,
        coexperienced_scalar_text=coexperienced_scalar_text,
        scene_task_id=scene_task_id,
        scene_language_text=scene_language_text,
        engine_id=engine_id,
    )
    episode = CoexperiencedSceneEpisode(
        profile_binding_sha256=profile_binding_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        sensory_evidence_receipt_sha256s=tuple(sensory_evidence_receipt_sha256s),
        coexperienced_scalar_text=coexperienced_scalar_text,
        scene_task_id=scene_task_id,
        scene_language_text=scene_language_text,
        engine_id=engine_id,
        episode_receipt_sha256=receipt_sha256(payload),
        episode_receipt_payload=payload,
    )
    episode.verify()
    return episode


def coexperienced_scene_archive_receipt_payload(
    episodes: tuple[CoexperiencedSceneEpisode, ...],
) -> bytes:
    return _canonical_bytes(
        {
            "episode_receipt_sha256s": [
                value.episode_receipt_sha256 for value in episodes
            ],
            "schema": COEXPERIENCED_SCENE_ARCHIVE_SCHEMA,
        }
    )


@dataclass(frozen=True, slots=True)
class CoexperiencedSceneArchive:
    """Immutable archive indexed only by the exact profile + six-lane sensory
    receipt set (the same resolve contract as ``RecallStoryEpisodeArchive``)."""

    episodes: tuple[CoexperiencedSceneEpisode, ...] = ()
    _by_receipts: Mapping[
        tuple[str, tuple[str, ...]], CoexperiencedSceneEpisode
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.episodes, tuple) or not all(
            isinstance(value, CoexperiencedSceneEpisode) for value in self.episodes
        ):
            raise ReceiptError("coexperienced scene archive must be typed and immutable")
        digests = tuple(value.episode_receipt_sha256 for value in self.episodes)
        if digests != tuple(sorted(digests)) or len(set(digests)) != len(digests):
            raise ReceiptError("coexperienced scene archive is not canonical and unique")
        index: dict[tuple[str, tuple[str, ...]], CoexperiencedSceneEpisode] = {}
        for value in self.episodes:
            value.verify()
            key = value.resolution_key
            if key in index:
                raise ReceiptError(
                    "two coexperienced scenes claim the same binding receipt set"
                )
            index[key] = value
        object.__setattr__(self, "_by_receipts", MappingProxyType(index))

    @property
    def receipt_payload(self) -> bytes:
        return coexperienced_scene_archive_receipt_payload(self.episodes)

    @property
    def receipt_sha256(self) -> str:
        return receipt_sha256(self.receipt_payload)

    def with_episode(
        self, episode: CoexperiencedSceneEpisode
    ) -> "CoexperiencedSceneArchive":
        if not isinstance(episode, CoexperiencedSceneEpisode):
            raise ReceiptError("coexperienced scene admission is not a typed episode")
        episode.verify()
        key = episode.resolution_key
        if key in self._by_receipts:
            current = self._by_receipts[key]
            if current == episode:
                return self
            raise ReceiptError("this exact binding receipt set is already archived")
        return CoexperiencedSceneArchive(
            tuple(
                sorted(
                    (*self.episodes, episode),
                    key=lambda value: value.episode_receipt_sha256,
                )
            )
        )

    def resolve(
        self,
        *,
        profile_binding_sha256: str,
        sensory_evidence_receipt_sha256s: tuple[str, ...],
    ) -> CoexperiencedSceneEpisode:
        sha256_digest(profile_binding_sha256, "coexperienced recall profile binding")
        if not isinstance(sensory_evidence_receipt_sha256s, tuple) or not (
            sensory_evidence_receipt_sha256s
        ):
            raise ReceiptError(
                "coexperienced recall requires an immutable complete sensory receipt set"
            )
        for index, value in enumerate(sensory_evidence_receipt_sha256s):
            sha256_digest(value, f"coexperienced recall sensory receipt[{index}]")
        if len(set(sensory_evidence_receipt_sha256s)) != len(
            sensory_evidence_receipt_sha256s
        ):
            raise ReceiptError("coexperienced recall sensory receipt set contains a duplicate")
        key = (
            profile_binding_sha256,
            tuple(sorted(sensory_evidence_receipt_sha256s)),
        )
        try:
            return self._by_receipts[key]
        except KeyError as exc:
            raise ReceiptError(
                "no coexperienced scene has this exact profile and complete sensory receipt set"
            ) from exc


def _episode_body(value: CoexperiencedSceneEpisode) -> dict[str, object]:
    return {
        "coexperienced_scalar_text": value.coexperienced_scalar_text,
        "engine_id": value.engine_id,
        "episode_receipt_payload_hex": value.episode_receipt_payload.hex(),
        "episode_receipt_sha256": value.episode_receipt_sha256,
        "motif_receipt_sha256": value.motif_receipt_sha256,
        "profile_binding_sha256": value.profile_binding_sha256,
        "scene_language_text": value.scene_language_text,
        "scene_task_id": value.scene_task_id,
        "sensory_evidence_receipt_sha256s": list(
            value.sensory_evidence_receipt_sha256s
        ),
    }


def coexperienced_scene_archive_checkpoint_payload(
    *,
    archive: CoexperiencedSceneArchive,
    checkpoint_id: str,
    authentication_key: bytes,
    key_id: str,
) -> bytes:
    if not isinstance(archive, CoexperiencedSceneArchive):
        raise ReceiptError("coexperienced scene checkpoint lacks an archive")
    require_identifier(checkpoint_id, "coexperienced scene checkpoint id")
    require_identifier(key_id, "coexperienced scene checkpoint key id")
    if not isinstance(authentication_key, bytes) or not authentication_key:
        raise ReceiptError("coexperienced scene checkpoint authentication key is absent")
    body = {
        "archive_receipt_sha256": archive.receipt_sha256,
        "checkpoint_id": checkpoint_id,
        "episodes": [_episode_body(value) for value in archive.episodes],
        "schema": COEXPERIENCED_SCENE_ARCHIVE_CHECKPOINT_SCHEMA,
    }
    signature = hmac.new(
        authentication_key,
        _canonical_bytes(body),
        hashlib.sha256,
    ).hexdigest()
    return _canonical_bytes(
        {
            "authentication": {
                "algorithm": ARCHIVE_CHECKPOINT_ALGORITHM,
                "key_id": key_id,
                "signature_sha256": signature,
            },
            "body": body,
        }
    )


_EPISODE_BODY_KEYS = frozenset(
    (
        "coexperienced_scalar_text",
        "engine_id",
        "episode_receipt_payload_hex",
        "episode_receipt_sha256",
        "motif_receipt_sha256",
        "profile_binding_sha256",
        "scene_language_text",
        "scene_task_id",
        "sensory_evidence_receipt_sha256s",
    )
)


def _restore_episode(value: object) -> CoexperiencedSceneEpisode:
    if not isinstance(value, dict):
        raise ReceiptError("coexperienced scene checkpoint episode is malformed")
    _expect_exact_keys(value, _EPISODE_BODY_KEYS, "coexperienced scene checkpoint episode")
    string_fields = (
        "coexperienced_scalar_text",
        "engine_id",
        "episode_receipt_payload_hex",
        "episode_receipt_sha256",
        "motif_receipt_sha256",
        "profile_binding_sha256",
        "scene_language_text",
        "scene_task_id",
    )
    if not all(isinstance(value.get(key), str) for key in string_fields):
        raise ReceiptError("coexperienced scene checkpoint episode fields are malformed")
    receipts = []
    for index, item in enumerate(
        _expect_list(
            value["sensory_evidence_receipt_sha256s"],
            "coexperienced scene checkpoint sensory receipts",
        )
    ):
        if not isinstance(item, str):
            raise ReceiptError(
                f"coexperienced scene checkpoint sensory receipt[{index}] is malformed"
            )
        receipts.append(item)
    episode = create_coexperienced_scene_episode(
        profile_binding_sha256=value["profile_binding_sha256"],  # type: ignore[arg-type]
        motif_receipt_sha256=value["motif_receipt_sha256"],  # type: ignore[arg-type]
        sensory_evidence_receipt_sha256s=tuple(receipts),
        coexperienced_scalar_text=value["coexperienced_scalar_text"],  # type: ignore[arg-type]
        scene_task_id=value["scene_task_id"],  # type: ignore[arg-type]
        scene_language_text=value["scene_language_text"],  # type: ignore[arg-type]
        engine_id=value["engine_id"],  # type: ignore[arg-type]
    )
    stored_payload = _hex_bytes(
        value["episode_receipt_payload_hex"],
        "coexperienced scene checkpoint episode payload",
    )
    if (
        episode.episode_receipt_sha256 != value["episode_receipt_sha256"]
        or episode.episode_receipt_payload != stored_payload
    ):
        raise ReceiptError(
            "coexperienced scene checkpoint episode differs from its content address"
        )
    return episode


def restore_coexperienced_scene_archive_checkpoint(
    *,
    checkpoint_payload: bytes,
    authentication_key: bytes,
    expected_key_id: str,
) -> CoexperiencedSceneArchive:
    if not isinstance(authentication_key, bytes) or not authentication_key:
        raise ReceiptError("coexperienced scene checkpoint authentication key is absent")
    require_identifier(expected_key_id, "coexperienced scene checkpoint expected key id")
    envelope = _strict_json_object(
        checkpoint_payload,
        "coexperienced scene checkpoint envelope",
    )
    _expect_exact_keys(
        envelope,
        frozenset(("authentication", "body")),
        "coexperienced scene checkpoint envelope",
    )
    authentication = envelope["authentication"]
    body = envelope["body"]
    if not isinstance(authentication, dict) or not isinstance(body, dict):
        raise ReceiptError("coexperienced scene checkpoint envelope is malformed")
    _expect_exact_keys(
        authentication,
        frozenset(("algorithm", "key_id", "signature_sha256")),
        "coexperienced scene checkpoint authentication",
    )
    _expect_exact_keys(
        body,
        frozenset(("archive_receipt_sha256", "checkpoint_id", "episodes", "schema")),
        "coexperienced scene checkpoint body",
    )
    if (
        authentication.get("algorithm") != ARCHIVE_CHECKPOINT_ALGORITHM
        or authentication.get("key_id") != expected_key_id
    ):
        raise ReceiptError("coexperienced scene checkpoint authentication authority changed")
    signature = authentication.get("signature_sha256")
    if not isinstance(signature, str) or _SHA256_RE.fullmatch(signature) is None:
        raise ReceiptError("coexperienced scene checkpoint signature is malformed")
    expected_signature = hmac.new(
        authentication_key,
        _canonical_bytes(body),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ReceiptError("coexperienced scene checkpoint authentication failed")
    if body.get("schema") != COEXPERIENCED_SCENE_ARCHIVE_CHECKPOINT_SCHEMA:
        raise ReceiptError("coexperienced scene checkpoint schema changed")
    checkpoint_id = body.get("checkpoint_id")
    if not isinstance(checkpoint_id, str):
        raise ReceiptError("coexperienced scene checkpoint id is malformed")
    require_identifier(checkpoint_id, "coexperienced scene checkpoint id")
    archive = CoexperiencedSceneArchive(
        tuple(
            _restore_episode(value)
            for value in _expect_list(
                body["episodes"], "coexperienced scene checkpoint episodes"
            )
        )
    )
    archive_digest = body.get("archive_receipt_sha256")
    if not isinstance(archive_digest, str):
        raise ReceiptError("coexperienced scene checkpoint root receipt is malformed")
    if sha256_digest(
        archive_digest, "coexperienced scene checkpoint root receipt"
    ) != archive.receipt_sha256:
        raise ReceiptError("coexperienced scene checkpoint root changed")
    return archive


__all__ = (
    "COEXPERIENCED_SCENE_ARCHIVE_CHECKPOINT_SCHEMA",
    "COEXPERIENCED_SCENE_ARCHIVE_SCHEMA",
    "COEXPERIENCED_SCENE_EPISODE_SCHEMA",
    "CoexperiencedSceneArchive",
    "CoexperiencedSceneEpisode",
    "coexperienced_scene_archive_checkpoint_payload",
    "coexperienced_scene_archive_receipt_payload",
    "coexperienced_scene_episode_receipt_payload",
    "create_coexperienced_scene_episode",
    "restore_coexperienced_scene_archive_checkpoint",
)
