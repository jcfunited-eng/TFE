"""Production boundary contract for embedded voice-reply delivery.

The browser polls POST /api/v1/gualaloom with command=/thought.  In the
production embedded topology, that route must return the thought held by the
live substrate runner; proving only the internal cache is insufficient.
"""

import asyncio

import httpx

import dsf_ai_service.app as appmod
import dsf_ai_service.substrate_runner as substrate_runner


def test_embedded_thought_route_delivers_live_substrate_reply(monkeypatch):
    expected = {
        "speech": "the committed voice reply",
        "tick": 4321,
        "ts": 123.0,
        "category": "voice_reply",
        "source": "guala",
    }
    monkeypatch.setattr(appmod, "SUBSTRATE_MODE", "embedded")
    with substrate_runner._autonomous_thought_lock:
        substrate_runner._last_autonomous_thought = dict(expected)

    async def request_thought():
        transport = httpx.ASGITransport(
            app=appmod.app,
            raise_app_exceptions=False,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.post(
                "/api/v1/gualaloom",
                json={"text": "", "command": "/thought"},
            )

    response = asyncio.run(request_thought())

    assert response.status_code == 200
    assert response.json() == expected

