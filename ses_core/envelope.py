from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Protocol, runtime_checkable

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
    created_at: str
    nonce: str
    key_id: str
    ciphertext: str

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

    # ----------------------
    # Serialization
    # ----------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "environment": self.environment,
            "region": self.region,
            "purpose": self.purpose,
            "version": self.version,
            "created_at": self.created_at,
            "nonce": self.nonce,
            "key_id": self.key_id,
            "ciphertext": self.ciphertext,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> Envelope:
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
        for f in required:
            if f not in data:
                raise ValueError(f"Missing envelope field: {f}")

        return Envelope(
            tenant_id=str(data["tenant_id"]),
            environment=str(data["environment"]),
            region=str(data["region"]),
            purpose=str(data["purpose"]),
            version=str(data["version"]),
            created_at=str(data["created_at"]),
            nonce=str(data["nonce"]),
            key_id=str(data["key_id"]),
            ciphertext=str(data["ciphertext"]),
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
    AES-GCM envelope service with deterministic SES-Core binding.
    """

    def __init__(
        self,
        key_derivation: KeyDerivationService,
        aead_backend: AEADBackend,
        algorithm_id: str = "aead",
    ) -> None:
        if not isinstance(aead_backend, AEADBackend):
            raise TypeError("aead_backend must implement AEADBackend")
        self._key_derivation = key_derivation
        self._aead_backend = aead_backend
        self._algorithm_id = algorithm_id

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
    ) -> Envelope:
        if not isinstance(plaintext, (bytes, bytearray)):
            raise TypeError("plaintext must be bytes")

        # Deterministic associated data (AAD)
        aad_dict: Dict[str, Any] = {
            "tenant_id": tenant.tenant_id,
            "environment": domain.environment,
            "region": domain.region,
            "purpose": domain.purpose,
            "version": domain.version,
            "algorithm": self._algorithm_id,
            "metadata": dict(associated_metadata),
        }
        aad_bytes = json.dumps(
            aad_dict, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")

        # Nonce
        nonce_bytes = os.urandom(12)

        # Operation key
        op_key = self._key_derivation.derive_operation_key(
            tenant=tenant,
            domain=domain,
            operation_name=domain.purpose,
            context_nonce=nonce_bytes,
        )

        # Encrypt
        ciphertext = self._aead_backend.encrypt(
            key=op_key,
            nonce=nonce_bytes,
            plaintext=plaintext,
            associated_data=aad_bytes,
        )

        # Key identification string
        key_id = (
            f"{tenant.tenant_id}:"
            f"{domain.environment}:"
            f"{domain.region}:"
            f"{domain.purpose}:"
            f"{domain.version}"
        )

        return Envelope(
            tenant_id=tenant.tenant_id,
            environment=domain.environment,
            region=domain.region,
            purpose=domain.purpose,
            version=domain.version,
            created_at=self._now_iso(),
            nonce=Envelope._b64encode(nonce_bytes),
            key_id=key_id,
            ciphertext=Envelope._b64encode(ciphertext),
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
        # Validate envelope domain binding
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

        # Deterministic AAD
        aad_dict: Dict[str, Any] = {
            "tenant_id": tenant.tenant_id,
            "environment": domain.environment,
            "region": domain.region,
            "purpose": domain.purpose,
            "version": domain.version,
            "algorithm": self._algorithm_id,
            "metadata": dict(associated_metadata),
        }
        aad_bytes = json.dumps(
            aad_dict, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")

        nonce = Envelope._b64decode(envelope.nonce)
        ciphertext = Envelope._b64decode(envelope.ciphertext)

        # Re-derive the same op key
        op_key = self._key_derivation.derive_operation_key(
            tenant=tenant,
            domain=domain,
            operation_name=domain.purpose,
            context_nonce=nonce,
        )

        plaintext = self._aead_backend.decrypt(
            key=op_key,
            nonce=nonce,
            ciphertext=ciphertext,
            associated_data=aad_bytes,
        )

        return plaintext
