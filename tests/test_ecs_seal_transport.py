import base64
import json
import subprocess
import sys

import pytest

from tools import ecs_seal_transport as transport


NONCE = "a" * 64


def _terminal_output(*, status=200, body=b'{"ok":true}', error=None):
    payload = {
        "body_base64": base64.b64encode(body).decode("ascii"),
        "http_status": status,
        "transport_error": error,
    }
    encoded = base64.b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).decode()
    return (
        "\x1b[0mStarting session\r\n"
        "__GUALA_SEAL_WAIT__\r\n"
        f"{transport._RESULT_MARKER}{encoded}\x1b[0m\r\n"
        "Exiting session\r\n"
    )


def _completed(command, *, returncode=0, output=""):
    return subprocess.CompletedProcess(
        command,
        returncode,
        output,
        "",
    )


def test_remote_seal_targets_local_owner_and_reads_task_secret():
    program = transport._remote_program(NONCE, "seal")
    assert "http://127.0.0.1:8080/internal/deployment/quiesce" in program
    assert 'os.environ["GUALALOOM_API_KEY"]' in program
    assert NONCE in program
    assert "dsf-ai.com" not in program


def test_remote_ready_probe_is_non_mutating():
    program = transport._remote_program(NONCE, "ready")
    assert "http://127.0.0.1:8080/ready" in program
    assert 'operation == "ready"' in program
    assert "method=\"GET\"" in program


def test_real_pty_runner_preserves_terminal_result():
    output = _terminal_output(status=200, body=b'{"ready":true}')
    completed = transport._run_interactive(
        [
            sys.executable,
            "-c",
            f"import sys;sys.stdout.write({output!r});sys.stdout.flush()",
        ],
        timeout=5,
    )

    assert completed.returncode == 0
    assert transport._decode_result(completed.stdout) == (
        200,
        b'{"ready":true}',
    )


def test_request_returns_original_http_result_through_pty(monkeypatch):
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _completed(
            command,
            output=_terminal_output(
                status=503,
                body=b'{"ok":false}',
            ),
        )

    monkeypatch.setattr(transport, "_run_interactive", run)
    status, body = transport.request_seal(
        cluster="cluster",
        task="arn:task/exact",
        container="dsf-ai",
        nonce=NONCE,
    )
    assert (status, body) == (503, b'{"ok":false}')
    assert captured["command"][0:3] == ["aws", "ecs", "execute-command"]
    assert captured["command"][captured["command"].index("--task") + 1] == (
        "arn:task/exact"
    )
    assert captured["kwargs"]["timeout"] == (
        transport._REMOTE_SEAL_TIMEOUT_SECONDS
        + transport._LOCAL_SESSION_GRACE_SECONDS
    )


def test_ready_probe_uses_short_exact_owner_session(monkeypatch):
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _completed(
            command,
            output=_terminal_output(
                status=200,
                body=b'{"ready":true,"owner":true}',
            ),
        )

    monkeypatch.setattr(transport, "_run_interactive", run)
    status, body = transport.request_ready(
        cluster="cluster",
        task="arn:task/exact",
        container="dsf-ai",
        nonce=NONCE,
    )

    assert status == 200
    assert json.loads(body) == {"ready": True, "owner": True}
    assert captured["kwargs"]["timeout"] == (
        transport._REMOTE_READY_TIMEOUT_SECONDS
        + transport._LOCAL_SESSION_GRACE_SECONDS
    )


def test_request_rejects_missing_or_ambiguous_terminal_result(monkeypatch):
    monkeypatch.setattr(
        transport,
        "_run_interactive",
        lambda command, **_kwargs: _completed(
            command,
            output="__GUALA_SEAL_WAIT__\n",
        ),
    )
    with pytest.raises(RuntimeError, match="no unique terminal result"):
        transport.request_seal(
            cluster="cluster",
            task="task",
            container="container",
            nonce=NONCE,
        )


def test_request_fails_closed_on_remote_transport_error(monkeypatch):
    monkeypatch.setattr(
        transport,
        "_run_interactive",
        lambda command, **_kwargs: _completed(
            command,
            returncode=1,
            output=_terminal_output(
                status=None,
                body=b"",
                error="TimeoutError: timed out",
            ),
        ),
    )
    with pytest.raises(RuntimeError, match="remote seal request failed"):
        transport.request_seal(
            cluster="cluster",
            task="task",
            container="container",
            nonce=NONCE,
        )


def test_nonce_is_strict_lowercase_hex():
    with pytest.raises(ValueError, match="64 lowercase hex"):
        transport.request_seal(
            cluster="cluster",
            task="task",
            container="container",
            nonce="A" * 64,
        )
