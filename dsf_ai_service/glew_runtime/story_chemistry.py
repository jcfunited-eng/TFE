"""Receipted virtual story-sense producer for the conserved chemical receiver.

This module is a replaceable physical boundary.  It does not turn words,
descriptors, hashes, or vocabulary entries into sensory values.  A caller must
provide an explicit boundary observation for every port that actually closes:
an exact start time, end time, signed native flux, physical unit, and provenance
receipt.  Ports absent from an event are not sampled and retain their state.

All receiver quantities come from an externally authenticated immutable
manifest.  The manifest supplies each port's local time unit, receptor mass,
initial R/A/D state, flux susceptibility, three inverse-time rates and their
derivations, normalized signal-unit authority, and an ordered set of pinned
backend precisions.  There are no numeric defaults in this adapter.

Evolution is atomic across the event.  A receipt failure, missing authority,
or unresolved numerical enclosure returns typed UNKNOWN with the exact prior
runtime object.  A successful result retains the full correlated R/A/D
enclosure, the separate signed native signal, and the complete A/R_total
relevance enclosure.  The relevance crosses the frozen binary64 kernel
boundary only when that entire enclosure proves one unique round-to-nearest,
ties-to-even binary64 value.  The signed manifest's precision sequence is
tried in order; no midpoint or nominal value is selected.

Persisted checkpoints are canonical authenticated envelopes.  Restart rebuilds
the receipt registry and correlated receiver states from those exact bytes and
verifies them before returning a runtime.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from importlib import resources
from typing import Iterable, Mapping, Sequence

from .certified_backend import CertifiedBall
from .closed_experience import (
    KernelNativeInputSample,
    KernelNativeInputStream,
    kernel_native_input_receipt_payload,
    source_evidence_stream_receipt_payload,
)
from .chemical_receiver import (
    CHEMICAL_AFFINE_CONSTRAINT_ID,
    ChemicalBackendAuthority,
    ChemicalEvolutionReceipt,
    ChemicalTimeUnitAuthority,
    CertifiedChemicalRelevance,
    CertifiedReceiverState,
    ExactReceiverState,
    KINETIC_RATE_TRANSITIONS,
    MountedActivationSusceptibility,
    MountedChemicalRate,
    NativeActivationInterval,
    ReceiverEvolutionAuthority,
    ReceiverEvolutionStatus,
    ReceiverState,
    ReceiverTransition,
    activation_susceptibility_authority_receipt_payload,
    certified_chemical_relevance_receipt_payload,
    chemical_backend_authority_receipt_payload,
    chemical_rate_authority_receipt_payload,
    chemical_time_unit_authority_receipt_payload,
    evolve_chemical_receiver,
    exact_receiver_state_receipt_payload,
    initial_receiver_authority_receipt_payload,
    native_activation_interval_receipt_payload,
    receiver_evolution_authority_receipt_payload,
)
from .model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)


STORY_CHEMISTRY_MANIFEST_SCHEMA = "glew.virtual_story_chemistry_manifest.v2"
STORY_CHEMISTRY_CHECKPOINT_SCHEMA = "glew.virtual_story_chemistry_checkpoint.v1"
STORY_BOUNDARY_OBSERVATION_SCHEMA = "glew.virtual_story_physical_boundary.v1"
STORY_BINARY64_RELEVANCE_SCHEMA = "glew.certified_binary64_relevance.v1"
STORY_AUTHENTICATION_ALGORITHM = "HMAC-SHA256"
PRODUCTION_STORY_CHEMISTRY_AUTHORITY_SCOPE = (
    "production_virtual_story_emulator_nondimensional_authority"
)
PRODUCTION_STORY_CHEMISTRY_MANIFEST_ID = (
    "production-nondimensional-five-sense-virtual-story-chemistry-v1"
)
PRODUCTION_STORY_CHEMISTRY_PROFILE_RESOURCE = (
    "profiles/production_virtual_story_chemistry_profile_v1.json"
)
PRODUCTION_STORY_PORT_LANES = (
    ("story-auditory.native-port-0", "sound"),
    ("story-smell.native-port-0", "smell"),
    ("story-taste.native-port-0", "taste"),
    ("story-touch.native-port-0", "touch"),
    ("story-vision.native-port-0", "sight"),
)

_CANONICAL_FRACTION_RE = re.compile(r"(?:0|-[1-9][0-9]*|[1-9][0-9]*)/[1-9][0-9]*\Z")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "story chemistry fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, field_name: str) -> Fraction:
    if not isinstance(value, str) or _CANONICAL_FRACTION_RE.fullmatch(value) is None:
        raise ReceiptError(f"{field_name} must be a canonical numerator/denominator string")
    numerator_text, denominator_text = value.split("/", 1)
    parsed = Fraction(int(numerator_text), int(denominator_text))
    if _fraction_text(parsed) != value:
        raise ReceiptError(f"{field_name} must be reduced to canonical form")
    return parsed


def _identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ReceiptError(f"{field_name} must be a string")
    return require_identifier(value, field_name)


def _positive_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ReceiptError(f"{field_name} must be an explicit positive integer")
    return value


def _expect_object(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ReceiptError(f"{field_name} must be an object")
    return value


def _expect_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list) or not value:
        raise ReceiptError(f"{field_name} must be a nonempty array")
    return value


def _expect_keys(
    value: Mapping[str, object],
    expected: Sequence[str],
    field_name: str,
) -> None:
    actual = set(value)
    required = set(expected)
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        raise ReceiptError(
            f"{field_name} has wrong fields; missing={missing}, extra={extra}"
        )


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ReceiptError(f"signed JSON contains duplicate field {key!r}")
        result[key] = value
    return result


def _parse_json(payload: bytes, field_name: str) -> dict[str, object]:
    if not isinstance(payload, bytes) or not payload:
        raise ReceiptError(f"{field_name} must be nonempty exact bytes")
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_strict_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{field_name} is not strict UTF-8 JSON") from exc
    return _expect_object(value, field_name)


def _payload_digest(payload: bytes, expected: object, field_name: str) -> str:
    digest = sha256_digest(expected, field_name)  # type: ignore[arg-type]
    if receipt_sha256(payload) != digest:
        raise ReceiptError(f"{field_name} differs from the signed manifest")
    return digest


def _verify_authenticated_envelope(
    *,
    envelope_payload: bytes,
    trusted_authentication_key: bytes,
    expected_key_id: str,
    field_name: str,
) -> tuple[dict[str, object], bytes, str]:
    if not isinstance(trusted_authentication_key, bytes) or not trusted_authentication_key:
        raise ReceiptError(f"{field_name} trusted authentication key is missing")
    require_identifier(expected_key_id, f"{field_name} expected key id")
    envelope = _parse_json(envelope_payload, field_name)
    _expect_keys(envelope, ("authentication", "body"), field_name)
    authentication = _expect_object(
        envelope["authentication"], f"{field_name}.authentication"
    )
    _expect_keys(
        authentication,
        ("algorithm", "key_id", "signature_sha256"),
        f"{field_name}.authentication",
    )
    if authentication["algorithm"] != STORY_AUTHENTICATION_ALGORITHM:
        raise ReceiptError(f"{field_name} authentication algorithm is not mounted")
    key_id = _identifier(authentication["key_id"], f"{field_name} key id")
    if key_id != expected_key_id:
        raise ReceiptError(f"{field_name} was authenticated by another key id")
    signature = sha256_digest(
        authentication["signature_sha256"],  # type: ignore[arg-type]
        f"{field_name} signature",
    )
    body = _expect_object(envelope["body"], f"{field_name}.body")
    body_payload = _canonical_bytes(body)
    expected_signature = hmac.new(
        trusted_authentication_key,
        body_payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ReceiptError(f"{field_name} authentication failed")
    return body, body_payload, key_id


def authenticated_story_envelope_payload(
    *, body: Mapping[str, object], authentication_key: bytes, key_id: str
) -> bytes:
    """Create an exact authenticated envelope for an already supplied body.

    This helper supplies no physical values.  It only canonicalizes and
    authenticates the caller's complete body.
    """

    if not isinstance(authentication_key, bytes) or not authentication_key:
        raise ReceiptError("story authentication key is missing")
    require_identifier(key_id, "story authentication key id")
    body_payload = _canonical_bytes(dict(body))
    signature = hmac.new(authentication_key, body_payload, hashlib.sha256).hexdigest()
    return _canonical_bytes(
        {
            "authentication": {
                "algorithm": STORY_AUTHENTICATION_ALGORITHM,
                "key_id": key_id,
                "signature_sha256": signature,
            },
            "body": dict(body),
        }
    )


def _validated_production_profile_body(
    profile_body_payload: bytes,
) -> dict[str, object]:
    body = _parse_json(
        profile_body_payload,
        "production story chemistry profile body",
    )
    canonical = _canonical_bytes(body)
    if profile_body_payload not in (canonical, canonical + b"\n"):
        raise ReceiptError(
            "production story chemistry profile must be canonical exact bytes "
            "with at most one terminal LF"
        )
    _expect_keys(
        body,
        ("authority_scope", "backends", "manifest_id", "ports", "schema"),
        "production story chemistry profile body",
    )
    if body["schema"] != STORY_CHEMISTRY_MANIFEST_SCHEMA:
        raise ReceiptError("production story chemistry schema is not mounted")
    if body["authority_scope"] != PRODUCTION_STORY_CHEMISTRY_AUTHORITY_SCOPE:
        raise ReceiptError("production story chemistry authority scope is not mounted")
    if body["manifest_id"] != PRODUCTION_STORY_CHEMISTRY_MANIFEST_ID:
        raise ReceiptError("production story chemistry manifest id is not mounted")
    raw_ports = _expect_list(body["ports"], "production story chemistry ports")
    identities = []
    for index, raw_port in enumerate(raw_ports):
        port = _expect_object(
            raw_port,
            f"production story chemistry ports[{index}]",
        )
        port_id = _identifier(
            port.get("port_id"),
            f"production story chemistry ports[{index}].port_id",
        )
        binding = _expect_object(
            port.get("kernel_binding"),
            f"production story chemistry ports[{index}].kernel_binding",
        )
        lane_id = _identifier(
            binding.get("lane_id"),
            f"production story chemistry ports[{index}].kernel_binding.lane_id",
        )
        identities.append((port_id, lane_id))
    if tuple(identities) != PRODUCTION_STORY_PORT_LANES:
        raise ReceiptError(
            "production story chemistry does not exactly mount five approved senses"
        )
    return body


def production_story_chemistry_profile_payload() -> bytes:
    """Read the packaged production body without supplying authentication."""

    return (
        resources.files("dsf_ai_service.glew_runtime")
        .joinpath(PRODUCTION_STORY_CHEMISTRY_PROFILE_RESOURCE)
        .read_bytes()
    )


def authenticate_production_story_chemistry_profile(
    *,
    profile_body_payload: bytes,
    runtime_authentication_key: bytes,
    runtime_key_id: str,
) -> bytes:
    """Authenticate the canonical production body through a runtime secret."""

    body = _validated_production_profile_body(profile_body_payload)
    return authenticated_story_envelope_payload(
        body=body,
        authentication_key=runtime_authentication_key,
        key_id=runtime_key_id,
    )


def mount_production_story_chemistry_profile(
    *,
    profile_body_payload: bytes,
    runtime_authentication_key: bytes,
    runtime_key_id: str,
) -> StoryChemistryMountResult:
    """Authenticate and mount the five-sense production virtual profile."""

    try:
        envelope = authenticate_production_story_chemistry_profile(
            profile_body_payload=profile_body_payload,
            runtime_authentication_key=runtime_authentication_key,
            runtime_key_id=runtime_key_id,
        )
    except ReceiptError as exc:
        return StoryChemistryMountResult(
            status=StoryChemistryStatus.UNKNOWN,
            runtime=None,
            reason=str(exc),
        )
    mounted = mount_story_chemistry(
        manifest_envelope_payload=envelope,
        trusted_authentication_key=runtime_authentication_key,
        expected_key_id=runtime_key_id,
    )
    if mounted.runtime is None:
        return mounted
    manifest = mounted.runtime.manifest
    identity_receipts = tuple(
        (
            port.native_signal_unit_authority_receipt_sha256,
            port.kernel_binding.authority_receipt_sha256,
            port.time_unit.authority_receipt_sha256,
            port.activation_susceptibility.authority_receipt_sha256,
            port.initial_state.receipt_sha256,
        )
        for port in manifest.ports
    )
    if len(set(identity_receipts)) != len(PRODUCTION_STORY_PORT_LANES):
        return StoryChemistryMountResult(
            status=StoryChemistryStatus.UNKNOWN,
            runtime=None,
            reason="production story senses do not have independent authorities",
        )
    return mounted


def mount_packaged_production_story_chemistry(
    *,
    runtime_authentication_key: bytes,
    runtime_key_id: str,
) -> StoryChemistryMountResult:
    """Mount the packaged profile through the caller's runtime secret boundary."""

    return mount_production_story_chemistry_profile(
        profile_body_payload=production_story_chemistry_profile_payload(),
        runtime_authentication_key=runtime_authentication_key,
        runtime_key_id=runtime_key_id,
    )


def story_kernel_binding_authority_receipt_payload(
    *,
    adapter_id: str,
    lane_id: str,
    port_id: str,
    native_signal_unit_authority_receipt_sha256: str,
    derivation_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "adapter_id": require_identifier(adapter_id, "story kernel adapter_id"),
            "derivation_receipt_sha256": sha256_digest(
                derivation_receipt_sha256,
                "story kernel binding derivation receipt",
            ),
            "kernel_map": {
                "forward": "F=1+s/2",
                "inverse": "s=2*(F-1)",
                "normalized_signal_domain": "[-1,1]",
                "relevance": "certified_binary64_fraction_identity",
            },
            "lane_id": require_identifier(lane_id, "story kernel lane_id"),
            "native_signal_unit_authority_receipt_sha256": sha256_digest(
                native_signal_unit_authority_receipt_sha256,
                "story kernel normalized-signal authority receipt",
            ),
            "port_id": require_identifier(port_id, "story kernel port_id"),
            "schema": "glew.virtual_story_frozen_kernel_binding.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class StoryKernelBindingAuthority:
    adapter_id: str
    lane_id: str
    port_id: str
    native_signal_unit_authority_receipt_sha256: str
    derivation_receipt_sha256: str
    authority_receipt_sha256: str
    authority_receipt_payload: bytes

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.native_signal_unit_authority_receipt_sha256,
            "story kernel normalized-signal authority receipt",
        )
        receipt_registry.resolve(
            self.derivation_receipt_sha256,
            "story kernel binding derivation receipt",
        )
        expected = story_kernel_binding_authority_receipt_payload(
            adapter_id=self.adapter_id,
            lane_id=self.lane_id,
            port_id=self.port_id,
            native_signal_unit_authority_receipt_sha256=(
                self.native_signal_unit_authority_receipt_sha256
            ),
            derivation_receipt_sha256=self.derivation_receipt_sha256,
        )
        if (
            self.authority_receipt_payload != expected
            or receipt_sha256(expected) != self.authority_receipt_sha256
            or receipt_registry.resolve(
                self.authority_receipt_sha256,
                "story kernel binding authority receipt",
            )
            != expected
        ):
            raise ReceiptError(
                "story frozen-kernel binding differs from its mounted receipt"
            )


@dataclass(frozen=True, slots=True)
class StoryPortChemicalAuthority:
    port_id: str
    native_signal_unit: str
    native_signal_unit_authority_receipt_sha256: str
    native_signal_unit_authority_payload: bytes
    kernel_binding: StoryKernelBindingAuthority
    time_unit: ChemicalTimeUnitAuthority
    activation_susceptibility: MountedActivationSusceptibility
    rates: tuple[MountedChemicalRate, ...]
    initial_state: ExactReceiverState


@dataclass(frozen=True, slots=True)
class SignedStoryChemistryManifest:
    manifest_id: str
    authority_scope: str
    authentication_key_id: str
    canonical_payload: bytes
    receipt_sha256: str
    backends: tuple[ChemicalBackendAuthority, ...]
    ports: tuple[StoryPortChemicalAuthority, ...]
    static_receipt_payloads: tuple[bytes, ...]

    def port(self, port_id: str) -> StoryPortChemicalAuthority:
        for value in self.ports:
            if value.port_id == port_id:
                return value
        raise ReceiptError("story boundary observation names an unmounted port")


class StoryChemistryStatus(str, Enum):
    MOUNTED = "mounted"
    EVOLVED = "evolved"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class StoryChemistryRuntime:
    manifest: SignedStoryChemistryManifest
    states: tuple[ReceiverState, ...]
    receipt_registry: ReceiptRegistry

    def state(self, port_id: str) -> ReceiverState:
        for value in self.states:
            if value.port_id == port_id:
                return value
        raise ReceiptError("story chemistry state is absent for a mounted port")


@dataclass(frozen=True, slots=True)
class StoryChemistryMountResult:
    status: StoryChemistryStatus
    runtime: StoryChemistryRuntime | None
    reason: str


def _derivation_payload(value: object, field_name: str) -> bytes:
    derivation = _expect_object(value, field_name)
    _expect_keys(
        derivation,
        ("basis", "explanation", "receipt_id"),
        field_name,
    )
    _identifier(derivation["receipt_id"], f"{field_name}.receipt_id")
    _identifier(derivation["basis"], f"{field_name}.basis")
    _identifier(derivation["explanation"], f"{field_name}.explanation")
    return _canonical_bytes(derivation)


def _parse_backend(
    value: object,
    field_name: str,
) -> tuple[ChemicalBackendAuthority, bytes]:
    backend = _expect_object(value, field_name)
    _expect_keys(
        backend,
        ("authority_id", "authority_receipt_sha256", "working_precision_bits"),
        field_name,
    )
    authority_id = _identifier(backend["authority_id"], f"{field_name}.authority_id")
    precision = _positive_integer(
        backend["working_precision_bits"], f"{field_name}.working_precision_bits"
    )
    payload = chemical_backend_authority_receipt_payload(
        authority_id=authority_id,
        working_precision_bits=precision,
    )
    digest = _payload_digest(
        payload,
        backend["authority_receipt_sha256"],
        f"{field_name}.authority_receipt_sha256",
    )
    return (
        ChemicalBackendAuthority(
            authority_id=authority_id,
            working_precision_bits=precision,
            authority_receipt_sha256=digest,
        ),
        payload,
    )


def _parse_time_unit(
    value: object,
    field_name: str,
) -> tuple[ChemicalTimeUnitAuthority, tuple[bytes, bytes]]:
    time_unit = _expect_object(value, field_name)
    _expect_keys(
        time_unit,
        (
            "authority_id",
            "authority_receipt_sha256",
            "derivation",
            "seconds_per_unit",
            "time_unit_id",
        ),
        field_name,
    )
    authority_id = _identifier(time_unit["authority_id"], f"{field_name}.authority_id")
    time_unit_id = _identifier(time_unit["time_unit_id"], f"{field_name}.time_unit_id")
    seconds_per_unit = _fraction(
        time_unit["seconds_per_unit"], f"{field_name}.seconds_per_unit"
    )
    if seconds_per_unit <= 0:
        raise ReceiptError(f"{field_name}.seconds_per_unit must be positive")
    derivation_payload = _derivation_payload(
        time_unit["derivation"], f"{field_name}.derivation"
    )
    authority_payload = chemical_time_unit_authority_receipt_payload(
        authority_id=authority_id,
        time_unit_id=time_unit_id,
        seconds_per_unit=seconds_per_unit,
        derivation_receipt_sha256=receipt_sha256(derivation_payload),
    )
    authority_digest = _payload_digest(
        authority_payload,
        time_unit["authority_receipt_sha256"],
        f"{field_name}.authority_receipt_sha256",
    )
    return (
        ChemicalTimeUnitAuthority(
            authority_id=authority_id,
            time_unit_id=time_unit_id,
            seconds_per_unit=seconds_per_unit,
            derivation_receipt_sha256=receipt_sha256(derivation_payload),
            authority_receipt_sha256=authority_digest,
        ),
        (derivation_payload, authority_payload),
    )


def _parse_signal_unit(
    *, value: object, native_signal_unit: str, field_name: str
) -> tuple[str, bytes]:
    authority = _expect_object(value, field_name)
    _expect_keys(
        authority,
        (
            "authority_receipt_sha256",
            "basis",
            "dimension",
            "explanation",
            "receipt_id",
            "unit",
        ),
        field_name,
    )
    for key in ("basis", "dimension", "explanation", "receipt_id", "unit"):
        _identifier(authority[key], f"{field_name}.{key}")
    if authority["unit"] != native_signal_unit:
        raise ReceiptError("native signal-unit authority names another unit")
    payload_body = {
        key: authority[key]
        for key in ("basis", "dimension", "explanation", "receipt_id", "unit")
    }
    payload = _canonical_bytes(payload_body)
    digest = _payload_digest(
        payload,
        authority["authority_receipt_sha256"],
        f"{field_name}.authority_receipt_sha256",
    )
    return digest, payload


def _parse_kernel_binding(
    *,
    value: object,
    port_id: str,
    native_signal_unit_authority_receipt_sha256: str,
    field_name: str,
) -> tuple[StoryKernelBindingAuthority, tuple[bytes, bytes]]:
    binding = _expect_object(value, field_name)
    _expect_keys(
        binding,
        (
            "adapter_id",
            "authority_receipt_sha256",
            "derivation",
            "lane_id",
        ),
        field_name,
    )
    adapter_id = _identifier(binding["adapter_id"], f"{field_name}.adapter_id")
    lane_id = _identifier(binding["lane_id"], f"{field_name}.lane_id")
    derivation_payload = _derivation_payload(
        binding["derivation"], f"{field_name}.derivation"
    )
    authority_payload = story_kernel_binding_authority_receipt_payload(
        adapter_id=adapter_id,
        lane_id=lane_id,
        port_id=port_id,
        native_signal_unit_authority_receipt_sha256=(
            native_signal_unit_authority_receipt_sha256
        ),
        derivation_receipt_sha256=receipt_sha256(derivation_payload),
    )
    authority_digest = _payload_digest(
        authority_payload,
        binding["authority_receipt_sha256"],
        f"{field_name}.authority_receipt_sha256",
    )
    return (
        StoryKernelBindingAuthority(
            adapter_id,
            lane_id,
            port_id,
            native_signal_unit_authority_receipt_sha256,
            receipt_sha256(derivation_payload),
            authority_digest,
            authority_payload,
        ),
        (derivation_payload, authority_payload),
    )


def _parse_activation_susceptibility(
    *,
    value: object,
    port_id: str,
    native_signal_unit: str,
    native_signal_unit_authority_receipt_sha256: str,
    time_unit: ChemicalTimeUnitAuthority,
    field_name: str,
) -> tuple[MountedActivationSusceptibility, tuple[bytes, bytes]]:
    susceptibility = _expect_object(value, field_name)
    _expect_keys(
        susceptibility,
        (
            "authority_receipt_sha256",
            "derivation",
            "susceptibility_id",
            "susceptibility_per_native_signal_unit_per_time_unit",
        ),
        field_name,
    )
    susceptibility_id = _identifier(
        susceptibility["susceptibility_id"],
        f"{field_name}.susceptibility_id",
    )
    coefficient = _fraction(
        susceptibility[
            "susceptibility_per_native_signal_unit_per_time_unit"
        ],
        f"{field_name}.susceptibility_per_native_signal_unit_per_time_unit",
    )
    if coefficient < 0:
        raise ReceiptError("story activation susceptibility cannot be negative")
    derivation_payload = _derivation_payload(
        susceptibility["derivation"], f"{field_name}.derivation"
    )
    authority_payload = activation_susceptibility_authority_receipt_payload(
        susceptibility_id=susceptibility_id,
        port_id=port_id,
        susceptibility_per_native_signal_unit_per_time_unit=coefficient,
        native_signal_unit=native_signal_unit,
        native_signal_unit_authority_receipt_sha256=(
            native_signal_unit_authority_receipt_sha256
        ),
        time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
        derivation_receipt_sha256=receipt_sha256(derivation_payload),
    )
    authority_digest = _payload_digest(
        authority_payload,
        susceptibility["authority_receipt_sha256"],
        f"{field_name}.authority_receipt_sha256",
    )
    return (
        MountedActivationSusceptibility(
            susceptibility_id=susceptibility_id,
            port_id=port_id,
            susceptibility_per_native_signal_unit_per_time_unit=coefficient,
            native_signal_unit=native_signal_unit,
            native_signal_unit_authority_receipt_sha256=(
                native_signal_unit_authority_receipt_sha256
            ),
            time_unit_authority_receipt_sha256=(
                time_unit.authority_receipt_sha256
            ),
            derivation_receipt_sha256=receipt_sha256(derivation_payload),
            authority_receipt_sha256=authority_digest,
        ),
        (derivation_payload, authority_payload),
    )


def _parse_rates(
    *,
    value: object,
    port_id: str,
    time_unit: ChemicalTimeUnitAuthority,
    field_name: str,
) -> tuple[tuple[MountedChemicalRate, ...], tuple[bytes, ...]]:
    raw_rates = _expect_list(value, field_name)
    if len(raw_rates) != len(KINETIC_RATE_TRANSITIONS):
        raise ReceiptError(
            "story manifest requires exactly three inverse-time receiver rates"
        )
    rates: list[MountedChemicalRate] = []
    payloads: list[bytes] = []
    for index, (raw, transition) in enumerate(
        zip(raw_rates, KINETIC_RATE_TRANSITIONS, strict=True)
    ):
        rate_name = f"{field_name}[{index}]"
        rate = _expect_object(raw, rate_name)
        _expect_keys(
            rate,
            (
                "authority_receipt_sha256",
                "derivation",
                "rate_id",
                "rate_per_time_unit",
                "transition",
            ),
            rate_name,
        )
        if rate["transition"] != transition.value:
            raise ReceiptError("story receiver rates are not in canonical transition order")
        rate_id = _identifier(rate["rate_id"], f"{rate_name}.rate_id")
        rate_value = _fraction(
            rate["rate_per_time_unit"], f"{rate_name}.rate_per_time_unit"
        )
        if rate_value < 0:
            raise ReceiptError("story receiver transition rate cannot be negative")
        derivation_payload = _derivation_payload(
            rate["derivation"], f"{rate_name}.derivation"
        )
        authority_payload = chemical_rate_authority_receipt_payload(
            rate_id=rate_id,
            port_id=port_id,
            transition=transition,
            rate_per_time_unit=rate_value,
            time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
            derivation_receipt_sha256=receipt_sha256(derivation_payload),
        )
        authority_digest = _payload_digest(
            authority_payload,
            rate["authority_receipt_sha256"],
            f"{rate_name}.authority_receipt_sha256",
        )
        rates.append(
            MountedChemicalRate(
                rate_id=rate_id,
                port_id=port_id,
                transition=transition,
                rate_per_time_unit=rate_value,
                time_unit_authority_receipt_sha256=(
                    time_unit.authority_receipt_sha256
                ),
                derivation_receipt_sha256=receipt_sha256(derivation_payload),
                authority_receipt_sha256=authority_digest,
            )
        )
        payloads.extend((derivation_payload, authority_payload))
    rate_ids = tuple(value.rate_id for value in rates)
    if len(set(rate_ids)) != len(rate_ids):
        raise ReceiptError("story receiver rate authority ids must be unique")
    return tuple(rates), tuple(payloads)


def _parse_initial_state(
    *,
    value: object,
    port_id: str,
    time_unit: ChemicalTimeUnitAuthority,
    field_name: str,
) -> tuple[ExactReceiverState, tuple[bytes, ...]]:
    state = _expect_object(value, field_name)
    _expect_keys(
        state,
        (
            "active_mass",
            "authority_receipt_sha256",
            "derivation",
            "desensitized_mass",
            "initial_condition_id",
            "receipt_sha256",
            "resting_mass",
            "source_time",
            "total_receptor_mass",
        ),
        field_name,
    )
    condition_id = _identifier(
        state["initial_condition_id"], f"{field_name}.initial_condition_id"
    )
    source_time = _fraction(state["source_time"], f"{field_name}.source_time")
    total = _fraction(
        state["total_receptor_mass"], f"{field_name}.total_receptor_mass"
    )
    resting = _fraction(state["resting_mass"], f"{field_name}.resting_mass")
    active = _fraction(state["active_mass"], f"{field_name}.active_mass")
    desensitized = _fraction(
        state["desensitized_mass"], f"{field_name}.desensitized_mass"
    )
    if total <= 0 or any(value < 0 for value in (resting, active, desensitized)):
        raise ReceiptError("story initial receptor masses violate the nonnegative domain")
    if resting + active + desensitized != total:
        raise ReceiptError("story initial receptor masses violate R+A+D=R_total")
    derivation_payload = _derivation_payload(
        state["derivation"], f"{field_name}.derivation"
    )
    authority_payload = initial_receiver_authority_receipt_payload(
        initial_condition_id=condition_id,
        port_id=port_id,
        source_time=source_time,
        time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
        total_receptor_mass=total,
        resting_mass=resting,
        active_mass=active,
        desensitized_mass=desensitized,
        derivation_receipt_sha256=receipt_sha256(derivation_payload),
    )
    authority_digest = _payload_digest(
        authority_payload,
        state["authority_receipt_sha256"],
        f"{field_name}.authority_receipt_sha256",
    )
    state_payload = exact_receiver_state_receipt_payload(
        port_id=port_id,
        source_time=source_time,
        time_unit_id=time_unit.time_unit_id,
        time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
        total_receptor_mass=total,
        resting_mass=resting,
        active_mass=active,
        desensitized_mass=desensitized,
        initial_authority_receipt_sha256=authority_digest,
    )
    state_digest = _payload_digest(
        state_payload,
        state["receipt_sha256"],
        f"{field_name}.receipt_sha256",
    )
    result = ExactReceiverState(
        port_id=port_id,
        source_time=source_time,
        time_unit_id=time_unit.time_unit_id,
        time_unit_authority_receipt_sha256=time_unit.authority_receipt_sha256,
        total_receptor_mass=total,
        resting_mass=resting,
        active_mass=active,
        desensitized_mass=desensitized,
        initial_condition_id=condition_id,
        initial_derivation_receipt_sha256=receipt_sha256(derivation_payload),
        initial_authority_receipt_sha256=authority_digest,
        receipt_sha256=state_digest,
        receipt_payload=state_payload,
    )
    return result, (derivation_payload, authority_payload, state_payload)


def _parse_port(
    value: object,
    field_name: str,
) -> tuple[StoryPortChemicalAuthority, tuple[bytes, ...]]:
    port = _expect_object(value, field_name)
    _expect_keys(
        port,
        (
            "activation_susceptibility",
            "initial_state",
            "kernel_binding",
            "native_signal_unit",
            "native_signal_unit_authority",
            "port_id",
            "rates",
            "time_unit",
        ),
        field_name,
    )
    port_id = _identifier(port["port_id"], f"{field_name}.port_id")
    native_signal_unit = _identifier(
        port["native_signal_unit"], f"{field_name}.native_signal_unit"
    )
    unit_digest, unit_payload = _parse_signal_unit(
        value=port["native_signal_unit_authority"],
        native_signal_unit=native_signal_unit,
        field_name=f"{field_name}.native_signal_unit_authority",
    )
    kernel_binding, kernel_payloads = _parse_kernel_binding(
        value=port["kernel_binding"],
        port_id=port_id,
        native_signal_unit_authority_receipt_sha256=unit_digest,
        field_name=f"{field_name}.kernel_binding",
    )
    time_unit, time_payloads = _parse_time_unit(
        port["time_unit"], f"{field_name}.time_unit"
    )
    susceptibility, susceptibility_payloads = _parse_activation_susceptibility(
        value=port["activation_susceptibility"],
        port_id=port_id,
        native_signal_unit=native_signal_unit,
        native_signal_unit_authority_receipt_sha256=unit_digest,
        time_unit=time_unit,
        field_name=f"{field_name}.activation_susceptibility",
    )
    rates, rate_payloads = _parse_rates(
        value=port["rates"],
        port_id=port_id,
        time_unit=time_unit,
        field_name=f"{field_name}.rates",
    )
    state, state_payloads = _parse_initial_state(
        value=port["initial_state"],
        port_id=port_id,
        time_unit=time_unit,
        field_name=f"{field_name}.initial_state",
    )
    return (
        StoryPortChemicalAuthority(
            port_id=port_id,
            native_signal_unit=native_signal_unit,
            native_signal_unit_authority_receipt_sha256=unit_digest,
            native_signal_unit_authority_payload=unit_payload,
            kernel_binding=kernel_binding,
            time_unit=time_unit,
            activation_susceptibility=susceptibility,
            rates=rates,
            initial_state=state,
        ),
        (
            unit_payload,
            *kernel_payloads,
            *time_payloads,
            *susceptibility_payloads,
            *rate_payloads,
            *state_payloads,
        ),
    )


def _load_manifest(
    *,
    envelope_payload: bytes,
    trusted_authentication_key: bytes,
    expected_key_id: str,
) -> SignedStoryChemistryManifest:
    body, body_payload, key_id = _verify_authenticated_envelope(
        envelope_payload=envelope_payload,
        trusted_authentication_key=trusted_authentication_key,
        expected_key_id=expected_key_id,
        field_name="story chemistry manifest",
    )
    _expect_keys(
        body,
        ("authority_scope", "backends", "manifest_id", "ports", "schema"),
        "story chemistry manifest body",
    )
    if body["schema"] != STORY_CHEMISTRY_MANIFEST_SCHEMA:
        raise ReceiptError("story chemistry manifest schema is not mounted")
    manifest_id = _identifier(body["manifest_id"], "story chemistry manifest_id")
    authority_scope = _identifier(
        body["authority_scope"], "story chemistry authority_scope"
    )
    backends: list[ChemicalBackendAuthority] = []
    static_payloads: list[bytes] = []
    previous_precision: int | None = None
    for index, raw_backend in enumerate(
        _expect_list(body["backends"], "story chemistry backends")
    ):
        backend, payload = _parse_backend(
            raw_backend, f"story chemistry backends[{index}]"
        )
        if previous_precision is not None and backend.working_precision_bits <= previous_precision:
            raise ReceiptError(
                "story chemistry backend precisions must be explicitly increasing"
            )
        previous_precision = backend.working_precision_bits
        backends.append(backend)
        static_payloads.append(payload)
    backend_ids = tuple(value.authority_id for value in backends)
    if len(set(backend_ids)) != len(backend_ids):
        raise ReceiptError("story chemistry backend authority ids must be unique")
    ports: list[StoryPortChemicalAuthority] = []
    for index, raw_port in enumerate(_expect_list(body["ports"], "story chemistry ports")):
        port, payloads = _parse_port(raw_port, f"story chemistry ports[{index}]")
        ports.append(port)
        static_payloads.extend(payloads)
    port_ids = tuple(value.port_id for value in ports)
    if tuple(sorted(port_ids)) != port_ids or len(set(port_ids)) != len(port_ids):
        raise ReceiptError("story chemistry ports must be unique and canonically ordered")
    return SignedStoryChemistryManifest(
        manifest_id=manifest_id,
        authority_scope=authority_scope,
        authentication_key_id=key_id,
        canonical_payload=body_payload,
        receipt_sha256=receipt_sha256(body_payload),
        backends=tuple(backends),
        ports=tuple(ports),
        static_receipt_payloads=tuple(static_payloads),
    )


def _unique_payloads(payloads: Iterable[bytes]) -> tuple[bytes, ...]:
    by_digest: dict[str, bytes] = {}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("story chemistry receipt payload is missing")
        digest = receipt_sha256(payload)
        previous = by_digest.get(digest)
        if previous is not None and previous != payload:
            raise ReceiptError("story chemistry receipt digest collision")
        by_digest[digest] = payload
    return tuple(by_digest[digest] for digest in sorted(by_digest))


def _extend_registry(
    registry: ReceiptRegistry,
    payloads: Iterable[bytes],
) -> ReceiptRegistry:
    records = list(registry.records)
    known = {record.digest: record.payload for record in records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("story chemistry registry extension payload is missing")
        digest = receipt_sha256(payload)
        prior = known.get(digest)
        if prior is not None:
            if prior != payload:
                raise ReceiptError("story chemistry receipt digest collision")
            continue
        known[digest] = payload
        records.append(ReceiptRecord(digest=digest, payload=payload))
    return ReceiptRegistry(
        profile_binding_sha256=registry.profile_binding_sha256,
        records=tuple(records),
    )


def mount_story_chemistry(
    *,
    manifest_envelope_payload: bytes,
    trusted_authentication_key: bytes,
    expected_key_id: str,
) -> StoryChemistryMountResult:
    """Authenticate and mount an exact story chemistry manifest."""

    try:
        manifest = _load_manifest(
            envelope_payload=manifest_envelope_payload,
            trusted_authentication_key=trusted_authentication_key,
            expected_key_id=expected_key_id,
        )
        registry = ReceiptRegistry.from_payloads(
            profile_payload=manifest.canonical_payload,
            receipt_payloads=_unique_payloads(manifest.static_receipt_payloads),
        )
        for backend in manifest.backends:
            backend.verify(registry)
        for port in manifest.ports:
            port.kernel_binding.verify(registry)
            port.time_unit.verify(registry)
            port.activation_susceptibility.verify(registry)
            for rate in port.rates:
                rate.verify(registry)
            port.initial_state.verify(registry)
        runtime = StoryChemistryRuntime(
            manifest=manifest,
            states=tuple(port.initial_state for port in manifest.ports),
            receipt_registry=registry,
        )
    except ReceiptError as exc:
        return StoryChemistryMountResult(
            status=StoryChemistryStatus.UNKNOWN,
            runtime=None,
            reason=str(exc),
        )
    return StoryChemistryMountResult(
        status=StoryChemistryStatus.MOUNTED,
        runtime=runtime,
        reason="authenticated exact story chemistry manifest mounted",
    )


def story_boundary_observation_receipt_payload(
    *,
    event_id: str,
    observation_id: str,
    port_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    signed_native_flux: Fraction,
    native_flux_unit: str,
    provenance_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "event_id": require_identifier(event_id, "story event_id"),
            "native_flux": {
                "signed_value": _fraction_text(signed_native_flux),
                "unit": require_identifier(native_flux_unit, "story native flux unit"),
            },
            "observation_id": require_identifier(
                observation_id, "story observation_id"
            ),
            "port_id": require_identifier(port_id, "story observation port_id"),
            "provenance_receipt_sha256": sha256_digest(
                provenance_receipt_sha256,
                "story observation provenance receipt",
            ),
            "schema": STORY_BOUNDARY_OBSERVATION_SCHEMA,
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
        }
    )


@dataclass(frozen=True, slots=True)
class StoryPhysicalBoundaryObservation:
    event_id: str
    observation_id: str
    port_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    signed_native_flux: Fraction
    native_flux_unit: str
    provenance_receipt_sha256: str
    provenance_receipt_payload: bytes
    observation_receipt_sha256: str
    observation_receipt_payload: bytes

    def verify(self) -> None:
        require_identifier(self.event_id, "story event_id")
        require_identifier(self.observation_id, "story observation_id")
        require_identifier(self.port_id, "story observation port_id")
        require_fraction(self.source_time_start, "story observation start")
        require_fraction(self.source_time_end, "story observation end")
        if self.source_time_end <= self.source_time_start:
            raise ReceiptError("story physical boundary must have positive duration")
        require_fraction(self.signed_native_flux, "story signed native flux")
        require_identifier(self.native_flux_unit, "story native flux unit")
        if (
            not isinstance(self.provenance_receipt_payload, bytes)
            or not self.provenance_receipt_payload
        ):
            raise ReceiptError("story observation provenance receipt is missing")
        if receipt_sha256(self.provenance_receipt_payload) != sha256_digest(
            self.provenance_receipt_sha256,
            "story observation provenance receipt",
        ):
            raise ReceiptError("story observation provenance receipt was tampered")
        expected = story_boundary_observation_receipt_payload(
            event_id=self.event_id,
            observation_id=self.observation_id,
            port_id=self.port_id,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            signed_native_flux=self.signed_native_flux,
            native_flux_unit=self.native_flux_unit,
            provenance_receipt_sha256=self.provenance_receipt_sha256,
        )
        if (
            not isinstance(self.observation_receipt_payload, bytes)
            or self.observation_receipt_payload != expected
            or receipt_sha256(expected)
            != sha256_digest(
                self.observation_receipt_sha256,
                "story boundary observation receipt",
            )
        ):
            raise ReceiptError("story physical boundary receipt was tampered")


@dataclass(frozen=True, slots=True)
class StoryPhysicalBoundaryEvent:
    event_id: str
    observations: tuple[StoryPhysicalBoundaryObservation, ...]

    def verify(self) -> None:
        require_identifier(self.event_id, "story boundary event_id")
        if not isinstance(self.observations, tuple) or not self.observations:
            raise ReceiptError("story boundary event requires observations")
        port_ids: list[str] = []
        for observation in self.observations:
            if not isinstance(observation, StoryPhysicalBoundaryObservation):
                raise ReceiptError("story boundary event contains an untyped observation")
            observation.verify()
            if observation.event_id != self.event_id:
                raise ReceiptError("story observation belongs to another event")
            port_ids.append(observation.port_id)
        if tuple(sorted(port_ids)) != tuple(port_ids) or len(set(port_ids)) != len(port_ids):
            raise ReceiptError(
                "story boundary observations must be unique and canonically ordered by port"
            )


def _ball_payload(value: CertifiedBall) -> dict[str, object]:
    if not isinstance(value, CertifiedBall):
        raise ReceiptError("story relevance is not a certified enclosure")
    return {
        "flint_version": value.flint_version,
        "lower_exponent": value.lower_exponent,
        "lower_mantissa": value.lower_mantissa,
        "python_flint_version": value.python_flint_version,
        "upper_exponent": value.upper_exponent,
        "upper_mantissa": value.upper_mantissa,
        "wheel_sha256": value.wheel_sha256,
        "working_precision_bits": value.working_precision_bits,
    }


def _ball_bounds(value: CertifiedBall) -> tuple[Fraction, Fraction]:
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


def certified_binary64_relevance_receipt_payload(
    *, relevance: CertifiedChemicalRelevance, exact_binary64: Fraction
) -> bytes:
    return _canonical_bytes(
        {
            "complete_relevance_enclosure": _ball_payload(relevance.value),
            "exact_fraction_from_binary64": _fraction_text(exact_binary64),
            "relevance_receipt_sha256": relevance.receipt_sha256,
            "rounding": "IEEE_754_binary64_roundTiesToEven",
            "schema": STORY_BINARY64_RELEVANCE_SCHEMA,
            "unique_rounding_proof": "both_closed_enclosure_endpoints_round_identically",
        }
    )


class Binary64RoundingStatus(str, Enum):
    CERTIFIED = "certified"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CertifiedBinary64Relevance:
    status: Binary64RoundingStatus
    binary64_value: float | None
    exact_binary64: Fraction | None
    complete_enclosure: CertifiedBall | None
    relevance_receipt_sha256: str | None
    receipt_sha256: str | None
    receipt_payload: bytes | None
    reason: str


def certify_unique_binary64_relevance(
    *,
    relevance: CertifiedChemicalRelevance,
    receipt_registry: ReceiptRegistry,
) -> CertifiedBinary64Relevance:
    """Certify one unique binary64 value for the complete closed enclosure."""

    try:
        if not isinstance(relevance, CertifiedChemicalRelevance):
            raise ReceiptError("typed certified chemical relevance is missing")
        expected_relevance_payload = certified_chemical_relevance_receipt_payload(
            port_id=relevance.port_id,
            state_receipt_sha256=relevance.state_receipt_sha256,
            active_mass=relevance.active_mass,
            total_receptor_mass=relevance.total_receptor_mass,
            relevance=relevance.value,
        )
        mounted = receipt_registry.resolve(
            relevance.receipt_sha256, "certified chemical relevance receipt"
        )
        if (
            mounted != relevance.receipt_payload
            or relevance.receipt_payload != expected_relevance_payload
            or receipt_sha256(expected_relevance_payload) != relevance.receipt_sha256
        ):
            raise ReceiptError("certified chemical relevance receipt was tampered")
        lower, upper = _ball_bounds(relevance.value)
        lower_binary64 = float(lower)
        upper_binary64 = float(upper)
        if (
            not math.isfinite(lower_binary64)
            or not math.isfinite(upper_binary64)
            or lower_binary64 != upper_binary64
        ):
            return CertifiedBinary64Relevance(
                status=Binary64RoundingStatus.UNKNOWN,
                binary64_value=None,
                exact_binary64=None,
                complete_enclosure=relevance.value,
                relevance_receipt_sha256=relevance.receipt_sha256,
                receipt_sha256=None,
                receipt_payload=None,
                reason="complete relevance enclosure does not prove one binary64 value",
            )
        exact = Fraction.from_float(lower_binary64)
        payload = certified_binary64_relevance_receipt_payload(
            relevance=relevance,
            exact_binary64=exact,
        )
        return CertifiedBinary64Relevance(
            status=Binary64RoundingStatus.CERTIFIED,
            binary64_value=lower_binary64,
            exact_binary64=exact,
            complete_enclosure=relevance.value,
            relevance_receipt_sha256=relevance.receipt_sha256,
            receipt_sha256=receipt_sha256(payload),
            receipt_payload=payload,
            reason="complete relevance enclosure proves one binary64 value",
        )
    except (ReceiptError, OverflowError) as exc:
        enclosure = (
            relevance.value
            if isinstance(relevance, CertifiedChemicalRelevance)
            else None
        )
        digest = (
            relevance.receipt_sha256
            if isinstance(relevance, CertifiedChemicalRelevance)
            else None
        )
        return CertifiedBinary64Relevance(
            status=Binary64RoundingStatus.UNKNOWN,
            binary64_value=None,
            exact_binary64=None,
            complete_enclosure=enclosure,
            relevance_receipt_sha256=digest,
            receipt_sha256=None,
            receipt_payload=None,
            reason=str(exc),
        )


@dataclass(frozen=True, slots=True)
class StoryPortChemicalOutput:
    event_id: str
    observation_id: str
    port_id: str
    source_time_end: Fraction
    state: CertifiedReceiverState
    relevance: CertifiedChemicalRelevance
    kernel_binary64_relevance: CertifiedBinary64Relevance
    signed_native_flux: Fraction
    native_flux_unit: str
    native_observation_receipt_sha256: str
    chemical_evolution_receipt: ChemicalEvolutionReceipt
    backend_authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class StoryChemistryEvolutionResult:
    status: StoryChemistryStatus
    runtime: StoryChemistryRuntime
    outputs: tuple[StoryPortChemicalOutput, ...]
    reason: str


def _evolve_one_observation(
    *,
    runtime: StoryChemistryRuntime,
    state: ReceiverState,
    port: StoryPortChemicalAuthority,
    observation: StoryPhysicalBoundaryObservation,
    base_registry: ReceiptRegistry,
) -> tuple[StoryPortChemicalOutput | None, ReceiptRegistry | None, str]:
    if observation.native_flux_unit != port.native_signal_unit:
        return None, None, "story observation unit differs from mounted port authority"
    if observation.source_time_start != state.source_time:
        return None, None, "story observation does not begin at retained port state"
    interval_payload = native_activation_interval_receipt_payload(
        interval_id=observation.observation_id,
        port_id=observation.port_id,
        source_time_start=observation.source_time_start,
        source_time_end=observation.source_time_end,
        time_unit_authority_receipt_sha256=port.time_unit.authority_receipt_sha256,
        activation_susceptibility_receipt_sha256=(
            port.activation_susceptibility.authority_receipt_sha256
        ),
        signed_native_signal=observation.signed_native_flux,
        native_signal_unit=observation.native_flux_unit,
        native_signal_unit_authority_receipt_sha256=(
            port.native_signal_unit_authority_receipt_sha256
        ),
        native_observation_receipt_sha256=observation.observation_receipt_sha256,
    )
    interval = NativeActivationInterval(
        interval_id=observation.observation_id,
        port_id=observation.port_id,
        source_time_start=observation.source_time_start,
        source_time_end=observation.source_time_end,
        time_unit_authority_receipt_sha256=port.time_unit.authority_receipt_sha256,
        activation_susceptibility_receipt_sha256=(
            port.activation_susceptibility.authority_receipt_sha256
        ),
        signed_native_signal=observation.signed_native_flux,
        native_signal_unit=observation.native_flux_unit,
        native_signal_unit_authority_receipt_sha256=(
            port.native_signal_unit_authority_receipt_sha256
        ),
        native_observation_receipt_sha256=observation.observation_receipt_sha256,
        interval_receipt_sha256=receipt_sha256(interval_payload),
    )
    observation_registry = _extend_registry(
        base_registry,
        (
            observation.provenance_receipt_payload,
            observation.observation_receipt_payload,
            interval_payload,
        ),
    )
    for backend in runtime.manifest.backends:
        authority_id = (
            f"{runtime.manifest.manifest_id}:{observation.event_id}:"
            f"{observation.observation_id}:{backend.authority_id}"
        )
        authority_payload = receiver_evolution_authority_receipt_payload(
            authority_id=authority_id,
            port_id=observation.port_id,
            prior_state_receipt_sha256=state.receipt_sha256,
            activation_interval_receipt_sha256=interval.interval_receipt_sha256,
            activation_susceptibility_receipt_sha256=(
                port.activation_susceptibility.authority_receipt_sha256
            ),
            ordered_rate_receipt_sha256s=tuple(
                rate.authority_receipt_sha256 for rate in port.rates
            ),
            time_unit_authority_receipt_sha256=port.time_unit.authority_receipt_sha256,
            backend_authority_receipt_sha256=backend.authority_receipt_sha256,
        )
        authority = ReceiverEvolutionAuthority(
            authority_id=authority_id,
            port_id=observation.port_id,
            prior_state_receipt_sha256=state.receipt_sha256,
            activation_interval=interval,
            activation_susceptibility=port.activation_susceptibility,
            rates=port.rates,
            time_unit=port.time_unit,
            backend=backend,
            authority_receipt_sha256=receipt_sha256(authority_payload),
        )
        attempt_registry = _extend_registry(observation_registry, (authority_payload,))
        evolved = evolve_chemical_receiver(
            state=state,
            authority=authority,
            receipt_registry=attempt_registry,
        )
        if evolved.status is not ReceiverEvolutionStatus.EVOLVED:
            return None, None, evolved.reason
        if (
            not isinstance(evolved.state, CertifiedReceiverState)
            or not isinstance(evolved.relevance, CertifiedChemicalRelevance)
            or not isinstance(evolved.receipt, ChemicalEvolutionReceipt)
        ):
            return None, None, "chemical receiver returned an incomplete evolved result"
        generated_registry = _extend_registry(
            attempt_registry,
            (
                evolved.state.receipt_payload,
                evolved.relevance.receipt_payload,
                evolved.receipt.effective_activation.receipt_payload,
                evolved.receipt.generator.receipt_payload,
                evolved.receipt.receipt_payload,
            ),
        )
        evolved.state.verify(generated_registry)
        rounding = certify_unique_binary64_relevance(
            relevance=evolved.relevance,
            receipt_registry=generated_registry,
        )
        if rounding.status is Binary64RoundingStatus.UNKNOWN:
            continue
        if rounding.receipt_payload is None:
            return None, None, "certified binary64 relevance receipt is absent"
        final_registry = _extend_registry(
            generated_registry, (rounding.receipt_payload,)
        )
        return (
            StoryPortChemicalOutput(
                event_id=observation.event_id,
                observation_id=observation.observation_id,
                port_id=observation.port_id,
                source_time_end=observation.source_time_end,
                state=evolved.state,
                relevance=evolved.relevance,
                kernel_binary64_relevance=rounding,
                signed_native_flux=observation.signed_native_flux,
                native_flux_unit=observation.native_flux_unit,
                native_observation_receipt_sha256=(
                    observation.observation_receipt_sha256
                ),
                chemical_evolution_receipt=evolved.receipt,
                backend_authority_receipt_sha256=backend.authority_receipt_sha256,
            ),
            final_registry,
            "chemical receiver evolved with uniquely certified kernel relevance",
        )
    return (
        None,
        None,
        "signed backend precision sequence did not prove unique binary64 relevance",
    )


def evolve_story_chemistry_event(
    *,
    runtime: StoryChemistryRuntime,
    event: StoryPhysicalBoundaryEvent,
) -> StoryChemistryEvolutionResult:
    """Evolve all closing event ports atomically or retain the prior runtime."""

    if not isinstance(runtime, StoryChemistryRuntime):
        raise ReceiptError("story chemistry runtime is missing")
    try:
        event.verify()
        provisional_registry = runtime.receipt_registry
        state_by_port = {state.port_id: state for state in runtime.states}
        outputs: list[StoryPortChemicalOutput] = []
        for observation in event.observations:
            port = runtime.manifest.port(observation.port_id)
            state = state_by_port.get(observation.port_id)
            if not isinstance(state, (ExactReceiverState, CertifiedReceiverState)):
                raise ReceiptError("story chemistry retained state is missing")
            output, evolved_registry, reason = _evolve_one_observation(
                runtime=runtime,
                state=state,
                port=port,
                observation=observation,
                base_registry=provisional_registry,
            )
            if output is None or evolved_registry is None:
                raise ReceiptError(reason)
            state_by_port[observation.port_id] = output.state
            provisional_registry = evolved_registry
            outputs.append(output)
        new_states = tuple(state_by_port[port.port_id] for port in runtime.manifest.ports)
        for state in new_states:
            state.verify(provisional_registry)
        result_runtime = StoryChemistryRuntime(
            manifest=runtime.manifest,
            states=new_states,
            receipt_registry=provisional_registry,
        )
    except ReceiptError as exc:
        return StoryChemistryEvolutionResult(
            status=StoryChemistryStatus.UNKNOWN,
            runtime=runtime,
            outputs=(),
            reason=str(exc),
        )
    return StoryChemistryEvolutionResult(
        status=StoryChemistryStatus.EVOLVED,
        runtime=result_runtime,
        outputs=tuple(outputs),
        reason="all observed story ports evolved atomically",
    )


def story_kernel_relevance_sequence_receipt_payload(
    *,
    lane_id: str,
    port_id: str,
    output_receipt_sha256s: Sequence[str],
    certified_binary64_receipt_sha256s: Sequence[str],
) -> bytes:
    if len(output_receipt_sha256s) != len(
        certified_binary64_receipt_sha256s
    ) or not output_receipt_sha256s:
        raise ReceiptError("story kernel relevance sequence is incomplete")
    return _canonical_bytes(
        {
            "certified_binary64_receipt_sha256s": [
                sha256_digest(value, "story certified binary64 receipt")
                for value in certified_binary64_receipt_sha256s
            ],
            "chemical_evolution_receipt_sha256s": [
                sha256_digest(value, "story chemical evolution receipt")
                for value in output_receipt_sha256s
            ],
            "lane_id": require_identifier(lane_id, "story kernel lane_id"),
            "port_id": require_identifier(port_id, "story kernel port_id"),
            "relevance_rule": "certified_binary64_fraction_identity",
            "schema": "glew.virtual_story_kernel_relevance_sequence.v1",
        }
    )


class StoryKernelBridgeStatus(str, Enum):
    READY = "ready"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class StoryFrozenKernelInputs:
    status: StoryKernelBridgeStatus
    streams: tuple[EvidenceStream, ...]
    kernel_inputs: tuple[KernelNativeInputStream, ...]
    receipt_registry: ReceiptRegistry
    reason: str


def build_story_frozen_kernel_inputs(
    *,
    runtime: StoryChemistryRuntime,
    output_frames: tuple[tuple[StoryPortChemicalOutput, ...], ...],
    source_epoch: str,
) -> StoryFrozenKernelInputs:
    """Bind actual evolved story outputs to the frozen L0 input contract."""

    if not isinstance(runtime, StoryChemistryRuntime):
        raise ReceiptError("story chemistry runtime is missing")
    retained_registry = runtime.receipt_registry
    try:
        require_identifier(source_epoch, "story kernel source_epoch")
        if not isinstance(output_frames, tuple) or len(output_frames) < 2:
            raise ReceiptError(
                "frozen kernel story input requires at least two evolved frames"
            )
        expected_ports = tuple(port.port_id for port in runtime.manifest.ports)
        frames_by_port: dict[str, list[StoryPortChemicalOutput]] = {
            port_id: [] for port_id in expected_ports
        }
        previous_physical_time: Fraction | None = None
        for frame in output_frames:
            if not isinstance(frame, tuple) or tuple(
                output.port_id for output in frame
            ) != expected_ports:
                raise ReceiptError(
                    "each story kernel frame must exactly cover manifest ports"
                )
            physical_times = []
            for output, port in zip(frame, runtime.manifest.ports, strict=True):
                if not isinstance(output, StoryPortChemicalOutput):
                    raise ReceiptError("story kernel frame contains an untyped output")
                if output.source_time_end != output.state.source_time:
                    raise ReceiptError("story output state and boundary time differ")
                if output.signed_native_flux != (
                    output.chemical_evolution_receipt.effective_activation
                    .signed_native_signal
                ):
                    raise ReceiptError("story output lost its signed boundary flux")
                if not Fraction(-1) <= output.signed_native_flux <= Fraction(1):
                    raise ReceiptError(
                        "story normalized boundary flux lies outside [-1,1]"
                    )
                rounding = output.kernel_binary64_relevance
                if (
                    rounding.status is not Binary64RoundingStatus.CERTIFIED
                    or rounding.exact_binary64 is None
                    or rounding.receipt_sha256 is None
                    or rounding.receipt_payload is None
                ):
                    raise ReceiptError(
                        "story relevance lacks a unique certified binary64 value"
                    )
                if not 0 <= rounding.exact_binary64 <= 1:
                    raise ReceiptError("story certified relevance left [0,1]")
                for digest, payload, name in (
                    (
                        output.state.receipt_sha256,
                        output.state.receipt_payload,
                        "story output state receipt",
                    ),
                    (
                        output.relevance.receipt_sha256,
                        output.relevance.receipt_payload,
                        "story output relevance receipt",
                    ),
                    (
                        output.chemical_evolution_receipt.receipt_sha256,
                        output.chemical_evolution_receipt.receipt_payload,
                        "story chemical evolution receipt",
                    ),
                    (
                        rounding.receipt_sha256,
                        rounding.receipt_payload,
                        "story binary64 relevance receipt",
                    ),
                ):
                    if retained_registry.resolve(digest, name) != payload:
                        raise ReceiptError(f"{name} differs from mounted bytes")
                frames_by_port[port.port_id].append(output)
                physical_times.append(
                    output.source_time_end * port.time_unit.seconds_per_unit
                )
            if len(set(physical_times)) != 1:
                raise ReceiptError(
                    "multisensory story frame does not share one physical time"
                )
            physical_time = physical_times[0]
            if (
                previous_physical_time is not None
                and physical_time <= previous_physical_time
            ):
                raise ReceiptError(
                    "story kernel frame physical times are not strictly increasing"
                )
            previous_physical_time = physical_time

        working = retained_registry
        streams: list[EvidenceStream] = []
        adapters: list[KernelNativeInputStream] = []
        generated_payloads: list[bytes] = []
        for port in runtime.manifest.ports:
            binding = port.kernel_binding
            binding.verify(working)
            outputs = tuple(frames_by_port[port.port_id])
            evolution_digests = tuple(
                output.chemical_evolution_receipt.receipt_sha256
                for output in outputs
            )
            rounding_digests = tuple(
                output.kernel_binary64_relevance.receipt_sha256
                for output in outputs
            )
            if any(value is None for value in rounding_digests):
                raise ReceiptError("story kernel relevance receipt is absent")
            relevance_payload = story_kernel_relevance_sequence_receipt_payload(
                lane_id=binding.lane_id,
                port_id=port.port_id,
                output_receipt_sha256s=evolution_digests,
                certified_binary64_receipt_sha256s=tuple(
                    value for value in rounding_digests if value is not None
                ),
            )
            samples = tuple(
                EvidenceSample(
                    source_index=index,
                    timestamp=(
                        output.source_time_end * port.time_unit.seconds_per_unit
                    ),
                    signal=output.signed_native_flux,
                    relevance=output.kernel_binary64_relevance.exact_binary64,
                    phase_turns=Fraction(0),
                )
                for index, output in enumerate(outputs)
                if output.kernel_binary64_relevance.exact_binary64 is not None
            )
            if len(samples) != len(outputs):
                raise ReceiptError("story kernel sample relevance is incomplete")
            stream = EvidenceStream(
                lane_id=binding.lane_id,
                port_id=port.port_id,
                evidence_id=f"{source_epoch}:{port.port_id}:story-evidence",
                source_epoch=source_epoch,
                port_kind="independent_virtual_story_native_port",
                physical_unit=port.native_signal_unit,
                profile_binding_sha256=runtime.manifest.receipt_sha256,
                calibration_receipt_sha256=(
                    port.native_signal_unit_authority_receipt_sha256
                ),
                relevance_receipt_sha256=receipt_sha256(relevance_payload),
                samples=samples,
            )
            stream_payload = source_evidence_stream_receipt_payload(stream)
            kernel_samples = tuple(
                KernelNativeInputSample(
                    source_index=sample.source_index,
                    timestamp=sample.timestamp,
                    dimensionless_field=Fraction(1) + sample.signal / 2,
                    l0_relevance=sample.relevance,
                )
                for sample in samples
            )
            adapter_payload = kernel_native_input_receipt_payload(
                adapter_id=binding.adapter_id,
                adapter_profile_receipt_sha256=(
                    binding.authority_receipt_sha256
                ),
                lane_id=binding.lane_id,
                port_id=port.port_id,
                source_stream_receipt_sha256=receipt_sha256(stream_payload),
                samples=kernel_samples,
            )
            adapter = KernelNativeInputStream(
                adapter_id=binding.adapter_id,
                adapter_profile_receipt_sha256=(
                    binding.authority_receipt_sha256
                ),
                lane_id=binding.lane_id,
                port_id=port.port_id,
                source_stream_receipt_sha256=receipt_sha256(stream_payload),
                samples=kernel_samples,
                authority_receipt_sha256=receipt_sha256(adapter_payload),
            )
            generated_payloads.extend(
                (relevance_payload, stream_payload, adapter_payload)
            )
            streams.append(stream)
            adapters.append(adapter)
        working = _extend_registry(working, generated_payloads)
        for stream, adapter in zip(streams, adapters, strict=True):
            adapter.verify(stream, working)
    except ReceiptError as exc:
        return StoryFrozenKernelInputs(
            StoryKernelBridgeStatus.UNKNOWN,
            (),
            (),
            retained_registry,
            str(exc),
        )
    return StoryFrozenKernelInputs(
        StoryKernelBridgeStatus.READY,
        tuple(streams),
        tuple(adapters),
        working,
        "evolved multisensory story outputs are mounted for frozen L0-L4",
    )


def _state_body(state: ReceiverState) -> dict[str, object]:
    common: dict[str, object] = {
        "port_id": state.port_id,
        "receipt_payload_hex": state.receipt_payload.hex(),
        "receipt_sha256": state.receipt_sha256,
        "source_time": _fraction_text(state.source_time),
        "time_unit_authority_receipt_sha256": (
            state.time_unit_authority_receipt_sha256
        ),
        "time_unit_id": state.time_unit_id,
        "total_receptor_mass": _fraction_text(state.total_receptor_mass),
    }
    if isinstance(state, ExactReceiverState):
        return {
            **common,
            "active_mass": _fraction_text(state.active_mass),
            "desensitized_mass": _fraction_text(state.desensitized_mass),
            "initial_authority_receipt_sha256": state.initial_authority_receipt_sha256,
            "initial_condition_id": state.initial_condition_id,
            "initial_derivation_receipt_sha256": (
                state.initial_derivation_receipt_sha256
            ),
            "resting_mass": _fraction_text(state.resting_mass),
            "state_kind": "exact",
        }
    if isinstance(state, CertifiedReceiverState):
        return {
            **common,
            "active_mass": _ball_payload(state.active_mass),
            "desensitized_mass": _ball_payload(state.desensitized_mass),
            "evolution_authority_receipt_sha256": (
                state.evolution_authority_receipt_sha256
            ),
            "exact_affine_constraint_id": state.exact_affine_constraint_id,
            "prior_state_receipt_sha256": state.prior_state_receipt_sha256,
            "resting_mass": _ball_payload(state.resting_mass),
            "state_kind": "certified",
        }
    raise ReceiptError("story checkpoint contains an untyped receiver state")


def story_chemistry_checkpoint_payload(
    *,
    runtime: StoryChemistryRuntime,
    checkpoint_id: str,
    authentication_key: bytes,
    key_id: str,
) -> bytes:
    """Serialize every correlated state and mounted receipt into signed bytes."""

    if not isinstance(runtime, StoryChemistryRuntime):
        raise ReceiptError("story chemistry runtime is missing")
    require_identifier(checkpoint_id, "story chemistry checkpoint_id")
    if runtime.receipt_registry.profile_binding_sha256 != runtime.manifest.receipt_sha256:
        raise ReceiptError("story chemistry runtime profile binding was tampered")
    if runtime.receipt_registry.resolve(
        runtime.manifest.receipt_sha256,
        "story chemistry runtime manifest receipt",
    ) != runtime.manifest.canonical_payload:
        raise ReceiptError("story chemistry runtime manifest bytes were tampered")
    if tuple(state.port_id for state in runtime.states) != tuple(
        port.port_id for port in runtime.manifest.ports
    ):
        raise ReceiptError("story chemistry runtime port topology was tampered")
    for state in runtime.states:
        state.verify(runtime.receipt_registry)
    body = {
        "checkpoint_id": checkpoint_id,
        "manifest_receipt_sha256": runtime.manifest.receipt_sha256,
        "receipt_records": [
            {"payload_hex": record.payload.hex(), "sha256": record.digest}
            for record in runtime.receipt_registry.records
        ],
        "schema": STORY_CHEMISTRY_CHECKPOINT_SCHEMA,
        "states": [_state_body(state) for state in runtime.states],
    }
    return authenticated_story_envelope_payload(
        body=body,
        authentication_key=authentication_key,
        key_id=key_id,
    )


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


def _parse_ball(value: object, field_name: str) -> CertifiedBall:
    ball = _expect_object(value, field_name)
    _expect_keys(
        ball,
        (
            "flint_version",
            "lower_exponent",
            "lower_mantissa",
            "python_flint_version",
            "upper_exponent",
            "upper_mantissa",
            "wheel_sha256",
            "working_precision_bits",
        ),
        field_name,
    )
    for key in (
        "lower_exponent",
        "lower_mantissa",
        "upper_exponent",
        "upper_mantissa",
    ):
        if isinstance(ball[key], bool) or not isinstance(ball[key], int):
            raise ReceiptError(f"{field_name}.{key} must be an integer")
    return CertifiedBall(
        lower_mantissa=ball["lower_mantissa"],  # type: ignore[arg-type]
        lower_exponent=ball["lower_exponent"],  # type: ignore[arg-type]
        upper_mantissa=ball["upper_mantissa"],  # type: ignore[arg-type]
        upper_exponent=ball["upper_exponent"],  # type: ignore[arg-type]
        working_precision_bits=_positive_integer(
            ball["working_precision_bits"], f"{field_name}.working_precision_bits"
        ),
        python_flint_version=_identifier(
            ball["python_flint_version"], f"{field_name}.python_flint_version"
        ),
        flint_version=_identifier(ball["flint_version"], f"{field_name}.flint_version"),
        wheel_sha256=sha256_digest(
            ball["wheel_sha256"], f"{field_name}.wheel_sha256"  # type: ignore[arg-type]
        ),
    )


def _parse_checkpoint_state(
    value: object,
    field_name: str,
) -> ReceiverState:
    state = _expect_object(value, field_name)
    common_keys = {
        "port_id",
        "receipt_payload_hex",
        "receipt_sha256",
        "source_time",
        "state_kind",
        "time_unit_authority_receipt_sha256",
        "time_unit_id",
        "total_receptor_mass",
    }
    kind = state.get("state_kind")
    exact_keys = common_keys | {
        "active_mass",
        "desensitized_mass",
        "initial_authority_receipt_sha256",
        "initial_condition_id",
        "initial_derivation_receipt_sha256",
        "resting_mass",
    }
    certified_keys = common_keys | {
        "active_mass",
        "desensitized_mass",
        "evolution_authority_receipt_sha256",
        "exact_affine_constraint_id",
        "prior_state_receipt_sha256",
        "resting_mass",
    }
    if kind == "exact":
        _expect_keys(state, tuple(exact_keys), field_name)
    elif kind == "certified":
        _expect_keys(state, tuple(certified_keys), field_name)
    else:
        raise ReceiptError("story checkpoint receiver state kind is not typed")
    port_id = _identifier(state["port_id"], f"{field_name}.port_id")
    source_time = _fraction(state["source_time"], f"{field_name}.source_time")
    time_unit_id = _identifier(state["time_unit_id"], f"{field_name}.time_unit_id")
    time_digest = sha256_digest(
        state["time_unit_authority_receipt_sha256"],  # type: ignore[arg-type]
        f"{field_name}.time_unit_authority_receipt_sha256",
    )
    total = _fraction(
        state["total_receptor_mass"], f"{field_name}.total_receptor_mass"
    )
    state_digest = sha256_digest(
        state["receipt_sha256"], f"{field_name}.receipt_sha256"  # type: ignore[arg-type]
    )
    state_payload = _hex_bytes(
        state["receipt_payload_hex"], f"{field_name}.receipt_payload_hex"
    )
    if receipt_sha256(state_payload) != state_digest:
        raise ReceiptError("story checkpoint state receipt payload was tampered")
    if kind == "exact":
        return ExactReceiverState(
            port_id=port_id,
            source_time=source_time,
            time_unit_id=time_unit_id,
            time_unit_authority_receipt_sha256=time_digest,
            total_receptor_mass=total,
            resting_mass=_fraction(state["resting_mass"], f"{field_name}.resting_mass"),
            active_mass=_fraction(state["active_mass"], f"{field_name}.active_mass"),
            desensitized_mass=_fraction(
                state["desensitized_mass"], f"{field_name}.desensitized_mass"
            ),
            initial_condition_id=_identifier(
                state["initial_condition_id"], f"{field_name}.initial_condition_id"
            ),
            initial_derivation_receipt_sha256=sha256_digest(
                state["initial_derivation_receipt_sha256"],  # type: ignore[arg-type]
                f"{field_name}.initial_derivation_receipt_sha256",
            ),
            initial_authority_receipt_sha256=sha256_digest(
                state["initial_authority_receipt_sha256"],  # type: ignore[arg-type]
                f"{field_name}.initial_authority_receipt_sha256",
            ),
            receipt_sha256=state_digest,
            receipt_payload=state_payload,
        )
    return CertifiedReceiverState(
        port_id=port_id,
        source_time=source_time,
        time_unit_id=time_unit_id,
        time_unit_authority_receipt_sha256=time_digest,
        total_receptor_mass=total,
        resting_mass=_parse_ball(state["resting_mass"], f"{field_name}.resting_mass"),
        active_mass=_parse_ball(state["active_mass"], f"{field_name}.active_mass"),
        desensitized_mass=_parse_ball(
            state["desensitized_mass"], f"{field_name}.desensitized_mass"
        ),
        exact_affine_constraint_id=_identifier(
            state["exact_affine_constraint_id"],
            f"{field_name}.exact_affine_constraint_id",
        ),
        prior_state_receipt_sha256=sha256_digest(
            state["prior_state_receipt_sha256"],  # type: ignore[arg-type]
            f"{field_name}.prior_state_receipt_sha256",
        ),
        evolution_authority_receipt_sha256=sha256_digest(
            state["evolution_authority_receipt_sha256"],  # type: ignore[arg-type]
            f"{field_name}.evolution_authority_receipt_sha256",
        ),
        receipt_sha256=state_digest,
        receipt_payload=state_payload,
    )


def restore_story_chemistry(
    *,
    manifest_envelope_payload: bytes,
    manifest_authentication_key: bytes,
    manifest_expected_key_id: str,
    checkpoint_envelope_payload: bytes,
    checkpoint_authentication_key: bytes,
    checkpoint_expected_key_id: str,
) -> StoryChemistryMountResult:
    """Restore a bit-exact authenticated checkpoint or fail closed."""

    mounted = mount_story_chemistry(
        manifest_envelope_payload=manifest_envelope_payload,
        trusted_authentication_key=manifest_authentication_key,
        expected_key_id=manifest_expected_key_id,
    )
    if mounted.status is StoryChemistryStatus.UNKNOWN or mounted.runtime is None:
        return mounted
    try:
        body, _, _ = _verify_authenticated_envelope(
            envelope_payload=checkpoint_envelope_payload,
            trusted_authentication_key=checkpoint_authentication_key,
            expected_key_id=checkpoint_expected_key_id,
            field_name="story chemistry checkpoint",
        )
        _expect_keys(
            body,
            (
                "checkpoint_id",
                "manifest_receipt_sha256",
                "receipt_records",
                "schema",
                "states",
            ),
            "story chemistry checkpoint body",
        )
        if body["schema"] != STORY_CHEMISTRY_CHECKPOINT_SCHEMA:
            raise ReceiptError("story chemistry checkpoint schema is not mounted")
        _identifier(body["checkpoint_id"], "story chemistry checkpoint_id")
        if body["manifest_receipt_sha256"] != mounted.runtime.manifest.receipt_sha256:
            raise ReceiptError("story chemistry checkpoint names another manifest")
        record_values = _expect_list(
            body["receipt_records"], "story chemistry checkpoint receipt records"
        )
        records: list[ReceiptRecord] = []
        for index, raw_record in enumerate(record_values):
            record = _expect_object(
                raw_record, f"story chemistry checkpoint receipt_records[{index}]"
            )
            _expect_keys(
                record,
                ("payload_hex", "sha256"),
                f"story chemistry checkpoint receipt_records[{index}]",
            )
            payload = _hex_bytes(
                record["payload_hex"],
                f"story chemistry checkpoint receipt_records[{index}].payload_hex",
            )
            digest = sha256_digest(
                record["sha256"],  # type: ignore[arg-type]
                f"story chemistry checkpoint receipt_records[{index}].sha256",
            )
            records.append(ReceiptRecord(digest=digest, payload=payload))
        registry = ReceiptRegistry(
            profile_binding_sha256=mounted.runtime.manifest.receipt_sha256,
            records=tuple(records),
        )
        if registry.resolve(
            mounted.runtime.manifest.receipt_sha256,
            "restored story manifest receipt",
        ) != mounted.runtime.manifest.canonical_payload:
            raise ReceiptError("restored story manifest bytes differ from mounted authority")
        for backend in mounted.runtime.manifest.backends:
            backend.verify(registry)
        for port in mounted.runtime.manifest.ports:
            if registry.resolve(
                port.native_signal_unit_authority_receipt_sha256,
                "restored native signal-unit authority receipt",
            ) != port.native_signal_unit_authority_payload:
                raise ReceiptError("restored native signal-unit authority was tampered")
            port.kernel_binding.verify(registry)
            port.time_unit.verify(registry)
            port.activation_susceptibility.verify(registry)
            for rate in port.rates:
                rate.verify(registry)
            port.initial_state.verify(registry)
        raw_states = _expect_list(body["states"], "story chemistry checkpoint states")
        states = tuple(
            _parse_checkpoint_state(value, f"story chemistry checkpoint states[{index}]")
            for index, value in enumerate(raw_states)
        )
        if tuple(state.port_id for state in states) != tuple(
            port.port_id for port in mounted.runtime.manifest.ports
        ):
            raise ReceiptError("story chemistry checkpoint port topology differs")
        for state, port in zip(states, mounted.runtime.manifest.ports, strict=True):
            if (
                state.time_unit_id != port.time_unit.time_unit_id
                or state.time_unit_authority_receipt_sha256
                != port.time_unit.authority_receipt_sha256
                or state.total_receptor_mass != port.initial_state.total_receptor_mass
            ):
                raise ReceiptError("story chemistry checkpoint changed mounted port physics")
            state.verify(registry)
        runtime = StoryChemistryRuntime(
            manifest=mounted.runtime.manifest,
            states=states,
            receipt_registry=registry,
        )
    except ReceiptError as exc:
        return StoryChemistryMountResult(
            status=StoryChemistryStatus.UNKNOWN,
            runtime=None,
            reason=str(exc),
        )
    return StoryChemistryMountResult(
        status=StoryChemistryStatus.MOUNTED,
        runtime=runtime,
        reason="authenticated story chemistry checkpoint restored bit-exactly",
    )


__all__ = (
    "Binary64RoundingStatus",
    "CertifiedBinary64Relevance",
    "PRODUCTION_STORY_CHEMISTRY_AUTHORITY_SCOPE",
    "PRODUCTION_STORY_CHEMISTRY_MANIFEST_ID",
    "PRODUCTION_STORY_CHEMISTRY_PROFILE_RESOURCE",
    "PRODUCTION_STORY_PORT_LANES",
    "STORY_AUTHENTICATION_ALGORITHM",
    "STORY_BINARY64_RELEVANCE_SCHEMA",
    "STORY_BOUNDARY_OBSERVATION_SCHEMA",
    "STORY_CHEMISTRY_CHECKPOINT_SCHEMA",
    "STORY_CHEMISTRY_MANIFEST_SCHEMA",
    "SignedStoryChemistryManifest",
    "StoryChemistryEvolutionResult",
    "StoryChemistryMountResult",
    "StoryChemistryRuntime",
    "StoryChemistryStatus",
    "StoryFrozenKernelInputs",
    "StoryKernelBindingAuthority",
    "StoryKernelBridgeStatus",
    "StoryPhysicalBoundaryEvent",
    "StoryPhysicalBoundaryObservation",
    "StoryPortChemicalAuthority",
    "StoryPortChemicalOutput",
    "authenticated_story_envelope_payload",
    "authenticate_production_story_chemistry_profile",
    "build_story_frozen_kernel_inputs",
    "certified_binary64_relevance_receipt_payload",
    "certify_unique_binary64_relevance",
    "evolve_story_chemistry_event",
    "mount_story_chemistry",
    "mount_packaged_production_story_chemistry",
    "mount_production_story_chemistry_profile",
    "production_story_chemistry_profile_payload",
    "restore_story_chemistry",
    "story_boundary_observation_receipt_payload",
    "story_chemistry_checkpoint_payload",
    "story_kernel_binding_authority_receipt_payload",
    "story_kernel_relevance_sequence_receipt_payload",
)
