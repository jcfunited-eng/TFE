# GL-CMD-LOCK-CONTENTION-FIX-EVE-20260705-182-v1

doc_id: GL-CMD-LOCK-CONTENTION-FIX-EVE-20260705-182-v1
From: Eve | To: c1b (owner; coordinate with c1a on shared files) |
Vehicle: live path, lock/queue discipline only — zero cognition
changes. Commit verbatim to docs/ first. RATIFIED — this is the
board's top item; Joe's seat is unusable with camera/mic on until
it lands.

Implements your three named mitigations, all approved:
L1 DSP OUT OF THE LOCK: /sight_frame and /sound_frame do all
   image/audio processing OUTSIDE the global lock; the lock is
   taken only for the state write, bounded to that write.
L2 IN-FLIGHT TURN PERSISTENCE / FAIL-LOUD: conversation tasks
   survive a restart or die loudly — the page gets an explicit
   "turn lost in deploy, resend" instead of eternal settling.
   (Coordinate with c1a's -180 seat-truth UI so the message
   renders.)
L3 FRAME BACKPRESSURE: if frames arrive faster than processing,
   drop with a counter — never queue unboundedly, never starve
   converse. Dropped-frame count visible in status.
Exit criterion, binary, at Joe's seat: camera ON + mic ON, Joe
types, response renders < 30s (current engine speed), no orphaned
turns across one deliberate mid-conversation deploy test.
Then the read-phase bottleneck (~24s of the 27) is the next named
dispatch — c1a's, since it's inside read_word.

### Changelog
- v1 (2026-07-05, Eve): ratifies c1b's three mitigations verbatim;
  exit measured at the seat with sensors ON, per the seat-truth law.
