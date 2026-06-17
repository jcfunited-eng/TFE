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


class SaveCoordinator:
    def __init__(self, guala, state_dir, s3_bucket=None):
        self.guala = guala
        self.state_dir = state_dir
        self.s3_bucket = s3_bucket
        self.s3_queue = queue.Queue(maxsize=20)
        self.last_save_tick = 0
        self.last_save_wall = 0.0
        self._lock = threading.Lock()

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
        """Non-blocking save if conditions are right. Returns quickly."""
        with self._lock:
            if not self._should_save(reason):
                return False
            self.last_save_tick = self.guala.tick
            self.last_save_wall = time.monotonic()
        try:
            self.guala.save_full_state(self.state_dir)
            if self.s3_bucket and reason in ("backup", "shutdown",
                                              "dream_end", "presence_quiet"):
                self.queue_s3(self.state_dir, self.guala.tick, reason)
            return True
        except Exception as e:
            log.error("[save] failed: %s", e)
            return False

    def _should_save(self, reason):
        if reason in ("shutdown", "backup", "dream_end"):
            return True
        # Defer if someone's actively interacting
        if self.guala.is_present_active():
            return False
        # Don't save too often
        tick_delta = self.guala.tick - self.last_save_tick
        wall_delta = time.monotonic() - self.last_save_wall
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
                    "guala_sections.json", "guala_bucket.json",
                    "guala_visual.json", "guala_sounds.json",
                    "guala_videos.json",
                ]
                uploaded = 0
                for fname in all_files:
                    fpath = os.path.join(state_dir, fname)
                    if os.path.exists(fpath):
                        s3.upload_file(fpath, self.s3_bucket,
                                       f"{s3_prefix}/{fname}")
                        uploaded += 1
                log.info("[s3] uploaded %d files → s3://%s/%s/ tick=%d",
                         uploaded, self.s3_bucket, s3_prefix, tick)
            except Exception as e:
                log.error("[s3] upload failed: %s", e)
