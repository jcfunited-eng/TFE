"""A NAMED boot halt must be externally visible as NOT ready.

Review ride-along 5 (2026-07-16): the named P4 halts
(WindowStoreIntegrityHalt / GualaBootIdentityUnreadableHalt /
GualaBootStateIntegrityHalt) were raised inside _eager_init, caught, and the
container kept answering /ready 200 — a healthy-looking zombie with no
substrate.  Contract under test: once a named halt is classified, /ready and
/ready/guala answer 503 with the halt reason; ordinary init errors keep their
existing (warming) semantics.
"""

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dsf_ai_service.app as appmod  # noqa: E402
from dsf_ai_service.substrate.window_manager import (  # noqa: E402
    WindowStoreIntegrityHalt,
)
from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    GualaBootIdentityUnreadableHalt,
    GualaBootStateIntegrityHalt,
)


def _run(coroutine):
    return asyncio.run(coroutine)


def _get(path):
    async def call():
        transport = httpx.ASGITransport(app=appmod.app)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.get(path)
    return _run(call())


# ── classifier: exactly the named halts, nothing else ───────────────────────

def test_classifier_names_every_p4_halt():
    for error in (
            WindowStoreIntegrityHalt("hash mismatch"),
            GualaBootIdentityUnreadableHalt("identity unreadable"),
            GualaBootStateIntegrityHalt("state without identity")):
        label = appmod._classify_boot_halt(error)
        assert label is not None
        assert type(error).__name__ in label


def test_classifier_ignores_ordinary_init_errors():
    assert appmod._classify_boot_halt(RuntimeError("EFS flake")) is None
    assert appmod._classify_boot_halt(ValueError("bad json")) is None


# ── readiness surface: 503 while halted, restored behavior otherwise ────────

def test_ready_reports_503_when_boot_halted(monkeypatch):
    monkeypatch.setattr(
        appmod, "_boot_halted",
        "WindowStoreIntegrityHalt: WAL record hash mismatch")
    response = _get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    assert "WindowStoreIntegrityHalt" in body["boot_halted"]
    assert response.headers.get("Retry-After") is not None


def test_ready_guala_reports_503_when_boot_halted(monkeypatch):
    monkeypatch.setattr(
        appmod, "_boot_halted",
        "GualaBootStateIntegrityHalt: state files vanished")
    response = _get("/ready/guala")
    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert "GualaBootStateIntegrityHalt" in response.json()["boot_halted"]


def test_ready_still_answers_normally_when_not_halted(monkeypatch):
    monkeypatch.setattr(appmod, "_boot_halted", None)
    response = _get("/ready")
    # Non-sealed test process: shallow-ready contract is unchanged.
    assert response.status_code == 200
    assert response.json()["ready"] is True
