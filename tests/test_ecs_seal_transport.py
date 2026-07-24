import base64
import json
from types import SimpleNamespace

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
        "Starting session\n"
        "__GUALA_SEAL_WAIT__\n"
        f"{transport._RESULT_MARKER}{encoded}\n"
        "Exiting session\n"
    )


def test_remote_program_targets_local_owner_and_reads_task_secret():
    program = transport._remote_program(NONCE)
    assert "http://127.0.0.1:8080/internal/deployment/quiesce" in program
    assert 'os.environ["GUALALOOM_API_KEY"]' in program
    assert NONCE in program
    assert "dsf-ai.com" not in program


def test_request_returns_original_http_result(monkeypatch):
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=_terminal_output(status=503, body=b'{"ok":false}'),
            stderr="",
        )

    monkeypatch.setattr(transport.subprocess, "run", run)
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
        transport._LOCAL_SESSION_TIMEOUT_SECONDS
    )


def test_request_rejects_missing_or_ambiguous_terminal_result(monkeypatch):
    monkeypatch.setattr(
        transport.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="__GUALA_SEAL_WAIT__\n",
            stderr="",
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
        transport.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout=_terminal_output(
                status=None,
                body=b"",
                error="TimeoutError: timed out",
            ),
            stderr="",
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
