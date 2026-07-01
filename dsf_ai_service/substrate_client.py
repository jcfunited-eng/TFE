"""
Substrate client — dual-path after GL-CMD-PROCESS-COLLAPSE-61.

SUBSTRATE_MODE=embedded (ECS default after collapse): dispatches ops directly
  to OP_HANDLERS in substrate_runner. No asyncio.Lock — concurrent calls are
  independent and only serialize on Guala.lock inside the target handler.

SUBSTRATE_MODE=remote (legacy, kept for dev/transition): talks to substrate
  runner over Unix socket via JSON-over-newline protocol.
"""
import asyncio
import os

SUBSTRATE_MODE = os.environ.get("SUBSTRATE_MODE", "embedded")


class SubstrateClient:
    """Async substrate client. Embedded = direct dispatch; remote = socket."""

    def __init__(self, socket_path=None):
        if SUBSTRATE_MODE == "remote":
            import json  # noqa: confirm json is available at call time
            self._socket_path = (
                socket_path
                or os.environ.get("SUBSTRATE_SOCKET", "/shared/substrate.sock")
            )
            self._reader = None
            self._writer = None
            self._lock = asyncio.Lock()

    @property
    def connected(self):
        if SUBSTRATE_MODE == "embedded":
            try:
                import dsf_ai_service.substrate_runner as _sr
                return _sr._guala is not None
            except Exception:
                return False
        return self._writer is not None and not self._writer.is_closing()

    async def call(self, op, timeout=30.0, **args):
        """Dispatch op to substrate. Embedded: direct (no lock). Remote: socket."""
        if SUBSTRATE_MODE == "embedded":
            return await self._call_embedded(op, timeout, args)
        return await self._call_remote(op, timeout, args)

    async def _call_embedded(self, op, timeout, args):
        """Direct in-process dispatch — no asyncio.Lock, no socket."""
        from dsf_ai_service.substrate_runner import OP_HANDLERS, _guala
        if _guala is None:
            raise RuntimeError("substrate not ready")
        handler = OP_HANDLERS.get(op)
        if handler is None:
            raise RuntimeError(f"unknown op: {op}")
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: handler(args)),
                timeout=timeout,
            )
        except asyncio.TimeoutError as e:
            raise ConnectionError(f"substrate call timeout: op={op}") from e
        except Exception as e:
            raise RuntimeError(f"substrate error in {op}: {e}") from e
        if not isinstance(result, dict):
            return result
        if not result.get("ok", True):
            raise RuntimeError(result.get("error", "unknown substrate error"))
        return result.get("result", result)

    async def _call_remote(self, op, timeout, args):
        """Legacy socket path — kept for remote mode backward compatibility."""
        import json
        import uuid
        async with self._lock:
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

    async def _connect(self):
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader, self._writer = await asyncio.open_unix_connection(
            self._socket_path, limit=64 * 1024 * 1024
        )

    async def close(self):
        if SUBSTRATE_MODE == "remote" and self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None
