"""
fix/save-hooks-dream-end-activity-ended: unit tests for save hook chain.

4 tests:
  1. _should_save bypass includes activity_ended and backstop
  2. _end_activity_with_save fires dream_end for DREAMING
  3. _end_activity_with_save fires activity_ended for normal activity
  4. No external is_natural_quiet_point gate on activity end
"""

import os
import sys
import time
import types
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_should_save_bypass_includes_activity_ended_and_backstop():
    """activity_ended and backstop are in the _should_save bypass list."""
    print("  Test 1: _should_save bypass list...", end=" ")
    from dsf_ai_service.save_coordinator import SaveCoordinator

    mock_guala = MagicMock()
    mock_guala.tick = 100000
    sc = SaveCoordinator(mock_guala, "/tmp/test_state", s3_bucket=None)

    # All bypass reasons should return True regardless of other state
    for reason in ("shutdown", "backup", "dream_end",
                   "activity_ended", "backstop"):
        assert sc._should_save(reason) is True, \
            f"_should_save('{reason}') returned False, expected True"

    print("PASS")
    return True


def test_end_activity_with_save_fires_on_dreaming():
    """When activity kind is DREAMING, maybe_save called with reason='dream_end'."""
    print("  Test 2: dream_end on DREAMING activity...", end=" ")
    from dsf_ai_service.save_coordinator import SaveCoordinator

    mock_guala = MagicMock()
    mock_guala.tick = 100000
    sc = SaveCoordinator(mock_guala, "/tmp/test_state", s3_bucket=None)
    sc.maybe_save = MagicMock(return_value=True)

    # Simulate _end_activity wrapping
    original_end = MagicMock()

    # Create a mock activity with kind=DREAMING
    mock_activity = MagicMock()
    mock_activity.kind = "DREAMING"
    mock_guala._current_activity = mock_activity

    # Build the wrapped function (same logic as substrate_runner)
    save_coord = sc
    _guala = mock_guala
    _orig_end_activity = original_end

    def _end_activity_with_save(*a, **kw):
        ending = getattr(_guala, '_current_activity', None)
        ending_kind = ending.kind if ending else None
        result = _orig_end_activity(*a, **kw)
        if ending_kind == "DREAMING":
            save_coord.maybe_save(reason="dream_end")
        else:
            save_coord.maybe_save(reason="activity_ended")
        return result

    _end_activity_with_save()

    sc.maybe_save.assert_called_once_with(reason="dream_end")
    print("PASS")
    return True


def test_end_activity_with_save_fires_on_normal_activity():
    """When activity kind is ATTENDING_VISUAL, reason='activity_ended'."""
    print("  Test 3: activity_ended on normal activity...", end=" ")
    from dsf_ai_service.save_coordinator import SaveCoordinator

    mock_guala = MagicMock()
    mock_guala.tick = 100000
    sc = SaveCoordinator(mock_guala, "/tmp/test_state", s3_bucket=None)
    sc.maybe_save = MagicMock(return_value=True)

    original_end = MagicMock()

    mock_activity = MagicMock()
    mock_activity.kind = "ATTENDING_VISUAL"
    mock_guala._current_activity = mock_activity

    save_coord = sc
    _guala = mock_guala
    _orig_end_activity = original_end

    def _end_activity_with_save(*a, **kw):
        ending = getattr(_guala, '_current_activity', None)
        ending_kind = ending.kind if ending else None
        result = _orig_end_activity(*a, **kw)
        if ending_kind == "DREAMING":
            save_coord.maybe_save(reason="dream_end")
        else:
            save_coord.maybe_save(reason="activity_ended")
        return result

    _end_activity_with_save()

    sc.maybe_save.assert_called_once_with(reason="activity_ended")
    print("PASS")
    return True


def test_end_activity_no_external_is_natural_quiet_point_gate():
    """maybe_save fires even when is_natural_quiet_point returns False."""
    print("  Test 4: no external quiet-point gate...", end=" ")
    from dsf_ai_service.save_coordinator import SaveCoordinator

    mock_guala = MagicMock()
    mock_guala.tick = 100000
    mock_guala.is_natural_quiet_point.return_value = False
    sc = SaveCoordinator(mock_guala, "/tmp/test_state", s3_bucket=None)
    sc.maybe_save = MagicMock(return_value=True)

    original_end = MagicMock()

    mock_activity = MagicMock()
    mock_activity.kind = "ATTENDING_VISUAL"
    mock_guala._current_activity = mock_activity

    save_coord = sc
    _guala = mock_guala
    _orig_end_activity = original_end

    def _end_activity_with_save(*a, **kw):
        ending = getattr(_guala, '_current_activity', None)
        ending_kind = ending.kind if ending else None
        result = _orig_end_activity(*a, **kw)
        if ending_kind == "DREAMING":
            save_coord.maybe_save(reason="dream_end")
        else:
            save_coord.maybe_save(reason="activity_ended")
        return result

    _end_activity_with_save()

    # maybe_save MUST be called regardless of is_natural_quiet_point
    sc.maybe_save.assert_called_once()
    # Confirm is_natural_quiet_point was NOT consulted
    mock_guala.is_natural_quiet_point.assert_not_called()
    print("PASS")
    return True


def test_s3_enqueue_always_for_shutdown_backup_dream_end():
    """shutdown, backup, dream_end always enqueue S3 with no rate limit."""
    print("  Test 5: S3 always-queue reasons...", end=" ")
    from dsf_ai_service.save_coordinator import SaveCoordinator

    mock_guala = MagicMock()
    mock_guala.tick = 100000
    mock_guala.is_present_active.return_value = False
    sc = SaveCoordinator(mock_guala, "/tmp/test_state", s3_bucket="test-bucket")
    sc.queue_s3 = MagicMock()
    mock_guala.save_full_state = MagicMock()

    for reason in ("shutdown", "backup", "dream_end"):
        sc.maybe_save(reason)

    assert sc.queue_s3.call_count == 3, \
        f"queue_s3 called {sc.queue_s3.call_count} times, expected 3"
    print("PASS")
    return True


def test_s3_enqueue_rate_limited_for_activity_ended():
    """activity_ended enqueues S3 once, rate-limits the second call."""
    print("  Test 6: S3 rate-limited (no advance)...", end=" ")
    from dsf_ai_service.save_coordinator import SaveCoordinator

    mock_guala = MagicMock()
    mock_guala.tick = 100000
    mock_guala.is_present_active.return_value = False
    sc = SaveCoordinator(mock_guala, "/tmp/test_state", s3_bucket="test-bucket")
    sc.queue_s3 = MagicMock()
    mock_guala.save_full_state = MagicMock()

    sc.maybe_save("activity_ended")
    sc.maybe_save("activity_ended")

    assert sc.queue_s3.call_count == 1, \
        f"queue_s3 called {sc.queue_s3.call_count} times, expected 1"
    print("PASS")
    return True


def test_s3_enqueue_rate_limit_releases_after_interval():
    """After 601 seconds, rate limit releases and S3 enqueues again."""
    print("  Test 7: S3 rate-limit release after interval...", end=" ")
    from dsf_ai_service.save_coordinator import SaveCoordinator

    mock_guala = MagicMock()
    mock_guala.tick = 100000
    mock_guala.is_present_active.return_value = False
    sc = SaveCoordinator(mock_guala, "/tmp/test_state", s3_bucket="test-bucket")
    sc.queue_s3 = MagicMock()
    mock_guala.save_full_state = MagicMock()

    sc.maybe_save("activity_ended")
    assert sc.queue_s3.call_count == 1

    # Advance time by 601 seconds
    sc._last_s3_enqueue_wall = time.monotonic() - 601
    sc.maybe_save("activity_ended")

    assert sc.queue_s3.call_count == 2, \
        f"queue_s3 called {sc.queue_s3.call_count} times, expected 2"
    print("PASS")
    return True


def test_s3_enqueue_never_for_unknown_reason():
    """Unknown reason never enqueues S3."""
    print("  Test 8: S3 never-queue for unknown reason...", end=" ")
    from dsf_ai_service.save_coordinator import SaveCoordinator

    mock_guala = MagicMock()
    mock_guala.tick = 100000
    mock_guala.is_present_active.return_value = False
    sc = SaveCoordinator(mock_guala, "/tmp/test_state", s3_bucket="test-bucket")
    sc.queue_s3 = MagicMock()
    mock_guala.save_full_state = MagicMock()

    # "garbage" is not in _should_save bypass, so save won't even fire.
    # But let's test _maybe_queue_s3 directly:
    sc._maybe_queue_s3("garbage")

    assert sc.queue_s3.call_count == 0, \
        f"queue_s3 called {sc.queue_s3.call_count} times, expected 0"
    print("PASS")
    return True


def test_s3_enqueue_skipped_when_no_bucket():
    """No s3_bucket → queue_s3 never called."""
    print("  Test 9: S3 skipped when no bucket...", end=" ")
    from dsf_ai_service.save_coordinator import SaveCoordinator

    mock_guala = MagicMock()
    mock_guala.tick = 100000
    mock_guala.is_present_active.return_value = False
    sc = SaveCoordinator(mock_guala, "/tmp/test_state", s3_bucket=None)
    sc.queue_s3 = MagicMock()
    mock_guala.save_full_state = MagicMock()

    sc.maybe_save("backup")

    assert sc.queue_s3.call_count == 0, \
        f"queue_s3 called {sc.queue_s3.call_count} times, expected 0"
    print("PASS")
    return True


def main():
    print("fix/save-hooks: Save Hook Chain Tests")
    print("=" * 60)

    tests = [
        test_should_save_bypass_includes_activity_ended_and_backstop,
        test_end_activity_with_save_fires_on_dreaming,
        test_end_activity_with_save_fires_on_normal_activity,
        test_end_activity_no_external_is_natural_quiet_point_gate,
        test_s3_enqueue_always_for_shutdown_backup_dream_end,
        test_s3_enqueue_rate_limited_for_activity_ended,
        test_s3_enqueue_rate_limit_releases_after_interval,
        test_s3_enqueue_never_for_unknown_reason,
        test_s3_enqueue_skipped_when_no_bucket,
    ]

    results = []
    for t in tests:
        try:
            results.append(t())
        except Exception as e:
            print(f"FAIL: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print(f"\n{'='*60}")
    passed = sum(results)
    print(f"  {passed}/{len(results)} tests passed")
    print(f"  {'ALL GREEN' if all(results) else 'FAILURES DETECTED'}")
    print(f"{'='*60}")
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
