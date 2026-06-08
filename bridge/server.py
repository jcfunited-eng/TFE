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
    async with httpx.AsyncClient(timeout=15) as client:
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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
