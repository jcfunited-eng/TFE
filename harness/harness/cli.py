"""Harness CLI.

Argparse-based, no external dependency. Per spec §4.1 invocation shape.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import __version__
from .runner import Runner, RunnerConfig
from .scenario import Scenario, ScenarioError
from .substrate_client import LegacySubstrateClient, MessagePassingSubstrateClient


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="harness",
        description="GualaLoom substrate verification harness "
                    f"(v{__version__})",
    )
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a scenario against a substrate")
    run_p.add_argument("scenario", help="Path to scenario YAML")
    run_p.add_argument(
        "--target",
        required=True,
        help="Substrate endpoint base URL",
    )
    run_p.add_argument(
        "--auth",
        required=True,
        help="Path to admin token JSON file",
    )
    run_p.add_argument(
        "--client-flavor",
        choices=["legacy", "message-passing"],
        default="legacy",
        help="Substrate client flavor. legacy = current substrate;"
             " message-passing = post-Phase-3-4 substrate",
    )
    run_p.add_argument(
        "--reports-dir",
        default="./reports",
        help="Directory to write reports into",
    )
    run_p.add_argument(
        "--aws-config",
        default=None,
        help="Path to AWS config JSON (cluster, service, filesystem_id, etc.)"
             " for AWS collector wiring. Optional in skeleton.",
    )
    run_p.add_argument("--dry-run", action="store_true")
    run_p.add_argument("--verbose", action="store_true")
    run_p.add_argument("--capture-only", action="store_true")
    run_p.add_argument("--compare", help="Prior report to diff against")
    run_p.add_argument("--baseline", action="store_true",
                       help="Mark this run as the new baseline")

    validate_p = sub.add_parser("validate", help="Parse and validate a scenario without running")
    validate_p.add_argument("scenario")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _cmd_validate(args)
    elif args.command == "run":
        return asyncio.run(_cmd_run(args))
    return 2


def _cmd_validate(args) -> int:
    try:
        scenario = Scenario.from_file(args.scenario)
        print(f"OK  {scenario.id}  ({scenario.category})")
        return 0
    except ScenarioError as e:
        print(f"FAIL {args.scenario}: {e}", file=sys.stderr)
        return 4


async def _cmd_run(args) -> int:
    # Load scenario
    try:
        scenario = Scenario.from_file(args.scenario)
    except ScenarioError as e:
        print(f"scenario error: {e}", file=sys.stderr)
        return 4

    # Load auth
    try:
        auth = json.loads(Path(args.auth).read_text())
        admin_token = auth.get("token", "")
    except Exception as e:
        print(f"auth load failed: {e}", file=sys.stderr)
        return 4

    # AWS config
    aws_config = None
    if args.aws_config:
        try:
            aws_config = json.loads(Path(args.aws_config).read_text())
        except Exception as e:
            print(f"aws-config load failed: {e}", file=sys.stderr)
            return 4

    # Client flavor
    if args.client_flavor == "legacy":
        client = LegacySubstrateClient(base_url=args.target, admin_token=admin_token)
    else:
        client = MessagePassingSubstrateClient(
            event_stream_url=args.target, admin_token=admin_token
        )

    config = RunnerConfig(
        substrate=client,
        scenario=scenario,
        reports_dir=Path(args.reports_dir),
        aws_config=aws_config,
        dry_run=args.dry_run,
        verbose=args.verbose,
        capture_only=args.capture_only,
    )

    runner = Runner(config)
    report = await runner.run()
    md_path, json_path = report.render(Path(args.reports_dir))
    print(f"verdict: {report.verdict.value}")
    print(f"report:  {md_path}")
    print(f"json:    {json_path}")
    return report.verdict.exit_code()


if __name__ == "__main__":
    sys.exit(main())
