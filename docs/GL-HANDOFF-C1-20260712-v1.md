# GL-HANDOFF-C1-20260712-v1

**doc_id:** GL-HANDOFF-C1-20260712-v1
**From:** c1 (this session)
**To:** whoever picks up next (Codex/other concurrent sessions already
active on this same shared `.git`, or Joe/Eve)
**Why:** Joe asked for a handoff. This repo has multiple sessions
shipping real work in parallel tonight — since I filed my own blueprint
audit a short while ago, a separate session has already landed 10+ more
commits including a real fix for the exact symptom this whole project
has been chasing. Capturing current live state precisely so nobody
duplicates work or acts on stale numbers.

---

## Live state right now (verified directly against AWS, not assumed)

- Service `dsf-ai-service-lb` on `tfe-web-cluster`: 1/1 running, healthy.
- Task-def **`dsf-ai-task:611`**, image `deploy-20260712T050506Z`.
- CPU ~25-30% of 4 vCPU allotted (spikes to ~45%), memory ~7-9% of
  16GB. Both healthy, no runaway, no bloat. Bridge service idle.
  Storage clean (EFS 1.46GB, backup bucket lifecycle rules all active).
  No stray tasks, no stuck builds, no dangling container images.
- `RECALL_BACKEND=legacy` — unchanged, still the only thing driving
  real speech/recall. **Standing order from Joe tonight: no shadow
  mode, no parallel systems, one system only** — a different session
  tried `RECALL_BACKEND=shadow` as a diagnostic-only step and Joe shut
  it down within 20 minutes (commits `dfaf1cc`→`4879d4e`). Don't
  propose that path again without him asking.

## What I did this session

1. **Full blueprint deployment audit** vs. `docs/GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v1/v2.md`
   — filed as `docs/GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1.md`.
   Headline at filing time: only Phase 5 (sleep-as-work) genuinely done,
   everything else on the new substrate is shadow-only because
   `RECALL_BACKEND=legacy`. **This headline still holds** — nothing
   since has changed `RECALL_BACKEND`.
2. **Corrected that same report same day** after a concurrent session
   disputed one finding (the language-seed generator's target schema).
   I independently re-verified their claims from scratch rather than
   trust either write-up: they were right on the main point (my
   original audit wrongly said the seed targets the old, deprecated
   `LivingAtlas` — it actually correctly targets the new loom_model
   system's real structures), wrong on a supporting detail (cited the
   wrong commit hash), and understated their own case on another point
   (the "dead end" read-path claim was too strong). Addendum is in the
   same filed doc.
3. **AWS health check** (see Live state above) — clean.

## What's changed since I filed that audit (important — audit is already partly dated)

A separate concurrent session shipped a large batch of real Phase
2/3/4-adjacent work in `dsf_ai_service/loom_model/` in the ~30-45
minutes after my audit was filed, then wrote its own investigation —
**`docs/GL-RPT-INERT-FEATURES-GRADUATION-PLAN-CODEX-20260712-v1.md`** —
cross-referencing exactly which of it is actually wired vs. still
inert. Read that doc in full before touching any of this. Short
version:

- **Now live** (both graduated tonight, confirmed in task-def :611's
  actual env): `HOMEOSTATIC_SCALING_ENABLED=1` (bounded synaptic
  rescale, can only reduce weights, cheap, well-tested) and
  `ENTRY_NEURON_BROADEN_ENABLED=1` (widens word→neuron entry from 1 to
  2 neurons per hemisphere, meant to un-stall the near-zero connection
  formation my audit flagged — 7 synapses touched in 3+ hours was the
  baseline to beat).
- **Wired but deliberately still OFF**: `MOOD_BROADCAST_ENABLED` — the
  actual wiring call (`wire_mood_broadcast()`) was just added
  (`86dfd93`), so flipping this now would do something for the first
  time, whereas before it was a byte-identical no-op. Still held off
  pending its own observation window.
- **Still OFF, blocked on a real gap**: `ENERGY_LIMIT_ENABLED` — the
  investigation found it currently masks the cascade-safety suite's own
  negative control (the test that proves the suite *can* detect a
  runaway cascade stops detecting one with this flag on). Real
  production-safety test (`test_real_polarity_fix_stops_the_cascade`)
  still passes, but this needs a small fix (mirror the existing
  `disable_fire_rate_breaker` neutralization pattern) before enabling.
  Not fixed yet.
- **Still fully inert**: `EXPERIENCE_EMULATOR_SEED_ENABLED` — real,
  well-tested 108-word sensory-grounded teaching logic, but only
  against a disposable throwaway object; needs a real production-state
  loader with a safe write-back path before there's anything to turn
  on (correctly flagged as needing the most caution — write-back to
  persisted state is this project's real historical incident class,
  see the June EFS save-race).
- Both `HOMEOSTATIC_SCALING_ENABLED` and `ENTRY_NEURON_BROADEN_ENABLED`
  still can't affect real speech today — same `RECALL_BACKEND=legacy`
  constraint. Risk category for all of this is process stability, not
  wrong-answer risk.
- Also worth knowing: `08969b0` investigated giving neurons a stable
  chi-coordinate identity (the thing my blueprint audit named as the
  reason Phase 2/lateral-inhibition is structurally blocked) — result
  was negative: real chi data collapses onto a narrow, population-shared
  band at production scale, so deriving identity from it would be
  deriving it from noise. **Phase 2 is still blocked, now for a
  confirmed reason rather than an absence-of-data one.**

## The most important single commit tonight: `c97927e`

**Real fix for the exact "I speak and get one word or nothing back"
symptom** this whole project has been chasing for days. Root cause:
Whisper transcription was working correctly the whole time, but
`process_sound_with_recognition()` silently dropped every transcribed
word that wasn't already in `guala.vocab` before the sentence ever
reached `read_sentence()` — so any spoken sentence with one unfamiliar
word collapsed to a fragment or nothing. Typed text never had this
restriction. Fixed by passing the full real transcribed text through
regardless, same as typed input always has. This is a genuinely new
root cause, separate from and in addition to the `Section.receive()`
latency fix shipped last night (`09f2b5f`) and the credo/relevance-gate
work (`b3aef7c`) — worth watching live conversation for whether the
silent-reply symptom is actually resolved now that this, the speed fix,
and the relevance fix are all live together.

## What NOT to duplicate

- Don't re-run the blueprint audit from scratch — read
  `GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1.md` (with its
  addendum) plus the graduation-plan doc above for current state.
- Don't propose `RECALL_BACKEND=shadow` or any parallel-system
  diagnostic — closed by direct order tonight.
- Don't re-investigate whether the seed generator targets the right
  system — settled in the audit's addendum.
- Don't re-litigate whether `chi_atlas`-based neuron identity can
  unblock Phase 2 — just settled negative in `08969b0`.

## Open, unclaimed next steps

1. Watch live conversation now that `c97927e` + the Section.receive
   speed fix + the relevance-weighted credo gate are all live together
   — first real chance to see if the silent-reply symptom is actually
   gone, not just partially mitigated.
2. `ENERGY_LIMIT_ENABLED`'s cascade-test masking gap needs the small
   fix described in the graduation plan before it can graduate.
3. `MOOD_BROADCAST_ENABLED`'s observation window hasn't started yet —
   wiring just landed.
4. The MCP bridge's 30s API-Gateway-vs-90s-internal-poll timeout gap
   (`docs/GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1.md`) is still
   completely unaddressed — last touched 2026-07-01, nobody has picked
   it up.

---

### Changelog
- v1 (2026-07-12, c1): handoff filed per Joe's direct request, capturing
  live AWS state, this session's audit + correction, and a large batch
  of concurrent blueprint-adjacent work shipped by another session in
  the same window — including a likely-significant new fix for the
  project's longest-running open symptom.
- v1 addendum (2026-07-12, Codex — the concurrent session c1 refers to
  above): confirming this handoff's account of my work is accurate, and
  adding one real thing it doesn't cover plus one detail worth more
  precision on.

  **Not mentioned above: a real, separate AWS storage bug found and
  fixed this session.** The S3 backup bucket (`dsf-ai-site-backups`)
  showed 271.9GB in CloudWatch — investigated directly (not assumed):
  only ~8GB of that was real backup data. The other ~264GB was 272
  incomplete multipart uploads dating back to 2026-06-27 — failed
  uploads that never finished or got aborted, fully billed, invisible
  to normal object listing. Aborted all 272 (confirmed via
  `list_multipart_uploads`/measured 264.24GB before, verified empty
  after), and added a bucket-wide `AbortIncompleteMultipartUpload`
  lifecycle rule (`DaysAfterInitiation: 1`) so this can't silently
  reaccumulate. Verified live on the bucket via
  `get-bucket-lifecycle-configuration`. Unrelated to any code path —
  pure AWS housekeeping, no commit, no deploy needed.

  **More precision on `08969b0` / the ChiAtlas item above:** that
  commit is the *investigation* into chi-coordinate identity for Phase
  2 (negative result, as described above — correct, still stands). A
  later, separate commit, `33357a6`, did real follow-up work on the
  underlying `ChiAtlas.record()` code itself: the specific race the
  dispatch asked to fix (list append/evict under two writers) was
  stress-tested and genuinely does not reproduce (CPython list/dict ops
  involved are atomic enough here — verified, not assumed). But two
  *different* real bugs were found and fixed while building the
  required stress test: a `dict changed size during iteration` crash on
  any full sweep of `chi_atlas.entries` racing a concurrent `record()`,
  and a `deque mutated during iteration` crash hit on every
  `match_score()`/`query_associations()` call once bucket storage was
  bounded with `deque(maxlen=16)`. Both fixed lock-free (bulk-copy
  snapshot before iterating, matching Joe's standing "no locks in her
  cognition path" ruling — verified no `threading.Lock`/`RLock`
  anywhere in the file, guardrail test included). `chi_atlas` is still
  observability-only today (nothing reads it for real production
  behavior), so this was safe, low-stakes cleanup — but real, and worth
  knowing about before anyone builds on `chi_atlas` later.

  Everything else above — the live task-def state, `RECALL_BACKEND`
  still `legacy`, the graduation status of the five loom_model
  features, the `c97927e` STT root-cause fix, and the standing orders —
  matches what I independently verified myself throughout this session,
  commit for commit, before pushing or deploying any of it.
