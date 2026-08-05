"""
Ring buffer consumers for persistence and S3 backup.

PersistenceConsumer: subscribes to SubstrateRing, writes append-only event log,
triggers checkpoint snapshots every 50,000 events.

S3Consumer: subscribes to SubstrateRing, uploads checkpoints and event log
segments to S3 after each checkpoint.

Both run as daemon threads — they never block the substrate.
"""

import contextlib
import hashlib
import hmac
import json
import os
import stat
import time
import threading
import glob as glob_mod
import logging

from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)
from dsf_ai_service.substrate.ring_buffer import (
    UINT64_MAX,
    canonical_substrate_event_bytes,
)

logger = logging.getLogger("guala.persistence")

# --- Constants ---
FSYNC_BATCH = 100
FSYNC_INTERVAL_S = 0.1
CHECKPOINT_INTERVAL = 50_000
POLL_INTERVAL_S = 0.01
LOCAL_CHECKPOINT_RETENTION = 2
RING_OBSERVATION_RECEIPT_SCHEMA = "guala.ring_observation_receipt.v1"
RING_CHECKPOINT_SCHEMA = "guala.ring_persistence_checkpoint.v1"
RING_CHECKPOINT_STATE_SCHEMA = "guala.ring_checkpoint_state.v1"
RING_RECEIPT_SEGMENT_MAX_BYTES = 1024 * 1024


class PersistenceRecoveryError(RuntimeError):
    """Durable checkpoint/event state cannot be replayed exactly."""


class PersistenceCapacityError(RuntimeError):
    """A ring event or checkpoint exceeds its declared exact profile."""


def _hmac_key(value):
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError("ring receipt HMAC key must be bytes")
    key = bytes(value)
    if len(key) < 32:
        raise ValueError("ring receipt HMAC key must contain at least 32 bytes")
    return key


def _canonical(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def ring_observation_receipt(event, *, hmac_key):
    """Authenticate one event without duplicating its detail payload."""
    event_bytes = canonical_substrate_event_bytes(event)
    unsigned = {
        "event_sha256": hashlib.sha256(event_bytes).hexdigest(),
        "schema": RING_OBSERVATION_RECEIPT_SCHEMA,
        "seq": event["seq"],
        "tick": event["tick"],
    }
    signature = hmac.new(
        _hmac_key(hmac_key),
        _canonical(unsigned),
        hashlib.sha256,
    ).hexdigest()
    return {
        **unsigned,
        "receipt_hmac_sha256": signature,
    }


def ring_observation_receipt_max_bytes():
    event = {
        "data": {},
        "kind": "x",
        "seq": UINT64_MAX,
        "tick": UINT64_MAX,
    }
    receipt = ring_observation_receipt(event, hmac_key=b"x" * 32)
    return len(_canonical(receipt)) + 1


def _validated_ring_observation_receipt(value, *, hmac_key):
    if not isinstance(value, dict) or set(value) != {
            "event_sha256", "receipt_hmac_sha256", "schema", "seq", "tick"}:
        raise PersistenceCapacityError(
            "existing ring receipt has an invalid field set")
    if value.get("schema") != RING_OBSERVATION_RECEIPT_SCHEMA:
        raise PersistenceCapacityError(
            "existing ring receipt schema is unsupported")
    for name in ("event_sha256", "receipt_hmac_sha256"):
        encoded = value.get(name)
        if (
            not isinstance(encoded, str)
            or len(encoded) != 64
            or any(character not in "0123456789abcdef"
                   for character in encoded)
        ):
            raise PersistenceCapacityError(
                f"existing ring receipt {name} is invalid")
    for name in ("seq", "tick"):
        number = value.get(name)
        if (
            isinstance(number, bool)
            or not isinstance(number, int)
            or not 0 <= number <= UINT64_MAX
        ):
            raise PersistenceCapacityError(
                f"existing ring receipt {name} is invalid")
    unsigned = {
        name: value[name]
        for name in ("event_sha256", "schema", "seq", "tick")
    }
    expected = hmac.new(
        _hmac_key(hmac_key),
        _canonical(unsigned),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(value["receipt_hmac_sha256"], expected):
        raise PersistenceCapacityError(
            "existing ring receipt HMAC is invalid")
    return value


def ring_checkpoint_state(engine_tick):
    """Return the complete bounded state owned by ring persistence.

    Learned state belongs to the immutable cold generation.  This checkpoint
    receipts only the ring cursor's engine-tick position; it does not pretend
    that an observability projection is a restorable learned-state snapshot.
    """
    if (
        isinstance(engine_tick, bool)
        or not isinstance(engine_tick, int)
        or not 0 <= engine_tick <= UINT64_MAX
    ):
        raise PersistenceCapacityError(
            "ring checkpoint engine tick must be a uint64 integer")
    return {
        "schema": RING_CHECKPOINT_STATE_SCHEMA,
        "engine_tick": engine_tick,
    }


def _validated_ring_checkpoint_state(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"engine_tick", "schema"}
        or value.get("schema") != RING_CHECKPOINT_STATE_SCHEMA
    ):
        raise PersistenceCapacityError(
            "ring checkpoint state differs from its finite schema")
    return ring_checkpoint_state(value["engine_tick"])


def _ring_checkpoint(unsigned, *, hmac_key):
    signature = hmac.new(
        _hmac_key(hmac_key),
        _canonical(unsigned),
        hashlib.sha256,
    ).hexdigest()
    return {
        **unsigned,
        "receipt_hmac_sha256": signature,
    }


def ring_checkpoint_max_bytes():
    """Exact maximum canonical bytes for one ring checkpoint."""
    return len(_canonical(_ring_checkpoint(
        {
            "schema": RING_CHECKPOINT_SCHEMA,
            "seq": UINT64_MAX,
            "state": ring_checkpoint_state(UINT64_MAX),
            "time_ns": UINT64_MAX,
        },
        hmac_key=b"x" * 32,
    )))


def _checkpoint_sequence(path):
    base = os.path.basename(path)
    prefix = "checkpoint-"
    suffix = ".json"
    if not base.startswith(prefix) or not base.endswith(suffix):
        return -1
    encoded = base[len(prefix):-len(suffix)]
    if (
        not encoded
        or not encoded.isascii()
        or not encoded.isdigit()
        or str(int(encoded)) != encoded
    ):
        return -1
    return int(encoded)


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_all(descriptor, data):
    view = memoryview(data)
    written = 0
    while written < len(view):
        count = os.write(descriptor, view[written:])
        if count <= 0:
            raise OSError("ring persistence write made no progress")
        written += count


class PersistenceConsumer:
    """Subscribes to a SubstrateRing and persists events to disk.

    - Append-only events.log (one JSON line per event)
    - fsync every FSYNC_BATCH events or FSYNC_INTERVAL_S, whichever first
    - Checkpoint snapshot every CHECKPOINT_INTERVAL events
    """

    def __init__(
            self, ring, state_dir, build_snapshot_fn, *,
            physical_byte_authority=None,
            max_event_record_bytes=None,
            max_checkpoint_bytes=None,
            max_event_segment_bytes=None,
            receipt_hmac_key=None):
        """
        Args:
            ring: SubstrateRing to subscribe to.
            state_dir: Directory for events.log and checkpoint files.
            build_snapshot_fn: Callable that returns a dict representing
                               the full substrate state for checkpointing.
        """
        self._ring = ring
        self._state_dir = state_dir
        self._build_snapshot_fn = build_snapshot_fn
        self._cursor = ring.subscribe()
        self._events_since_checkpoint = 0
        self._last_fsync_time = time.monotonic()
        self._unfsynced = 0
        self._stop = threading.Event()
        self._thread = None
        self._log_path = os.path.join(state_dir, "events.log")
        self._log_fd = None
        self._failure = None
        self._last_persisted_seq = None
        if physical_byte_authority is not None and not isinstance(
                physical_byte_authority, PhysicalByteCeilingAuthority):
            raise TypeError(
                "physical_byte_authority must be a "
                "PhysicalByteCeilingAuthority")
        self._physical_byte_authority = physical_byte_authority
        for value, description in (
                (max_event_record_bytes, "ring event record capacity"),
                (max_checkpoint_bytes, "ring checkpoint capacity"),
                (max_event_segment_bytes, "ring event segment capacity")):
            if value is not None and (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0):
                raise ValueError(f"{description} must be a positive integer")
        if physical_byte_authority is not None and (
                max_event_record_bytes is None
                or max_checkpoint_bytes is None
                or max_event_segment_bytes is None
                or receipt_hmac_key is None):
            raise ValueError(
                "bounded ring persistence requires receipt, segment, "
                "checkpoint, and HMAC-key capacities")
        self._max_event_record_bytes = max_event_record_bytes
        self._max_checkpoint_bytes = max_checkpoint_bytes
        self._max_event_segment_bytes = max_event_segment_bytes
        self._receipt_hmac_key = (
            None if receipt_hmac_key is None else _hmac_key(receipt_hmac_key))
        os.makedirs(state_dir, exist_ok=True)

    def _validate_existing_resource_profile(self):
        """Refuse an oversized legacy body without mutating or deleting it."""
        if (
            self._max_event_record_bytes is None
            or self._max_checkpoint_bytes is None
            or self._max_event_segment_bytes is None
        ):
            return
        try:
            log_info = os.lstat(self._log_path)
        except FileNotFoundError:
            pass
        else:
            if (
                not stat.S_ISREG(log_info.st_mode)
                or log_info.st_nlink != 1
            ):
                raise PersistenceCapacityError(
                    "existing ring event log is not a private regular file")
            if log_info.st_size > self._max_event_segment_bytes:
                raise PersistenceCapacityError(
                    "existing ring event segment exceeds the production "
                    "resource profile")
            with open(self._log_path, "rb") as existing:
                records = existing.readlines()
            if records and not records[-1].endswith(b"\n"):
                raise PersistenceCapacityError(
                    "existing ring event segment ends with a torn record")
            if any(
                    len(record) > self._max_event_record_bytes
                    for record in records):
                raise PersistenceCapacityError(
                    "existing ring event record exceeds its byte capacity")
            expected_seq = None
            for record in records:
                try:
                    value = json.loads(record)
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise PersistenceCapacityError(
                        "existing ring receipt is not strict JSON") from error
                _validated_ring_observation_receipt(
                    value,
                    hmac_key=self._receipt_hmac_key,
                )
                if record != _canonical(value) + b"\n":
                    raise PersistenceCapacityError(
                        "existing ring receipt is not canonical")
                if expected_seq is not None and value["seq"] != expected_seq:
                    raise PersistenceCapacityError(
                        "existing ring receipt sequence is not contiguous")
                expected_seq = value["seq"] + 1
            if records:
                self._last_persisted_seq = value["seq"]
        checkpoints = [
            path
            for path in glob_mod.glob(
                os.path.join(self._state_dir, "checkpoint-*.json"))
            if _checkpoint_sequence(path) >= 0
        ]
        if len(checkpoints) > LOCAL_CHECKPOINT_RETENTION:
            raise PersistenceCapacityError(
                "existing ring checkpoints exceed retained-copy capacity")
        for path in checkpoints:
            info = os.lstat(path)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_size > self._max_checkpoint_bytes
            ):
                raise PersistenceCapacityError(
                    "existing ring checkpoint exceeds its finite profile")

    def start(self):
        """Start the persistence thread."""
        if self._thread is not None:
            raise RuntimeError(
                "persistence consumer cannot be started more than once")
        self._validate_existing_resource_profile()
        descriptor = os.open(
            self._log_path,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
            0o600,
        )
        descriptor_info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(descriptor_info.st_mode)
            or descriptor_info.st_nlink != 1
        ):
            os.close(descriptor)
            raise ValueError(
                "persistence event log must be a private regular file")
        self._log_fd = os.fdopen(descriptor, "ab", buffering=0)
        self._failure = None
        self._thread = threading.Thread(
            target=self._run, name="persistence-consumer", daemon=True
        )
        self._thread.start()

    def stop(self, timeout=120.0):
        """Signal, join, fsync, and fail loudly if the writer remains live."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=float(timeout))
            if self._thread.is_alive():
                raise RuntimeError("persistence consumer did not stop")
        if self._log_fd is not None:
            self._flush_fsync()
            self._log_fd.close()
            self._log_fd = None
        if self._failure is not None:
            raise RuntimeError("persistence consumer failed") from self._failure

    def _run(self):
        try:
            while not self._stop.is_set():
                events = self._cursor.read_available()
                if events:
                    self._write_events(events)
                else:
                    # No events — but check if we need a time-based fsync
                    now = time.monotonic()
                    if (
                        self._unfsynced > 0
                        and now - self._last_fsync_time >= FSYNC_INTERVAL_S
                    ):
                        self._flush_fsync()
                    self._stop.wait(timeout=POLL_INTERVAL_S)
        except Exception as exc:
            self._failure = exc
            logger.exception(
                "Persistence consumer stopped after durable-write failure")
            self._stop.set()

    def _write_events(self, events):
        for event in events:
            receipt = ring_observation_receipt(
                event,
                hmac_key=self._receipt_hmac_key,
            )
            line = _canonical(receipt) + b"\n"
            if (
                self._max_event_record_bytes is not None
                and len(line) > self._max_event_record_bytes
            ):
                raise PersistenceCapacityError(
                    "ring event record exceeds its configured byte capacity")
            if (
                self._max_event_segment_bytes is not None
                and len(line) > self._max_event_segment_bytes
            ):
                raise PersistenceCapacityError(
                    "one ring receipt exceeds the complete segment capacity")
            if (
                self._max_event_segment_bytes is not None
                and self._last_persisted_seq is not None
                and os.fstat(self._log_fd.fileno()).st_size + len(line)
                > self._max_event_segment_bytes
            ):
                self._write_checkpoint(self._last_persisted_seq)
                self._events_since_checkpoint = 0
            authority = self._physical_byte_authority
            if authority is None:
                _write_all(self._log_fd.fileno(), line)
            else:
                with authority.admitted_mutation(
                        operation="append_ring_persistence_event",
                        requested_bytes=len(line)):
                    prior_size = os.fstat(self._log_fd.fileno()).st_size
                    try:
                        _write_all(self._log_fd.fileno(), line)
                    except BaseException:
                        os.ftruncate(self._log_fd.fileno(), prior_size)
                        os.fsync(self._log_fd.fileno())
                        raise
            self._unfsynced += 1
            self._events_since_checkpoint += 1
            self._last_persisted_seq = event["seq"]

            # Batch fsync
            now = time.monotonic()
            if self._unfsynced >= FSYNC_BATCH or now - self._last_fsync_time >= FSYNC_INTERVAL_S:
                self._flush_fsync()

            # Checkpoint
            if (
                self._max_event_segment_bytes is None
                and self._events_since_checkpoint >= CHECKPOINT_INTERVAL
            ):
                self._write_checkpoint(event["seq"])
                self._events_since_checkpoint = 0

    def _flush_fsync(self):
        if self._log_fd is not None and self._unfsynced > 0:
            self._log_fd.flush()
            os.fsync(self._log_fd.fileno())
            self._unfsynced = 0
            self._last_fsync_time = time.monotonic()

    def _write_checkpoint(self, seq):
        """Write an atomic checkpoint snapshot."""
        self._flush_fsync()
        if (
            isinstance(seq, bool)
            or not isinstance(seq, int)
            or not 0 <= seq <= UINT64_MAX
        ):
            raise PersistenceCapacityError(
                "ring checkpoint sequence must be a uint64 integer")
        snapshot = _validated_ring_checkpoint_state(
            self._build_snapshot_fn())
        time_ns = time.time_ns()
        if not 0 <= time_ns <= UINT64_MAX:
            raise PersistenceCapacityError(
                "ring checkpoint time exceeds its uint64 profile")
        unsigned = {
            "schema": RING_CHECKPOINT_SCHEMA,
            "seq": seq,
            "state": snapshot,
            "time_ns": time_ns,
        }
        checkpoint = _ring_checkpoint(
            unsigned,
            hmac_key=self._receipt_hmac_key,
        )
        path = os.path.join(self._state_dir, f"checkpoint-{seq}.json")
        encoded = json.dumps(
            checkpoint,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if (
            self._max_checkpoint_bytes is not None
            and len(encoded) > self._max_checkpoint_bytes
        ):
            raise PersistenceCapacityError(
                "ring checkpoint exceeds its configured byte capacity")
        authority = self._physical_byte_authority
        if authority is None:
            tmp = path + ".tmp"
            try:
                with open(tmp, "wb") as f:
                    f.write(encoded)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, path)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
            _fsync_directory(self._state_dir)
        else:
            authority.atomic_replace_bytes(
                path,
                encoded,
                operation="publish_ring_persistence_checkpoint",
            )
        logger.info("Checkpoint written: %s", path)
        self._prune_local_checkpoints()

        # 2026-07-09 fix: truncate events.log now that this checkpoint's
        # snapshot fully captures everything written to it so far --
        # recover() (below) only ever reads events with seq > the LATEST
        # checkpoint's own seq, so every event already folded into this
        # checkpoint is now pure dead weight, growing the local file
        # forever within a single process's lifetime. Found live: this
        # ever-growing file was being re-uploaded IN FULL by S3Consumer
        # on every subsequent checkpoint (confirmed via a real /debug/
        # thread_dump of the running process -- continuous, ever-larger
        # multipart uploads, not a stall, real sustained CPU spend on
        # SSL + checksums). Safe here specifically: _write_checkpoint
        # only ever runs from _write_events, on this consumer's own
        # single writer thread -- no other thread ever touches
        # self._log_fd, so there's no concurrent-write race to guard
        # against (unlike S3Consumer's separate delete step, which
        # deliberately never touches this file for exactly that reason).
        truncation = (
            contextlib.nullcontext()
            if self._physical_byte_authority is None
            else self._physical_byte_authority.admitted_mutation(
                operation="truncate_checkpointed_ring_events",
                requested_bytes=0,
            )
        )
        with truncation:
            os.ftruncate(self._log_fd.fileno(), 0)
            os.fsync(self._log_fd.fileno())

    def _prune_local_checkpoints(self):
        checkpoints = sorted(
            (
                (_checkpoint_sequence(path), path)
                for path in glob_mod.glob(
                    os.path.join(self._state_dir, "checkpoint-*.json")
                )
                if _checkpoint_sequence(path) >= 0
            ),
            reverse=True,
        )
        stale = checkpoints[LOCAL_CHECKPOINT_RETENTION:]
        mutation = (
            contextlib.nullcontext()
            if self._physical_byte_authority is None
            else self._physical_byte_authority.admitted_mutation(
                operation="prune_ring_persistence_checkpoints",
                requested_bytes=0,
            )
        )
        with mutation:
            for _sequence, path in stale:
                os.remove(path)
            if stale:
                _fsync_directory(self._state_dir)

    @staticmethod
    def recover(state_dir):
        """Find latest checkpoint and replay events after it.

        Returns:
            (checkpoint_data, events_since) where:
            - checkpoint_data: dict from the checkpoint file, or None if no checkpoint
            - events_since: list of event dicts from events.log with seq > checkpoint seq
        """
        # Find latest checkpoint by sequence number
        pattern = os.path.join(state_dir, "checkpoint-*.json")
        checkpoint_files = glob_mod.glob(pattern)
        checkpoint_data = None
        checkpoint_seq = -1

        if checkpoint_files:
            # Parse exact writer-produced sequence names and verify candidates
            # newest-first.  A torn newest checkpoint must not conceal an
            # older complete recovery point.
            candidates = sorted(
                (
                    (sequence, path)
                    for path in checkpoint_files
                    if (sequence := _checkpoint_sequence(path)) >= 0
                ),
                reverse=True,
            )
            for filename_seq, candidate in candidates:
                try:
                    with open(candidate, "r") as f:
                        value = json.load(f)
                except (json.JSONDecodeError, OSError):
                    logger.warning(
                        "Failed to read checkpoint %s", candidate)
                    continue
                body_seq = (
                    value.get("seq")
                    if isinstance(value, dict)
                    else None
                )
                if (
                    isinstance(body_seq, bool)
                    or not isinstance(body_seq, int)
                    or body_seq != filename_seq
                ):
                    logger.warning(
                        "Checkpoint sequence mismatch in %s", candidate)
                    continue
                checkpoint_data = value
                checkpoint_seq = body_seq
                break

        # Read events after checkpoint sequence
        events_since = []
        expected_replay_seq = checkpoint_seq + 1
        log_path = os.path.join(state_dir, "events.log")
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
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
                        raise PersistenceRecoveryError(
                            "events.log contains a malformed complete record"
                        ) from error
                    event_seq = (
                        event.get("seq")
                        if isinstance(event, dict)
                        else None
                    )
                    if (
                        isinstance(event_seq, bool)
                        or not isinstance(event_seq, int)
                        or event_seq < 0
                    ):
                        raise PersistenceRecoveryError(
                            "events.log contains invalid sequence metadata")
                    if event_seq > checkpoint_seq:
                        if event_seq != expected_replay_seq:
                            raise PersistenceRecoveryError(
                                "events.log replay sequence is not contiguous")
                        events_since.append(event)
                        expected_replay_seq = event_seq + 1

        return checkpoint_data, events_since


class S3Consumer:
    """Subscribes to SubstrateRing and uploads checkpoints + event segments to S3.

    Watches for checkpoint files to appear, then uploads them along with
    the event log segment since the previous checkpoint. Never blocks substrate.
    """

    def __init__(
            self, ring, state_dir, bucket=None, s3_client=None,
            version_aware_retirement=False):
        """
        Args:
            ring: SubstrateRing to subscribe to (used to track position).
            state_dir: Directory where PersistenceConsumer writes files.
            bucket: S3 bucket name. Defaults to GUALA_S3_BACKUP_BUCKET env var
                    or "dsf-ai-site-backups".
            s3_client: Optional already-constructed S3-compatible client.  This
                       is the production test seam; when supplied, start() does
                       not construct a second client.
        """
        self._ring = ring
        self._state_dir = state_dir
        self._bucket = bucket or os.environ.get(
            "GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups"
        )
        self._last_uploaded_seq = -1
        self._stop = threading.Event()
        self._thread = None
        self._s3 = s3_client
        self._failure = None
        if not isinstance(version_aware_retirement, bool):
            raise TypeError(
                "version-aware S3 retirement flag must be boolean"
            )
        self._version_aware_retirement = version_aware_retirement

    def start(self):
        """Start the S3 upload thread."""
        if self._s3 is None:
            try:
                import boto3
                self._s3 = boto3.client("s3")
            except Exception:
                logger.exception("S3 client construction failed")
                raise
        self._failure = None
        self._thread = threading.Thread(
            target=self._run, name="s3-consumer", daemon=True
        )
        self._thread.start()

    def stop(self, timeout=120.0):
        """Signal and join, failing if an S3 upload remains live."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=float(timeout))
            if self._thread.is_alive():
                raise RuntimeError("S3 consumer did not stop")
        if self._failure is not None:
            raise RuntimeError("S3 consumer failed") from self._failure

    def _run(self):
        while not self._stop.is_set():
            try:
                self._check_and_upload()
            except Exception as exc:
                self._failure = exc
                logger.exception("S3 consumer stopped after persistence failure")
                self._stop.set()
                return
            self._stop.wait(timeout=5.0)

    def _check_and_upload(self):
        """Look for new checkpoint files and upload them.

        Remote storage retains one complete replacement recovery point.
        Local storage separately retains the newest checkpoint plus one
        predecessor so a torn newest file has an exact fallback.  The prior
        remote objects are deleted only after the replacement uploads return
        successfully.  This consumer never mutates the local events.log
        because PersistenceConsumer owns its open append handle."""
        pattern = os.path.join(self._state_dir, "checkpoint-*.json")
        checkpoint_files = glob_mod.glob(pattern)
        if not checkpoint_files:
            return

        # Process only the latest local checkpoint.  On restart the retained
        # local predecessor supplies the prior remote sequence to retire after
        # the replacement is uploaded; it is not itself re-uploaded.
        checkpoint_files_by_seq = sorted(
            ((_checkpoint_sequence(p), p) for p in checkpoint_files),
            key=lambda t: t[0],
        )
        checkpoint_files_by_seq = [(s, p) for s, p in checkpoint_files_by_seq if s >= 0]
        if not checkpoint_files_by_seq:
            return
        seq, cp_path = checkpoint_files_by_seq[-1]
        base = os.path.basename(cp_path)

        if seq <= self._last_uploaded_seq:
            return
        prev_seq = self._last_uploaded_seq
        if prev_seq < 0 and len(checkpoint_files_by_seq) > 1:
            prev_seq = checkpoint_files_by_seq[-2][0]
        # A recovery point consists of its checkpoint and, when present, the
        # event-log segment captured with it.  Upload both before advancing the
        # local cursor or deleting any prior recovery point.  upload_file is
        # synchronous: return means the S3 client accepted the complete object;
        # any failure propagates and leaves all prior state intact.
        self._upload_file(cp_path, f"guala/checkpoints/{base}")
        events_path = os.path.join(self._state_dir, "events.log")
        if os.path.exists(events_path):
            self._upload_file(
                events_path, f"guala/events/events-upto-{seq}.log"
            )

        # The replacement now exists in full.  Superseded remote and local
        # recovery points may be retired.  Deletion failures propagate; they
        # are persistence failures, even though retaining an older recovery
        # point is safe.
        if prev_seq >= 0:
            self._delete_object(f"guala/checkpoints/checkpoint-{prev_seq}.json")
            self._delete_object(f"guala/events/events-upto-{prev_seq}.log")
        for stale_seq, stale_path in checkpoint_files_by_seq[
                :-LOCAL_CHECKPOINT_RETENTION]:
            os.remove(stale_path)

        self._last_uploaded_seq = seq
        logger.info("S3 replacement complete for checkpoint seq=%d", seq)

    def _delete_object(self, s3_key):
        """Delete one superseded object and propagate an unproven result."""
        if self._version_aware_retirement:
            self._delete_all_object_versions(s3_key)
            return
        self._s3.delete_object(Bucket=self._bucket, Key=s3_key)

    def _object_versions(self, s3_key):
        list_versions = getattr(self._s3, "list_object_versions", None)
        if not callable(list_versions):
            raise RuntimeError(
                "production S3 recovery retirement has no version listing"
            )
        key_marker = None
        version_marker = None
        records = []
        while True:
            options = {
                "Bucket": self._bucket,
                "Prefix": s3_key,
            }
            if key_marker is not None:
                options["KeyMarker"] = key_marker
            if version_marker is not None:
                options["VersionIdMarker"] = version_marker
            response = list_versions(**options)
            if not isinstance(response, dict):
                raise RuntimeError(
                    "S3 version listing returned no object response"
                )
            for field in ("Versions", "DeleteMarkers"):
                values = response.get(field) or []
                if not isinstance(values, list):
                    raise RuntimeError(
                        "S3 version listing has an invalid record list"
                    )
                for value in values:
                    if (
                        not isinstance(value, dict)
                        or value.get("Key") != s3_key
                        or not isinstance(
                            value.get("VersionId"),
                            str,
                        )
                        or not value["VersionId"]
                    ):
                        raise RuntimeError(
                            "S3 version listing has an invalid exact-key "
                            "record"
                        )
                    records.append({
                        "Key": s3_key,
                        "VersionId": value["VersionId"],
                    })
            if response.get("IsTruncated") is not True:
                return tuple(records)
            key_marker = response.get("NextKeyMarker")
            version_marker = response.get("NextVersionIdMarker")
            if (
                not isinstance(key_marker, str)
                or not key_marker
                or not isinstance(version_marker, str)
                or not version_marker
            ):
                raise RuntimeError(
                    "truncated S3 version listing has no continuation"
                )

    def _delete_all_object_versions(self, s3_key):
        delete_objects = getattr(self._s3, "delete_objects", None)
        if not callable(delete_objects):
            raise RuntimeError(
                "production S3 recovery retirement has no version deletion"
            )
        records = self._object_versions(s3_key)
        for offset in range(0, len(records), 1_000):
            response = delete_objects(
                Bucket=self._bucket,
                Delete={
                    "Objects": list(records[offset:offset + 1_000]),
                    "Quiet": True,
                },
            )
            if not isinstance(response, dict) or response.get("Errors"):
                raise RuntimeError(
                    "S3 version deletion returned an unproven result"
                )
        if self._object_versions(s3_key):
            raise RuntimeError(
                "superseded S3 recovery object retains versions or markers"
            )

    def _upload_file(self, local_path, s3_key):
        """Upload one complete object and propagate an unproven result."""
        self._s3.upload_file(local_path, self._bucket, s3_key)
