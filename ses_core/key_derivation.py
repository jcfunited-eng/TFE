from __future__ import annotations

import os
import hmac
import hashlib
from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Optional

from .tenant_id import TenantIdentity
from .domain_params import DomainParameters


@runtime_checkable
class RootKeyProvider(Protocol):
    """
    Interface for obtaining the SES-Core root key material.
    """

    def get_root_key(self) -> bytes:
        """
        Return a root key suitable as HKDF IKM.
        """
        ...


@dataclass
class StaticRootKeyProvider:
    """
    Development root key provider for deterministic integration testing.
    """

    key: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.key, (bytes, bytearray)):
            raise TypeError("key must be bytes")
        if len(self.key) < 32:
            raise ValueError("root key must be at least 32 bytes")

    def get_root_key(self) -> bytes:
        return bytes(self.key)


@dataclass(frozen=True)
class KeyDerivationConfig:
    """
    Configuration for HKDF.
    """

    length: int = 32
    hash_name: str = "sha256"

    def hash_cls(self):
        """
        Returns the hash constructor (e.g., hashlib.sha256).
        """
        try:
            hashlib.new(self.hash_name)
        except ValueError as exc:
            raise ValueError(f"Unsupported hash: {self.hash_name}") from exc
        return lambda data=b"": hashlib.new(self.hash_name, data)


class KeyDerivationService:
    """
    Hierarchical SES-Core key derivation (tenant → domain → operation).
    """

    def __init__(
        self,
        root_key_provider: RootKeyProvider,
        config: Optional[KeyDerivationConfig] = None,
    ) -> None:
        if not isinstance(root_key_provider, RootKeyProvider):
            raise TypeError("root_key_provider must implement RootKeyProvider")

        self._root_key_provider = root_key_provider
        self._config = config or KeyDerivationConfig()

    # --------------------------
    # Corrected HKDF implementation
    # --------------------------
    def _hkdf(
        self,
        ikm: bytes,
        salt: Optional[bytes],
        info: bytes,
        length: Optional[int] = None,
    ) -> bytes:
        hash_cls = self._config.hash_cls()  # constructor
        digest_size = hash_cls().digest_size

        if salt is None:
            salt = b"\x00" * digest_size

        # Extract
        prk = hmac.new(salt, ikm, hash_cls).digest()

        # Expand
        output_length = length or self._config.length
        if output_length <= 0:
            raise ValueError("length must be positive")

        n = (output_length + digest_size - 1) // digest_size
        okm = b""
        t = b""

        for i in range(1, n + 1):
            t = hmac.new(prk, t + info + bytes([i]), hash_cls).digest()
            okm += t

        return okm[:output_length]

    # --------------------------
    # SES-Core level derivation
    # --------------------------
    def derive_tenant_root_key(self, tenant: TenantIdentity) -> bytes:
        root_key = self._root_key_provider.get_root_key()
        salt = tenant.hkdf_salt()
        info = b"ses-core:tenant-root"
        return self._hkdf(root_key, salt=salt, info=info)

    def derive_domain_key(
        self,
        tenant: TenantIdentity,
        domain: DomainParameters,
    ) -> bytes:
        tenant_root = self.derive_tenant_root_key(tenant)
        info = b"ses-core:domain-key:" + domain.kdf_context()
        return self._hkdf(tenant_root, salt=None, info=info)

    def derive_operation_key(
        self,
        tenant: TenantIdentity,
        domain: DomainParameters,
        operation_name: str,
        context_nonce: Optional[bytes] = None,
    ) -> bytes:
        if not operation_name:
            raise ValueError("operation_name must be non-empty")

        domain_key = self.derive_domain_key(tenant, domain)

        if context_nonce is None:
            context_nonce = os.urandom(16)

        info = (
            b"ses-core:op-key:"
            + operation_name.encode("utf-8")
            + b":"
            + context_nonce
        )
        return self._hkdf(domain_key, salt=None, info=info)
