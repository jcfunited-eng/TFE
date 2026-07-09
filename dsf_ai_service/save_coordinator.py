"""
GL-CMD-C1-SAVE-NON-BLOCKING-EVE-20260617-07

Presence-detected save coordinator.
Saves trigger at natural quiet points (activity transitions, dream end,
presence departure), not on fixed timers.
S3 uploads run on a dedicated background thread — never block substrate.
"""
import threading
import queue
import time
import json
import logging
import os

log = logging.getLogger(__name__)

SAVE_COORDINATOR = None  # set by substrate_runner on init

S3_MIN_INTERVAL_SECONDS = 86400   # 2026-07-09: Joe's explicit call -- one
# automatic S3 backup per day, not one every 10 minutes. The 10-minute
# value already fixed a real live incident (dream_end queuing unlimited
# uploads with no rate limit at all -- see this file's other 2026-07-09
# comment), but at ~150-190MB per backup and dozens of automatic quiet
# points per day (activity_ended, backstop, presence_quiet, dream_end),
# 10 minutes still produced ~30GB/day of near-duplicate snapshots this
# same session found and deleted. Local EFS state (guala.save_hot_state,
# unaffected by this constant) is the substrate's real, continuously-
# current save -- this constant only governs how often that state ALSO
# gets mirrored to S3 as an off-box safety copy, so widening it to a day
# does not reduce how current her real save actually is, only how often
# a redundant duplicate of it leaves the box.


class SaveCoordinator:
    def __init__(self, guala, state_dir, s3_bucket=None):
        self.guala = guala
        self.state_dir = state_dir
        self.s3_bucket = s3_bucket
        # GL-CMD-SLOT-LIMITS-REMOVAL-EVE-20260707-v1: maxsize=20 KEPT,
        # not removed -- initially reasoned this was low-risk since
        # callers are expected to rate-limit themselves to one enqueue
        # per S3_MIN_INTERVAL_SECONDS (10 min), but a direct stress test
        # disproved that: the rate limit is enforced by caller
        # convention, not by the queue itself, and an unbounded producer
        # grows this queue exactly as unboundedly as the other three
        # (~3M items, ~1.2GB RSS in 8 seconds with the cap removed and
        # no consumer draining). Same confirmed runaway pattern; see the
        # accompanying report.
        self.s3_queue = queue.Queue(maxsize=20)
        self.last_save_tick = 0
        self.last_save_wall = 0.0
        self.last_save_timestamp = None  # ISO wall-clock string, set on each save
        self._last_s3_enqueue_wall = 0.0
        self._lock = threading.Lock()
        self._last_s3_result = None  # GL-CMD-97: set by _s3_loop after upload

        if s3_bucket:
            t = threading.Thread(target=self._s3_loop, daemon=True,
                                 name="s3-saver")
            t.start()

    def queue_s3(self, state_dir, tick, reason):
        """Queue an S3 backup of the files already written to state_dir."""
        try:
            self.s3_queue.put_nowait((state_dir, tick, reason))
        except queue.Full:
            log.warning("[s3] queue full — dropping backup tick=%d", tick)

    def maybe_save(self, reason="presence_quiet"):
        """Non-blocking save if conditions are right. Returns quickly.
        GL-CMD-DEEP-STORE-PHYSICS-86 P2: activity transitions → hot save.
        Cold stores (atlas/deep_atlas/sections) written by force_save or
        _periodic_v6_save cold lane (30-min bound)."""
        with self._lock:
            if not self._should_save(reason):
                return False
            self.last_save_tick = self.guala.tick
            self.last_save_wall = time.monotonic()
            self.last_save_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            self.guala.save_hot_state(self.state_dir)
            if self.s3_bucket:
                self._maybe_queue_s3(reason)
            return True
        except Exception as e:
            log.error("[save] failed: %s", e)
            return False

    def _maybe_queue_s3(self, reason):
        """Enqueue an S3 backup if reason warrants it.

        Three classes:
          - always-queue: shutdown, backup (no rate limit)
          - rate-limited: activity_ended, backstop, presence_quiet, dream_end
          - never: anything else

        2026-07-09: dream_end moved out of "always" -- confirmed live,
        found via a real thread-dump of the running process, not a
        report: every dream cycle ending queued a full ~24MB multipart
        S3 upload (guala_atlas.json ~7MB, guala_deep_atlas.json ~9MB,
        guala_organism.pkl.gz ~5MB, guala_sections.json ~2.8MB, plus
        the rest) unconditionally, no rate limit at all -- and dream
        cycles complete every few minutes under ordinary operation.
        With uploads queuing faster than s3transfer's own multipart
        threads could always finish each one, this produced sustained,
        continuous CPU spend on SSL + CRC32 checksums (confirmed via a
        live /debug/thread_dump: 10+ worker threads permanently busy in
        s3transfer's upload_part). Real memory each dream consolidates
        deserves a real backup, but not more than once per
        S3_MIN_INTERVAL_SECONDS regardless of how many dreams happen in
        that window -- same rate limit already governing every other
        frequent, non-manual save reason below."""
        always = ("shutdown", "backup")
        ratelimited = ("activity_ended", "backstop", "presence_quiet", "dream_end")
        if reason in always:
            self.queue_s3(self.state_dir, self.guala.tick, reason)
            self._last_s3_enqueue_wall = time.monotonic()
            return
        if reason in ratelimited:
            now = time.monotonic()
            if (now - self._last_s3_enqueue_wall) >= S3_MIN_INTERVAL_SECONDS:
                self.queue_s3(self.state_dir, self.guala.tick, reason)
                self._last_s3_enqueue_wall = now
            return
        # unknown reason — never queue

    def _should_save(self, reason):
        if reason in ("shutdown", "backup", "dream_end"):
            return True
        # Rate-limit activity_ended and backstop saves — with AUTONOMY_PHASED=1
        # activities end every 2-10s wall time. save_full_state holds self.lock
        # for ~4-6s (Phase 1 snapshot + EFS disk write). Unrestricted saves
        # hold the lock 45-100% of the time, blocking /converse. Cap at 60s.
        wall_delta = time.monotonic() - self.last_save_wall
        if reason in ("activity_ended", "backstop") and wall_delta < 60:
            return False
        # Defer if someone's actively interacting
        if self.guala.is_present_active():
            return False
        # Don't save too often
        tick_delta = self.guala.tick - self.last_save_tick
        if tick_delta < 200 or wall_delta < 30:
            return False
        return True

    def force_save(self, reason="shutdown"):
        """Save immediately regardless of conditions."""
        try:
            self.guala.save_full_state(self.state_dir)
            if self.s3_bucket:
                self.queue_s3(self.state_dir, self.guala.tick, reason)
        except Exception as e:
            log.error("[save] force failed: %s", e)

    def _s3_loop(self):
        """Dedicated S3 upload thread — never blocks substrate."""
        import boto3
        s3 = boto3.client("s3", region_name="us-east-1")
        prefix_base = os.environ.get("GUALA_S3_BACKUP_PREFIX", "guala/auto")
        while True:
            state_dir, tick, reason = self.s3_queue.get()
            try:
                ts_label = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())
                s3_prefix = f"{prefix_base}/{ts_label}_{reason}"
                all_files = [
                    "guala_identity.json", "guala_core.json",
                    "guala_needs.json", "guala_coordinator.json",
                    "guala_atlas.json", "guala_deep_atlas.json",
                    "guala_survival.json",  # GL-102: own cold file for survival history
                    "guala_sections.json", "guala_bucket.json",
                    "guala_visual.json", "guala_sounds.json",
                    "guala_videos.json", "guala_teaching.json",
                    "guala_organism.pkl.gz", "guala_tapestry.pkl.gz",  # GL-CMD-175 P1
                ]
                uploaded = 0
                for fname in all_files:
                    fpath = os.path.join(state_dir, fname)
                    if not os.path.exists(fpath):
                        continue
                    if fname.endswith(".json"):
                        # 2026-07-09: the .pkl.gz files below were already
                        # gzip-compressed before this loop ever sees them;
                        # the plain .json state files (atlas/deep_atlas/
                        # sections/survival/etc, several MB each) were not
                        # -- uploaded byte-for-byte. Compress in-flight,
                        # in memory, for the S3 mirror only -- the local
                        # EFS copy this loop reads from stays plain JSON,
                        # untouched, so the fast local save/restore path
                        # this constant doesn't govern is not affected at
                        # all by this change.
                        import gzip as _gzip
                        import io as _io
                        with open(fpath, "rb") as f:
                            raw = f.read()
                        buf = _io.BytesIO(_gzip.compress(raw))
                        s3.upload_fileobj(buf, self.s3_bucket,
                                          f"{s3_prefix}/{fname}.gz")
                    else:
                        s3.upload_file(fpath, self.s3_bucket,
                                       f"{s3_prefix}/{fname}")
                    uploaded += 1
                # GL-CMD-97: track last S3 result for handle_backup to report
                self._last_s3_result = {
                    "s3_prefix": f"{s3_prefix}/",
                    "files_uploaded": uploaded,
                    "timestamp": ts_label,
                }
                log.info("[s3] uploaded %d files → s3://%s/%s/ tick=%d",
                         uploaded, self.s3_bucket, s3_prefix, tick)
            except Exception as e:
                self._last_s3_result = {"s3_error": str(e)}
                log.error("[s3] upload failed: %s", e)
            finally:
                self.s3_queue.task_done()
