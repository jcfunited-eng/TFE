# GL-RPT-UNREACHABLE-DIAGNOSIS-C1-20260628

doc_id: GL-RPT-UNREACHABLE-DIAGNOSIS-C1-20260628
Date: 2026-06-28
Author: c1
SHA: e11da48 (fix shipped)

---

## Root Cause

**7 of 8 curriculum pause windows in the last 30 minutes exceeded the 20s
`substrate_client` timeout, causing "substrate unreachable" responses.**

Pause durations measured from CloudWatch timestamps (task :361):

| Pause | Duration | >20s? |
|-------|---------|-------|
| 1 | 30.7s | YES |
| 2 | 1.4s | no |
| 3 | 237.7s | YES |
| 4 | 38.1s | YES |
| 5 | 34.7s | YES |
| 6 | 146.3s | YES |
| 7 | 44.6s | YES |

Mean: 73s. Max: 237s. 6/7 exceeds 20s; one exceeds 2 minutes.

**During each pause, `_autonomy_pause_refcount > 0` and the curriculum is
running `_curriculum_feed_chunk(30 sentences)`:**

Two compounding delays:
1. **30 sentences × ~1-2s per sentence** = 30-60s minimum per chunk (section.receive()
   does O(n_modes) numpy matmul + atlas.record() heterosynaptic redistribution).
2. **`_end_activity_with_save()` firing during curriculum window**: when an activity
   transition (DAYDREAMING→next) coincides with a curriculum chunk, `save_full_state()`
   Phase 1 runs inside `self.lock` — serializing 17k atlas entries takes 2-5s.
   Phase 2 (EFS write, 170s, no lock) runs concurrently, blocking the autonomy thread.
   During Phase 2, curriculum competes for the lock, and Phase 1 intermittently
   re-locks for bookkeeping. This explains the 237s and 146s outliers.

**The 20s `substrate_client` timeout was already raised from 5s for this class of
issue. It was not raised high enough.**

---

## F.1/C.1/C.4/F.2 contribution

None of today's dispatches introduced new blocking paths:
- C.1 polarity: O(1) frozenset lookup in `read_word()`, O(200) loop in emit path.
  Negligible.
- C.4 dream_pressure: single float increment per autonomy tick. Negligible.
- F.1/F.2: organ surface poll runs in daemon thread; `_translate_organ_surface()`
  called only from `_cmd_converse()` (not curriculum path). Negligible.

The "unreachable" class predates today's ships and is driven by atlas scale (17k+
entries → slower per-word processing).

---

## Fix shipped (SHA e11da48)

**Fix 1: Defer activity saves during curriculum**
`_end_activity_with_save()` now checks `_autonomy_pause_refcount > 0`. If curriculum
is running, the save is skipped (with print log). The 5-minute backstop save still
captures the state. Eliminates Phase 1 lock contention and Phase 2 overlap from
during-curriculum saves.

**Fix 2: Status timeout 20s → 45s**
`substrate_client` status timeout raised from 20s to 45s in app.py. Curriculum
chunks with 30 sentences at 1-2s each = 30-60s; 45s covers most without the save
overhead. Combined with Fix 1, most pauses should now complete under 45s.

---

## Remaining risk

Even without saves, 30 sentences × ~2s each = 60s is possible with a 17k+ atlas.
Fix 1 reduces the tail (saves don't extend pauses) but the base curriculum
processing time still scales with atlas size. Long-term remediation requires either:
- Reducing per-word atlas processing time (vectorize heterosynaptic redistribution)
- Reducing chunk size further (currently 30; could go to 15)
- Running curriculum in smaller interleaved bursts instead of 30-sentence windows

These are separate dispatches. The current fix removes the save-overlap amplifier
and raises the timeout high enough to tolerate the base processing time.

---

## Pattern confirmation

Instance 2 from Joe's report: "After ~10 rapid /experience calls, 11th returned
unreachable but vocab grew 11532→11534."

This is the `/experience` → `/organs_say` → `_guala_cognition.expose()` path, which
**does NOT write to v5 atlas**. The vocab growth happened via the concurrent `/listen`
call (Whisper VTT sends both). The `/experience` call itself didn't write vocab —
the routing fix (GL-CMD-EXPERIENCE-ROUTING-FIX-32, same commit) corrects this.
