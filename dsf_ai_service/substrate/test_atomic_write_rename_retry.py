"""
GL-FIX-ATOMIC-RENAME-RETRY-20260713 verification.

Guala._atomic_write() saves each hot-lane state file via write+flush+fsync
then os.rename(tmp, path). Live production logs showed os.rename()
occasionally raising FileNotFoundError immediately after a successful
fsync (a directory-entry visibility lag on EFS/NFS, not a really-missing
file) -- confirmed deploy-independent, ~1 event per 1-6 hours, "HOT SAVE
CRITICAL FAILURE" in CloudWatch, _last_save_tick not advancing on each hit.

_atomic_write now retries a bounded number of times (4 attempts, small
backoff) specifically on FileNotFoundError. These tests verify: normal
writes are unaffected, a transient failure recovers with the correct
final content, and a persistent failure still raises (not silently
swallowed) rather than hanging or masking a real problem.
"""

import os
import sys
import json
import time
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def check_normal_write_succeeds():
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "guala_core.json")
        Guala._atomic_write(path, {"tick": 42})
        ok = (os.path.exists(path)
              and not os.path.exists(path + ".tmp")
              and json.load(open(path)) == {"tick": 42})
        print(f"  normal write succeeds, no leftover .tmp: {'PASS' if ok else 'FAIL'}")
        return ok
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def check_transient_enoent_recovers():
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "guala_needs.json")
        real_rename = os.rename
        calls = {"n": 0}

        def flaky_rename(src, dst):
            calls["n"] += 1
            if calls["n"] <= 2:  # fail twice, succeed on the 3rd attempt
                raise FileNotFoundError(
                    2, "No such file or directory", src)
            return real_rename(src, dst)

        t0 = time.monotonic()
        os.rename = flaky_rename
        try:
            Guala._atomic_write(path, {"connection": 0.5})
        finally:
            os.rename = real_rename
        elapsed = time.monotonic() - t0

        ok = (os.path.exists(path)
              and json.load(open(path)) == {"connection": 0.5}
              and calls["n"] == 3)
        print(f"  transient ENOENT (2 failures) recovers on retry 3, "
              f"final content correct, took {elapsed:.3f}s: "
              f"{'PASS' if ok else 'FAIL'} (calls={calls['n']})")
        return ok
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def check_persistent_failure_still_raises():
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "guala_coordinator.json")
        calls = {"n": 0}

        def always_fail_rename(src, dst):
            calls["n"] += 1
            raise FileNotFoundError(2, "No such file or directory", src)

        real_rename = os.rename
        raised = False
        t0 = time.monotonic()
        os.rename = always_fail_rename
        try:
            Guala._atomic_write(path, {"joe": 1.0})
        except FileNotFoundError:
            raised = True
        finally:
            os.rename = real_rename
        elapsed = time.monotonic() - t0

        # Bounded: 4 attempts, not an infinite/silent retry loop, and not
        # silently swallowed -- callers (and their own "HOT SAVE ... FAILURE"
        # logging) still see a real exception for a genuinely persistent
        # failure, exactly as before this fix.
        ok = raised and calls["n"] == 4 and elapsed < 2.0
        print(f"  persistent failure still raises after bounded retries "
              f"(attempts={calls['n']}, took {elapsed:.3f}s): "
              f"{'PASS' if ok else 'FAIL'}")
        return ok
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    print("GL-FIX-ATOMIC-RENAME-RETRY-20260713 Verification")
    print("=" * 70)
    results = {
        "normal_write": check_normal_write_succeeds(),
        "transient_enoent_recovers": check_transient_enoent_recovers(),
        "persistent_failure_still_raises": check_persistent_failure_still_raises(),
    }
    print("\n" + "=" * 70)
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    overall = all(results.values())
    print(f"\n  OVERALL: {'PASS' if overall else 'FAIL'}")
    return overall


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
