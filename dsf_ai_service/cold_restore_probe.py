"""Read-only fresh-process proof of one native-organism CURRENT pointer."""

from __future__ import annotations

import argparse
import hashlib
import json
import re

from dsf_ai_service.substrate.native_organism_binary_store import (
    restore_current_native_organism,
)
from dsf_ai_service.substrate.native_resident_resource_admission import (
    derive_native_resident_resource_admission,
)


PROOF_SCHEMA = "guala.production_native_current_cold_restore.v1"
_COMMIT = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-store-root", required=True)
    parser.add_argument("--expected-identity", required=True)
    parser.add_argument("--expected-tick", required=True, type=int)
    parser.add_argument("--expected-state-sha256", required=True)
    parser.add_argument("--candidate-git-sha", required=True)
    parser.add_argument("--candidate-image-digest", required=True)
    return parser.parse_args()


def main() -> int:
    values = _arguments()
    if _SHA256.fullmatch(values.expected_state_sha256) is None:
        raise ValueError("expected state SHA-256 is not canonical")
    if _COMMIT.fullmatch(values.candidate_git_sha) is None:
        raise ValueError("candidate commit is not canonical")
    if _DIGEST.fullmatch(values.candidate_image_digest) is None:
        raise ValueError("candidate image digest is not canonical")
    admission = derive_native_resident_resource_admission(
        values.native_store_root
    )
    restored = restore_current_native_organism(
        values.native_store_root,
        max_envelope_bytes=admission.max_envelope_bytes,
        max_fabric_bytes=admission.max_fabric_bytes,
        max_logical_peak_bytes=admission.max_logical_peak_bytes,
    )
    before = restored.organism.readiness()
    state = restored.organism.save()
    after = restored.organism.readiness()
    if (
        before.identity != values.expected_identity
        or before.organism_tick != values.expected_tick
        or before.state_sha256 != values.expected_state_sha256
        or before.state_sha256 != after.state_sha256
        or before.state_bytes != len(state)
        or hashlib.sha256(state).hexdigest() != before.state_sha256
        or before.python_callback_count != 0
        or restored.pointer.identity != before.identity
        or restored.pointer.organism_tick != before.organism_tick
        or restored.pointer.state_sha256 != before.state_sha256
    ):
        raise RuntimeError("native CURRENT cold restore changed")
    record = {
        "candidate_git_sha": values.candidate_git_sha,
        "candidate_image_digest": values.candidate_image_digest,
        "cold_restore_exact": True,
        "mode": "cold-restore",
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": before.state_bytes,
        "resident_state_sha256": before.state_sha256,
        "schema": PROOF_SCHEMA,
        "source_identity": before.identity,
        "source_mount_read_only": True,
        "tick": before.organism_tick,
    }
    proof = {
        **record,
        "receipt_sha256": hashlib.sha256(_canonical(record)).hexdigest(),
    }
    print(_canonical(proof).decode("ascii"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
