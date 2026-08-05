from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple


_CANONICAL_TUPLE_KEYS: Tuple[str, ...] = (
    "symbol",
    "window_start",
    "window_end",
    "timeframe",
    "uf_version",
    "ses_version",
    "tenant_id",
    "engine_variant",
    "environment",
)


@dataclass(frozen=True)
class DomainParameters:
    """
    Domain parameters bind keys and envelopes to a specific logical context.

    Legacy fields (currently used by active runtime paths):
    - environment
    - region
    - purpose
    - version

    Canonical UF tuple support (spec-aligned, optional but all-or-none):
    - symbol
    - window_start
    - window_end
    - timeframe
    - uf_version
    - ses_version
    - tenant_id
    - engine_variant
    - environment (shared with legacy field)
    """

    environment: str
    region: str
    purpose: str
    version: str

    symbol: str = ""
    window_start: str = ""
    window_end: str = ""
    timeframe: str = ""
    uf_version: str = ""
    ses_version: str = ""
    tenant_id: str = ""
    engine_variant: str = ""

    def __post_init__(self) -> None:
        if not str(self.environment).strip():
            raise ValueError("environment must be non-empty")
        if not str(self.region).strip():
            raise ValueError("region must be non-empty")
        if not str(self.purpose).strip():
            raise ValueError("purpose must be non-empty")
        if not str(self.version).strip():
            raise ValueError("version must be non-empty")

        tuple_values = {
            "symbol": str(self.symbol).strip(),
            "window_start": str(self.window_start).strip(),
            "window_end": str(self.window_end).strip(),
            "timeframe": str(self.timeframe).strip(),
            "uf_version": str(self.uf_version).strip(),
            "ses_version": str(self.ses_version).strip(),
            "tenant_id": str(self.tenant_id).strip(),
            "engine_variant": str(self.engine_variant).strip(),
            "environment": str(self.environment).strip(),
        }

        has_any = any(bool(tuple_values[k]) for k in _CANONICAL_TUPLE_KEYS if k != "environment")
        has_all = all(bool(tuple_values[k]) for k in _CANONICAL_TUPLE_KEYS)

        if has_any and not has_all:
            missing = [k for k in _CANONICAL_TUPLE_KEYS if not bool(tuple_values[k])]
            raise ValueError(
                "Canonical DomainParams tuple must be all-or-none when provided. "
                f"Missing fields: {', '.join(missing)}"
            )

    def has_canonical_tuple(self) -> bool:
        """
        Return True only when all canonical tuple fields are present.
        """
        return all(
            [
                bool(str(self.symbol).strip()),
                bool(str(self.window_start).strip()),
                bool(str(self.window_end).strip()),
                bool(str(self.timeframe).strip()),
                bool(str(self.uf_version).strip()),
                bool(str(self.ses_version).strip()),
                bool(str(self.tenant_id).strip()),
                bool(str(self.engine_variant).strip()),
                bool(str(self.environment).strip()),
            ]
        )

    def canonical_tuple_dict(self) -> Dict[str, Any]:
        """
        Return canonical tuple mapping.
        Raises when canonical tuple is not fully populated.
        """
        if not self.has_canonical_tuple():
            raise ValueError("Canonical DomainParams tuple is not fully populated")

        return {
            "symbol": self.symbol,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "timeframe": self.timeframe,
            "uf_version": self.uf_version,
            "ses_version": self.ses_version,
            "tenant_id": self.tenant_id,
            "engine_variant": self.engine_variant,
            "environment": self.environment,
        }

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "environment": self.environment,
            "region": self.region,
            "purpose": self.purpose,
            "version": self.version,
        }

        if self.has_canonical_tuple():
            payload["domain_params_tuple"] = self.canonical_tuple_dict()

        return payload

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "DomainParameters":
        environment = str(data.get("environment", "")).strip()
        region = str(data.get("region", "")).strip()
        purpose = str(data.get("purpose", "")).strip()
        version = str(data.get("version", "")).strip()

        if not environment:
            raise ValueError("environment must be non-empty")
        if not region:
            raise ValueError("region must be non-empty")
        if not purpose:
            raise ValueError("purpose must be non-empty")
        if not version:
            raise ValueError("version must be non-empty")

        tuple_obj = data.get("domain_params_tuple")
        tuple_map = tuple_obj if isinstance(tuple_obj, Mapping) else {}

        symbol = str(tuple_map.get("symbol", data.get("symbol", ""))).strip()
        window_start = str(tuple_map.get("window_start", data.get("window_start", ""))).strip()
        window_end = str(tuple_map.get("window_end", data.get("window_end", ""))).strip()
        timeframe = str(tuple_map.get("timeframe", data.get("timeframe", ""))).strip()
        uf_version = str(tuple_map.get("uf_version", data.get("uf_version", ""))).strip()
        ses_version = str(tuple_map.get("ses_version", data.get("ses_version", ""))).strip()
        tenant_id = str(tuple_map.get("tenant_id", data.get("tenant_id", ""))).strip()
        engine_variant = str(tuple_map.get("engine_variant", data.get("engine_variant", ""))).strip()

        return DomainParameters(
            environment=environment,
            region=region,
            purpose=purpose,
            version=version,
            symbol=symbol,
            window_start=window_start,
            window_end=window_end,
            timeframe=timeframe,
            uf_version=uf_version,
            ses_version=ses_version,
            tenant_id=tenant_id,
            engine_variant=engine_variant,
        )

    def kdf_context(self) -> bytes:
        """
        Returns canonical byte string used as HKDF 'info' input.

        Backward-compatibility rule:
        - Legacy runtime paths (no canonical tuple) preserve previous context shape.
        - Canonical tuple is included only when fully populated.
        """
        canonical = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return canonical
