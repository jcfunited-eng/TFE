"""Substrate client.

Wraps the substrate endpoints and bridge tools the harness needs. Two
flavors present at v1:

- LegacySubstrateClient: talks to the current pre-message-passing substrate
  via existing HTTP endpoints and the guala_* bridge tools. This is what
  runs against staging today.
- MessagePassingSubstrateClient: talks to the message-passing substrate
  once it exists. Subscribes directly to the event stream, uses the
  component snapshot API. Interface identical; implementation different.

The runner uses SubstrateClient (the abstract base) and doesn't know which
flavor it's got — chosen by the substrate target's declared shape in the
CLI config.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

import httpx


@dataclass
class SubstrateEvent:
    """One event from the substrate event stream. Shape matches
    guala_get_events output in the legacy substrate, and the event stream
    schema in the message-passing substrate."""

    tick: int
    wall_clock: float
    kind: str
    source_component: str
    payload: dict[str, Any]


@dataclass
class SubstrateStatus:
    """Snapshot of substrate state at a moment. Used for preconditions and
    for pre/post deltas."""

    tick: int
    identity: str
    current_activity: str | None
    vocab_size: int
    atlas_bindings: int
    deep_atlas_entries: int
    organism_neurons: int
    presence: dict[str, bool]     # {joe, wc, c1}
    ladder: dict[str, float]      # mean_utterance_len, question_rate, etc.
    raw: dict[str, Any]           # full raw for anything not enumerated


class SubstrateClient(ABC):
    """Runner-facing interface. Concrete client chosen by CLI config."""

    @abstractmethod
    async def status(self) -> SubstrateStatus:
        """One-shot substrate status. Used for preconditions and deltas."""

    @abstractmethod
    async def stream_events(
        self, since_tick: int
    ) -> AsyncIterator[SubstrateEvent]:
        """Async iterator over events from since_tick onward. Yields as
        events arrive; ends when the caller cancels the iteration."""

    @abstractmethod
    async def inject_probe(
        self, method: str, payload: dict[str, Any], auth_as: str
    ) -> dict[str, Any]:
        """Fire one probe step against the substrate. Returns whatever the
        endpoint returns for its own record-keeping — the substrate event
        stream is where the harness reads outcomes."""

    @abstractmethod
    async def snapshot_state(self, label: str) -> str:
        """Snapshot substrate state, return a snapshot ID for later
        restore. Used for pre-run snapshot in the runtime sequence."""

    @abstractmethod
    async def restore_state(self, snapshot_id: str) -> None:
        """Restore substrate state from a prior snapshot. Used in cleanup."""


def _map_status(raw: dict[str, Any]) -> SubstrateStatus:
    """Map a raw /api/v1/gualaloom {"command":"/status"} response (the
    same shape guala_status returns) onto SubstrateStatus.

    Field origins verified against live responses, not guessed:
      - tick has no top-level key; it lives at atlas_health.tick.
      - presence is {"joe": {"present": bool, ...}, ...} server-side;
        SubstrateStatus wants the flattened {"joe": bool, ...} the
        precondition checker in runner.py compares against directly.
    """
    presence_raw = raw.get("presence", {}) or {}
    atlas_health = raw.get("atlas_health", {}) or {}
    persistence_health = raw.get("persistence_health", {}) or {}
    deep_atlas = raw.get("deep_atlas", {}) or {}
    organism_growth = raw.get("organism_growth", {}) or {}
    current_activity = raw.get("current_activity") or {}

    return SubstrateStatus(
        tick=int(atlas_health.get("tick", 0)),
        identity=str(persistence_health.get("guala_identity", "")),
        current_activity=current_activity.get("kind"),
        vocab_size=int(raw.get("vocab", 0)),
        atlas_bindings=int(atlas_health.get("n_total_entries", 0)),
        deep_atlas_entries=int(deep_atlas.get("n_entries", 0)),
        organism_neurons=int(
            raw.get("organism_population", organism_growth.get("total_neurons", 0))
        ),
        presence={
            role: bool((presence_raw.get(role) or {}).get("present", False))
            for role in ("joe", "wc", "c1")
        },
        ladder=dict(raw.get("ladder", {}) or {}),
        raw=raw,
    )


def _map_event(raw: dict[str, Any]) -> SubstrateEvent:
    """Map one raw event dict from GET .../events onto SubstrateEvent.

    Known gap, not papered over: the legacy diary/event log's entries are
    shaped {tick, kind, detail} — there is no top-level source_component or
    wall_clock field the harness spec's event schema assumes. source_
    component is approximated from detail.source/emitter when present, or
    the first underscore-delimited token of kind as a last resort;
    wall_clock falls back to observation time when detail.ts is absent.
    This is real signal for Eve, not a harness bug: the message-passing
    substrate spec's own event schema (§5.2) is what actually fixes this.
    """
    detail = raw.get("detail", {}) or {}
    kind = str(raw.get("kind", ""))
    source_component = (
        detail.get("source")
        or detail.get("emitter")
        or detail.get("source_component")
        or (kind.split("_", 1)[0] if kind else "unknown")
    )
    wall_clock = detail.get("ts")
    if isinstance(wall_clock, str):
        try:
            from datetime import datetime
            wall_clock = datetime.fromisoformat(
                wall_clock.replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            wall_clock = time.time()
    elif not isinstance(wall_clock, (int, float)):
        wall_clock = time.time()

    return SubstrateEvent(
        tick=int(raw.get("tick", 0)),
        wall_clock=float(wall_clock),
        kind=kind,
        source_component=str(source_component),
        payload=dict(detail),
    )


class LegacySubstrateClient(SubstrateClient):
    """Talks to the current substrate via its HTTP surface.

    Wired per `GL-CMD-HARNESS-DEPLOY-EVE-20260706-v1` §3. There is no
    dedicated bridge-tool RPC channel reachable from a standalone process —
    the guala_* MCP bridge tools are themselves thin wrappers around this
    same HTTP surface (`bridge/server.py`), so this client calls the
    underlying endpoints directly rather than the MCP tools.

    Confirmed endpoint shapes (read directly from `bridge/server.py` and
    `dsf_ai_service/app.py`, not guessed):
      - status/wake/say/give_experience all funnel through one endpoint,
        POST {base_url}/api/v1/gualaloom, dispatched by an optional
        "command" field. No command + non-empty text = converse (202 +
        poll). A command present = synchronous JSON reply.
      - events: GET {base_url}/api/v1/gualaloom/events?since=<tick>&n=<n>
        (the dedicated route, app.py:3600 — distinct from the bridge's own
        command="/events" path, which silently drops its limit param).
      - backup: POST {base_url}/api/v1/gualaloom/admin/backup, no body.
        Fire-and-forget (202) even in embedded mode — completion shows up
        later as persistence_health.last_s3_backup on /status, not as a
        returned key. See snapshot_state() below for what this means for
        the returned "snapshot_id".
      - converse (the v7 session path, distinct from "say"): POST
        {base_url}/v7/converse, synchronous.
      - addpicture/addsound: multipart POST to
        {base_url}/api/v1/gualaloom/upload/{picture,sound}, form field
        name "file" (app.py:3792, 3889).
      - auth: every call sends header X-API-Key: <admin_token>, matching
        bridge/server.py's _headers(). Only the /admin/* routes actually
        enforce it server-side (_api_key_dep) — the main /api/v1/gualaloom
        route currently has no auth dependency in app.py. Sent unconditionally
        anyway so this client is correct once that gap closes.
    """

    def __init__(self, base_url: str, admin_token: str,
                 http_timeout_sec: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token
        self._http_timeout = http_timeout_sec
        # One v7 session per client instance, so a scenario's "converse"
        # probe steps share context across the run the way a real
        # conversational session would, rather than one-shotting each turn.
        self._v7_session_id = f"harness_{uuid.uuid4().hex[:12]}"

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.admin_token}

    async def status(self) -> SubstrateStatus:
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/gualaloom",
                json={"text": "", "command": "/status"},
                headers=self._headers(),
            )
            r.raise_for_status()
            raw = r.json()
        return _map_status(raw)

    async def stream_events(
        self, since_tick: int
    ) -> AsyncIterator[SubstrateEvent]:
        cursor = since_tick
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            while True:
                r = await client.get(
                    f"{self.base_url}/api/v1/gualaloom/events",
                    params={"since": cursor, "n": 200},
                    headers=self._headers(),
                )
                r.raise_for_status()
                raw = r.json()
                raw_events = raw if isinstance(raw, list) else raw.get("events", [])
                for e in raw_events:
                    tick = int(e.get("tick", cursor))
                    if tick <= cursor:
                        continue
                    yield _map_event(e)
                    cursor = tick
                await asyncio.sleep(0.2)  # 200ms cadence per dispatch §3

    async def inject_probe(
        self, method: str, payload: dict[str, Any], auth_as: str
    ) -> dict[str, Any]:
        if method == "give_experience":
            return await self._probe_give_experience(payload, auth_as)
        elif method == "say":
            return await self._probe_say(payload, auth_as)
        elif method == "converse":
            return await self._probe_converse(payload, auth_as)
        elif method == "wake":
            return await self._probe_wake(auth_as)
        elif method == "addpicture":
            return await self._probe_upload(payload, kind="picture")
        elif method == "addsound":
            return await self._probe_upload(payload, kind="sound")
        elif method == "direct_event":
            raise ValueError(
                "direct_event probe method is not supported on the legacy"
                " substrate — there is no raw event-injection surface;"
                " requires the message-passing substrate's event stream"
            )
        else:
            raise ValueError(f"unknown probe method: {method!r}")

    async def _probe_give_experience(
        self, payload: dict[str, Any], auth_as: str
    ) -> dict[str, Any]:
        # Bundle-shape mapping is a judgment call, not a confirmed contract:
        # the scenario schema's picture_ref/sound_ref (arbitrary test-fixture
        # paths) don't have a declared correspondence to the real bundle
        # handler's picture_id/sound_id (which expect IDs of items already
        # known to the substrate, e.g. via /upload/picture's response).
        # Passed through as-is; a mismatch here is real signal for the
        # report, not a harness bug to paper over.
        bundle: dict[str, Any] = {}
        if "word" in payload:
            bundle["caption"] = payload["word"]
        if payload.get("touch_descriptors"):
            bundle["touch"] = ",".join(payload["touch_descriptors"])
        if "picture_ref" in payload:
            bundle["picture_id"] = payload["picture_ref"]
        if "sound_ref" in payload:
            bundle["sound_id"] = payload["sound_ref"]
        source = payload.get("source_tag", auth_as)
        bundle_name = f"{source}_{uuid.uuid4().hex[:8]}"
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/gualaloom",
                json={
                    "text": json.dumps(bundle),
                    "command": f"/bundle:{bundle_name}",
                    "source": source,
                },
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def _probe_say(
        self, payload: dict[str, Any], auth_as: str
    ) -> dict[str, Any]:
        # No "command" key -> converse-shaped (202 + poll_url) per
        # gualaloom_chat's dispatch. inject_probe's contract is to fire and
        # return the endpoint's own bookkeeping response, not to poll to
        # completion — outcome observation is the event stream's job
        # (SubstrateClient.stream_events docstring).
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/gualaloom",
                json={"text": payload.get("text", ""), "source": auth_as},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def _probe_converse(
        self, payload: dict[str, Any], auth_as: str
    ) -> dict[str, Any]:
        # Distinct from "say": the v7 conversational session endpoint,
        # synchronous (no 202+poll dance).
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            r = await client.post(
                f"{self.base_url}/v7/converse",
                json={
                    "text": payload.get("text", ""),
                    "session_id": self._v7_session_id,
                    "emission_mode": payload.get("emission_mode"),
                },
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def _probe_wake(self, auth_as: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/gualaloom",
                json={"text": auth_as, "command": "/wake"},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def _probe_upload(
        self, payload: dict[str, Any], kind: str
    ) -> dict[str, Any]:
        path = payload.get("path")
        if not path:
            raise ValueError(
                f"addpicture/addsound probe requires payload.path (local file"
                f" to upload) — no route accepts an inline picture_ref/"
                f"sound_ref string, only multipart upload"
            )
        file_path = Path(path)
        content = file_path.read_bytes()
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/gualaloom/upload/{kind}",
                files={"file": (file_path.name, content)},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def snapshot_state(self, label: str) -> str:
        # admin_backup is fire-and-forget even in embedded mode (app.py:3091-
        # 3094 comment: save+S3 upload takes 30-120s, API GW has a 30s cap) —
        # it returns 202 immediately with no backup key/ID. There is nothing
        # to poll to confirm completion within a run-scoped timeout budget;
        # the only observable signal is persistence_health.last_s3_backup on
        # a LATER /status call, with no correlation ID tying it back to THIS
        # backup call. The returned "snapshot_id" here is therefore a locally
        # -generated label, not a real handle — restore_state() below can't
        # use it for anything and doesn't try to. Flagged as a finding in the
        # deploy report; this is a real gap in what "snapshot" can mean on
        # the legacy substrate, not a harness bug.
        snapshot_id = f"{label}_{int(time.time())}"
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/gualaloom/admin/backup",
                headers=self._headers(),
            )
            r.raise_for_status()
        return snapshot_id

    async def restore_state(self, snapshot_id: str) -> None:
        # Confirmed (not assumed): the only restore-shaped endpoint on the
        # legacy substrate is POST /api/v1/gualaloom/admin/restore_from_s3_
        # prefix (app.py:3287), which explicitly requires a substrate
        # RESTART afterward to take effect. A harness scenario run cannot
        # restart the ECS service as part of its own cleanup step (that is
        # substrate-side infrastructure control, out of this dispatch's
        # scope per the guardrails, and would make a "verification harness"
        # capable of taking the substrate down — a much larger blast radius
        # than a test tool should have). There is no synchronous,
        # same-process restore path. Per dispatch: mark DIRTY, add a
        # finding, exit RESTORE_FAILED — raising a plain exception (not
        # NotImplementedError) so runner.py's cleanup() routes this into its
        # CRITICAL/DIRTY branch rather than the softer NotImplementedError/
        # WATCH branch.
        raise RuntimeError(
            "LegacySubstrateClient.restore_state: no usable restore path on"
            " the legacy substrate — the only candidate endpoint"
            " (admin/restore_from_s3_prefix) requires a substrate restart to"
            " take effect, which is out of a harness run's scope. Substrate"
            " is DIRTY after this scenario; route to Eve for a scope"
            " decision before running further scenarios against this target."
        )


class MessagePassingSubstrateClient(SubstrateClient):
    """Talks to the message-passing substrate via its event stream and
    component snapshot API.

    Not implemented at all in v1 — the message-passing substrate does not
    exist yet. Kept here as a placeholder so the interface split is
    visible in the code from day one.
    """

    def __init__(self, event_stream_url: str, admin_token: str):
        self.event_stream_url = event_stream_url
        self.admin_token = admin_token

    async def status(self) -> SubstrateStatus:
        raise NotImplementedError(
            "MessagePassingSubstrateClient not yet implemented — awaits"
            " Phase 3-4 architecture rewrite per GL-SPEC-SUBSTRATE-FOUNDATION"
            "-EVE-20260706-v1 §5"
        )

    async def stream_events(
        self, since_tick: int
    ) -> AsyncIterator[SubstrateEvent]:
        raise NotImplementedError(
            "MessagePassingSubstrateClient not yet implemented"
        )
        yield  # pragma: no cover

    async def inject_probe(
        self, method: str, payload: dict[str, Any], auth_as: str
    ) -> dict[str, Any]:
        raise NotImplementedError(
            "MessagePassingSubstrateClient not yet implemented"
        )

    async def snapshot_state(self, label: str) -> str:
        raise NotImplementedError(
            "MessagePassingSubstrateClient not yet implemented"
        )

    async def restore_state(self, snapshot_id: str) -> None:
        raise NotImplementedError(
            "MessagePassingSubstrateClient not yet implemented"
        )
