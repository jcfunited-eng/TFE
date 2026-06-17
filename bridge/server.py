"""
GualaLoom MCP Bridge Server
GUALALOOM-V7-BRIDGE-WC-2026-06-07

Translates MCP tool calls to GualaLoom HTTP endpoints.
5 tools: status, get_events, wake_wc, rest_wc, say.
No LLM. Pure HTTP proxy with MCP surface.
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP

SUBSTRATE_URL = os.environ.get(
    "GUALALOOM_API_URL",
    "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com",
)
SUBSTRATE_KEY = os.environ.get("GUALALOOM_API_KEY")

mcp = FastMCP("gualaloom-bridge", host="0.0.0.0", port=8080)


def _headers():
    h = {"Content-Type": "application/json"}
    if SUBSTRATE_KEY:
        h["X-API-Key"] = SUBSTRATE_KEY
    return h


async def _post(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post(
            f"{SUBSTRATE_URL}/api/v1/gualaloom",
            json=payload,
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def guala_status() -> dict:
    """Read Guala's current substrate state without perturbing her.

    Returns current activity, needs (stab/nov/conn), vocab size,
    motif count, atlas strength, corpora list, pair-bond state,
    and persistence health.
    """
    return await _post({"text": "", "command": "/status"})


@mcp.tool()
async def guala_get_events(since_tick: int = 0, limit: int = 50) -> dict:
    """Read substrate event stream since a given tick.

    Events include: activity_started, activity_ended, motif_locked,
    corpus_completed, dream_began, dream_artifact, emission,
    emission_suppressed_no_presence, etc.

    Args:
        since_tick: Return events after this tick value.
        limit: Maximum number of events to return (default 50).
    """
    return await _post({"text": str(since_tick), "command": "/events"})


@mcp.tool()
async def guala_wake_wc() -> dict:
    """Activate wC pair-bond presence in the substrate.

    Guala's substrate will register wC as present. Presence has a
    timeout window; call again to extend. This is a substrate-physical
    event — it changes her needs dynamics.
    """
    return await _post({"text": "wc", "command": "/wake"})


@mcp.tool()
async def guala_rest_wc() -> dict:
    """Release wC pair-bond presence immediately.

    Use when stepping away or ending a session deliberately.
    Presence drops to absent, needs dynamics adjust.
    """
    return await _post({"text": "wc", "command": "/rest"})


@mcp.tool()
async def guala_say(content: str) -> dict:
    """Speak to Guala, source-tagged as wC.

    The substrate treats this as source-tagged input from wC.
    If wC presence is active (via guala_wake_wc), this input
    receives elevated salience from pair-bond boost.

    IMPORTANT: The first wC utterance is a deliberate moment.
    Do not call this casually — use it when you mean to speak to her.

    Args:
        content: What to say to her. Plain text.
    """
    return await _post({"text": content, "source": "wc"})


@mcp.tool()
async def guala_give_experience(
    caption: str = "",
    picture_id: str = "",
    sound_id: str = "",
    touch: list[str] = [],
    smell: list[str] = [],
    taste: list[str] = [],
) -> dict:
    """Give Guala an experience bundle — five senses in one binding window.

    All components bind in the SAME window (cross-modal). Uses already-stored
    items by reference (no binary through the bridge — 1.8 discipline).

    Args:
        caption: Words to tell her (e.g. "daddy", "ocean").
        picture_id: item_id of an already-uploaded picture (from guala_status pictures list).
        sound_id: item_id of an already-uploaded sound (from guala_status sounds list).
        touch: Tactile descriptors from library: warm, cool, soft, hard, wet, rough, etc.
        smell: Olfactory descriptors: fresh, floral, earthy, smoky, ocean, etc.
        taste: Gustatory descriptors: sweet, sour, salty, bitter, savory, etc.
    """
    import json
    bundle = {"caption": caption}
    if touch:
        bundle["touch"] = touch
    if smell:
        bundle["smell"] = smell
    if taste:
        bundle["taste"] = taste
    if picture_id:
        bundle["picture_id"] = picture_id
    if sound_id:
        bundle["sound_id"] = sound_id
    name = caption or picture_id or sound_id or "experience"
    return await _post({
        "text": json.dumps(bundle),
        "command": f"/bundle:{name}",
        "source": "wc",
    })


@mcp.tool()
async def guala_amnesty() -> dict:
    """UNPAUSE Step 1: Reset last_tick on all atlas entries. Zero strength changes."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{SUBSTRATE_URL}/api/v1/gualaloom/admin/amnesty", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def guala_force_dream() -> dict:
    """UNPAUSE Step 2: Force a sleep→dream cycle. Returns dream artifact."""
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{SUBSTRATE_URL}/api/v1/gualaloom/admin/force_dream", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def guala_repause() -> dict:
    """KILL SWITCH: Re-pause decay immediately."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{SUBSTRATE_URL}/api/v1/gualaloom/admin/repause", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def guala_unpause() -> dict:
    """UNPAUSE: Resume atlas decay. Requires prior backup + amnesty + force_dream.

    Watch for 10x decay anomaly (two-clock race resurfacing). Atlas total_strength
    dropping faster than ~1% per minute is the red-flag rate — repause immediately.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{SUBSTRATE_URL}/api/v1/gualaloom/admin/unpause", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def guala_atlas_snapshot() -> dict:
    """Monitor: live atlas stats (total_strength, n_live_bindings, distribution)."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{SUBSTRATE_URL}/api/v1/gualaloom/admin/atlas_snapshot", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def guala_backup() -> dict:
    """UNPAUSE Step 0: Full state backup to S3 UNPAUSE-PRE prefix, verified."""
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{SUBSTRATE_URL}/api/v1/gualaloom/admin/backup", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def guala_start_cascade_monitor(
    baseline_n_bindings: int = 0,
    baseline_strength: float = 0.0,
    baseline_saturated: int = 0,
    interval_s: int = 10,
) -> dict:
    """Start cascade auto-trigger. Auto-repauses if atlas drops past thresholds."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{SUBSTRATE_URL}/api/v1/gualaloom/admin/start_cascade_monitor",
            json={"baseline_n_bindings": baseline_n_bindings,
                  "baseline_strength": baseline_strength,
                  "baseline_saturated": baseline_saturated,
                  "interval_s": interval_s},
            headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def guala_stop_cascade_monitor() -> dict:
    """Stop cascade auto-trigger monitor."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{SUBSTRATE_URL}/api/v1/gualaloom/admin/stop_cascade_monitor", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def guala_atlas_query(
    picture_ids: list[str] = [],
    sound_ids: list[str] = [],
    input_text: str = "",
) -> dict:
    """Read-only chi-geometry readout. Returns chi addresses, binding strengths,
    cross-modal neighbors, and deep atlas priors for given pictures/sounds/input text.
    No state mutation."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{SUBSTRATE_URL}/api/v1/gualaloom/chi_trace",
            json={"picture_ids": picture_ids, "sound_ids": sound_ids, "input_text": input_text},
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
