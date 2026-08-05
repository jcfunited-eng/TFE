"""
Substrate Event Log — write-ahead, synchronous, replayable.

Events log is the canonical record. Snapshots are compaction checkpoints.
On boot: load snapshot + replay events since snapshot timestamp.

GL-SPEC-persistence-architecture-20260609
"""

import contextlib
import json
import os
import stat
import time
import threading
from pathlib import Path

from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
    PhysicalByteCeilingConfigurationError,
)


_COMPACTION_BOUNDARY_TYPE = "_compaction_boundary"


def _write_all(descriptor, data):
    view = memoryview(data)
    written = 0
    while written < len(view):
        count = os.write(descriptor, view[written:])
        if count <= 0:
            raise OSError("event-log write made no forward progress")
        written += count


def _validated_session_id(value):
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
    ):
        raise ValueError(
            "event-log session id must be one nonempty path component")
    return value


class EventLog:
    """Write-ahead event log for substrate state mutations.
    Every mutation writes an event BEFORE (or atomically with) the
    in-memory change. On crash, the events log has the event even
    if the in-memory state is lost."""

    def __init__(
            self, log_dir, session_id, *,
            physical_byte_authority=None,
            physical_byte_ceiling=None,
            physical_byte_scope=None):
        self.log_dir = log_dir
        self.session_id = _validated_session_id(session_id)
        self.log_filename = f"{session_id}.events.jsonl"
        self.log_path = os.path.join(log_dir, self.log_filename)
        self._lock = threading.Lock()
        os.makedirs(log_dir, exist_ok=True)
        root_info = os.lstat(log_dir)
        if (
            not stat.S_ISDIR(root_info.st_mode)
            or stat.S_ISLNK(root_info.st_mode)
        ):
            raise ValueError(
                "event-log directory must be a real directory")
        self._log_directory_identity = (
            root_info.st_dev,
            root_info.st_ino,
        )
        if physical_byte_authority is not None and (
            physical_byte_ceiling is not None
            or physical_byte_scope is not None
        ):
            raise ValueError(
                "event log accepts either a physical-byte authority or "
                "ceiling configuration, not both")
        if physical_byte_authority is not None:
            if not isinstance(
                    physical_byte_authority,
                    PhysicalByteCeilingAuthority):
                raise TypeError(
                    "physical_byte_authority must be a "
                    "PhysicalByteCeilingAuthority")
            self._physical_byte_authority = physical_byte_authority
        elif physical_byte_ceiling is not None:
            if physical_byte_scope is None:
                raise ValueError(
                    "physical-byte event-log ceiling requires a shared scope")
            self._physical_byte_authority = PhysicalByteCeilingAuthority(
                physical_byte_scope,
                physical_byte_ceiling,
            )
        else:
            if physical_byte_scope is not None:
                raise ValueError(
                    "physical-byte event-log scope requires a ceiling")
            self._physical_byte_authority = None
        if self._physical_byte_authority is not None:
            try:
                Path(self.log_dir).resolve().relative_to(
                    self._physical_byte_authority.scope_root)
            except ValueError as error:
                raise PhysicalByteCeilingConfigurationError(
                    "event-log directory must be inside the physical-byte "
                    "scope") from error
        try:
            log_info = os.lstat(self.log_path)
        except FileNotFoundError:
            pass
        else:
            if (
                not stat.S_ISREG(log_info.st_mode)
                or log_info.st_nlink != 1
            ):
                raise ValueError(
                    "event-log path must be a private regular file")
        self._event_count = self._recover_next_sequence()

    def physical_byte_status(self):
        if self._physical_byte_authority is None:
            return None
        return self._physical_byte_authority.status()

    def _open_verified_log_directory(self):
        try:
            descriptor = os.open(
                self.log_dir,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            )
        except OSError as error:
            raise ValueError(
                "event-log directory must remain the startup directory"
            ) from error
        descriptor_info = os.fstat(descriptor)
        if (
            descriptor_info.st_dev,
            descriptor_info.st_ino,
        ) != self._log_directory_identity:
            os.close(descriptor)
            raise ValueError(
                "event-log directory must remain the startup directory")
        return descriptor

    def _read_all_unlocked(self):
        directory_descriptor = self._open_verified_log_directory()
        try:
            try:
                descriptor = os.open(
                    self.log_filename,
                    os.O_RDONLY | os.O_NOFOLLOW,
                    dir_fd=directory_descriptor,
                )
            except FileNotFoundError:
                return []
        finally:
            os.close(directory_descriptor)
        descriptor_info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(descriptor_info.st_mode)
            or descriptor_info.st_nlink != 1
        ):
            os.close(descriptor)
            raise ValueError(
                "event-log path must remain a private regular file")
        events = []
        previous_sequence = None
        with os.fdopen(descriptor, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                terminated = line.endswith("\n")
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as error:
                    if not terminated:
                        break
                    raise EventLogReplayError(
                        "durable event log contains a malformed complete "
                        "record"
                    ) from error
                if not isinstance(event, dict):
                    raise EventLogReplayError(
                        "durable event log record is not an object")
                sequence = event.get("seq")
                event_type = event.get("t")
                if (
                    isinstance(sequence, bool)
                    or not isinstance(sequence, int)
                    or sequence < 0
                    or not isinstance(event_type, str)
                    or not event_type
                ):
                    raise EventLogReplayError(
                        "durable event log record metadata is invalid")
                if (
                    event_type == _COMPACTION_BOUNDARY_TYPE
                    and set(event) != {"seq", "t"}
                ):
                    raise EventLogReplayError(
                        "durable event log contains a forged compaction marker")
                if (
                    previous_sequence is not None
                    and sequence != previous_sequence + 1
                ):
                    raise EventLogReplayError(
                        "durable event log sequence is not contiguous")
                events.append(event)
                previous_sequence = sequence
        return events

    def _recover_next_sequence(self):
        highest = -1
        for event in self._read_all_unlocked():
            sequence = event.get("seq")
            if (
                isinstance(sequence, int)
                and not isinstance(sequence, bool)
                and sequence >= 0
            ):
                highest = max(highest, sequence)
        return highest + 1

    def write(self, event_type, **data):
        """Write one event synchronously to disk. Returns event dict."""
        if (
            not isinstance(event_type, str)
            or not event_type
            or event_type.strip() != event_type
            or event_type == _COMPACTION_BOUNDARY_TYPE
        ):
            raise ValueError(
                "event type must be a canonical nonempty public string")
        with self._lock:
            event = {
                **data,
                "t": event_type,
                "ts": time.time(),
                "seq": self._event_count,
            }
            line = (json.dumps(event, allow_nan=False) + "\n").encode("utf-8")
            authority_context = (
                contextlib.nullcontext()
                if self._physical_byte_authority is None
                else self._physical_byte_authority.exclusive_writer()
            )
            with authority_context:
                if self._physical_byte_authority is not None:
                    self._physical_byte_authority.admit(
                        operation=f"append_event_log:{self.log_filename}",
                        requested_bytes=len(line),
                    )
                directory_descriptor = self._open_verified_log_directory()
                try:
                    descriptor = os.open(
                        self.log_filename,
                        os.O_WRONLY
                        | os.O_APPEND
                        | os.O_CREAT
                        | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=directory_descriptor,
                    )
                finally:
                    os.close(directory_descriptor)
                descriptor_info = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(descriptor_info.st_mode)
                    or descriptor_info.st_nlink != 1
                ):
                    os.close(descriptor)
                    raise ValueError(
                        "event-log path must remain a private regular file")
                try:
                    _write_all(descriptor, line)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            self._event_count += 1
        return event

    def read_all(self):
        """Read all events from log. Returns list of dicts."""
        with self._lock:
            return [
                event
                for event in self._read_all_unlocked()
                if event.get("t") != _COMPACTION_BOUNDARY_TYPE
            ]

    def read_since(self, after_seq):
        """Read events at or after a snapshot's next-sequence boundary."""
        return [e for e in self.read_all() if e.get("seq", -1) >= after_seq]

    def truncate_before(self, seq):
        """Keep only events with seq >= seq. For compaction."""
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            raise ValueError("compaction sequence must be a non-negative integer")
        with self._lock:
            if seq > self._event_count:
                raise ValueError(
                    "compaction sequence cannot exceed the allocated "
                    "event frontier")
            durable_events = self._read_all_unlocked()
            durable_floor = 0
            if durable_events:
                first = durable_events[0]
                durable_floor = first["seq"]
                if first["t"] == _COMPACTION_BOUNDARY_TYPE:
                    durable_floor += 1
            if seq < durable_floor:
                raise ValueError(
                    "compaction sequence cannot precede the durable "
                    "event floor")
            events = [
                event
                for event in durable_events
                if (
                    event.get("t") != _COMPACTION_BOUNDARY_TYPE
                    and isinstance(event.get("seq"), int)
                    and not isinstance(event.get("seq"), bool)
                    and event["seq"] >= seq
                )
            ]
            durable = list(events)
            if seq > 0:
                durable.insert(0, {
                    "t": _COMPACTION_BOUNDARY_TYPE,
                    "seq": seq - 1,
                })
            payload = b"".join(
                (json.dumps(event, allow_nan=False) + "\n").encode("utf-8")
                for event in durable
            )
            temporary_filename = self.log_filename + ".tmp"
            authority_context = (
                contextlib.nullcontext()
                if self._physical_byte_authority is None
                else self._physical_byte_authority.exclusive_writer()
            )
            with authority_context:
                if self._physical_byte_authority is not None:
                    self._physical_byte_authority.admit(
                        operation=(
                            f"allocate_event_log_compaction:"
                            f"{self.log_filename}"),
                        requested_bytes=len(payload),
                    )
                directory_descriptor = self._open_verified_log_directory()
                try:
                    descriptor = os.open(
                        temporary_filename,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=directory_descriptor,
                    )
                    try:
                        _write_all(descriptor, payload)
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
                    if self._physical_byte_authority is not None:
                        self._physical_byte_authority.admit(
                            operation=(
                                f"rename_event_log_compaction:"
                                f"{self.log_filename}"),
                            requested_bytes=0,
                        )
                    os.replace(
                        temporary_filename,
                        self.log_filename,
                        src_dir_fd=directory_descriptor,
                        dst_dir_fd=directory_descriptor,
                    )
                    os.fsync(directory_descriptor)
                finally:
                    try:
                        os.unlink(
                            temporary_filename,
                            dir_fd=directory_descriptor,
                        )
                    except FileNotFoundError:
                        pass
                    os.close(directory_descriptor)
            self._event_count = max(self._event_count, seq)
            return len(events)

    @property
    def count(self):
        with self._lock:
            return self._event_count

    def exists(self):
        directory_descriptor = self._open_verified_log_directory()
        try:
            try:
                info = os.stat(
                    self.log_filename,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return False
        finally:
            os.close(directory_descriptor)
        return (
            stat.S_ISREG(info.st_mode)
            and info.st_nlink == 1
            and info.st_size > 0
        )


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
