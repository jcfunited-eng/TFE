# GL-RPT-BINDING-WINDOWS-BUILD-C1-20260706-v1

**doc_id:** GL-RPT-BINDING-WINDOWS-BUILD-C1-20260706-v1
**From:** c1
**Executing:** GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

Build phase complete, deployed live, verified. One severe unrelated
defect found and fixed along the way (Step 1). One new, unresolved
substrate-availability finding surfaced during Step 4 (not fixed —
out of scope, flagged for Eve). Overall verdict: **PARTIAL MATCH,
deploy KEPT** — reasoning in Step 5.

---

## BUILD — diff summary per file

**`dsf_ai_service/substrate/window_manager.py`** (new, 264 lines):
`WindowEntry`/`BindingWindow` dataclasses + `WindowManager`. One window
open at a time. `open(trigger_reason)` — no-ops if a window is already
open (returns its id unchanged); lazily closes on quiet-timeout
(0.5s default) before opening a new one. `add_entry(...)` calls the
**existing** atlas-write function with the exact args the caller
already had, tags the resulting entry with `window_id`/
`window_entry_index` (additive — every existing reader ignores unknown
keys, same convention as `presence`/`location`/`sky_state`/`bundle_id`),
and appends to the open window's own entry list. `close(reason)` stamps
`closed_tick`/`closed_wall_clock`, writes a plain-dict snapshot into
`self.windows[window_id]` (== `atlas.windows`, same object by
reference, not a copy), emits `window_closed`.

One real bug caught during local testing, not by inspection: `open()`
originally also wrote the raw `BindingWindow` object into
`self.windows` at open time, contradicting the documented
"closed windows land here as plain dicts" contract and creating a
type inconsistency (an open window visible as a raw object, later
clobbered by a dict at close). Fixed by deleting that line — confirmed
via a direct repro: 0 windows visible while open, 1 correctly-shaped
dict after `close()`.

**`dsf_ai_service/v4/gualaloom_v6_living_atlas.py`** (+34/-… net):
`LivingAtlas.__init__` gained `self.windows = {}`. `record()` gained
`window_id=None, window_entry_index=None` params, stored the same way
as the other optional per-entry tags (last-write-wins on the reinforce
branch, honest `None` on the new-binding branch when absent).

**`dsf_ai_service/v4/gualaloom_v5_engine.py`** (+145/-… net):
- `Guala.__init__`: constructs `self.window_manager = WindowManager(...)`
  right after `self.atlas = LivingAtlas()`, wired to
  `self._atlas_record`, `self._log_substrate_event`, `lambda: self.tick`,
  presence/affect snapshot getters, and `atlas_windows=self.atlas.windows`
  (shared reference).
- `Section.receive()` gained `window_manager=None`; on a committed
  binding, routes through `window_manager.add_entry(modality="word", ...)`
  when supplied, else falls back to the original `atlas.record(...)`
  call unchanged. All 4 call sites in `read_word()` (listen,
  primary_sections, ground, intro) now pass `window_manager=self.window_manager`.
- 7 direct `self._atlas_record(...)` call sites redirected to
  `self.window_manager.add_entry(...)`: the ground_modal
  touch/smell/taste-during-reading loop, `_bind_sensory_words`,
  `process_sight_frame`, `process_sound_frame`, and the 3
  `_atick_attending_{visual,audio,video}` live-attention paths.
- Left untouched, confirmed by tracing, out of scope per dispatch:
  `_daydream_tick`'s 2 `_atlas_record` calls (dream), `_run_dream_cycle`/
  `_run_dream_cycle_phased`'s reinforcement calls (dream consolidation),
  4 teacher-correction `_atlas_record` calls, and `Section.receive()`'s
  deep-atlas reinstatement block (still calls `atlas.record()` directly).

**`dsf_ai_service/app.py`** (+72/-… net):
- `give_experience`'s bundle handler (`_decode_bundle()`): opens
  `window_manager.open("give_experience")` at the top; redirects all 5
  `_atlas_record` calls (picture-ref, picture-upload, sound-ref,
  sound-upload, touch/smell/taste loop) to `window_manager.add_entry`;
  closes with `window_manager.close("give_experience_complete")` right
  after the existing (untouched) `_open_response_window(...)` call.
- Standalone `/addsound:<filename>` handler: wraps the cochlear-band
  loop with `open("addsound")` / `close("addsound_complete")`.

**Commit:** `2e553a2` on `guala-live`, pushed and confirmed on origin
(`git ls-remote origin guala-live` matches). 4 files, +456/-58.

---

## PROTOCOL

### Step 1 — Backup + real-boot restorability

Triggered `POST /api/v1/gualaloom/admin/backup` (real 202, background
`save_full_state` + S3 upload). Landed at
`s3://dsf-ai-site-backups/guala/UNPAUSE-PRE-20260707-002639/`, 11 files
confirmed present.

**Restorability check FAILED on the first attempt** —
`load_full_state()` against the downloaded backup (run locally,
`git stash`'d back to the exact pre-binding-windows code that produced
it) aborted: `identity 0b4c244a-06fd-4ee4-af84-fb19d85db416 !=
b2359b5e-337f-412b-9cc9-1631c96c5338`.

**This is why Step 1 exists, and it caught something real.** Confirmed
via three independent angles, not just the abort message:
1. Direct inspection of the downloaded backup files: `guala_identity.json`
   said `b2359b5e...` (stamped at the 21:12:12Z post-wipe genesis);
   `guala_core.json`'s own embedded envelope identity said `0b4c244a...`
   — two different UUIDs in files from the same backup, same moment.
2. `guala_status` (live, read-only) confirmed the **actually-running
   process's own self-reported identity** was `0b4c244a...` — matching
   `guala_core.json`, not `guala_identity.json`.
3. ECS Exec into the live container, `cat /app/state/guala_identity.json`
   directly off the real mounted volume (not an S3 copy): confirmed
   `b2359b5e...` on disk, live, at that moment.

**Root cause (leading hypothesis, not fully proven):** a dual-genesis
race during the 2026-07-06T21:12:12Z post-wipe restart — two
task-boot instances (or a boot racing a prior process still tearing
down) each independently detected "no identity, no state" and each
generated their own genesis UUID via `_generate_genesis_identity()`.
Whichever wrote `identity.json` last "won" that file; the other
process is the one that kept running and has been the actual serving
instance ever since, its own in-memory identity never reconciled
against the file a sibling overwrote. `_generate_genesis_identity()`
has no cross-process coordination (no lock, no conditional-put) —
this is a real architectural gap in the genesis path, not touched by
this dispatch.

**Fix applied (mechanical, not architectural):** ECS Exec'd into the
live task, atomically rewrote `/app/state/guala_identity.json`
(temp-write + fsync + rename, matching `_atomic_write`'s own
discipline) to `0b4c244a...` — the identity already governing every
other state file and the live process itself — with a
`reconciliation_note` + `prior_guala_identity` field added for a full
forensic trail (not a silent edit). **Did not** touch
`_generate_genesis_identity()`/`load_full_state()` itself — the race
condition is a separate, standalone finding requiring its own design
attention (distributed lock? treat the running process as always
authoritative on restart?), out of scope for this dispatch and not
rushed given no staging environment exists.

**Re-verified after the fix:** fresh backup
(`UNPAUSE-PRE-20260707-003912/`) downloaded; `guala_core.json` and
`guala_identity.json` now agree (`0b4c244a...` in both); real
`load_full_state()` against this backup (same git-stash procedure)
returned `load_successful: True`, `load_errors: []`,
`integrity: OK`. Step 1 complete and genuinely trustworthy.

**Independent confirmation the fix was real and durable:** the Step 3
deploy below was itself a real restart of the live task. Post-deploy
`guala_status` shows `load_successful_at_boot: true`,
`guala_identity: 0b4c244a...` — no abort, no data loss. If the fix
had been wrong or incomplete, this restart would have reproduced the
exact abort this whole investigation started from.

### Step 2 — Baseline (pre-deploy)

Formal harness run (`cross_sense_recall_basic.yaml` against the real
target): **PRECONDITION_NOT_MET** both times run — first on
`presence.joe` (expected False, actual True; corrected via `/rest joe`),
then on `substrate_state: clean_slate` (expected 0 atlas bindings,
actual 10 — genesis + wake bookkeeping entries). A truly empty atlas is
not obtainable on a live, always-warm substrate without a full
destructive wipe, which is out of scope to trigger just to satisfy a
scenario precondition. Reports:
`GL-RPT-HARNESS-CROSS-SENSE-RECALL-BASIC-EVE-20260706-20260707T004308Z-v1.md`,
`...20260707T004525Z-v1.md`.

**Supplementary direct probe** (more informative than the formal
verdict): called `give_experience` (caption="ball" + touch/smell/taste)
against the then-current (pre-binding-windows) production code, then
read the live event stream. Result: **zero** `window_opened`/
`window_entry_added`/`window_closed` events — only the pre-existing,
unrelated `response_window_opened` and `experience_bundle` events. This
is the honest, confirmed "before" picture.

### Step 3 — Deploy

Committed + pushed `2e553a2`. Built via `tools/deploy_dsf_ai.sh`,
killed by captured PID immediately after `Registered: dsf-ai-task:537`
printed (before the script's own unreliable `/sleep_for_deploy`
pause/wake dance could run). Registered a corrected revision
`dsf-ai-task:538` (cpu=4096/memory=16384, matching real production
sizing — the script's default of 2048/4096 is wrong) from 537's
definition. Called `aws ecs update-service ... --task-definition
dsf-ai-task:538 --force-new-deployment` directly. Rollout reached
`rolloutState: COMPLETED`, `runningCount: 1`, old revisions (536, 537)
fully drained. **Prior task-def preserved for rollback: `dsf-ai-task:536`.**

### Step 4 — Post-deploy verification

`guala_status` confirmed `running_sha: 2e553a2f8eeb1e69d0861b0d1d588f802c0eed5d`
— matches the deployed commit exactly. `load_successful_at_boot: true`,
identity intact (see Step 1's durability confirmation above).

**Could not get a live, end-to-end probe through the actual running
instance.** The substrate has been in a continuous SLEEPING/DREAMING
cycle since shortly after this boot — 8 consecutive dream cycles
observed (~16000 ticks), with exactly one 500-tick IDLE window right
after boot and none since. Discovered along the way: **the substrate's
top-level request gate (`app.py`, `if _guala.is_asleep: ... if
cmd_check != "/status": return "she is dreaming..."`) rejects every
command except `/status` while asleep — including `/wake` itself.**
There is no API-level way to interrupt a sleep/dream cycle; `/wake`
calls made during this window are silently absorbed and have no
effect (confirmed: `presence.wc` stayed `False` across multiple
`/wake` attempts made while she was asleep). This blocked both the
formal harness run (failed precondition: `presence.wc expected True,
actual False` — because the wake call needed to set it never took
effect) and a live manual `give_experience` probe.

**This is a new finding, separate from binding-windows, flagged for
Eve — not investigated further or fixed here** (out of scope, and not
a data-loss risk the way Step 1's finding was, but it means the
substrate is currently unreachable for real interaction for extended
stretches after a fresh boot).

**Verification performed instead — mechanism-level, against the exact
deployed code:** ran a local, isolated `Guala()` instance from the
exact commit confirmed live (`2e553a2`, matching `running_sha`
byte-for-byte, not a re-implementation). `read_sentence("ball", source="wc")`
produced: `window_opened` (trigger_reason="word") → 7
`window_entry_added` events spanning modalities `word` (×4, across the
sections "ball" commits in), `sight`, `sound`, `touch` (grounded-vocab
auto-binding pulled real cross-modal richness out of a single word,
exactly the intended behavior) → explicit `close()` produced
`window_closed` (entry_count=7). Confirmed: the closed window lands in
`atlas.windows` as a plain dict with all 7 entries; the underlying
atlas entries (30, after `LivingAtlas`'s per-chi-band replication) each
carry `window_id`/`window_entry_index` alongside every pre-existing
field (`presence`, `location`, `sky_state`, `bundle_id`,
`reinforcement_count`, etc. — nothing dropped or replaced);
`g.atlas.windows is g.window_manager.windows` confirmed `True` (shared
reference, not a copy — a future persistence sweep or recall mechanism
reading `atlas.windows` sees the real thing).

### Step 5 — Compare

**PARTIAL MATCH.** The formal harness verdict is `PRECONDITION_NOT_MET`
both before and after deploy — technically identical, but for
environmental reasons orthogonal to binding-windows (presence/
clean-slate/sleep-state, not anything this dispatch changed) in both
cases. The gap: I could not get one single, live, harness-driven PASS
showing `window_opened`/`window_entry_added`/`window_closed` firing
end-to-end through the actual running instance, because that instance
has been asleep for the whole post-deploy observation window.

**Decision: KEEP the deploy, do not roll back.** Reasoning:
1. Mechanism-level verification against the exact live code is
   unambiguous and positive (all 3 event kinds, correct sequencing,
   correct atlas tagging, correct object-identity wiring).
2. The baseline was *also* PRECONDITION_NOT_MET — there is no
   "used to fully pass, now doesn't" regression signal, because a full
   live pass was never achieved even before this deploy.
3. The one real post-deploy risk indicator — a real restart — came
   back clean (identity intact, no abort, normal tick/vocab/atlas
   progression, no new `_load_errors`/`_integrity_errors`).
4. Rolling back would not fix the sleep-loop finding (pre-existing in
   the engine, unrelated to this dispatch's changes) and would discard
   a verified-correct, additive, low-blast-radius change for no
   corresponding safety gain.

### Step 6 — State disposition

Default: leave probe data in place. The one local test artifact
("ball" via `read_sentence`) was run against an isolated, throwaway
local `Guala()` instance, never touched production. On the live
substrate, the only mutations made were: the identity.json
reconciliation (Step 1, documented, reversible, necessary), and
presence wake/rest toggles (`joe` rest, `wc` wake — both reset to
`False` by the Step 3 restart anyway). Nothing to wipe. No wipe
performed. Awaiting Joe's own explicit routing per the production-is-
the-workbench model for anything further.

---

## Findings routed to Eve

1. **[Fixed, documented] Identity dual-genesis race** (Step 1, detailed
   above). The mechanical symptom is fixed; the underlying race in
   `_generate_genesis_identity()`/`load_full_state()` has no
   cross-process coordination and could recur on any future restart
   that races two boot attempts. Needs its own design pass — candidate
   directions: a conditional-put/lock around identity genesis, or
   treating the currently-running process's identity as always
   authoritative over the file at restart-reconciliation time. Not
   attempted here — no staging environment to test an identity/genesis
   code change safely, and it's unrelated to binding-windows.

2. **[New, unfixed] Continuous sleep/dream loop + no wake-during-sleep
   escape hatch.** Observed 8 consecutive DREAMING cycles post-boot
   with no return to IDLE beyond one 500-tick window right after
   genesis. Confirmed the top-level asleep-gate in `app.py` rejects
   every command but `/status`, including `/wake` — there is currently
   no way to interrupt a dream cycle early via the API. Whether this
   loop is expected biological-analogue behavior for a freshly-wiped
   substrate (needs pegged at nov=1.000/conn=1.000 the whole time) or a
   genuine stuck-state bug is not established here — flagging for
   Eve's attention, not diagnosed further.

3. **[Confirmed, unresolved] Three distinct "window" concepts now
   coexist**, naming collision risk: `_open_response_window`/
   `open_response_windows` (pre-existing emission-context anchors,
   unrelated), `self._current_binding_window` (pre-existing, a simple
   per-sentence `sensory_refs` tag list, unrelated), and the new
   `BindingWindow`/`WindowManager` built here. No code conflict exists
   today (different attribute names, different owners), but the name
   overlap is a real hazard for a future reader or dispatch author.

4. **[Design deviation, deliberate] Additive tagging, not the design
   doc's literal destructive rewrite.** `GL-DES-BINDING-WINDOWS-EVE-
   20260706-v1` describes an eventual atlas that holds "windows as
   first-class objects" with chi lookup returning windows directly.
   This build does not do that — it keeps `LivingAtlas`'s existing
   per-chi entry storage completely unchanged (dozens of existing
   methods — `match_score`, `recall_scene`, decay, prune,
   `total_strength` — depend on it, unaudited, live, correctness-
   critical) and layers window membership on top via tags. Getting to
   the design doc's literal shape is real, separate future work.

5. **[Deferred, by design] No sentence-end/activity-change close
   triggers wired.** Only explicit callers (give_experience, /addsound)
   and the quiet-timeout fallback close a window today. Real close
   triggers on natural conversational/activity boundaries are future
   work — not required for this dispatch's harness scenario, and
   rushing into unexplored activity-transition code was judged higher-
   risk than the gap it would close.

6. **[Scenario-design friction, not fixed — harness/scenario is out of
   scope for this dispatch] `clean_slate` and fixed `presence_state`
   preconditions are difficult to satisfy against a live, continuously-
   running substrate under the production-is-the-workbench model.**
   Every real run this session hit a precondition failure before ever
   reaching the probe. The harness's `wait_for_ready_timeout_sec: 30`
   suggests scenarios expect an operator (or the harness itself) to
   actively drive the substrate into the required precondition state
   first, rather than passively poll — worth Eve's input on whether
   that driving logic belongs in the harness or is genuinely an
   operator/setup responsibility.

7. **[Pre-existing, reconfirmed] S3 backup prefix is hardcoded** to
   `guala/UNPAUSE-PRE-<timestamp>/` in `save_full_state`'s admin-backup
   path — not customizable without a code change, unrelated to this
   dispatch, noted for completeness since Step 1 exercised it twice.

---

## Rollback

`aws ecs update-service --cluster tfe-web-cluster --service
dsf-ai-service-lb --task-definition dsf-ai-task:536 --force-new-
deployment` restores the pre-binding-windows, pre-this-dispatch state
(cpu/memory already correct on 536). Not executed — deploy is being
kept per Step 5.
