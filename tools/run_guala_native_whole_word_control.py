#!/usr/bin/env python3
"""Run the bounded native whole-word control after a read-only AWS gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from probe_guala_exact_self_hearing import _aws_health


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-task-definition", default="1429")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--cluster", default="tfe-web-cluster")
    parser.add_argument("--service", default="dsf-ai-service-lb")
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    arguments = _arguments()
    repository = Path(__file__).resolve().parents[1]
    native_source = repository / "native/guala_core/src/virtual_articulatory_body.rs"
    health = _aws_health(
        region=arguments.region,
        cluster=arguments.cluster,
        service=arguments.service,
        expected_task_definition=arguments.expected_task_definition,
    )
    arguments.output.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["GUALA_VOICE_HARNESS_DIR"] = str(arguments.output.resolve())
    completed = subprocess.run(
        (
            "cargo",
            "test",
            "--manifest-path",
            "native/guala_core/Cargo.toml",
            "--lib",
            "virtual_articulatory_body::tests::write_temporary_native_whole_word_control",
            "--",
            "--exact",
            "--ignored",
            "--nocapture",
            "--test-threads=1",
        ),
        check=False,
        cwd=repository,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    (arguments.output / "native-test.log").write_text(
        completed.stdout,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "native whole-word control failed; see "
            f"{arguments.output / 'native-test.log'}"
        )
    manifest_path = arguments.output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["aws_health"] = health
    manifest["source_commit"] = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        check=True,
        cwd=repository,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    manifest["source_files"] = {
        str(native_source.relative_to(repository)): _sha256(native_source),
        str(Path(__file__).resolve().relative_to(repository)): _sha256(
            Path(__file__).resolve()
        ),
    }
    manifest["artifacts"] = {
        path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in sorted(arguments.output.glob("*.wav"))
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
