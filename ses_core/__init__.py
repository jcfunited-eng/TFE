"""
SES-Core v2.0 – Core Python Interfaces for TFE Integration (Phase 1)

This package provides the foundational primitives required for:
- Tenant identity representation (TIRM binding).
- Domain parameter modeling for key binding.
- Hierarchical key derivation.
- Envelope construction and parsing.
- Chain-of-custody event creation and recording.
"""

from .tenant_id import TenantIdentity, UserIdentity, TenantIdentityService
from .domain_params import DomainParameters
from .key_derivation import (
    RootKeyProvider,
    StaticRootKeyProvider,
    KeyDerivationConfig,
    KeyDerivationService,
)
from .envelope import Envelope, AEADBackend, EnvelopeService
from .chain_of_custody import (
    ChainOfCustodyEvent,
    ChainOfCustodySink,
    FileChainOfCustodySink,
    ChainOfCustodyService,
)

__all__ = [
    "TenantIdentity",
    "UserIdentity",
    "TenantIdentityService",
    "DomainParameters",
    "RootKeyProvider",
    "StaticRootKeyProvider",
    "KeyDerivationConfig",
    "KeyDerivationService",
    "Envelope",
    "AEADBackend",
    "EnvelopeService",
    "ChainOfCustodyEvent",
    "ChainOfCustodySink",
    "FileChainOfCustodySink",
    "ChainOfCustodyService",
]
