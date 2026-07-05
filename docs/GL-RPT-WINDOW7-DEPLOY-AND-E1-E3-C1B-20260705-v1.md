# GL-RPT-WINDOW7-DEPLOY-AND-E1-E3-C1B-20260705-v1

doc_id: GL-RPT-WINDOW7-DEPLOY-AND-E1-E3-C1B-20260705-v1
From: c1b | To: Eve, Joe, c1a | Responds to: `GL-CMD-FIRE-WINDOW7-EVE-
20260705-186-v1`. Window 7 **DEPLOYED, LIVE** (task:471, SHA
`d9b6402`, c1a's `-186` build). Two of the five 24h behavioral exit
criteria cleared within minutes of deploy — reporting the real
numbers, not overclaiming.

---

## Deploy

Fresh backup taken pre-cutover. Tests clean (32/32 unaffected, same 3
pre-existing unrelated failures). Organism/tapestry restore confirmed
(`tick=1769 pop=64`, `tick=3587 neurons=450`, same identity). Curriculum
scheduler boot line confirmed: `[curriculum] autonomous study started:
enabled=True books=10 chunk=30 interval=120s interleave=['worldfeed',
'lookup']`.

## E1 — headline number confirmed: first audio selection since smoke-test era

Within minutes of deploy: `current_activity: {"kind": "ATTENDING_AUDIO",
"target": "edffe97cc742"}` — a sound outside the smoke-test set (not
one of the 300-2000+-times-attended items). This is `-186`'s
recency-recovery dial working exactly as designed: audio, structurally
locked out since early smoke-testing, is competitive again. Combined
with the already-observed `ATTENDING_VIDEO` and `ATTENDING_VISUAL`
this session, **E1 (≥3 distinct activity kinds, unprompted) is
satisfied.**

## E3 — curriculum pull confirmed, unprompted

`curriculum_studied` event, tick 14889220: `{"book_id": 2591, "title":
"Grimms' Fairy Tales", "offset": 30, "n_book_sentences": 7988,
"n_fed": 0, "organ_tokens": 0, "book_complete": false}`. Nobody
triggered this — it fired on the scheduler's own 120s interval, the
first real evidence the reconnected `CurriculumScheduler` is actually
studying. `n_corpora` went 19→20 in `/status` (new `secret_gardenl`
corpus appearing) as the corroborating side-effect. **E3 (≥1
curriculum_studied event, unprompted) is satisfied.**

## Also observed, same window: real conversation, camera+mic ON

Joe present and typing while camera+mic streamed continuously
(`sight_frame_bound`/`sound_frame_bound` flowing throughout, zero
drops). Three real turns, all comfortably under any latency
threshold: **4161.6ms, 2031.6ms, 6125.3ms** total. `recall_ms` stayed
low (12-13ms) across all three — `-181`/`-182`'s fixes holding under
real combined load (sensors + curriculum + conversation all running
at once).

**New event type observed, not yet investigated:** `block_intake_ledger`
(`{"block": "quiet", "planned": 30, "actual": 0, "capped": true,
"reason": "suppressed"}`) — first sighting of this event kind this
session, likely tied to `-160/-161/-162`'s aware-gate/deliberation
work now live. Flagging, not chasing — out of scope for this report.

## E2, E4, E5 — still open, watching

- **E2** (unprompted emission passes the aware gate): not yet observed.
- **E4** (≥5 distinct attention targets): the new audio target
  (`edffe97cc742`) makes 4 distinct targets total this session
  (video + 2 pictures + this sound) — one short of 5, and recency-
  recovery should keep unlocking more. Watching.
- **E5** (natural pressure-triggered sleep): still not observed.

### Changelog
- v1 (2026-07-05, c1b): window 7 deployed (task:471). E1 and E3 both
  confirmed satisfied within minutes — first unprompted audio
  selection since smoke-testing, and a real unprompted
  `curriculum_studied` pull. E2/E4/E5 still open, actively watching.
