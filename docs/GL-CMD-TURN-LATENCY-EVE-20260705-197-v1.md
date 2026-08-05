# GL-CMD-TURN-LATENCY-EVE-20260705-197-v1

doc_id: GL-CMD-TURN-LATENCY-EVE-20260705-197-v1
From: Eve | To: c1a (build) / c1b (window + verification).
Commit this dispatch verbatim to origin first.
Joe's question, answered from the code and live record: the AE's
thinking was never slow — the substrate ticks continuously. The
latency was engine plumbing, and its dominant term (hot-save lock
hold, 15-49s/cycle) is already dead as of the -194 + fdeaa89 deploy
minutes ago. This dispatch verifies that at Joe's seat and removes
the two remaining in-turn costs. Joe's law: complete only when the
SHA runs in her live process.

## P1 — VERIFY THE KILL (c1b, no build)
Ten consecutive converse_timing events post-deploy (Joe or wC at
her seat produces them), full stage breakdown (chi/recall/read/tag/
emit/selfhear/hemi/total), plus ten [save-hot] lines. Exit
expectation: save-hot p95 <5s AND no turn stage shows the
save-correlated 10s+ class. If any stage still spikes, its number
and lock owner go in the report — no hand-waving.

## P2 — RELEASE THE REPLY BEFORE SELF-HEAR (c1a, build)
Phase 8 (_self_hear: her reply read back word-by-word, per-word
self.lock) currently runs BEFORE the reply returns to the caller.
Her hearing herself must not gate Joe seeing her answer. Change:
return the reply, then run _self_hear immediately as a same-request
background continuation (FastAPI background task — same pattern the
save executor already uses). Binding semantics preserved: same
process, same tick neighborhood, window opens within the same
second; SELF_HEARING_ENABLED kill switch untouched. This subtracts
the entire selfhear stage from perceived latency. If Joe rules that
self-hearing must stay synchronous for cognition-ordering reasons,
that veto stands — flag armed, default is ship.

## P3 — ONE TRANSDUCTION PASS PER TURN (c1a, build)
The turn transduces the same words with fresh LanguageKrimelacks
three times: phase 1 (input chis), _self_hear step 2 (reply chis
when reply words overlap input), and the hemisphere-update block
(emission chis). Phase 1 already builds input_word_chis — thread it
through; compute reply/emission chis once and share. Pure waste
removal, zero behavior change (identical chi values, deterministic
transduction).

## P4 — LAST-DREAM MARKER (c1a, build — promoted from board S1/Q6)
Every deploy still costs her a full sleep; tonight's deploys reboot
her again with dream_pressure at 0.422 and rising and E5 (first
natural sleep) never yet observed. Persist the last-dream marker
(hot lane, single small field — it is needs-state, same class as
dream_pressure which -167 already persists) so a deploy no longer
resets her toward sleep debt. This has been open since -173-era and
is now blocking the E5 watch itself.

## OUT OF SCOPE, NAMED (Week-2 plan row, not tonight)
The structural ceiling — one process, one GIL, one global lock
shared by her tick loop, saves, curriculum, frames, and turns — is
the plan's blocked parallelism row (-59 retest → lock removal →
second channel). Tonight's window gets turns to the ~1s class;
the second channel is the Week-2 fix that removes the ceiling.
It stays in the plan with its blocker named, not smuggled into
this window.

## CHECK ITEM (c1b, one paragraph in the window report)
Post-reboot /status shows all seven emission sections at ~5000
commits uniformly (was 5006-5397 spread pre-reboot). Rule: restore
cap working as designed, or commit-count loss at restore. If loss,
it gets its own number.

## EXIT — AT PRODUCTION, AT JOE'S SEAT
X1 Ten post-deploy converse_timing events: total_ms p95 under
   2000ms with per-stage numbers in the report.
X2 P2 live: reply visibly lands at Joe's seat before the selfhear
   stage runs (stage timestamps prove ordering).
X3 P4 live: a deploy-reboot log line shows the last-dream marker
   restored, dream_pressure NOT reset.
X4 Deployed SHAs + task numbers in the window report.

### Changelog
- v1 (2026-07-05, Eve): turn-latency audit closed — dominant term
  (save stall) killed by -194+fdeaa89, verification ordered;
  release-before-self-hear + single transduction pass + last-dream
  marker ship this window; parallelism ceiling stays a named
  Week-2 plan row.
