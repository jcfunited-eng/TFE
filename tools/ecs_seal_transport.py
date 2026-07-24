#!/usr/bin/env python3
"""Request a Guala deployment seal through the exact ECS task.

The public ALB is a serving surface, not a management-plane transport.  Its
idle timeout can expire while a valid cold restore is still running and turn
an eventual seal into an ambiguous deployment result.  This client uses ECS
ExecuteCommand to run the authenticated request against localhost inside the
already-proven sole owner.  The remote request emits heartbeats through the
SSM session, then returns the original HTTP body and status to the caller.

The API key never enters the ECS command or local process arguments.  It is
read from the task's existing ``GUALALOOM_API_KEY`` environment variable.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import textwrap


_NONCE_RE = re.compile(r"[0-9a-f]{64}")
_RESULT_MARKER = "__GUALA_SEAL_RESULT__"
_REMOTE_REQUEST_TIMEOUT_SECONDS = 1_800
_LOCAL_SESSION_TIMEOUT_SECONDS = 1_860


def _remote_program(nonce: str) -> str:
    return textwrap.dedent(
        f"""
        import base64
        import json
        import os
        import sys
        import threading
        import urllib.error
        import urllib.request

        nonce = {nonce!r}
        result = {{}}

        def request_seal():
            body = json.dumps({{"deploy_nonce": nonce}}).encode("utf-8")
            request = urllib.request.Request(
                "http://127.0.0.1:8080/internal/deployment/quiesce",
                data=body,
                headers={{
                    "Content-Type": "application/json",
                    "X-API-Key": os.environ["GUALALOOM_API_KEY"],
                    "X-Deploy-Nonce": nonce,
                }},
                method="POST",
            )
            try:
                with urllib.request.urlopen(
                    request,
                    timeout={_REMOTE_REQUEST_TIMEOUT_SECONDS},
                ) as response:
                    result["http_status"] = int(response.status)
                    result["body"] = response.read()
                    result["transport_error"] = None
            except urllib.error.HTTPError as error:
                result["http_status"] = int(error.code)
                result["body"] = error.read()
                result["transport_error"] = None
            except BaseException as error:
                result["http_status"] = None
                result["body"] = b""
                result["transport_error"] = (
                    type(error).__name__ + ": " + str(error)
                )

        worker = threading.Thread(target=request_seal, daemon=False)
        worker.start()
        while worker.is_alive():
            print("__GUALA_SEAL_WAIT__", flush=True)
            worker.join(30.0)
        worker.join()
        payload = {{
            "http_status": result.get("http_status"),
            "body_base64": base64.b64encode(
                result.get("body", b"")
            ).decode("ascii"),
            "transport_error": result.get("transport_error"),
        }}
        encoded = base64.b64encode(
            json.dumps(
                payload,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).decode("ascii")
        print({_RESULT_MARKER!r} + encoded, flush=True)
        sys.exit(0 if payload["transport_error"] is None else 1)
        """
    ).strip()


def _command(*, cluster: str, task: str, container: str, nonce: str) -> list[str]:
    program = base64.b64encode(_remote_program(nonce).encode("utf-8")).decode(
        "ascii"
    )
    remote_command = (
        "/usr/local/bin/python -c "
        f"'import base64;exec(base64.b64decode(\"{program}\"))'"
    )
    return [
        "aws",
        "ecs",
        "execute-command",
        "--cluster",
        cluster,
        "--task",
        task,
        "--container",
        container,
        "--interactive",
        "--command",
        remote_command,
    ]


def _decode_result(output: str) -> tuple[int, bytes]:
    encoded_results = [
        line.split(_RESULT_MARKER, 1)[1].strip()
        for line in output.splitlines()
        if _RESULT_MARKER in line
    ]
    if len(encoded_results) != 1:
        raise RuntimeError(
            "ECS seal transport returned no unique terminal result"
        )
    try:
        payload = json.loads(
            base64.b64decode(encoded_results[0], validate=True).decode("utf-8")
        )
        transport_error = payload["transport_error"]
        status = payload["http_status"]
        body = base64.b64decode(payload["body_base64"], validate=True)
    except Exception as error:
        raise RuntimeError("ECS seal transport result is malformed") from error
    if transport_error is not None:
        raise RuntimeError(f"remote seal request failed: {transport_error}")
    if isinstance(status, bool) or not isinstance(status, int):
        raise RuntimeError("remote seal response has no HTTP status")
    return status, body


def request_seal(
    *,
    cluster: str,
    task: str,
    container: str,
    nonce: str,
) -> tuple[int, bytes]:
    if not _NONCE_RE.fullmatch(nonce):
        raise ValueError("deployment nonce must be exactly 64 lowercase hex digits")
    completed = subprocess.run(
        _command(
            cluster=cluster,
            task=task,
            container=container,
            nonce=nonce,
        ),
        check=False,
        capture_output=True,
        text=True,
        timeout=_LOCAL_SESSION_TIMEOUT_SECONDS,
    )
    combined = (completed.stdout or "") + "\n" + (completed.stderr or "")
    try:
        return _decode_result(combined)
    except RuntimeError:
        if completed.returncode != 0 and _RESULT_MARKER not in combined:
            diagnostic = combined[-4_096:].strip()
            raise RuntimeError(
                "ECS ExecuteCommand seal session failed: "
                f"{diagnostic or 'no diagnostic output'}"
            )
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--nonce", required=True)
    args = parser.parse_args(argv)
    try:
        status, body = request_seal(
            cluster=args.cluster,
            task=args.task,
            container=args.container,
            nonce=args.nonce,
        )
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.write(f"\n__HTTP__{status}\n".encode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
