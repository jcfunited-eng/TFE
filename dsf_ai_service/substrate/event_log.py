"""
Substrate Event Log — write-ahead, synchronous, replayable.

Events log is the canonical record. Snapshots are compaction checkpoints.
On boot: load snapshot + replay events since snapshot timestamp.

GL-SPEC-persistence-architecture-20260609
"""

import json
import os
import time
import threading


class EventLog:
    """Write-ahead event log for substrate state mutations.
    Every mutation writes an event BEFORE (or atomically with) the
    in-memory change. On crash, the events log has the event even
    if the in-memory state is lost."""

    def __init__(self, log_dir, session_id):
        self.log_dir = log_dir
        self.session_id = session_id
        self.log_path = os.path.join(log_dir, f"{session_id}.events.jsonl")
        self._lock = threading.Lock()
        self._event_count = 0
        os.makedirs(log_dir, exist_ok=True)

    def write(self, event_type, **data):
        """Write one event synchronously to disk. Returns event dict."""
        event = {
            "t": event_type,
            "ts": time.time(),
            "seq": self._event_count,
            **data,
        }
        line = json.dumps(event, default=str) + "\n"
        with self._lock:
            with open(self.log_path, "a") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            self._event_count += 1
        return event

    def read_all(self):
        """Read all events from log. Returns list of dicts."""
        if not os.path.exists(self.log_path):
            return []
        events = []
        with open(self.log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return events

    def read_since(self, after_seq):
        """Read events after a sequence number (for replay after snapshot)."""
        return [e for e in self.read_all() if e.get("seq", 0) > after_seq]

    def truncate_before(self, seq):
        """Keep only events with seq >= seq. For compaction."""
        events = [e for e in self.read_all() if e.get("seq", 0) >= seq]
        tmp = self.log_path + ".tmp"
        with open(tmp, "w") as f:
            for e in events:
                f.write(json.dumps(e, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, self.log_path)
        return len(events)

    @property
    def count(self):
        return self._event_count

    def exists(self):
        return os.path.exists(self.log_path) and os.path.getsize(self.log_path) > 0


class EventLogReplayError(Exception):
    """Raised when replay encounters an unknown event type."""
    pass


def replay_persistent(session, events):
    """Replay persistent events against a V7Session to reconstruct state.

    Only processes event types whose effects persist across sessions:
      - vocab_install: word installed into session vocab (persistent)
      - feedback: apply_feedback adjusts session state (persistent)
      - self_voice: telemetry — logged but not replayed (skip silently)

    Session-local types (converse, quiet) are written to the event log for
    observability but are NOT replayed here: their effects are captured by
    snapshot persistence (save_session after each converse). See
    GL-RPT-EVENT-LOG-REPLAY-SPLIT-C1-20260620-01 V1.2-V1.3.

    Raises EventLogReplayError for any unrecognized event type.
    """
    replayed = 0
    for ev in events:
        t = ev.get("t")

        if t == "vocab_install":
            slot = ev.get("slot")
            word = ev.get("word")
            if slot and word and word not in session.vocab.get(slot, []):
                session.lookup_or_install(word)
            replayed += 1

        elif t == "feedback":
            correct = ev.get("correct", False)
            session.apply_feedback(correct)
            replayed += 1

        elif t == "self_voice":
            # Telemetry — logged for observability, not replayed.
            pass

        elif t == "converse" or t == "quiet":
            # Session-local — effects snapshot-persisted via save_session.
            # Not replayed; skipped silently.
            pass

        else:
            raise EventLogReplayError(
                f"Unknown event type '{t}' at seq={ev.get('seq', '?')}. "
                f"Event log may contain data from a newer schema version."
            )

    return replayed


def reconstruct_session(session):
    """Reconstruct per-session transient state after replay_persistent.

    Currently a no-op. Mode_strength changes from tick_once/replay_tick
    are snapshot-persisted via save_session per converse (intentional,
    per GL-RPT-EVENT-LOG-REPLAY-SPLIT-C1-20260620-01 V1.3). Reserved
    for future per-session reconstruction work.
    """
    pass
