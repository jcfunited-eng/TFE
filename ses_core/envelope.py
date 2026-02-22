from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Protocol, Tuple, runtime_checkable

from .tenant_id import TenantIdentity
from .domain_params import DomainParameters
from .key_derivation import KeyDerivationService


@runtime_checkable
class AEADBackend(Protocol):
    """
    Interface for authenticated encryption backends.
    """

    def encrypt(
        self,
        key: bytes,
        nonce: bytes,
        plaintext: bytes,
        associated_data: bytes,
    ) -> bytes:
        ...

    def decrypt(
        self,
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        associated_data: bytes,
    ) -> bytes:
        ...


def _default_redacted_summary() -> Dict[str, Any]:
    """
    Canonical SES redaction-summary shape required by UF/SES spec.
    """
    return {
        "S": None,
        "R": None,
        "GSS": None,
        "DSS": None,
        "DSFStability": None,
        "collapse_flags": {},
        "safemode": None,
    }


@dataclass(frozen=True)
class Envelope:
    """
    SES-Core authenticated envelope.
    """

    tenant_id: str
    environment: str
    region: str
    purpose: str
    version: str
    algorithm: str = "aead"
    created_at: str = ""
    nonce: str = ""
    key_id: str = ""
    ciphertext: str = ""
    summary: Optional[Dict[str, Any]] = None
    domain_params_tuple: Optional[Dict[str, Any]] = None

    # ----------------------
    # Base64 helpers
    # ----------------------
    @staticmethod
    def _b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64decode(data: str) -> bytes:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded.encode("ascii"))

    @staticmethod
    def _normalize_summary_data(raw_summary: Any) -> Dict[str, Any]:
        summary = _default_redacted_summary()
        if isinstance(raw_summary, Mapping):
            for key, value in raw_summary.items():
                summary[str(key)] = value
        return summary

    @staticmethod
    def _normalize_domain_tuple(raw_tuple: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(raw_tuple, Mapping):
            return None
        normalized: Dict[str, Any] = {}
        for key, value in raw_tuple.items():
            normalized[str(key)] = value
        return normalized or None

    @staticmethod
    def _legacy_read_mode() -> str:
        mode = str(os.environ.get("TFE_ENVELOPE_LEGACY_READ_MODE", "sunset")).strip().lower()
        if mode in {"allow", "warn", "sunset", "deny"}:
            return mode
        return "sunset"

    @staticmethod
    def _legacy_sunset_utc() -> datetime:
        raw = str(
            os.environ.get("TFE_ENVELOPE_LEGACY_READ_SUNSET_UTC", "2026-03-31T00:00:00Z")
        ).strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return datetime(2026, 3, 31, tzinfo=timezone.utc)

    @staticmethod
    def _legacy_read_policy() -> Tuple[bool, str]:
        mode = Envelope._legacy_read_mode()
        if mode == "deny":
            return (
                False,
                "legacy envelope reads are disabled (TFE_ENVELOPE_LEGACY_READ_MODE=deny)",
            )

        if mode in {"allow", "warn"}:
            return (
                True,
                f"legacy envelope read allowed (mode={mode})",
            )

        sunset = Envelope._legacy_sunset_utc()
        now_utc = datetime.now(timezone.utc)
        if now_utc <= sunset:
            return (
                True,
                f"legacy envelope read allowed until sunset {sunset.isoformat()}",
            )

        return (
            False,
            (
                "legacy envelope read blocked: sunset passed "
                f"(now={now_utc.isoformat()}, sunset={sunset.isoformat()})"
            ),
        )

    def _header_dict(self) -> Dict[str, Any]:
        header: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "environment": self.environment,
            "region": self.region,
            "purpose": self.purpose,
            "version": self.version,
            "algorithm": self.algorithm,
            "created_at": self.created_at,
            "nonce": self.nonce,
            "key_id": self.key_id,
        }
        tuple_data = Envelope._normalize_domain_tuple(self.domain_params_tuple)
        if tuple_data is not None:
            header["domain_params_tuple"] = tuple_data
        return header

    # ----------------------
    # Serialization
    # ----------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "header": self._header_dict(),
            "summary": Envelope._normalize_summary_data(self.summary),
            "ciphertext": self.ciphertext,
        }

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Legacy flat envelope representation kept for controlled compatibility.
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "environment": self.environment,
            "region": self.region,
            "purpose": self.purpose,
            "version": self.version,
            "algorithm": self.algorithm,
            "created_at": self.created_at,
            "nonce": self.nonce,
            "key_id": self.key_id,
            "ciphertext": self.ciphertext,
        }
        tuple_data = Envelope._normalize_domain_tuple(self.domain_params_tuple)
        if tuple_data is not None:
            payload["domain_params_tuple"] = tuple_data
        payload["summary"] = Envelope._normalize_summary_data(self.summary)
        return payload

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> Envelope:
        # Canonical shape: {"header": {...}, "summary": {...}, "ciphertext": "..."}
        if "header" in data:
            header_obj = data["header"]
            if not isinstance(header_obj, Mapping):
                raise ValueError("Envelope field 'header' must be an object")

            required_header = [
                "tenant_id",
                "environment",
                "region",
                "purpose",
                "version",
                "created_at",
                "nonce",
                "key_id",
            ]
            for field_name in required_header:
                if field_name not in header_obj:
                    raise ValueError(f"Missing envelope header field: {field_name}")

            if "ciphertext" not in data:
                raise ValueError("Missing envelope field: ciphertext")

            algorithm = str(header_obj.get("algorithm", "aead")).strip() or "aead"
            summary = Envelope._normalize_summary_data(data.get("summary"))
            domain_tuple = Envelope._normalize_domain_tuple(
                header_obj.get("domain_params_tuple")
            )

            return Envelope(
                tenant_id=str(header_obj["tenant_id"]),
                environment=str(header_obj["environment"]),
                region=str(header_obj["region"]),
                purpose=str(header_obj["purpose"]),
                version=str(header_obj["version"]),
                algorithm=algorithm,
                created_at=str(header_obj["created_at"]),
                nonce=str(header_obj["nonce"]),
                key_id=str(header_obj["key_id"]),
                ciphertext=str(data["ciphertext"]),
                summary=summary,
                domain_params_tuple=domain_tuple,
            )

        # Legacy flat shape (read compatibility)
        allowed, policy_detail = Envelope._legacy_read_policy()
        if not allowed:
            raise ValueError(policy_detail)

        required = [
            "tenant_id",
            "environment",
            "region",
            "purpose",
            "version",
            "created_at",
            "nonce",
            "key_id",
            "ciphertext",
        ]
        for field_name in required:
            if field_name not in data:
                raise ValueError(f"Missing envelope field: {field_name}")

        algorithm = str(data.get("algorithm", "aead")).strip() or "aead"
        summary = Envelope._normalize_summary_data(data.get("summary"))
        domain_tuple = Envelope._normalize_domain_tuple(data.get("domain_params_tuple"))

        return Envelope(
            tenant_id=str(data["tenant_id"]),
            environment=str(data["environment"]),
            region=str(data["region"]),
            purpose=str(data["purpose"]),
            version=str(data["version"]),
            algorithm=algorithm,
            created_at=str(data["created_at"]),
            nonce=str(data["nonce"]),
            key_id=str(data["key_id"]),
            ciphertext=str(data["ciphertext"]),
            summary=summary,
            domain_params_tuple=domain_tuple,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @staticmethod
    def from_json(data: str) -> Envelope:
        parsed = json.loads(data)
        if not isinstance(parsed, Mapping):
            raise ValueError("Envelope JSON must represent an object")
        return Envelope.from_dict(parsed)


class EnvelopeService:
    """
    Envelope service with deterministic SES-Core binding and algorithm dispatch.
    """

    def __init__(
        self,
        key_derivation: KeyDerivationService,
        aead_backend: AEADBackend,
        algorithm_id: str = "aead",
        algorithm_backends: Optional[Mapping[str, AEADBackend]] = None,
    ) -> None:
        if not isinstance(aead_backend, AEADBackend):
            raise TypeError("aead_backend must implement AEADBackend")

        normalized_algorithm_id = str(algorithm_id).strip()
        if not normalized_algorithm_id:
            raise ValueError("algorithm_id must be non-empty")

        self._key_derivation = key_derivation
        self._algorithm_id = normalized_algorithm_id
        self._aead_backends: Dict[str, AEADBackend] = {}

        self._register_backend(name=normalized_algorithm_id, backend=aead_backend)

        if algorithm_backends is not None:
            for backend_name, backend in dict(algorithm_backends).items():
                self._register_backend(name=str(backend_name), backend=backend)

    def _register_backend(self, name: str, backend: AEADBackend) -> None:
        normalized = str(name).strip()
        if not normalized:
            raise ValueError("algorithm backend name must be non-empty")
        if not isinstance(backend, AEADBackend):
            raise TypeError(f"backend '{normalized}' must implement AEADBackend")
        self._aead_backends[normalized] = backend

    def _resolve_backend(self, algorithm: str) -> AEADBackend:
        backend = self._aead_backends.get(algorithm)
        if backend is None:
            available = ",".join(sorted(self._aead_backends.keys()))
            raise ValueError(f"Unsupported envelope algorithm '{algorithm}'. available={available}")
        return backend

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # -------------------------
    # Encrypt
    # -------------------------
    def encrypt(
        self,
        tenant: TenantIdentity,
        domain: DomainParameters,
        plaintext: bytes,
        associated_metadata: Mapping[str, Any],
        redacted_summary: Optional[Mapping[str, Any]] = None,
    ) -> Envelope:
        if not isinstance(plaintext, (bytes, bytearray)):
            raise TypeError("plaintext must be bytes")

        algorithm = self._algorithm_id
        backend = self._resolve_backend(algorithm=algorithm)

        # Deterministic associated data (AAD)
        aad_dict: Dict[str, Any] = {
            "tenant_id": tenant.tenant_id,
            "environment": domain.environment,
            "region": domain.region,
            "purpose": domain.purpose,
            "version": domain.version,
            "algorithm": algorithm,
            "metadata": dict(associated_metadata),
        }
        aad_bytes = json.dumps(aad_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")

        nonce_bytes = os.urandom(12)

        op_key = self._key_derivation.derive_operation_key(
            tenant=tenant,
            domain=domain,
            operation_name=domain.purpose,
            context_nonce=nonce_bytes,
        )

        ciphertext = backend.encrypt(
            key=op_key,
            nonce=nonce_bytes,
            plaintext=bytes(plaintext),
            associated_data=aad_bytes,
        )

        key_id = (
            f"{tenant.tenant_id}:"
            f"{domain.environment}:"
            f"{domain.region}:"
            f"{domain.purpose}:"
            f"{domain.version}"
        )

        domain_tuple: Optional[Dict[str, Any]] = None
        if domain.has_canonical_tuple():
            domain_tuple = domain.canonical_tuple_dict()

        return Envelope(
            tenant_id=tenant.tenant_id,
            environment=domain.environment,
            region=domain.region,
            purpose=domain.purpose,
            version=domain.version,
            algorithm=algorithm,
            created_at=self._now_iso(),
            nonce=Envelope._b64encode(nonce_bytes),
            key_id=key_id,
            ciphertext=Envelope._b64encode(ciphertext),
            summary=Envelope._normalize_summary_data(redacted_summary),
            domain_params_tuple=domain_tuple,
        )

    # -------------------------
    # Decrypt
    # -------------------------
    def decrypt(
        self,
        tenant: TenantIdentity,
        domain: DomainParameters,
        envelope: Envelope,
        associated_metadata: Mapping[str, Any],
    ) -> bytes:
        if envelope.tenant_id != tenant.tenant_id:
            raise ValueError("Envelope tenant mismatch")
        if envelope.environment != domain.environment:
            raise ValueError("Envelope environment mismatch")
        if envelope.region != domain.region:
            raise ValueError("Envelope region mismatch")
        if envelope.purpose != domain.purpose:
            raise ValueError("Envelope purpose mismatch")
        if envelope.version != domain.version:
            raise ValueError("Envelope version mismatch")

        algorithm = str(envelope.algorithm).strip() or "aead"
        backend = self._resolve_backend(algorithm=algorithm)

        aad_dict: Dict[str, Any] = {
            "tenant_id": tenant.tenant_id,
            "environment": domain.environment,
            "region": domain.region,
            "purpose": domain.purpose,
            "version": domain.version,
            "algorithm": algorithm,
            "metadata": dict(associated_metadata),
        }
        aad_bytes = json.dumps(aad_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")

        nonce = Envelope._b64decode(envelope.nonce)
        ciphertext = Envelope._b64decode(envelope.ciphertext)

        op_key = self._key_derivation.derive_operation_key(
            tenant=tenant,
            domain=domain,
            operation_name=domain.purpose,
            context_nonce=nonce,
        )

        return backend.decrypt(
            key=op_key,
            nonce=nonce,
            ciphertext=ciphertext,
            associated_data=aad_bytes,
        )
