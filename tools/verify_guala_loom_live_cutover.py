#!/usr/bin/env python3
"""Fail-closed proof for the public observation_snapshot.v5 surfaces.

The verifier proves that:

* the public observation response is one internally receipted v5 snapshot;
* the reviewed and served Guala/Loom bytes are identical;
* both pages make exactly one read-only API call, to the v5 observation route;
* neither page contains scripted mutation, conversation, recognition, browser
  speech, teaching authority, legacy status, event, or routing identity;
* the reviewed live camera element remains sensory transport only;
* protected physical-action routes remain protected and the retired bootstrap
  route remains absent.

The browser surfaces observe supplied state only. They do not evaluate,
compress, score, or decide from the DSF field.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


VERIFICATION_SCHEMA = "guala.loom_live_cutover_verification.v2"
OBSERVATION_SCHEMA = "guala.observation_snapshot.v5"
CAUSAL_THING_SCHEMA = (
    "guala.truthful_loom.causal_thing_observation.v1"
)
SIGHT_ARTICULATION_SCHEMA = (
    "guala.truthful_loom."
    "consequence_evoked_articulatory_observation.v1"
)
FULL_FIELD_NAMES = (
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
)

DEFAULT_OBSERVATION_URL = (
    "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
    "/api/v1/gualaloom/observation"
)
DEFAULT_CAUSAL_INQUIRY_TRANSIENT_ACT_URL = (
    "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
    "/api/v1/causal-inquiry/transient-act"
)
DEFAULT_CAUSAL_INQUIRY_TRANSIENT_CONSEQUENCE_URL = (
    "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
    "/api/v1/causal-inquiry/transient-consequence"
)
DEFAULT_EMBODIMENT_ACTION_EXPERIENCE_URL = (
    "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
    "/api/v1/embodiment/action-experience"
)
DEFAULT_LEARNED_BODY_ACT_TRIAL_START_URL = (
    "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
    "/api/v1/embodiment/learned-body-act-trial"
)
DEFAULT_LEARNED_BODY_ACT_TRIAL_POLL_URL = (
    "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
    "/api/v1/embodiment/learned-body-act-trial/"
    "0000000000000000000000000000000000000000000000000000000000000000"
)
DEFAULT_RETIRED_TUTOR_BOOTSTRAP_URL = (
    "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
    "/api/v1/causal-inquiry/tutor-bootstrap"
)
DEFAULT_GUALALOOM_URL = "https://dsf-ai.com/gualaloom.html"
DEFAULT_LOOMSCAN_URL = "https://dsf-ai.com/loomscan.html"
DEFAULT_TIMEOUT_SECONDS = 20
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 60

MAX_OBSERVATION_BYTES = 1_048_576
MAX_GUALALOOM_BYTES = 262_144
MAX_LOOMSCAN_BYTES = 131_072
MAX_ROUTE_BOUNDARY_BYTES = 65_536
READ_CHUNK_BYTES = 65_536

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEWED_STATIC_DIR = REPO_ROOT / "dsf_ai_service" / "static"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_OBSERVATION_SCHEMA_PATTERN = re.compile(
    r"guala\.observation_snapshot\.v([0-9]+)"
)
_LITERAL_API_ROUTE_PATTERN = re.compile(
    r"""(?<![A-Za-z0-9_./-])((?:/api/v1/[A-Za-z0-9_./-]+)|/(?:sight|sound)_frame)(?![A-Za-z0-9_./-])"""
)
_PHYSICAL_SENSORY_INGRESS_ROUTES = {
    "/sight_frame",
    "/sound_frame",
    "/api/v1/visual/capture-contract",
    "/api/v1/auditory/pcm/open",
    "/api/v1/auditory/pcm/close",
    "/api/v1/auditory/binaural-pcm/open",
    "/api/v1/auditory/binaural-pcm/lineage",
    "/api/v1/auditory/binaural-pcm/chunk",
    "/api/v1/auditory/binaural-pcm/close",
}
_TYPED_INPUT_PATTERNS = (
    re.compile(
        r"""<input\b[^>]*\btype\s*=\s*(["'])text\1""",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"""\bcontenteditable\s*=\s*(["'])?true(?:\1)?""",
        re.IGNORECASE,
    ),
)
_FORBIDDEN_BROWSER_TOKENS = (
    "<audio",
    "speechSynthesis",
    "SpeechSynthesisUtterance",
    "teacher",
    "correction",
    "reply",
    "chi_density",
    "pollEvents",
    "upload",
    "takeSnapshot",
    "/api/v1/gualaloom/events",
    "/api/v1/gualaloom/chi_density",
    "/api/v1/gualaloom/admin/atlas_snapshot",
    "/status",
    "/events",
)
_GUALALOOM_REQUIRED_MARKERS = (
    "Guala — live experience",
    "/gualaloom-rich-room-v3.png",
    "Approved room artwork · illustrative only",
    "This image is non-authoritative artwork",
    "Camera offered to sight",
    "Actual substrate attention",
    "Physical sensory controls",
    "/api/v1/gualaloom/observation",
    "function renderObservation(",
    "async function pollObservation()",
    OBSERVATION_SCHEMA,
    "passive_whole_organism_thing_learning",
    "whole_organism_permanent_wiring",
    "latest_resolution",
    "reciprocal_exact_trace",
    "master_sense",
    "persistence_health",
    "physical_bytes",
    "Click Camera, Microphone, or Cards once to start and again to stop",
    "live browser audiovisual transport supplies sight and sound",
    "whole_organism_cognitive_progression",
    "dreaming",
    "Browser-generated speech and physical speaker authority are not claimed",
    "Only those pixels enter sight",
    "Human-side browser transcript · not Guala cognition",
    "No authenticated learned-articulation transcription supplied",
    "Settled physical auditory evidence",
    "A motif firing is not rendered as a transcript, word, or recognition",
    "auditory_physical_experience",
    "Give picture",
    "Unavailable: production exposes no public authenticated PDF",
    "Project Gutenberg",
    "YouTube",
    "Khan Academy",
    "Spotify",
)
_LOOMSCAN_REQUIRED_MARKERS = (
    "Read-only observation_snapshot.v5 instrument",
    "Decision authority: false",
    "Biological localization authority: false",
    "Read-only live organism evidence",
    "Sensory receptor populations",
    "Causal thought / action loop",
    "Settled physical auditory experience",
    "Motif activity grants no transcript, word, or recognition authority",
    "auditory_physical_experience",
    "Permanent mechanism wiring",
    "Full DSF observation",
    "Bounded persistence",
    "/api/v1/gualaloom/observation",
    "function renderMechanisms(",
    "function renderNeurons(",
    "function renderGrowth(",
    "function renderFullField(",
    "async function pollObservation()",
    OBSERVATION_SCHEMA,
    "passive_whole_organism_thing_learning",
    "whole_organism_permanent_wiring",
    "physical_bytes",
    "dreaming",
    "Retained mechanism state is not new activity",
    "Quiescent, unavailable, and not observed are never painted as active",
)


class ResponseLike(Protocol):
    status: int
    headers: Mapping[str, str]

    def read(self, amount: int = -1) -> bytes: ...

    def geturl(self) -> str: ...

    def __enter__(self) -> "ResponseLike": ...

    def __exit__(self, exc_type, exc_value, traceback) -> None: ...


class OpenerLike(Protocol):
    def open(
        self,
        request: urllib.request.Request,
        timeout: int,
    ) -> ResponseLike: ...


class CutoverVerificationError(RuntimeError):
    """One stable fail-closed diagnostic."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class _DuplicateJSONKey(ValueError):
    pass


@dataclass(frozen=True)
class ResourceSpec:
    name: str
    url: str
    maximum_bytes: int
    expected_content_type: str


@dataclass(frozen=True)
class RouteBoundarySpec:
    name: str
    url: str
    expected_status: int
    method: str = "POST"


@dataclass(frozen=True)
class FetchedResource:
    name: str
    url: str
    body: bytes
    content_type: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


@dataclass(frozen=True)
class VerificationConfig:
    observation_url: str = DEFAULT_OBSERVATION_URL
    causal_inquiry_transient_act_url: str = (
        DEFAULT_CAUSAL_INQUIRY_TRANSIENT_ACT_URL
    )
    causal_inquiry_transient_consequence_url: str = (
        DEFAULT_CAUSAL_INQUIRY_TRANSIENT_CONSEQUENCE_URL
    )
    embodiment_action_experience_url: str = (
        DEFAULT_EMBODIMENT_ACTION_EXPERIENCE_URL
    )
    learned_body_act_trial_start_url: str = (
        DEFAULT_LEARNED_BODY_ACT_TRIAL_START_URL
    )
    learned_body_act_trial_poll_url: str = (
        DEFAULT_LEARNED_BODY_ACT_TRIAL_POLL_URL
    )
    retired_tutor_bootstrap_url: str = (
        DEFAULT_RETIRED_TUTOR_BOOTSTRAP_URL
    )
    gualaloom_url: str = DEFAULT_GUALALOOM_URL
    loomscan_url: str = DEFAULT_LOOMSCAN_URL
    reviewed_static_dir: Path = DEFAULT_REVIEWED_STATIC_DIR
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def verify(self) -> None:
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int)
            or not (
                MIN_TIMEOUT_SECONDS
                <= self.timeout_seconds
                <= MAX_TIMEOUT_SECONDS
            )
        ):
            raise CutoverVerificationError(
                "configuration.timeout",
                (
                    "timeout_seconds must be an integer from "
                    f"{MIN_TIMEOUT_SECONDS} through {MAX_TIMEOUT_SECONDS}"
                ),
            )
        for name, value in (
            ("observation_url", self.observation_url),
            (
                "causal_inquiry_transient_act_url",
                self.causal_inquiry_transient_act_url,
            ),
            (
                "causal_inquiry_transient_consequence_url",
                self.causal_inquiry_transient_consequence_url,
            ),
            (
                "embodiment_action_experience_url",
                self.embodiment_action_experience_url,
            ),
            (
                "learned_body_act_trial_start_url",
                self.learned_body_act_trial_start_url,
            ),
            (
                "learned_body_act_trial_poll_url",
                self.learned_body_act_trial_poll_url,
            ),
            (
                "retired_tutor_bootstrap_url",
                self.retired_tutor_bootstrap_url,
            ),
            ("gualaloom_url", self.gualaloom_url),
            ("loomscan_url", self.loomscan_url),
        ):
            if (
                not isinstance(value, str)
                or not value.startswith("https://")
                or any(character.isspace() for character in value)
            ):
                raise CutoverVerificationError(
                    f"configuration.{name}",
                    "live cutover URLs must be explicit HTTPS URLs",
                )
        if not isinstance(self.reviewed_static_dir, Path):
            raise CutoverVerificationError(
                "configuration.reviewed_static_dir",
                "reviewed_static_dir must be a filesystem path",
            )


def _fail(code: str, detail: str) -> None:
    raise CutoverVerificationError(code, detail)


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        _fail(code, detail)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    value = headers.get(name)
    return value if value is not None else headers.get(name.lower())


def _bounded_read(
    response: ResponseLike,
    *,
    resource_name: str,
    maximum_bytes: int,
) -> bytes:
    content_length = _header(response.headers, "Content-Length")
    if content_length is not None:
        try:
            declared_bytes = int(content_length)
        except ValueError:
            _fail(
                f"{resource_name}.content_length",
                "Content-Length is not an integer",
            )
        if declared_bytes < 0:
            _fail(
                f"{resource_name}.content_length",
                "Content-Length is negative",
            )
        if declared_bytes > maximum_bytes:
            _fail(
                f"{resource_name}.response_too_large",
                (
                    f"declared {declared_bytes} bytes exceeds "
                    f"the {maximum_bytes}-byte ceiling"
                ),
            )
    chunks: list[bytes] = []
    total = 0
    while True:
        amount = min(READ_CHUNK_BYTES, maximum_bytes + 1 - total)
        chunk = response.read(amount)
        if not isinstance(chunk, bytes):
            _fail(
                f"{resource_name}.response_type",
                "HTTP response body was not bytes",
            )
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        total += len(chunk)
        if total > maximum_bytes:
            _fail(
                f"{resource_name}.response_too_large",
                f"response exceeds the {maximum_bytes}-byte ceiling",
            )


def _fetch(
    spec: ResourceSpec,
    *,
    opener: OpenerLike,
    timeout_seconds: int,
) -> FetchedResource:
    request = urllib.request.Request(
        spec.url,
        method="GET",
        headers={
            "Accept": spec.expected_content_type,
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
            "User-Agent": "guala-observation-surface-verifier/3",
        },
    )
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", None)
            if status != 200:
                _fail(
                    f"{spec.name}.http_status",
                    f"expected HTTP 200, received {status!r}",
                )
            if response.geturl() != spec.url:
                _fail(
                    f"{spec.name}.redirect",
                    f"request resolved to unexpected URL {response.geturl()!r}",
                )
            raw_content_type = _header(response.headers, "Content-Type")
            content_type = (
                raw_content_type.split(";", 1)[0].strip().lower()
                if raw_content_type is not None else ""
            )
            if content_type != spec.expected_content_type:
                _fail(
                    f"{spec.name}.content_type",
                    (
                        f"expected {spec.expected_content_type}, "
                        f"received {content_type or 'missing'}"
                    ),
                )
            body = _bounded_read(
                response,
                resource_name=spec.name,
                maximum_bytes=spec.maximum_bytes,
            )
    except CutoverVerificationError:
        raise
    except urllib.error.HTTPError as error:
        _fail(
            f"{spec.name}.http_status",
            f"expected HTTP 200, received {error.code}",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        _fail(
            f"{spec.name}.transport",
            f"request failed with {type(error).__name__}",
        )
    return FetchedResource(
        name=spec.name,
        url=spec.url,
        body=body,
        content_type=content_type,
    )


def _verify_route_boundary(
    spec: RouteBoundarySpec,
    *,
    opener: OpenerLike,
    timeout_seconds: int,
) -> dict[str, object]:
    request = urllib.request.Request(
        spec.url,
        data=(b"" if spec.method == "POST" else None),
        method=spec.method,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "User-Agent": "guala-observation-surface-verifier/3",
        },
    )
    try:
        try:
            response = opener.open(request, timeout=timeout_seconds)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            status = getattr(response, "status", None)
            if response.geturl() != spec.url:
                _fail(
                    f"{spec.name}.redirect",
                    f"request resolved to unexpected URL {response.geturl()!r}",
                )
            _bounded_read(
                response,
                resource_name=spec.name,
                maximum_bytes=MAX_ROUTE_BOUNDARY_BYTES,
            )
    except CutoverVerificationError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        _fail(
            f"{spec.name}.transport",
            f"request failed with {type(error).__name__}",
        )
    _require(
        status == spec.expected_status,
        f"{spec.name}.http_status",
        (
            f"expected HTTP {spec.expected_status}, "
            f"received {status!r}"
        ),
    )
    return {
        "authentication_supplied": False,
        "expected_status": spec.expected_status,
        "method": spec.method,
        "status": status,
        "url": spec.url,
    }


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value}")


def _unique_mapping(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKey(key)
        result[key] = value
    return result


def _mapping(
    value: object,
    *,
    code: str,
    name: str,
) -> Mapping[str, object]:
    _require(isinstance(value, Mapping), code, f"{name} must be an object")
    return value


def _false_authorities(
    value: object,
    *,
    code: str,
    names: tuple[str, ...],
) -> None:
    authorities = _mapping(value, code=code, name="authorities")
    for name in names:
        _require(
            authorities.get(name) is False,
            code,
            f"{name} authority must be explicitly false",
        )


def _verify_observation(resource: FetchedResource) -> dict[str, object]:
    try:
        text = resource.body.decode("utf-8", errors="strict")
        decoded = json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_mapping,
        )
    except UnicodeDecodeError:
        _fail("observation.utf8", "response is not strict UTF-8")
    except _DuplicateJSONKey as error:
        _fail(
            "observation.json_duplicate_key",
            f"duplicate JSON key {str(error)!r}",
        )
    except (json.JSONDecodeError, ValueError):
        _fail("observation.json", "response is not strict JSON")
    value = _mapping(
        decoded,
        code="observation.shape",
        name="observation response",
    )
    _require(
        value.get("schema") == OBSERVATION_SCHEMA,
        "observation.schema",
        f"expected {OBSERVATION_SCHEMA}",
    )
    required_top_level = (
        "observed_at_tick",
        "identity",
        "embodiment",
        "embodied_action",
        "full_field_authority",
        "integrated_thing_memory",
        "sight_evoked_articulatory_action",
        "causal_action",
        "causal_thing_action",
        "snapshot_receipt_sha256",
    )
    missing = [name for name in required_top_level if name not in value]
    _require(
        not missing,
        "observation.required_fields",
        f"missing required v5 fields: {','.join(missing)}",
    )
    tick = value["observed_at_tick"]
    _require(
        isinstance(tick, int) and not isinstance(tick, bool) and tick >= 0,
        "observation.observed_at_tick",
        "observed_at_tick must be a nonnegative integer",
    )
    _require(
        isinstance(value["identity"], str) and bool(value["identity"]),
        "observation.identity",
        "identity must be nonempty text",
    )
    for name in ("embodiment", "embodied_action", "causal_action"):
        _mapping(
            value[name],
            code=f"observation.{name}",
            name=name,
        )
    full_field = _mapping(
        value["full_field_authority"],
        code="observation.full_field_authority",
        name="full_field_authority",
    )
    contract = _mapping(
        full_field.get("view_contract"),
        code="observation.full_field_view_contract",
        name="full-field view_contract",
    )
    _require(
        contract.get("decision_authority") is False,
        "observation.full_field_view_contract",
        "full-field observation must have no decision authority",
    )
    _require(
        contract.get("projection") == "latest_exact_tuple_per_substream",
        "observation.full_field_view_contract",
        "full-field projection contract changed",
    )
    _require(
        contract.get("required_fields") == list(FULL_FIELD_NAMES),
        "observation.full_field_view_contract",
        "full-field required field order changed",
    )
    projection_loss = contract.get("projection_loss")
    _require(
        isinstance(projection_loss, str) and bool(projection_loss.strip()),
        "observation.full_field_view_contract",
        "full-field projection loss must be explicit",
    )
    senses = full_field.get("senses")
    _require(
        isinstance(senses, list),
        "observation.full_field_authority",
        "full-field senses must be a list",
    )
    for sense_index, sense_value in enumerate(senses):
        sense = _mapping(
            sense_value,
            code="observation.full_field_authority",
            name=f"sense {sense_index}",
        )
        substreams = sense.get("substreams")
        _require(
            isinstance(substreams, list),
            "observation.full_field_authority",
            f"sense {sense_index} substreams must be a list",
        )
        for substream_index, substream_value in enumerate(substreams):
            substream = _mapping(
                substream_value,
                code="observation.full_field_authority",
                name=f"sense {sense_index} substream {substream_index}",
            )
            fields = substream.get("fields")
            names = [
                item[0]
                for item in fields
                if isinstance(fields, list)
                and isinstance(item, list)
                and len(item) == 2
            ] if isinstance(fields, list) else []
            _require(
                isinstance(fields, list)
                and names == list(FULL_FIELD_NAMES)
                and len(fields) == len(FULL_FIELD_NAMES),
                "observation.full_field_authority",
                (
                    f"sense {sense_index} substream {substream_index} "
                    "does not expose the exact full field"
                ),
            )
    thing = _mapping(
        value["integrated_thing_memory"],
        code="observation.integrated_thing_memory",
        name="integrated_thing_memory",
    )
    _require(
        thing.get("schema") == CAUSAL_THING_SCHEMA,
        "observation.integrated_thing_memory",
        f"expected {CAUSAL_THING_SCHEMA}",
    )
    _false_authorities(
        thing.get("authorities"),
        code="observation.integrated_thing_memory",
        names=("cognition", "decision", "meaning"),
    )
    _require(
        thing.get("full_field_preserved_upstream") is True
        and thing.get("reduced_approximation") is False,
        "observation.integrated_thing_memory",
        "causal THING view must preserve the unreduced full field upstream",
    )
    articulation = _mapping(
        value["sight_evoked_articulatory_action"],
        code="observation.sight_articulation",
        name="sight_evoked_articulatory_action",
    )
    _require(
        articulation.get("schema") == SIGHT_ARTICULATION_SCHEMA,
        "observation.sight_articulation",
        f"expected {SIGHT_ARTICULATION_SCHEMA}",
    )
    _false_authorities(
        articulation.get("authorities"),
        code="observation.sight_articulation",
        names=(
            "cognition",
            "decision",
            "label",
            "legacy_route",
            "meaning",
            "speech_understanding",
            "transcript",
            "word",
        ),
    )
    _require(
        articulation.get("retained_pcm_bytes") == 0,
        "observation.sight_articulation",
        "Loom articulation observation must retain no PCM",
    )
    transient = _mapping(
        articulation.get("transient_act"),
        code="observation.sight_articulation",
        name="sight articulation transient_act",
    )
    _require(
        set(transient) == {"committed", "pcm_byte_count", "pcm_sha256"},
        "observation.sight_articulation",
        "transient act boundary changed",
    )
    causal_thing_action = _mapping(
        value["causal_thing_action"],
        code="observation.causal_thing_action",
        name="causal_thing_action",
    )
    _require(
        causal_thing_action.get("full_dsf_field_preserved") is True
        and causal_thing_action.get("reduced_approximation") is False,
        "observation.causal_thing_action",
        "causal THING action must preserve the unreduced full DSF field",
    )
    for optional in (
        "passive_whole_organism_thing_learning",
        "persistence_health",
        "whole_organism_cognitive_progression",
        "dreaming",
    ):
        if optional in value:
            _mapping(
                value[optional],
                code=f"observation.{optional}",
                name=optional,
            )
    receipt = value["snapshot_receipt_sha256"]
    _require(
        isinstance(receipt, str)
        and _SHA256_PATTERN.fullmatch(receipt) is not None,
        "observation.snapshot_receipt",
        "snapshot receipt must be a lowercase SHA-256 identity",
    )
    receipt_payload = dict(value)
    del receipt_payload["snapshot_receipt_sha256"]
    expected_receipt = hashlib.sha256(json.dumps(
        receipt_payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()
    _require(
        receipt == expected_receipt,
        "observation.snapshot_receipt",
        "snapshot receipt does not match the observed payload",
    )
    return {
        "bytes": len(resource.body),
        "observed_at_tick": tick,
        "schema": OBSERVATION_SCHEMA,
        "sha256": resource.sha256,
        "snapshot_receipt_sha256": receipt,
        "url": resource.url,
    }


def _verify_html_contract(
    resource: FetchedResource,
    *,
    reviewed_path: Path,
    required_markers: tuple[str, ...],
) -> dict[str, object]:
    try:
        text = resource.body.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _fail(f"{resource.name}.utf8", "response is not strict UTF-8")
    versions = {
        int(match)
        for match in _OBSERVATION_SCHEMA_PATTERN.findall(text)
    }
    _require(
        versions == {5},
        f"{resource.name}.legacy_schema",
        (
            "observation schema references must be exactly v5; "
            f"found {sorted(versions)}"
        ),
    )
    for marker in required_markers:
        _require(
            marker in text,
            f"{resource.name}.truthful_contract",
            f"required reviewed marker is absent: {marker!r}",
        )
    for pattern in _TYPED_INPUT_PATTERNS:
        _require(
            pattern.search(text) is None,
            f"{resource.name}.typed_chat",
            "typed chat input is present",
        )
    for token in _FORBIDDEN_BROWSER_TOKENS:
        _require(
            token not in text,
            (
                f"{resource.name}.chi_atlas_polling"
                if token in {
                    "chi_density",
                    "/api/v1/gualaloom/chi_density",
                    "/api/v1/gualaloom/admin/atlas_snapshot",
                }
                else f"{resource.name}.browser_speech"
                if token in {
                    "speechSynthesis",
                    "SpeechSynthesisUtterance",
                }
                else f"{resource.name}.retired_surface"
            ),
            f"retired browser token is present: {token}",
        )
    is_gualaloom = resource.name == "gualaloom"
    if not is_gualaloom:
        _require(
            "method:\"POST\"" not in text and "method:'POST'" not in text,
            f"{resource.name}.mutation",
            "browser POST behavior is present",
        )
    routes = set(_LITERAL_API_ROUTE_PATTERN.findall(text))
    expected_routes = {"/api/v1/gualaloom/observation"}
    if is_gualaloom:
        expected_routes.update(_PHYSICAL_SENSORY_INGRESS_ROUTES)
    _require(
        routes == expected_routes,
        f"{resource.name}.network_graph",
        f"browser API routes changed: {sorted(routes)}",
    )
    try:
        reviewed = reviewed_path.read_bytes()
    except OSError as error:
        _fail(
            f"{resource.name}.reviewed_source",
            f"reviewed source is unreadable: {type(error).__name__}",
        )
    reviewed_sha256 = hashlib.sha256(reviewed).hexdigest()
    _require(
        resource.body == reviewed,
        f"{resource.name}.reviewed_content_mismatch",
        (
            f"live sha256 {resource.sha256} does not match "
            f"reviewed sha256 {reviewed_sha256}"
        ),
    )
    return {
        "bytes": len(resource.body),
        "reviewed_sha256": reviewed_sha256,
        "sha256": resource.sha256,
        "url": resource.url,
    }


def verify_live_cutover(
    config: VerificationConfig,
    *,
    opener: OpenerLike | None = None,
) -> dict[str, object]:
    """Prove the three public resources and six route boundaries."""

    config.verify()
    live_opener = opener or urllib.request.build_opener()
    observation = _fetch(
        ResourceSpec(
            name="observation",
            url=config.observation_url,
            maximum_bytes=MAX_OBSERVATION_BYTES,
            expected_content_type="application/json",
        ),
        opener=live_opener,
        timeout_seconds=config.timeout_seconds,
    )
    route_boundaries = {}
    for spec in (
        RouteBoundarySpec(
            "causal_inquiry_transient_act",
            config.causal_inquiry_transient_act_url,
            401,
        ),
        RouteBoundarySpec(
            "causal_inquiry_transient_consequence",
            config.causal_inquiry_transient_consequence_url,
            401,
        ),
        RouteBoundarySpec(
            "embodiment_action_experience",
            config.embodiment_action_experience_url,
            401,
        ),
        RouteBoundarySpec(
            "learned_body_act_trial_start",
            config.learned_body_act_trial_start_url,
            401,
        ),
        RouteBoundarySpec(
            "learned_body_act_trial_poll",
            config.learned_body_act_trial_poll_url,
            401,
            method="GET",
        ),
        RouteBoundarySpec(
            "retired_causal_inquiry_tutor_bootstrap",
            config.retired_tutor_bootstrap_url,
            404,
        ),
    ):
        route_boundaries[spec.name] = _verify_route_boundary(
            spec,
            opener=live_opener,
            timeout_seconds=config.timeout_seconds,
        )
    gualaloom = _fetch(
        ResourceSpec(
            name="gualaloom",
            url=config.gualaloom_url,
            maximum_bytes=MAX_GUALALOOM_BYTES,
            expected_content_type="text/html",
        ),
        opener=live_opener,
        timeout_seconds=config.timeout_seconds,
    )
    loomscan = _fetch(
        ResourceSpec(
            name="loomscan",
            url=config.loomscan_url,
            maximum_bytes=MAX_LOOMSCAN_BYTES,
            expected_content_type="text/html",
        ),
        opener=live_opener,
        timeout_seconds=config.timeout_seconds,
    )
    return {
        "resources": {
            "gualaloom": _verify_html_contract(
                gualaloom,
                reviewed_path=(
                    config.reviewed_static_dir / "gualaloom.html"
                ),
                required_markers=_GUALALOOM_REQUIRED_MARKERS,
            ),
            "loomscan": _verify_html_contract(
                loomscan,
                reviewed_path=(
                    config.reviewed_static_dir / "loomscan.html"
                ),
                required_markers=_LOOMSCAN_REQUIRED_MARKERS,
            ),
            "observation": _verify_observation(observation),
        },
        "route_boundaries": route_boundaries,
        "schema": VERIFICATION_SCHEMA,
        "status": "verified",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prove the public v5 observation API, protected physical routes, "
            "retired bootstrap route, and reviewed observation-only pages."
        ),
    )
    parser.add_argument("--observation-url", default=DEFAULT_OBSERVATION_URL)
    parser.add_argument(
        "--causal-inquiry-transient-act-url",
        default=DEFAULT_CAUSAL_INQUIRY_TRANSIENT_ACT_URL,
    )
    parser.add_argument(
        "--causal-inquiry-transient-consequence-url",
        default=DEFAULT_CAUSAL_INQUIRY_TRANSIENT_CONSEQUENCE_URL,
    )
    parser.add_argument(
        "--embodiment-action-experience-url",
        default=DEFAULT_EMBODIMENT_ACTION_EXPERIENCE_URL,
    )
    parser.add_argument(
        "--learned-body-act-trial-start-url",
        default=DEFAULT_LEARNED_BODY_ACT_TRIAL_START_URL,
    )
    parser.add_argument(
        "--learned-body-act-trial-poll-url",
        default=DEFAULT_LEARNED_BODY_ACT_TRIAL_POLL_URL,
    )
    parser.add_argument(
        "--retired-tutor-bootstrap-url",
        default=DEFAULT_RETIRED_TUTOR_BOOTSTRAP_URL,
    )
    parser.add_argument("--gualaloom-url", default=DEFAULT_GUALALOOM_URL)
    parser.add_argument("--loomscan-url", default=DEFAULT_LOOMSCAN_URL)
    parser.add_argument(
        "--reviewed-static-dir",
        type=Path,
        default=DEFAULT_REVIEWED_STATIC_DIR,
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = VerificationConfig(
        observation_url=args.observation_url,
        causal_inquiry_transient_act_url=(
            args.causal_inquiry_transient_act_url
        ),
        causal_inquiry_transient_consequence_url=(
            args.causal_inquiry_transient_consequence_url
        ),
        embodiment_action_experience_url=(
            args.embodiment_action_experience_url
        ),
        learned_body_act_trial_start_url=(
            args.learned_body_act_trial_start_url
        ),
        learned_body_act_trial_poll_url=(
            args.learned_body_act_trial_poll_url
        ),
        retired_tutor_bootstrap_url=args.retired_tutor_bootstrap_url,
        gualaloom_url=args.gualaloom_url,
        loomscan_url=args.loomscan_url,
        reviewed_static_dir=args.reviewed_static_dir,
        timeout_seconds=args.timeout_seconds,
    )
    try:
        proof = verify_live_cutover(config)
    except CutoverVerificationError as error:
        print(f"FAIL [{error.code}] {error.detail}", file=sys.stderr)
        return 1
    print(json.dumps(
        proof,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
