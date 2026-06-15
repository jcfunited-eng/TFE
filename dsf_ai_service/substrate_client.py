"""
Substrate client — async client for frontend to talk to substrate runner
over a Unix socket using JSON-over-newline protocol.

GL-ARCH-FRONTEND-SPLIT-WC-20260614-01, Phase 1.
"""
import asyncio
import json
import os
import uuid

SOCKET_PATH = os.environ.get("SUBSTRATE_SOCKET", "/shared/substrate.sock")


class SubstrateClient:
    """Async client that talks to the substrate runner over Unix socket."""

    def __init__(self, socket_path=None):
        self.socket_path = socket_path or SOCKET_PATH
        self._reader = None
        self._writer = None
        self._lock = asyncio.Lock()

    @property
    def connected(self):
        return self._writer is not None and not self._writer.is_closing()

    async def _connect(self):
        """Connect (or reconnect) to the substrate socket."""
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader, self._writer = await asyncio.open_unix_connection(
            self.socket_path
        )

    async def call(self, op, timeout=30.0, **args):
        """Send an op to the substrate and return the result dict.

        Raises ConnectionError if substrate is unreachable.
        Raises RuntimeError if substrate returns an error.
        """
        async with self._lock:
            # Connect/reconnect if needed
            if not self.connected:
                try:
                    await self._connect()
                except (ConnectionRefusedError, FileNotFoundError, OSError) as e:
                    raise ConnectionError(f"substrate unreachable: {e}") from e

            req_id = str(uuid.uuid4())[:8]
            req = {"id": req_id, "op": op, "args": args}
            line = json.dumps(req, default=str) + "\n"

            try:
                self._writer.write(line.encode())
                await self._writer.drain()
                resp_line = await asyncio.wait_for(
                    self._reader.readline(), timeout=timeout
                )
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                # Connection lost — mark for reconnect
                self._writer = None
                self._reader = None
                raise ConnectionError(f"substrate connection lost: {e}") from e

            if not resp_line:
                self._writer = None
                self._reader = None
                raise ConnectionError("substrate disconnected (empty response)")

            resp = json.loads(resp_line)
            if not resp.get("ok"):
                raise RuntimeError(resp.get("error", "unknown substrate error"))
            return resp.get("result")

    async def close(self):
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None
