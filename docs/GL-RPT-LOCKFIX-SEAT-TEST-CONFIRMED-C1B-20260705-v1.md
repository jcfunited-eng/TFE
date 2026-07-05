# GL-RPT-LOCKFIX-SEAT-TEST-CONFIRMED-C1B-20260705-v1

doc_id: GL-RPT-LOCKFIX-SEAT-TEST-CONFIRMED-C1B-20260705-v1
From: c1b | To: Eve, Joe, c1a | Closes the open item from `GL-RPT-
ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1.md`: "what I cannot
verify myself... needs Joe's participation." He was at the seat with
camera+mic on and it happened live. Reporting the real numbers.

---

## Live seat test, unprompted, camera+mic ON throughout

Joe's session went active (`presence.joe: true`) with continuous
`sight_frame_bound`/`sound_frame_bound` events (camera ~every 5-6s,
mic ~every 5s) already flowing cleanly — zero drops the entire time
(`frame_backpressure.dropped: {sight: 0, sound: 0}` before, during,
and after). He then sent two real messages. Both `converse_timing`
events, measured with sensors actively streaming:

| turn | n_words | recall_ms | read_ms | total_ms |
|---|---|---|---|---|
| 1 | 6 | 12.0 | 516.8 | **870.8** |
| 2 | 7 | 11.5 | 2795.3 | **4671.7** |

Both **emphatically clear** the <30s exit criterion — under 1 second
and under 5 seconds respectively, with camera and mic both live the
whole time. `read_ms` (the phase L1 targeted) dropped as low as
516.8ms — down from the pre-`-182` reading of 24,673.9ms (~48x) and
even further below the clean-no-sensors 8,225.4ms reading from right
after deploy. This is strong evidence L1 (DSP outside the lock) is
doing exactly what it was built to do: sensory streaming and
conversation no longer fight over the same lock.

No `response_window_expired` with `n_responses_bound: 0` for either of
these two windows as of this report, no frame drops, no errors. This
is the real thing Eve's exit criterion asked for, not a synthetic
approximation — I didn't manufacture this test; Joe's own live session
produced it while I was watching.

**Confirmed at the screen itself, not just the backend:** Joe sent a
screenshot of `gualaloom.html` mid-exchange. Both messages ("what are
you doing in there", "I see you're finally watching a video") are
visible, each rendered fast with c1a's `-180` honest-empty text —
`(she had nothing — emission was empty)` — not stuck on "(settling...)",
not a raw silent `...`. This matches the two `converse_timing` events
above exactly (tick 14874780 / 14874808 in the events panel, same
ticks). The render worked; the content was genuinely empty (the
organism/brain had nothing confident enough to say) — that's the
known, separate, already-documented P3 "honest silence, never
backfilled" behavior, not a new bug and not a latency problem. Latency
and content are two different axes: `-182` fixed the first; the
second (why she has so little to say) is `-179`/`-178`'s territory,
not this dispatch's.

**Still open:** the deliberate mid-conversation deploy test specifically
(deploying WHILE a turn is in flight, to prove L2's fail-loud path)
hasn't happened yet — this was a clean live-traffic test, not a deploy-
collision test. Will report if/when a deploy lands during a real
exchange, or set one up deliberately if asked.

### Changelog
- v1 (2026-07-05, c1b): live, camera+mic-on seat test confirmed by
  Joe's own real session — two real turns, 870.8ms and 4671.7ms,
  zero drops, zero errors. CMD-182's core latency exit criterion met
  with real numbers. The deploy-collision half of L2 (fail-loud across
  a live restart) remains separately untested.
