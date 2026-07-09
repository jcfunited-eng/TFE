"""
Ring buffer consumers for persistence and S3 backup.

PersistenceConsumer: subscribes to SubstrateRing, writes append-only event log,
triggers checkpoint snapshots every 50,000 events.

S3Consumer: subscribes to SubstrateRing, uploads checkpoints and event log
segments to S3 after each checkpoint.

Both run as daemon threads — they never block the substrate.
"""

import json
import os
import time
import threading
import glob as glob_mod
import logging

logger = logging.getLogger("guala.persistence")

# --- Constants ---
FSYNC_BATCH = 100
FSYNC_INTERVAL_S = 0.1
CHECKPOINT_INTERVAL = 50_000
POLL_INTERVAL_S = 0.01


class PersistenceConsumer:
    """Subscribes to a SubstrateRing and persists events to disk.

    - Append-only events.log (one JSON line per event)
    - fsync every FSYNC_BATCH events or FSYNC_INTERVAL_S, whichever first
    - Checkpoint snapshot every CHECKPOINT_INTERVAL events
    """

    def __init__(self, ring, state_dir, build_snapshot_fn):
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
        os.makedirs(state_dir, exist_ok=True)

    def start(self):
        """Start the persistence thread."""
        self._log_fd = open(self._log_path, "a")
        self._thread = threading.Thread(
            target=self._run, name="persistence-consumer", daemon=True
        )
        self._thread.start()

    def stop(self):
        """Signal the thread to stop and wait for it."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        if self._log_fd is not None:
            self._flush_fsync()
            self._log_fd.close()
            self._log_fd = None

    def _run(self):
        while not self._stop.is_set():
            events = self._cursor.read_available()
            if events:
                self._write_events(events)
            else:
                # No events — but check if we need a time-based fsync
                now = time.monotonic()
                if self._unfsynced > 0 and now - self._last_fsync_time >= FSYNC_INTERVAL_S:
                    self._flush_fsync()
                self._stop.wait(timeout=POLL_INTERVAL_S)

    def _write_events(self, events):
        for event in events:
            line = json.dumps(event, default=str) + "\n"
            self._log_fd.write(line)
            self._unfsynced += 1
            self._events_since_checkpoint += 1

            # Batch fsync
            now = time.monotonic()
            if self._unfsynced >= FSYNC_BATCH or now - self._last_fsync_time >= FSYNC_INTERVAL_S:
                self._flush_fsync()

            # Checkpoint
            if self._events_since_checkpoint >= CHECKPOINT_INTERVAL:
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
        try:
            snapshot = self._build_snapshot_fn()
        except Exception:
            logger.exception("build_snapshot_fn failed at seq %d", seq)
            return
        checkpoint = {"seq": seq, "ts": time.time(), "state": snapshot}
        path = os.path.join(self._state_dir, f"checkpoint-{seq}.json")
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(checkpoint, f, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, path)
        logger.info("Checkpoint written: %s", path)

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
        try:
            os.ftruncate(self._log_fd.fileno(), 0)
        except Exception:
            logger.exception("events.log truncate failed at seq %d (non-fatal)", seq)

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
            # Parse sequence numbers from filenames, pick highest
            def _extract_seq(path):
                base = os.path.basename(path)
                # checkpoint-12345.json -> 12345
                try:
                    return int(base.replace("checkpoint-", "").replace(".json", ""))
                except ValueError:
                    return -1

            checkpoint_files.sort(key=_extract_seq)
            latest = checkpoint_files[-1]
            try:
                with open(latest, "r") as f:
                    checkpoint_data = json.load(f)
                checkpoint_seq = checkpoint_data.get("seq", -1)
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to read checkpoint %s", latest)
                checkpoint_data = None

        # Read events after checkpoint sequence
        events_since = []
        log_path = os.path.join(state_dir, "events.log")
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("seq", -1) > checkpoint_seq:
                        events_since.append(event)

        return checkpoint_data, events_since


class S3Consumer:
    """Subscribes to SubstrateRing and uploads checkpoints + event segments to S3.

    Watches for checkpoint files to appear, then uploads them along with
    the event log segment since the previous checkpoint. Never blocks substrate.
    """

    def __init__(self, ring, state_dir, bucket=None):
        """
        Args:
            ring: SubstrateRing to subscribe to (used to track position).
            state_dir: Directory where PersistenceConsumer writes files.
            bucket: S3 bucket name. Defaults to GUALA_S3_BACKUP_BUCKET env var
                    or "dsf-ai-site-backups".
        """
        self._ring = ring
        self._state_dir = state_dir
        self._bucket = bucket or os.environ.get(
            "GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups"
        )
        self._last_uploaded_seq = -1
        self._stop = threading.Event()
        self._thread = None
        self._s3 = None

    def start(self):
        """Start the S3 upload thread."""
        try:
            import boto3
            self._s3 = boto3.client("s3")
        except Exception:
            logger.warning("boto3 not available — S3Consumer disabled")
            return
        self._thread = threading.Thread(
            target=self._run, name="s3-consumer", daemon=True
        )
        self._thread.start()

    def stop(self):
        """Signal the thread to stop and wait."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10.0)

    def _run(self):
        while not self._stop.is_set():
            self._check_and_upload()
            self._stop.wait(timeout=5.0)

    def _check_and_upload(self):
        """Look for new checkpoint files and upload them.

        2026-07-08 bloat fix: recover() only ever reads the single
        highest-seq checkpoint plus whatever's in the current events.log
        (its own filter is `seq > checkpoint_seq` against the LATEST
        checkpoint only) -- every older checkpoint/events-log object this
        method ever uploaded to S3 has been permanently dead weight since
        the moment a newer one was written, not a real recovery point.
        Confirmed live: guala/events/ alone reached ~50GB, uploading the
        entire ever-growing local events.log under a brand-new key every
        checkpoint, never deleting the previous one. Deleting the
        previous seq's two objects right after a successful upload of
        the new ones keeps S3 storage for these two prefixes bounded to
        "the one current recovery point," matching what recover() will
        ever actually read, instead of every recovery point that has
        ever existed. Deliberately NOT touching the local events.log
        write/truncate path (PersistenceConsumer, a different thread) --
        that would risk a real race against its still-open append-mode
        file handle; deleting old S3 objects from this single thread,
        after their own upload already succeeded, has no such race."""
        pattern = os.path.join(self._state_dir, "checkpoint-*.json")
        checkpoint_files = glob_mod.glob(pattern)
        if not checkpoint_files:
            return

        def _extract_seq(path):
            base = os.path.basename(path)
            try:
                return int(base.replace("checkpoint-", "").replace(".json", ""))
            except ValueError:
                return -1

        # 2026-07-09 fix: process only the SINGLE latest (highest-seq)
        # local checkpoint file, not every one with seq > _last_uploaded_
        # seq. _last_uploaded_seq is in-memory-only state on this
        # consumer instance -- it resets to -1 on every process restart,
        # but local checkpoint-*.json files are never cleaned up and
        # live forever on EFS (persistent storage, survives restarts).
        # Found live: on every deploy/restart tonight, this loop was
        # re-uploading EVERY checkpoint file that has EVER existed on
        # EFS, from -1, in full, over and over -- confirmed via a real
        # /debug/thread_dump of the running process showing continuous
        # s3transfer upload_part activity that never let up, even
        # moments after a fresh boot with an empty events.log. recover()
        # (this same file) only ever reads the single highest-seq
        # checkpoint anyway -- every older one has been pure dead weight,
        # locally AND in S3, since the moment a newer one was written,
        # not something a restart needs to catch up on.
        checkpoint_files_by_seq = sorted(
            ((_extract_seq(p), p) for p in checkpoint_files), key=lambda t: t[0]
        )
        checkpoint_files_by_seq = [(s, p) for s, p in checkpoint_files_by_seq if s >= 0]
        if not checkpoint_files_by_seq:
            return
        seq, cp_path = checkpoint_files_by_seq[-1]
        base = os.path.basename(cp_path)

        # Local cleanup: every OTHER local checkpoint file is dead weight
        # (recover() will never read it) -- remove it now rather than
        # let it accumulate forever, same reasoning as the S3-side delete
        # below, just applied locally too.
        for stale_seq, stale_path in checkpoint_files_by_seq[:-1]:
            try:
                os.remove(stale_path)
            except Exception:
                logger.exception("stale local checkpoint cleanup failed: %s", stale_path)

        if seq <= self._last_uploaded_seq:
            return
        prev_seq = self._last_uploaded_seq
        # Upload checkpoint
        self._upload_file(cp_path, f"guala/checkpoints/{base}")
        # Upload events.log snapshot
        events_path = os.path.join(self._state_dir, "events.log")
        if os.path.exists(events_path):
            self._upload_file(
                events_path, f"guala/events/events-upto-{seq}.log"
            )
        self._last_uploaded_seq = seq
        logger.info("S3 upload complete for checkpoint seq=%d", seq)
        if prev_seq >= 0:
            self._delete_object(f"guala/checkpoints/checkpoint-{prev_seq}.json")
            self._delete_object(f"guala/events/events-upto-{prev_seq}.log")

    def _delete_object(self, s3_key):
        """Best-effort delete of a superseded recovery-point object.
        Swallows errors -- never crashes the substrate, and a leftover
        old object is no worse than today's status quo."""
        try:
            self._s3.delete_object(Bucket=self._bucket, Key=s3_key)
        except Exception:
            logger.exception("S3 delete failed (non-fatal): s3://%s/%s",
                             self._bucket, s3_key)

    def _upload_file(self, local_path, s3_key):
        """Upload a single file to S3. Swallows errors — never crashes substrate."""
        try:
            self._s3.upload_file(local_path, self._bucket, s3_key)
        except Exception:
            logger.exception("S3 upload failed: %s -> s3://%s/%s",
                             local_path, self._bucket, s3_key)
