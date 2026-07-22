"""
Ring buffers for Guala substrate — LMAX Disruptor-style.

SubstrateRing: single-writer (substrate tick loop), multi-reader (consumers).
InputRing: multi-writer (companion, bridge, admin), single-reader (substrate).

SubstrateRing has no lock on its single-writer hot path. InputRing uses one
short admission/drain lock so multiple writers cannot overwrite unread input.
Sequence counters provide ordering guarantees, and pre-allocated storage
avoids GC pressure during operation.
"""

import json
import threading
import numpy as np


DEFAULT_INPUT_RING_MAX_PENDING_BYTES = 16 * 1024 * 1024


class InputRingCapacityError(RuntimeError):
    """The inbound ring cannot retain another transport event safely."""


class Cursor:
    """Read cursor for a SubstrateRing. Each consumer gets its own cursor
    that tracks how far it has read independently of other consumers."""

    def __init__(self, ring):
        self._ring = ring
        # Start at current published position (no backfill of old events)
        self._read_seq = ring._published_seq

    def read_available(self):
        """Return list of events from cursor position to latest published.
        Non-blocking, wait-free. Returns empty list if caught up."""
        published = self._ring._published_seq
        if self._read_seq >= published:
            return []
        events = []
        mask = self._ring._mask
        start = self._read_seq
        # Cap to ring size to avoid reading overwritten entries
        if published - start > self._ring._size:
            start = published - self._ring._size
        for seq in range(start, published):
            idx = seq & mask
            # Only read if the sequence stamp matches — confirms not overwritten
            if self._ring._seq_array[idx] == seq:
                events.append(self._ring._data[idx])
        self._read_seq = published
        return events

    def read_one(self):
        """Return next event or None if caught up. Advances cursor by one."""
        published = self._ring._published_seq
        if self._read_seq >= published:
            return None
        # If writer has lapped us, jump forward
        if published - self._read_seq > self._ring._size:
            self._read_seq = published - self._ring._size
        idx = self._read_seq & self._ring._mask
        if self._ring._seq_array[idx] != self._read_seq:
            # Slot was overwritten between check and read — skip
            self._read_seq += 1
            return None
        event = self._ring._data[idx]
        self._read_seq += 1
        return event

    @property
    def behind(self):
        """Number of unread events."""
        return max(0, self._ring._published_seq - self._read_seq)


class SubstrateRing:
    """Single-writer, multi-reader ring buffer.

    The substrate tick loop is the sole writer. Consumers (persistence,
    S3 backup, debug listeners) subscribe and read at their own pace.

    Size must be a power of 2. Default 2^20 = 1,048,576 entries.
    """

    def __init__(self, size=1 << 20):
        if size & (size - 1) != 0:
            raise ValueError(f"size must be power of 2, got {size}")
        self._size = size
        self._mask = size - 1
        # Pre-allocated sequence array — uint64. Initial fill with max to
        # distinguish empty slots from seq=0.
        self._seq_array = np.full(size, np.iinfo(np.uint64).max, dtype=np.uint64)
        # Event data stored in a plain Python list (dict per slot)
        self._data = [None] * size
        # Monotonically increasing sequence counter.
        # Only the single writer thread touches this, so no lock needed.
        self._published_seq = 0

    def publish(self, kind, tick, **data):
        """Write one event to the ring. Returns the sequence number assigned.

        MUST be called from the single writer thread only.
        """
        seq = self._published_seq
        idx = seq & self._mask
        event = {"seq": seq, "kind": kind, "tick": tick, "data": data}
        self._data[idx] = event
        # Write the sequence stamp AFTER the data — this is the commit barrier.
        # Readers check _seq_array[idx] == expected_seq before reading data.
        self._seq_array[idx] = np.uint64(seq)
        self._published_seq = seq + 1
        return seq

    def subscribe(self):
        """Create a new read cursor starting at the current published position."""
        return Cursor(self)


class InputRing:
    """Multi-writer, single-reader ring buffer for inbound events.

    Multiple sources (companion text, bridge commands, sensory frames,
    admin signals) write concurrently. The substrate tick loop is the
    sole reader via drain().

    Size must be a power of 2. Default 2^16 = 65,536 entries.
    """

    # Valid input event kinds
    KINDS = frozenset({
        "text_input",
        "sight_frame",
        "sound_window",
        "experience_bundle",
        "wake_signal",
        "rest_signal",
        "admin_command",
    })

    def __init__(
        self,
        size=1 << 16,
        *,
        max_pending_bytes=DEFAULT_INPUT_RING_MAX_PENDING_BYTES,
    ):
        if size <= 0 or size & (size - 1) != 0:
            raise ValueError(f"size must be power of 2, got {size}")
        if (
            isinstance(max_pending_bytes, bool)
            or not isinstance(max_pending_bytes, int)
            or max_pending_bytes <= 0
        ):
            raise ValueError("max_pending_bytes must be a positive integer")
        self._size = size
        self._mask = size - 1
        self._max_pending_bytes = max_pending_bytes
        # Pre-allocated sequence array
        self._seq_array = np.full(size, np.iinfo(np.uint64).max, dtype=np.uint64)
        self._data = [None] * size
        self._slot_transport_bytes = [0] * size
        # One state lock makes admission, publication, draining, and byte
        # release one atomic ownership transition.  A claim can therefore
        # never advance ahead of its committed event, and an unread slot can
        # never be overwritten.
        self._claim_seq = 0
        self._read_seq = 0
        self._pending_transport_bytes = 0
        self._rejected_events = 0
        self._overrun_recoveries = 0
        self._state_lock = threading.Lock()

    @staticmethod
    def _transport_bytes(kind, source, data):
        """Exact canonical UTF-8 transport size retained by one event."""
        try:
            payload = json.dumps(
                {"data": data, "kind": kind, "source": source},
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise ValueError("input ring event is not canonical JSON") from error
        return len(payload)

    def _recover_overrun_locked(self):
        """Recover a legacy/lapped cursor instead of stalling forever.

        New publications cannot create this state because admission fails
        before overwrite.  The recovery remains for an already-lapped ring
        handed across a rolling code transition or for detected corruption.
        """
        earliest_available = max(0, self._claim_seq - self._size)
        if self._read_seq >= earliest_available:
            return
        self._read_seq = earliest_available
        self._pending_transport_bytes = sum(
            self._slot_transport_bytes[seq & self._mask]
            for seq in range(self._read_seq, self._claim_seq)
            if self._seq_array[seq & self._mask] == np.uint64(seq)
        )
        self._overrun_recoveries += 1

    def publish(self, kind, source, **data):
        """Atomically claim a slot and write an input event.

        Thread-safe for multiple concurrent writers.
        Returns the sequence number assigned.  Raises before mutation when
        either the slot capacity or retained transport-byte budget is full.
        """
        if kind not in self.KINDS:
            raise ValueError(f"unsupported input event kind: {kind!r}")
        transport_bytes = self._transport_bytes(kind, source, data)
        with self._state_lock:
            self._recover_overrun_locked()
            if self._claim_seq - self._read_seq >= self._size:
                self._rejected_events += 1
                raise InputRingCapacityError("input ring slot capacity is full")
            if (
                transport_bytes > self._max_pending_bytes
                or self._pending_transport_bytes + transport_bytes
                > self._max_pending_bytes
            ):
                self._rejected_events += 1
                raise InputRingCapacityError(
                    "input ring transport-byte capacity is full"
                )
            seq = self._claim_seq
            idx = seq & self._mask
            event = {"seq": seq, "kind": kind, "source": source, "data": data}
            self._data[idx] = event
            self._slot_transport_bytes[idx] = transport_bytes
            self._seq_array[idx] = np.uint64(seq)
            self._pending_transport_bytes += transport_bytes
            self._claim_seq = seq + 1
            return seq

    def drain(self, max_n=100):
        """Read up to max_n available events. Advances the read cursor.

        MUST be called from the single reader thread only (substrate tick loop).
        Returns list of events in sequence order.
        """
        if isinstance(max_n, bool) or not isinstance(max_n, int) or max_n < 0:
            raise ValueError("max_n must be a non-negative integer")
        events = []
        with self._state_lock:
            self._recover_overrun_locked()
            for _ in range(max_n):
                if self._read_seq >= self._claim_seq:
                    break
                seq = self._read_seq
                idx = seq & self._mask
                stamp = int(self._seq_array[idx])
                if stamp > seq:
                    # A legacy writer lapped this cursor. Move to the oldest
                    # sequence still physically present and continue.
                    self._read_seq = max(seq + 1, self._claim_seq - self._size)
                    self._overrun_recoveries += 1
                    continue
                if stamp != seq:
                    break
                events.append(self._data[idx])
                self._pending_transport_bytes -= self._slot_transport_bytes[idx]
                self._slot_transport_bytes[idx] = 0
                self._data[idx] = None
                self._seq_array[idx] = np.iinfo(np.uint64).max
                self._read_seq = seq + 1
            if self._pending_transport_bytes < 0:
                raise RuntimeError("input ring transport-byte accounting inverted")
        return events

    @property
    def pending(self):
        """Exact number of unread admitted events."""
        with self._state_lock:
            self._recover_overrun_locked()
            return max(0, self._claim_seq - self._read_seq)

    @property
    def pending_transport_bytes(self):
        with self._state_lock:
            self._recover_overrun_locked()
            return self._pending_transport_bytes

    @property
    def max_pending_transport_bytes(self):
        return self._max_pending_bytes

    @property
    def rejected_events(self):
        with self._state_lock:
            return self._rejected_events

    @property
    def overrun_recoveries(self):
        with self._state_lock:
            return self._overrun_recoveries
