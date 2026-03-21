#!/usr/bin/env python3
"""
Migrate legacy portfolio envelopes (AES-GCM / legacy domain binding)
to current SCE-SIV + canonical domain tuple envelopes.

Default scope:
- input directory: tfe_encrypted_portfolios
- root key: tfe_root_key.bin
- purpose prefix: tfe

The tool creates a per-file backup before overwriting:
  <file>.pre-gap03-migration.bak
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ses_core import DomainParameters, Envelope, EnvelopeService, KeyDerivationService, StaticRootKeyProvider
from ses_core.aead_backend import AESGCMBackend
from tfe_ses_core_adapter import TenantIdentity, encrypt_blob, initialize_ses_core_for_env, make_domain

LEGACY_ALGORITHMS = {"aead", "aes-gcm-v1"}
PRIVATE_FILE_MODE = 0o600


def _read_root_key(path: Path) -> bytes:
    key = path.read_bytes()
    if len(key) < 32:
        raise ValueError(f"Root key file is invalid (<32 bytes): {path}")
    return key


def _write_private_text(path: Path, text: str) -> None:
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, PRIVATE_FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    try:
        os.chmod(path, PRIVATE_FILE_MODE)
    except Exception:
        pass


def _portfolio_id_from_name(filename: str) -> str:
    stem = Path(filename).stem
    if "__" in stem:
        return stem.split("__", 1)[1]
    return stem


def _decrypt_legacy_payload(
    envelope: Envelope,
    root_key: bytes,
    actor_candidates: List[str],
) -> Tuple[Mapping[str, object], str]:
    root_provider = StaticRootKeyProvider(key=root_key)
    kdf = KeyDerivationService(root_key_provider=root_provider)
    aes_backend = AESGCMBackend()
    legacy_service = EnvelopeService(
        key_derivation=kdf,
        aead_backend=aes_backend,
        algorithm_id="aead",
        algorithm_backends={"aead": aes_backend, "aes-gcm-v1": aes_backend},
    )

    tenant = TenantIdentity(
        tenant_id=envelope.tenant_id,
        display_name="Tao Tenant",
        environment=envelope.environment,
        attributes={},
    )

    domain = DomainParameters(
        environment=envelope.environment,
        region=envelope.region,
        purpose=envelope.purpose,
        version=envelope.version,
    )

    last_error = "unknown decrypt error"
    for actor_id in actor_candidates:
        metadata = {"actor_id": actor_id, "source": "tfe-adapter"}
        try:
            plaintext = legacy_service.decrypt(
                tenant=tenant,
                domain=domain,
                envelope=envelope,
                associated_metadata=metadata,
            )
            payload = json.loads(plaintext.decode("utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("legacy payload was not a JSON object")
            return payload, actor_id
        except Exception as exc:
            last_error = f"actor={actor_id} {type(exc).__name__}: {exc}"

    raise RuntimeError(last_error)


def _migrate_file(
    file_path: Path,
    root_key: bytes,
    actor_candidates: List[str],
    purpose_prefix: str,
    dry_run: bool,
) -> str:
    raw = file_path.read_text(encoding="utf-8")
    envelope = Envelope.from_json(raw)

    algorithm = str(envelope.algorithm).strip().lower()
    if algorithm not in LEGACY_ALGORITHMS:
        return "skip-non-legacy"

    payload, actor_id = _decrypt_legacy_payload(
        envelope=envelope,
        root_key=root_key,
        actor_candidates=actor_candidates,
    )

    portfolio_id = _portfolio_id_from_name(file_path.name)

    ctx = initialize_ses_core_for_env(
        environment=envelope.environment,
        region=envelope.region,
        purpose_prefix=purpose_prefix,
        root_key=root_key,
    )
    tenant = TenantIdentity(
        tenant_id=envelope.tenant_id,
        display_name="Tao Tenant",
        environment=envelope.environment,
        attributes={},
    )
    domain = make_domain(
        ctx=ctx,
        purpose_suffix=f"portfolio-{portfolio_id}",
        version=envelope.version,
    )

    new_envelope = encrypt_blob(
        ctx=ctx,
        tenant=tenant,
        domain=domain,
        payload=payload,
        actor_id=actor_id,
    )

    if dry_run:
        return "would-convert"

    backup_path = file_path.with_suffix(file_path.suffix + ".pre-gap03-migration.bak")
    _write_private_text(backup_path, raw)
    _write_private_text(file_path, new_envelope.to_json())
    return "converted"


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy portfolio envelopes to SCE-SIV canonical format")
    parser.add_argument("--portfolio-dir", default="tfe_encrypted_portfolios", help="Directory with encrypted portfolio files")
    parser.add_argument("--root-key-path", default="tfe_root_key.bin", help="Path to SES root key file")
    parser.add_argument("--purpose-prefix", default="tfe", help="SES purpose prefix")
    parser.add_argument("--actor-candidates", default="user-primary", help="Comma-separated actor ids to try for legacy decrypt")
    parser.add_argument("--dry-run", action="store_true", help="Analyze and report without writing changes")
    args = parser.parse_args()

    portfolio_dir = Path(args.portfolio_dir)
    root_key_path = Path(args.root_key_path)

    if not portfolio_dir.is_dir():
        raise SystemExit(f"Portfolio directory not found: {portfolio_dir}")
    if not root_key_path.exists():
        raise SystemExit(f"Root key file not found: {root_key_path}")

    root_key = _read_root_key(root_key_path)
    actor_candidates = [token.strip() for token in str(args.actor_candidates).split(",") if token.strip()]
    if not actor_candidates:
        raise SystemExit("At least one actor candidate is required")

    converted = 0
    skipped = 0
    errors: List[str] = []

    files = sorted(portfolio_dir.glob("*.json"))
    for file_path in files:
        try:
            result = _migrate_file(
                file_path=file_path,
                root_key=root_key,
                actor_candidates=actor_candidates,
                purpose_prefix=str(args.purpose_prefix),
                dry_run=bool(args.dry_run),
            )
            if result in ("converted", "would-convert"):
                converted += 1
            else:
                skipped += 1
            print(f"{file_path.name}: {result}")
        except Exception as exc:
            errors.append(f"{file_path.name}: {type(exc).__name__}: {exc}")
            print(f"{file_path.name}: error")

    print("summary:")
    print(f"  files={len(files)}")
    print(f"  converted_or_would_convert={converted}")
    print(f"  skipped={skipped}")
    print(f"  errors={len(errors)}")
    for item in errors:
        print(f"  - {item}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
