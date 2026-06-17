"""
Ring buffers for Guala substrate — LMAX Disruptor-style.

SubstrateRing: single-writer (substrate tick loop), multi-reader (consumers).
InputRing: multi-writer (companion, bridge, admin), single-reader (substrate).

No locks on the hot path. Sequence counters provide ordering guarantees.
Pre-allocated storage avoids GC pressure during operation.
"""

import threading
import numpy as np


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

    def __init__(self, size=1 << 16):
        if size & (size - 1) != 0:
            raise ValueError(f"size must be power of 2, got {size}")
        self._size = size
        self._mask = size - 1
        # Pre-allocated sequence array
        self._seq_array = np.full(size, np.iinfo(np.uint64).max, dtype=np.uint64)
        self._data = [None] * size
        # Claim counter — writers atomically increment to reserve a slot.
        # Protected by a lightweight lock (the only lock; unavoidable for
        # multi-writer correctness without CAS instructions in Python).
        self._claim_seq = 0
        self._claim_lock = threading.Lock()
        # Published fence — set after data is written, so reader knows
        # the slot is safe to read. Uses the seq_array stamp.
        # Reader cursor — only touched by the single drain() caller.
        self._read_seq = 0

    def publish(self, kind, source, **data):
        """Atomically claim a slot and write an input event.

        Thread-safe for multiple concurrent writers.
        Returns the sequence number assigned.
        """
        # Claim phase — acquire slot atomically
        with self._claim_lock:
            seq = self._claim_seq
            self._claim_seq = seq + 1

        idx = seq & self._mask
        event = {"seq": seq, "kind": kind, "source": source, "data": data}
        self._data[idx] = event
        # Commit: stamp the sequence so the reader knows data is ready
        self._seq_array[idx] = np.uint64(seq)
        return seq

    def drain(self, max_n=100):
        """Read up to max_n available events. Advances the read cursor.

        MUST be called from the single reader thread only (substrate tick loop).
        Returns list of events in sequence order.
        """
        events = []
        for _ in range(max_n):
            seq = self._read_seq
            idx = seq & self._mask
            # Check if this slot has been published
            if self._seq_array[idx] != np.uint64(seq):
                break
            events.append(self._data[idx])
            self._read_seq = seq + 1
        return events

    @property
    def pending(self):
        """Approximate number of unread events."""
        return max(0, self._claim_seq - self._read_seq)
