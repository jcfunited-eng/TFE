#!/usr/bin/env python3
"""Use the exact ECS owner task for readiness proof and deployment sealing.

AWS ECS ExecuteCommand is an interactive Session Manager transport.  Running
it behind ordinary captured pipes can lose the terminal result even after the
remote request completed.  This client gives the AWS CLI a real pseudoterminal,
keeps the session alive while the cold seal runs, and extracts one exact
base64-framed terminal result.

The seal API key never enters local arguments or the session transcript.  The
remote program reads it from the task's existing environment.
"""

from __future__ import annotations

import argparse
import base64
import errno
import fcntl
import json
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import textwrap
import time


_NONCE_RE = re.compile(r"[0-9a-f]{64}")
_RESULT_MARKER = "__GUALA_SEAL_RESULT__"
_RESULT_RE = re.compile(
    re.escape(_RESULT_MARKER) + r"([A-Za-z0-9+/]+={0,2})"
)
_OPERATIONS = frozenset({"ready", "seal"})
# Revision 739's one-time migration seal measured roughly 17 minutes for
# serialization before candidate restore/upload.  The generation authority
# independently caps every candidate at 2 GiB.  This is a watchdog, not a
# performance target.
_REMOTE_SEAL_TIMEOUT_SECONDS = 5_400
_REMOTE_READY_TIMEOUT_SECONDS = 30
_LOCAL_SESSION_GRACE_SECONDS = 60


def _remote_program(nonce: str, operation: str = "seal") -> str:
    if operation not in _OPERATIONS:
        raise ValueError("unsupported ECS owner operation")
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
        operation = {operation!r}
        result = {{}}

        def request_owner():
            if operation == "ready":
                request = urllib.request.Request(
                    "http://127.0.0.1:8080/ready",
                    method="GET",
                )
                timeout = {_REMOTE_READY_TIMEOUT_SECONDS}
            else:
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
                timeout = {_REMOTE_SEAL_TIMEOUT_SECONDS}
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=timeout,
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

        worker = threading.Thread(target=request_owner, daemon=False)
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


def _command(
        *, cluster: str, task: str, container: str, nonce: str,
        operation: str = "seal") -> list[str]:
    program = base64.b64encode(
        _remote_program(nonce, operation).encode("utf-8")
    ).decode("ascii")
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


def _terminate_session(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait(timeout=5)


def _read_pty(master_fd: int) -> bytes:
    try:
        return os.read(master_fd, 65_536)
    except OSError as error:
        if error.errno == errno.EIO:
            return b""
        raise


def _run_interactive(
        command: list[str], *, timeout: int) -> subprocess.CompletedProcess:
    """Run one Session Manager command with a real terminal and exact timeout."""
    master_fd, slave_fd = pty.openpty()
    fcntl.ioctl(
        slave_fd,
        termios.TIOCSWINSZ,
        struct.pack("HHHH", 24, 4096, 0, 0),
    )
    environment = dict(os.environ)
    environment.update({
        "AWS_PAGER": "",
        "COLUMNS": "4096",
        "LINES": "24",
        "TERM": "dumb",
    })
    process = None
    chunks = []
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(
            command,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            env=environment,
            start_new_session=True,
        )
        os.close(slave_fd)
        slave_fd = -1
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                output = b"".join(chunks).decode("utf-8", errors="replace")
                raise subprocess.TimeoutExpired(
                    command,
                    timeout,
                    output=output,
                )
            readable, _, _ = select.select(
                [master_fd],
                [],
                [],
                min(1.0, remaining),
            )
            if readable:
                data = _read_pty(master_fd)
                if data:
                    chunks.append(data)
                elif process.poll() is not None:
                    break
            if process.poll() is not None:
                while select.select([master_fd], [], [], 0)[0]:
                    data = _read_pty(master_fd)
                    if not data:
                        break
                    chunks.append(data)
                break
        return subprocess.CompletedProcess(
            command,
            process.wait(),
            b"".join(chunks).decode("utf-8", errors="replace"),
            "",
        )
    except BaseException:
        if process is not None:
            _terminate_session(process)
        raise
    finally:
        if slave_fd >= 0:
            os.close(slave_fd)
        os.close(master_fd)


def _decode_result(output: str) -> tuple[int, bytes]:
    encoded_results = _RESULT_RE.findall(output)
    if len(encoded_results) != 1:
        raise RuntimeError(
            "ECS seal transport returned no unique terminal result"
        )
    try:
        payload = json.loads(
            base64.b64decode(
                encoded_results[0],
                validate=True,
            ).decode("utf-8")
        )
        if set(payload) != {
            "body_base64",
            "http_status",
            "transport_error",
        }:
            raise ValueError("terminal payload field set changed")
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


def _request(
        *, cluster: str, task: str, container: str, nonce: str,
        operation: str) -> tuple[int, bytes]:
    if not _NONCE_RE.fullmatch(nonce):
        raise ValueError(
            "deployment nonce must be exactly 64 lowercase hex digits")
    if operation not in _OPERATIONS:
        raise ValueError("unsupported ECS owner operation")
    remote_timeout = (
        _REMOTE_SEAL_TIMEOUT_SECONDS
        if operation == "seal"
        else _REMOTE_READY_TIMEOUT_SECONDS
    )
    completed = _run_interactive(
        _command(
            cluster=cluster,
            task=task,
            container=container,
            nonce=nonce,
            operation=operation,
        ),
        timeout=remote_timeout + _LOCAL_SESSION_GRACE_SECONDS,
    )
    combined = (completed.stdout or "") + "\n" + (completed.stderr or "")
    try:
        return _decode_result(combined)
    except RuntimeError:
        if completed.returncode != 0 and _RESULT_MARKER not in combined:
            diagnostic = combined[-4_096:].strip()
            raise RuntimeError(
                "ECS ExecuteCommand session failed: "
                f"{diagnostic or 'no diagnostic output'}"
            )
        raise


def request_seal(
    *,
    cluster: str,
    task: str,
    container: str,
    nonce: str,
) -> tuple[int, bytes]:
    return _request(
        cluster=cluster,
        task=task,
        container=container,
        nonce=nonce,
        operation="seal",
    )


def request_ready(
    *,
    cluster: str,
    task: str,
    container: str,
    nonce: str,
) -> tuple[int, bytes]:
    return _request(
        cluster=cluster,
        task=task,
        container=container,
        nonce=nonce,
        operation="ready",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument(
        "--probe-ready",
        action="store_true",
        help="prove the exact owner and PTY transport without mutating it",
    )
    args = parser.parse_args(argv)
    try:
        request = request_ready if args.probe_ready else request_seal
        status, body = request(
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
