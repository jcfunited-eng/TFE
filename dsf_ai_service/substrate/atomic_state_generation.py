"""Atomic, crash-safe local save generations for the flat GualaLoom state dir.

GL-FIX-ATOMIC-SAVE-GENERATIONS-20260715

Problem this solves
-------------------
The engine writes its state as separate JSON and structural binary files into a single
flat directory (``STATE_DIR``).  Each file is written with an atomic
temp+fsync+rename, but the *set* is not atomic: a kill (ECS health-check,
OOM, deploy) between two file writes leaves a directory that mixes files from
two different save cycles.  Historically the loader then rejected the whole
directory and the process silently time-travelled to a days-old S3 backup.

This module adds an atomic *generation* snapshot on top of the flat directory,
reusing the concepts (not the code) of ``ImmutableGenerationStore``:

  * a whole save cycle is snapshotted into a private staging directory,
  * every file is hard-linked (byte-identical, no copy) from the flat dir,
  * a MANIFEST is written last, then the staging dir is atomically renamed
    into ``generations/<uuid>`` and the parent dir is fsync'd,
  * a ``CURRENT_GEN`` pointer is atomically swapped to name it,
  * the oldest generations beyond ``keep`` are pruned.

A kill at *any* instant leaves the previous complete generation untouched and
discoverable.  Recovery walks generations newest-first and returns the first
one that a caller-supplied load test accepts.

Design guarantees
-----------------
* ``publish`` is best-effort: it never raises into the save path.  A failed
  publish just means no new fallback point; the flat files are unaffected.
* Files keep their exact on-disk bytes (hard-link, or copy fallback).  Every
  existing reader and the S3-backup path keep working unchanged.
* Retired verbatim BindingWindow WAL data is not part of a generation. The
  atlas, sections, organism, and other structural stores are the durable
  cognition state.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from typing import Callable, Optional

GENERATIONS_DIRNAME = "generations"
CURRENT_GEN_NAME = "CURRENT_GEN"
MANIFEST_NAME = "GEN_MANIFEST.json"
STAGING_PREFIX = ".staging-"
MANIFEST_SCHEMA = "atomic_state_generation_v1"

# Files smaller than this are hashed into the manifest for integrity; larger
# stores (atlas/deep_atlas/structural graphs) record size+tick only, and rely on the
# hard-link to the just-written flat file for byte fidelity.  Hashing multi-MB
# stores on every hot save would reintroduce the exact per-cycle cost the hot
# lane was optimized to avoid.
_HASH_MAX_BYTES = 512 * 1024

WAL_DIRNAME = "guala_windows_wal"
RETIRED_STATE_FILES = frozenset({"guala_windows.json"})
_SKIP_DIRS = frozenset({
    GENERATIONS_DIRNAME, WAL_DIRNAME, "ring_events", "__pycache__",
})


def _fsync_dir(path: str) -> None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _snapshot_relpaths(state_dir: str) -> list:
    """The set of flat files a generation should capture.

    Every regular file directly under ``state_dir`` plus one level of the
    ``pictures``/media subdirectories, excluding scratch/WAL dirs and any
    in-progress temp files.
    """
    rels = []
    for name in sorted(os.listdir(state_dir)):
        if (name in _SKIP_DIRS or name in RETIRED_STATE_FILES
                or name in (CURRENT_GEN_NAME,)):
            continue
        if name.endswith(".tmp") or name.startswith(STAGING_PREFIX):
            continue
        full = os.path.join(state_dir, name)
        if os.path.islink(full):
            continue
        if os.path.isfile(full):
            rels.append(name)
        elif os.path.isdir(full) and name in ("pictures", "videos_assets"):
            # Media originals referenced by the visual/video stores.
            for sub in sorted(os.listdir(full)):
                subfull = os.path.join(full, sub)
                if os.path.isfile(subfull) and not os.path.islink(subfull):
                    rels.append(os.path.join(name, sub))
    return rels


def _link_or_copy(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _generations_root(state_dir: str) -> str:
    return os.path.join(state_dir, GENERATIONS_DIRNAME)


def publish_generation(state_dir: str, tick: int, identity: Optional[str],
                       keep: int = 3, log=print) -> Optional[str]:
    """Atomically snapshot the current flat state dir as one generation.

    Best-effort: returns the generation uuid on success, or None on any
    failure (logged), never raising into the caller's save path.
    """
    try:
        gen_root = _generations_root(state_dir)
        os.makedirs(gen_root, exist_ok=True)
        gen_uuid = str(uuid.uuid4())
        staging = os.path.join(gen_root, STAGING_PREFIX + gen_uuid)
        final = os.path.join(gen_root, gen_uuid)
        if os.path.exists(staging) or os.path.exists(final):
            return None
        os.makedirs(staging, exist_ok=False)

        rels = _snapshot_relpaths(state_dir)
        if "guala_core.json" not in rels:
            # Nothing worth snapshotting yet (fresh dir mid-genesis).
            shutil.rmtree(staging, ignore_errors=True)
            return None

        records = []
        for rel in rels:
            src = os.path.join(state_dir, rel)
            dst = os.path.join(staging, rel)
            try:
                size = os.path.getsize(src)
            except OSError:
                continue
            _link_or_copy(src, dst)
            rec = {"path": rel, "size": size}
            # Per-file save tick, cheaply parsed from the envelope header for
            # JSON stores; used by recovery to reject a torn generation.
            if rel.endswith(".json"):
                rec["saved_at_tick"] = _read_saved_at_tick(dst)
            if size <= _HASH_MAX_BYTES:
                rec["sha256"] = _sha256_file(dst)
            records.append(rec)

        manifest = {
            "schema": MANIFEST_SCHEMA,
            "generation_uuid": gen_uuid,
            "identity": identity,
            "tick": int(tick),
            "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": records,
        }
        man_path = os.path.join(staging, MANIFEST_NAME)
        with open(man_path, "w") as fh:
            json.dump(manifest, fh)
            fh.flush()
            os.fsync(fh.fileno())
        _fsync_dir(staging)

        os.rename(staging, final)
        _fsync_dir(gen_root)

        _write_current_pointer(state_dir, gen_uuid, int(tick), log=log)
        prune_generations(state_dir, keep=keep, log=log)
        return gen_uuid
    except Exception as exc:  # never break a save
        try:
            log(f"[gen] publish failed (non-fatal): {exc}")
        except Exception:
            pass
        return None


def _read_saved_at_tick(json_path: str) -> Optional[int]:
    """Parse only the envelope's saved_at_tick without loading the whole file."""
    try:
        with open(json_path, "rb") as fh:
            head = fh.read(4096)
        import re
        m = re.search(rb'"saved_at_tick"\s*:\s*(\d+)', head)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def _write_current_pointer(state_dir: str, gen_uuid: str, tick: int,
                           log=print) -> None:
    pointer = {"schema": MANIFEST_SCHEMA, "generation_uuid": gen_uuid,
               "tick": int(tick),
               "generation_path": f"{GENERATIONS_DIRNAME}/{gen_uuid}"}
    tmp = os.path.join(state_dir, CURRENT_GEN_NAME + ".tmp")
    dst = os.path.join(state_dir, CURRENT_GEN_NAME)
    try:
        with open(tmp, "w") as fh:
            json.dump(pointer, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, dst)
        _fsync_dir(state_dir)
    except Exception as exc:
        try:
            log(f"[gen] CURRENT_GEN write failed (non-fatal): {exc}")
        except Exception:
            pass
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _validate_generation(gen_dir: str) -> Optional[dict]:
    """Return the manifest dict if the generation is structurally complete,
    else None.  Checks: manifest present+parseable, every listed file present
    with matching size, and every recorded sha256 matches."""
    man_path = os.path.join(gen_dir, MANIFEST_NAME)
    if not os.path.isfile(man_path):
        return None
    try:
        with open(man_path) as fh:
            manifest = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    if manifest.get("schema") != MANIFEST_SCHEMA:
        return None
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return None
    for rec in files:
        rel = rec.get("path")
        if not isinstance(rel, str):
            return None
        full = os.path.join(gen_dir, rel)
        if not os.path.isfile(full):
            return None
        actual = os.path.getsize(full)
        if actual != rec.get("size"):
            return None
        want = rec.get("sha256")
        if want is not None and _sha256_file(full) != want:
            return None
    return manifest


def list_generations(state_dir: str) -> list:
    """Return [(gen_dir, manifest)] for every complete generation, newest
    (highest tick) first."""
    gen_root = _generations_root(state_dir)
    if not os.path.isdir(gen_root):
        return []
    out = []
    for name in os.listdir(gen_root):
        if name.startswith(STAGING_PREFIX) or name.startswith("."):
            continue
        gen_dir = os.path.join(gen_root, name)
        if not os.path.isdir(gen_dir):
            continue
        manifest = _validate_generation(gen_dir)
        if manifest is not None and manifest.get("generation_uuid") == name:
            out.append((gen_dir, manifest))
    out.sort(key=lambda gm: (gm[1].get("tick", -1), gm[1].get("published_at", "")),
             reverse=True)
    return out


def prune_generations(state_dir: str, keep: int = 3, log=print) -> None:
    """Keep the newest ``keep`` complete generations; remove older ones and
    any orphaned staging directories."""
    gen_root = _generations_root(state_dir)
    if not os.path.isdir(gen_root):
        return
    # Remove orphaned staging dirs (from an interrupted publish).
    for name in os.listdir(gen_root):
        if name.startswith(STAGING_PREFIX):
            shutil.rmtree(os.path.join(gen_root, name), ignore_errors=True)
    gens = list_generations(state_dir)
    for gen_dir, _man in gens[keep:]:
        shutil.rmtree(gen_dir, ignore_errors=True)
    # GL-FIX-PRUNE-INVALID-GENERATIONS-20260717: a generation whose
    # hard-linked files were later mutated in place (appended WAL/segment
    # stores share inodes with the flat set) fails _validate_generation,
    # which made it invisible to BOTH the keep-N prune above and recovery
    # — unrestorable disk garbage that accumulated forever (live: 14 of
    # 17 generations, ~15GB pinned).  Anything unlisted, non-staging, and
    # older than an hour is terminal: recovery can never use it (it only
    # walks the validated list), so remove it.  The age guard protects a
    # publish racing this prune from another process.
    recognized = {os.path.basename(gen_dir) for gen_dir, _man in gens}
    now = time.time()
    for name in os.listdir(gen_root):
        if name.startswith(STAGING_PREFIX) or name.startswith("."):
            continue
        path = os.path.join(gen_root, name)
        if not os.path.isdir(path) or name in recognized:
            continue
        try:
            age_s = now - os.path.getmtime(path)
        except OSError:
            continue
        if age_s > 3600.0:
            log(f"[gen] pruning invalid/unrestorable generation {name} "
                f"(age {age_s / 3600.0:.1f}h)")
            shutil.rmtree(path, ignore_errors=True)


def _materialize_into(gen_dir: str, manifest: dict, state_dir: str,
                      log=print) -> None:
    """Copy a validated generation's files into ``state_dir`` (overwriting the
    flat set).  Only ever called after the generation load-tested clean."""
    for rec in manifest.get("files", []):
        rel = rec["path"]
        src = os.path.join(gen_dir, rel)
        dst = os.path.join(state_dir, rel)
        os.makedirs(os.path.dirname(dst) or state_dir, exist_ok=True)
        tmp = dst + ".genrestore.tmp"
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    _fsync_dir(state_dir)


def recover_from_generations(state_dir: str,
                             load_test: Callable[[str], bool],
                             log=print) -> Optional[dict]:
    """Walk generations newest-first; return the manifest of the first one that
    ``load_test(gen_dir)`` accepts, after materializing it into ``state_dir``.

    ``load_test`` must be side-effect-free with respect to ``state_dir`` (it is
    given the generation directory to load from directly).  Returns None if no
    generation validates AND load-tests clean -- the caller must then halt
    loudly rather than silently reaching for S3.
    """
    gens = list_generations(state_dir)
    if not gens:
        log("[gen] no complete local generations available for recovery")
        return None
    for gen_dir, manifest in gens:
        gtick = manifest.get("tick")
        try:
            ok = bool(load_test(gen_dir))
        except Exception as exc:
            log(f"[gen] generation {os.path.basename(gen_dir)} "
                f"(tick={gtick}) failed load test: {exc}")
            ok = False
        if not ok:
            log(f"[gen] generation {os.path.basename(gen_dir)} "
                f"(tick={gtick}) did not validate -- trying older")
            continue
        log(f"[gen] recovering from local generation "
            f"{os.path.basename(gen_dir)} (tick={gtick})")
        _materialize_into(gen_dir, manifest, state_dir, log=log)
        return manifest
    log("[gen] no local generation passed load test")
    return None
