"""Substrate event stream collector.

Subscribes to the substrate event stream and captures every event fired
during the run window. Correlates with trace_id t_offset_ms.

This is the load-bearing collector — everything else is context. Runner
crashes if this fails; degraded is not enough for the primary event
stream.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..substrate_client import SubstrateClient, SubstrateEvent
from ..types import TraceId
from .collector import Collector, Sample


class EventStreamCollector(Collector):
    """Streams substrate events into the harness for the run window.

    Unlike the /proc-based collectors which sample at a fixed interval,
    this one runs a continuous subscription and appends every event as
    it arrives. Sample interval controls how often the summary metrics
    are recomputed for the report, not how often events are captured.
    """

    name = "substrate_events"
    sample_interval_ms = 1000

    def __init__(
        self,
        trace_id: TraceId,
        substrate: SubstrateClient,
        since_tick: int,
    ):
        super().__init__(trace_id)
        self.substrate = substrate
        self.since_tick = since_tick
        self._events: list[SubstrateEvent] = []
        self._stream_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start both the event subscription and the sampling loop."""
        # Kick off the subscription first so we don't miss events fired
        # between probe injection and the first sample tick.
        self._stream_task = asyncio.create_task(
            self._stream_loop(), name="event_stream_subscription"
        )
        await super().start()

    async def stop(self) -> None:
        """Stop the sampling loop and the event subscription."""
        await super().stop()
        if self._stream_task is not None:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except (asyncio.CancelledError, Exception):
                pass
            self._stream_task = None

    async def _stream_loop(self) -> None:
        """Continuous subscription. Captures every event as it arrives.

        On error, marks degraded but continues attempting to reconnect —
        losing events from a transient network blip is preferable to
        losing all subsequent events.
        """
        while not self._stop_event.is_set():
            try:
                async for event in self.substrate.stream_events(
                    since_tick=self.since_tick
                ):
                    self._events.append(event)
                    self.since_tick = event.tick
                    if self._stop_event.is_set():
                        break
            except NotImplementedError:
                # Client isn't wired yet. Mark degraded, don't spin.
                self._mark_degraded(
                    "SubstrateClient.stream_events not implemented"
                )
                return
            except Exception as e:
                self._mark_degraded(
                    f"event stream error: {type(e).__name__}: {e}"
                )
                # Back off before retry to avoid hammering
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    pass

    async def _sample_once(self) -> Sample | None:
        """Emit a rate sample: events observed per second in the last window."""
        return Sample(
            t_offset_ms=self.trace_id.t_offset_ms(),
            values={
                "total_events": len(self._events),
                "latest_tick": self._events[-1].tick if self._events else 0,
            },
        )

    def _summarize(self) -> dict[str, Any]:
        """Summary: event count by kind, by source_component, time span."""
        by_kind: dict[str, int] = {}
        by_source: dict[str, int] = {}
        for event in self._events:
            by_kind[event.kind] = by_kind.get(event.kind, 0) + 1
            by_source[event.source_component] = (
                by_source.get(event.source_component, 0) + 1
            )
        first_tick = self._events[0].tick if self._events else 0
        last_tick = self._events[-1].tick if self._events else 0
        return {
            "total_events": len(self._events),
            "unique_kinds": len(by_kind),
            "unique_sources": len(by_source),
            "by_kind": by_kind,
            "by_source_component": by_source,
            "first_tick": first_tick,
            "last_tick": last_tick,
            "tick_span": last_tick - first_tick,
        }

    def events(self) -> list[SubstrateEvent]:
        """Return the captured events, in arrival order. The expectations
        checker consumes this; the report renders it."""
        return list(self._events)
