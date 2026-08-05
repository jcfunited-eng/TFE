#!/usr/bin/env python3
"""Recoverably quarantine one exact unpublished generation over ECS Exec."""

from __future__ import annotations

import argparse
import base64
import json
import re

from ecs_seal_transport import _run_interactive


_MARKER = "__GUALA_QUARANTINE_RESULT__"
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}"
)


def _remote_program(*, current_uuid: str, candidate_uuid: str) -> str:
    return f"""
import base64
import fcntl
import hashlib
import json
import os
import pathlib
import stat

root = pathlib.Path("/app/guala/sealed")
generations = root / "generations"
current_uuid = {current_uuid!r}
candidate_uuid = {candidate_uuid!r}
lock_path = root / ".generation-store.lock"
candidate = generations / candidate_uuid
quarantine_root = pathlib.Path(
    "/app/guala/recovery-quarantine/generations"
)
target = quarantine_root / candidate_uuid

flags = os.O_RDWR | os.O_CLOEXEC
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
descriptor = os.open(lock_path, flags)
try:
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RuntimeError("generation lock is not a unique regular file")
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    current = json.loads((root / "CURRENT").read_text(encoding="utf-8"))
    if current.get("generation_uuid") != current_uuid:
        raise RuntimeError("CURRENT changed before quarantine")
    if candidate_uuid == current_uuid:
        raise RuntimeError("refusing to quarantine CURRENT")
    if candidate.is_symlink() or not candidate.is_dir():
        raise RuntimeError("candidate is absent or unsafe")
    entries = sorted(path.name for path in candidate.iterdir())
    if entries != ["MANIFEST.json"]:
        raise RuntimeError("candidate contains unexpected materialization")
    manifest_path = candidate / "MANIFEST.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema") != "immutable_generation_content_manifest_v2":
        raise RuntimeError("candidate is not the exact unsupported V2 manifest")
    if manifest.get("generation_uuid") != candidate_uuid:
        raise RuntimeError("candidate manifest UUID changed")
    if manifest.get("identity") != current.get("identity"):
        raise RuntimeError("candidate identity differs from CURRENT")
    if manifest.get("tick") != current.get("tick"):
        raise RuntimeError("candidate tick differs from CURRENT")
    if target.exists() or target.is_symlink():
        raise RuntimeError("quarantine target already exists")
    quarantine_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.rename(candidate, target)
    for directory in (generations, quarantine_root):
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    result = {{
        "candidate_generation_uuid": candidate_uuid,
        "current_generation_uuid": current_uuid,
        "manifest_bytes": len(manifest_bytes),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "quarantine_path": str(target),
        "status": "quarantined_unpublished_generation",
    }}
finally:
    try:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)

encoded = base64.b64encode(
    json.dumps(
        result,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
).decode("ascii")
print({_MARKER!r} + encoded, flush=True)
""".strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--current-generation", required=True)
    parser.add_argument("--candidate-generation", required=True)
    arguments = parser.parse_args()
    for value in (
        arguments.current_generation,
        arguments.candidate_generation,
    ):
        if _UUID_RE.fullmatch(value) is None:
            parser.error("generation identifiers must be canonical UUIDs")

    program = base64.b64encode(
        _remote_program(
            current_uuid=arguments.current_generation,
            candidate_uuid=arguments.candidate_generation,
        ).encode("utf-8")
    ).decode("ascii")
    command = [
        "aws",
        "ecs",
        "execute-command",
        "--cluster",
        arguments.cluster,
        "--task",
        arguments.task,
        "--container",
        arguments.container,
        "--interactive",
        "--command",
        (
            "/usr/local/bin/python -c "
            f"'import base64;exec(base64.b64decode(\"{program}\"))'"
        ),
    ]
    completed = _run_interactive(command, timeout=120)
    if completed.returncode != 0:
        raise SystemExit(completed.stdout)
    matches = re.findall(
        re.escape(_MARKER) + r"([A-Za-z0-9+/]+={0,2})",
        completed.stdout,
    )
    if len(matches) != 1:
        raise SystemExit(
            "quarantine result frame is absent or ambiguous:\n"
            + completed.stdout
        )
    result = json.loads(base64.b64decode(matches[0]))
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
