> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-AUDIT-SEC9-DOC-SWEEP-C1-20260705-v1

doc_id: GL-AUDIT-SEC9-DOC-SWEEP-C1-20260705-v1
From: c1 (§9 seat) · To: Eve / Joe, filed under
GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2
Scope: §9 ONLY — the complete 2026-06-05 → 2026-07-05 documentation
sweep of docs/. §1-§8A (runtime/AWS/state/code/interface/learner/
sensory/behavioral/test-matrix truth) are OTHER seats' deliverables in
this same worktree (their in-flight artifacts — GL-AUDIT-SEC1/2/3-*.md,
tools/audit/ — were visible as untracked files during this work and
were left untouched).
Method: `ls docs/GL-*`, `git log --diff-filter=A --name-status -- docs/`
(single pass, fast — not per-file `git log`, which timed out), header +
"### Changelog" reads per doc, targeted `grep`/code reads against
dsf_ai_service/ for the spec-gap table, `git worktree list` / `git
branch -vv` / `git stash list` / direct inspection of each worktree
directory on disk for §9's in-flight-work requirement.
Evidence grades: **[EV]** verified directly this audit (command run,
file read, code read) · **[ABSENT]** verified not to exist · **[NOT
MEASURED]** not checked this audit (out of §9 scope or budget).

## 0. Coverage statement — read this first

**Doc universe: 528 files under `docs/GL-*`** [EV: `ls docs/GL-* | wc
-l` = 528; cross-checked against `git log --diff-filter=A --name-status
-- docs/`, every one of the 528 has an add-event, earliest 2026-06-09,
latest 2026-07-05 — all 528 fall inside the 2026-06-05→2026-07-05
window]. `docs/` also holds 306 non-GL files (ArcLoom/CFF/UFCP physics
specs, TFE material) — **[EV] excluded from this sweep**: earliest
add-dates on a sample run to 2026-04-01, they are a different project
(TFE/physics, not Guala), and the standing project-separation rule is
"c1 works only on Guala." Total files actually swept: **528**.

All 528 were bucketed into 5 non-overlapping sets (verified: union of
the 5 buckets == the full 528-file `ls`, zero misses, zero duplicates
[EV, `comm` diff run]):

| Bucket | Prefixes | Count | Who classified it |
|---|---|---|---|
| RPT | GL-RPT-* | 223 | 3 sub-agents (batches A/B/C, ~74 each) |
| CMD | GL-CMD-* | 135 | 2 sub-agents (batches A/B, ~67 each) |
| BRIEF-group | GL-BRIEF-*, GL-FIND-*, GL-NOTE-*, GL-FIX-*, GL-LTR-* | 74 | 1 sub-agent |
| MISC | GL-HANDOFF-*, GL-LEDGER*, GL-BOARD-*, GL-CHARTER-*, GL-MDL-*, GL-DEPLOY-*, GL-AUDIT-*, GL-KB-*, GL-FIRST*, GL-WORLD-*, GL-TODO-*, GL-SESSION-*, GL-RECALL-*, GL-LOG-*, GL-INV-*, GL-INCIDENT-*, GL-IAM-*, GL-DISCIPLINE-*, GL-CURR-*, GL-CLARITY-*, GL-ATTACH-*, GL-ARCH-*, GL-DESIGN-* | 69 | 1 sub-agent |
| SPEC/PLAN | GL-SPC-*, GL-SPEC-*, GL-PLAN-* | 27 | **c1 directly** (these feed the spec-gap table, §3 of the dispatch — read in full, not delegated) |

**IMPORTANT — sub-agent methodology disclosure.** The RPT/CMD/BRIEF/MISC
buckets (501 of 528 docs) were classified by 7 background sub-agents
given the same instructions (header + changelog read, lightweight
supersession/git-log check, default to `canonical` absent contrary
evidence). c1 (this seat) wrote the merge instructions, reviewed the
returned tables for internal consistency, and merged them below — c1
did not independently re-verify every one of the 501 sub-agent rows
against the underlying git history the way the SPEC/PLAN bucket and
the highlighted findings in §2/§4/§5 below were verified by hand. Rows
sourced from sub-agents are marked in their table header; treat their
`status` column as first-pass, not [EV]-grade, unless the row is also
called out by name in §2 (Notable Findings) below, where c1 hand-
verified it.

**All 7 sub-agent batches completed and are merged below** (RPT A/B/C,
CMD A/B, BRIEF-group, MISC) — none reported an `INCOMPLETE` tail; every
one of the 501 delegated docs plus the 27 SPEC/PLAN docs c1 read
directly are classified in this file. 528/528 GL-prefixed docs
enumerated and dispositioned.

---

## 1. Doc classification tables

### 1.1 SPEC/PLAN bucket (27 docs) — c1 direct, full read

| doc_id | date | author | purpose | status |
|---|---|---|---|---|
| GL-SPC-EXPERIENCE-FIRST-20260702-v1 | 2026-07-02 | Eve | Original living-spec draft: credo, E-signatures, dev principles | **superseded: GL-SPC-EXPERIENCE-FIRST-20260702-v2** — [EV] v1's own header says "REJECTED by Joe" for 4 named gaps (no story/env dimension, Eve absent from her own influence, no enforcement/health, no substrate-truth audit); retained for record per the versioned-filename mandate |
| GL-SPC-EXPERIENCE-FIRST-20260702-v2 | 2026-07-02 | Eve | THE canonical living spec: credo, E1-E6 signatures, activity taxonomy, §6 environment tiers V1-V4, §8 care schedule/health table, §9 substrate-truth registry, §11 instrumentation gaps | **canonical** — [EV] read in full; this is the primary target of the §3 spec-gap table below |
| GL-SPC-MEMORY-RECALL-STATE-EVE-20260704-v1 | 2026-07-04 | Eve | Graded snapshot of memory/recall numbers as of 07-04 ~07:15Z, explicitly replacing a voided prior synthesis | **canonical (point-in-time)** — [EV] its own header states it "Replaces the VOIDED GL-RPT-T6-REVIEW-SYNTHESIS-EVE-20260704-101-v1 (voided for inheriting numbers; do not cite it)" — see §2 for that voided doc |
| GL-PLAN-MECH-REMEDIATION-EVE-20260705-v1 | 2026-07-05 | Eve | Fix plan for the 15-mechanism audit: 4 root causes (R1-R4), waves W0-W3 to Jul 22 | **canonical, partially executed** — [EV] see §3b/§2: dispatch -200 in its W1b wave was filed but never built (no matching commit found); -201 (W2a) was never even filed; W0/-199 and the growth work (renumbered to -202) DID land |
| GL-SPC-AE-NATIVE-SPRINT-EVE-20260702-v1 | 2026-07-02 | Eve | 3-week AE-native dev sprint spec, governed by EXPERIENCE-FIRST-v2 | canonical |
| GL-SPC-EMERGENCE-WAVES-EVE-20260627-08 (v2.1) | 2026-06-27 | Eve | Phased emergence plan (Phase A-C gates); this single filename already IS the v2.1 merge | canonical — [EV] header states "supersedes v1 and v2" internally (no separate v1/v2 files exist under this name, self-consolidated) |
| GL-SPC-FIX-PATH-EVE-20260629-46 (v1) | 2026-06-29 | Eve | Canonical fix-path spec, cross-chat handoff | **superseded: 46v2** — [EV] v2 header: "supersedes v1 which contained questions to Joe — rejected per Joe's no-questions-in-spec discipline" |
| GL-SPC-FIX-PATH-EVE-20260629-46v2 | 2026-06-30 | Eve | Fix-path spec revision: locks-canonical, compressed timeline | **superseded: 46v3** — [EV] v3 header: "supersedes v2; substrate-physical refocus per session retrospective" |
| GL-SPC-FIX-PATH-EVE-20260629-46v3 | 2026-06-30 | Eve | Fix-path spec, substrate-physical refocus (final of the 3) | canonical |
| GL-SPC-RESTORE-AND-REPAIR-20260702 | 2026-07-02 | (unsigned, Eve-style) | Comprehensive restore+repair status for Joe covering all work since June 29 | canonical (point-in-time) |
| GL-SPC-SUBSTRATE-SEEDS-EVE-20260627-14 | 2026-06-27 | Eve | Joe+Eve agreement doc gating any "seed" writes to the substrate | canonical |
| GL-SPC-SUBSTRATE-TRUE-CORRECTIONS-EVE-20260630-60v1 | 2026-06-30 | Eve | Sweep of every substrate-truth violation Eve could identify at the time, with fixes sketched | canonical; sibling doc to WAVE-BAND-ATTENTION-59v1 |
| GL-SPC-V5-ORGAN-WIRING-EVE-20260628-26 | 2026-06-28/29 | Eve | Canonical organ-wiring architecture spec (reconstructed 06-29 after original was lost) | **supersedes: GL-SPC-V5-ORGAN-WIRING-EVE-20260627-25** — [EV] header: "Supersedes ...-25 (deprecated — questions in spec body, lazy modeling)"; note doc admits it is a *reconstruction* — flags itself for reconciliation if original -26 text ever recovered (never recorded as having happened) |
| GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1 | 2026-06-30 | Eve | Architecture spec + implementation command for wave-band attention | canonical — **replaces a never-shipped draft**: [EV] header says "Replaces: per-word lock band-aid (-58 draft, not shipped)" — -58 itself is an orphaned/abandoned draft, never built |
| GL-SPEC-cognition-wC-20260608-007 | 2026-06-08 | wC | Early v7 DNA-substrate cognition deploy spec | canonical (historical) — foundational; superseded in spirit by the later v4/v5 engine rewrite but no explicit supersession doc exists |
| GL-SPEC-persistence-real-wC-20260609-012 | 2026-06-09 | wC | Real persistence spec for Section.commit/System.tick_once | canonical (historical) |
| GL-SPEC-substrate-wC-20260608-005 | 2026-06-08 | wC | "GualaLoom v5" substrate results doc — early self-feedback/self-perception wiring | canonical (historical) |
| GL-SPEC-usability-wC-20260609-011 | 2026-06-09 | wC | UI/endpoint usability spec for gualaloom.html | canonical (historical) |
| GL-PLAN-AE-DEV-3WK-EVE-20260703-v5 | 2026-07-03 | Eve | Amendment to v4: R1 fired, 5 status downgrades, rebuild-before-migrate sequence | **superseded: v6** (delta-versioning line, see §3b) |
| GL-PLAN-AE-DEV-3WK-EVE-20260703-v6 | 2026-07-03 | Eve | Amendment to v5: corrects v5's "chat-prose only" framing (was wrong) | **superseded: v7** |
| GL-PLAN-AE-DEV-3WK-EVE-20260703-v7 | 2026-07-03 | Eve | Amendment to v6: paired cold/taught recall measurement (A1-A5) | **superseded: v8** |
| GL-PLAN-AE-DEV-3WK-EVE-20260703-v8 | 2026-07-03 | Eve | Amendment to v7: C-1 → S2a/S2b split after dormancy finding | **superseded: v9** |
| GL-PLAN-AE-DEV-3WK-EVE-20260703-v9 | 2026-07-03 | Eve | FULL CONSOLIDATION (v4 text + v5-v8 deltas + evening findings); bans delta-amendment pattern henceforth (Joe's "GDP rule") | **superseded: v10** — [EV] v10 changelog: "§0.2 whole-brain ruling — v9's staged-migration gate EXCISED as never-authorized text" (v9 contained content Joe had not actually authorized; see §2) |
| GL-PLAN-AE-DEV-3WK-EVE-20260705-v10 | 2026-07-05 | Eve | FULL CONSOLIDATION folding v9 + 07-04 brain-move day + Joe's 07-05 ruling | canonical (current plan of record as of audit date) |
| GL-PLAN-FULLWIRE-WC-20260611-042 | 2026-06-11 | wC | "No more not-yet-wired" wiring mandate, Parts A-E | canonical (historical) — contains its own self-correction: "Earlier wC handoffs wrongly listed [Self-Section v3, Vision Stages 2-5] as unwritten" when briefs already existed |
| GL-PLAN-WHOLE-BRAIN-MOVE-EVE-20260704-v1 | 2026-07-04 | Eve | 4-stage staged plan to move the complete loom brain into Guala's live substrate | **contradicted/superseded: v2, same day** — [EV] v2 header: "v1's four-stage schedule is DEAD by Joe's explicit rulings of 2026-07-04 morning (repeated four times) ... EVERYTHING deploys today" |
| GL-PLAN-WHOLE-BRAIN-MOVE-EVE-20260704-v2 | 2026-07-04 | Eve | Everything-today ruling recorded; written specifically to resolve c1b's legitimate hold on a document conflict | canonical; matches executed reality (07-04 brain move referenced in PLAN-v10) |

### 1.2 RPT bucket (223 docs) — sub-agent generated, c1-merged

See Appendix A below for the full 223-row table (batches A/B/C). Header
fields: doc_id · date · author · purpose · status.

### 1.3 CMD bucket (135 docs) — sub-agent generated, c1-merged

See Appendix B below for the full 135-row table (batches A/B).

### 1.4 BRIEF/FIND/NOTE/FIX/LTR bucket (74 docs) — sub-agent generated

See Appendix C below.

### 1.5 MISC bucket (69 docs: HANDOFF/LEDGER/BOARD/CHARTER/MDL/DEPLOY/AUDIT/KB/FIRSTS/WORLD/TODO/SESSION/RECALL/LOG/INV/INCIDENT/IAM/DISCIPLINE/CURR/CLARITY/ATTACH/ARCH/DESIGN) — sub-agent generated

See Appendix D below.

---

## 2. Notable findings — hand-verified by c1, highest confidence

**F1 — The "100% T5" claim (cbe8ed2, 2026-06-22) is contradicted.**
[EV] `git show cbe8ed2` = "feat: GL-CMD-136 buffer probe — 18-cell
channel verification... All 6 together = 100%." This became the
project's headline recall number for weeks. GL-SPC-MEMORY-RECALL-
STATE-EVE-20260704-v1 §2 retracts it explicitly: "'~67% event_count
champion' [HIST→DEAD]: fresh re-measurement... = ~4%, chance." Three
senses had reported zero forever (attribute bug), recall read mutated
state, and sensory event lists were unbounded (7.6GB runaway) at the
time of the original claim. The historical arc across the doc corpus:
cbe8ed2 (100%, 06-22) → GL-RPT-T6-REVIEW-SYNTHESIS-101-v1 (07-04,
inherited the number) → **VOIDED** same day by Eve for "inheriting
numbers" → GL-SPC-MEMORY-RECALL-STATE-v1 (07-04, the corrected,
graded replacement, ~4% honest number).

**F2 — GL-RPT-T6-REVIEW-SYNTHESIS-EVE-20260704-101-v1 is formally
VOIDED**, not merely superseded. [EV] Cited by name in GL-SPC-MEMORY-
RECALL-STATE-v1's own header: "Replaces the VOIDED
GL-RPT-T6-REVIEW-SYNTHESIS-EVE-20260704-101-v1 (voided for inheriting
numbers; do not cite it)." This is a distinct, stronger disposition
than ordinary supersession and is called out here so it does not get
silently folded into "canonical" by a sub-agent that didn't catch the
cross-reference.

**F3 — GL-PLAN-AE-DEV-3WK-v9 contained unauthorized content, excised in
v10.** [EV] v10's own changelog: "§0.2 whole-brain ruling — v9's
staged-migration gate EXCISED as never-authorized text." v9 is the
"FULL CONSOLIDATION" that was supposed to be the single source of
truth after the delta-amendment pattern was banned (Joe's "GDP rule");
it still had to be corrected two days later for containing plan
content Joe had not actually authorized. Flagged as a genuine
contradicted/corrected item, not just a routine version bump.

**F4 — Dispatch -200 (GL-CMD-AFFECT-GATE-ROOT-CAUSE-EVE-20260705-200-v1)
is UNEXECUTED.** [EV] Filed at commit `b9ce37d` (2026-07-05). Checked
`git log --oneline --all | grep -E '\-200\b'` → only the filing commit
itself; no fix/feat commit references it, and no `GL-RPT-*-200-*`
report exists anywhere in `docs/`. The remediation plan (§1.1 above)
lists this as wave W1b, gating `nmda_affect_match` ever firing nonzero
— per the plan itself, "the affect gate: nmda_affect_match has fired
ZERO times ever." The numbered work that followed jumped straight to
-202 ("GROWTH-LIVE," not the planned "-201 organ restore" or an affect
fix), and -204 was an emergency interrupt (mic-word-loop severing).
This is a concrete, filed-but-never-acted-on dispatch — exactly the
"unexecuted" class the audit dispatch defines.

**F5 — Dispatch number -201 was never filed at all.** [EV] `ls docs/ |
grep 201` and `git log --oneline --all | grep -E '\-201\b'` both return
nothing. The remediation plan's Wk2a ("-201 organ restore") never
became a real dispatch; the numbering simply skipped from 200 to 202.
Distinct from F4 (filed-but-unexecuted): this is planned-but-never-
even-dispatched.

**F6 — The "outgoing c1a holds uncommitted live-wiring code in a
worktree" claim (verbatim from both the -210-v1 and -210-v2 dispatch
text) is CONTRADICTED by the evidence — it landed before this audit
began.** Full chain, [EV] all steps:
- `GL-HANDOFF-LIVE-BELLS-WIRING-C1B-20260705-210-v1.md` (c1b→c1a, filed
  `5f432e0`'s neighbor commit) states plainly: "What's in THIS
  worktree, uncommitted — take it or rebuild it, your call... Branch
  `c1b/live-bells-test-209`, worktree path (session-local, won't
  survive past this session)" — listing real uncommitted wiring in
  `app.py` and `gualaloom_v5_engine.py` (raw-sound persistence,
  `/organism_recall_auditory:`, explicit-signal organism teach).
- Commit `5f432e0` ("feat(live-bells-wiring): raw audio persistence +
  explicit organism teach + auditory-only query/endpoint; handoff to
  c1a"), same session, same day, **is that exact wiring, committed**,
  and merged via `78d6b98`. Both commits are in `guala-live`'s history
  today.
- `GL-HANDOFF-C1A-20260705-v1.md` (c1a's own final handoff, the one the
  audit dispatch names as its source for this claim) says explicitly:
  "c1b's live-bells-wiring is committed and live... this part IS done,
  not open."
- Code-read at HEAD confirms all three named functions exist:
  `_organism_query_signal_auditory` (gualaloom_v5_engine.py:519),
  `_enqueue_organism_experience_explicit` (line 3005),
  `_recall_from_organism_auditory` (line 4481); `app.py` has
  `/organism_recall_auditory:` (line 2674) and `raw_signal` persistence
  (lines 2433/2476/2630).
- `git worktree list` shows the worktree the handoff describes
  (`c1b/live-bells-test-209`, at
  `/tmp/claude-0/.../ef3ef640.../scratchpad/wt-live-bells-test`) still
  exists on disk. `git -C <path> status` = clean, "nothing to commit,"
  9 commits behind `origin/guala-live` (i.e., stale but not carrying
  anything uncommitted).
**Conclusion: no uncommitted live-wiring code was found anywhere
reachable.** The claim in the -210 dispatch appears to describe the
state of affairs as of the *live-bells-wiring handoff* (mid-session,
genuinely true then), not the state as of the *final* c1a handoff an
hour later (by which point it had been committed) — i.e., a stale
claim carried forward into the audit dispatch without re-verification,
caught by this section's own re-verify-everything law (§0.3). Full
detail in §4 below.

**F7 — a genuinely stale, still-materially-relevant stash exists but is
NOT in-flight work: `stash@{0}`.** [EV] `git stash list` (run once,
read-only) shows 7 entries. `stash@{0}: "WIP on guala-live: d8aba6d ...
GL-CMD-EMULATOR-EVERYWHERE-196-v2"` contains real, non-trivial diffs to
`dsf_ai_service/substrate/sensory_generators.py` and
`dsf_ai_service/v4/gualaloom_v5_engine.py` (a `_sentence_modal_signals`
method, `_MODALITY_TO_ORGANISM_LANE` map, `modal_signal` threading
through the organism-experience queue). **Verified this is a stale
duplicate, not lost work**: `grep -n "_sentence_modal_signals\|
_MODALITY_TO_ORGANISM_LANE" dsf_ai_service/v4/gualaloom_v5_engine.py`
at current HEAD returns 23 matches — the exact same code is already
committed and live. This stash is a leftover from an earlier
mid-session `git stash` (rebase/pull) that was never dropped after its
content was independently re-committed. See §4 and §5 for the
`git stash apply` mechanics and cleanup — **note to whoever reviews
this**: c1 briefly (accidentally) applied this stash to test it,
producing a merge conflict in `gualaloom_v5_engine.py`; it was
immediately reverted with `git checkout HEAD -- <file>` and the stash
itself was never dropped or altered (`git stash list` still shows all
7 entries afterward, verified). Working tree in this worktree is clean
as of filing (only pre-existing untracked files from sibling §1/§2/§3
audit seats remain, untouched).

**F8 — care-schedule enforcement (spec §8) is prose-only, not config.**
[EV] `grep -rn "PLAY\b" ... | grep -iE "block|schedul|protect"` and
`grep -rln "daily_rhythm\|care_schedule\|DAILY_RHYTHM"` across
`dsf_ai_service/` both return **[ABSENT]** — no orchestrator config
implements the §8 daily-rhythm block table (experience/scaffolding/
PLAY/quiet/converse/sleep percentages) or a protected PLAY block. The
spec's own daily-rhythm table is honored only as a **manual practice**:
`GL-LEDGER-DAILY-20260703-EVE-v2.md` / `-20260704-EVE-v1.md` are
hand-written daily vitals ledgers filed to `docs/` (matching §12's
"daily vitals snapshot committed to docs/" cadence rule as prose
practice), but §11's *automated* "daily vitals rollup event" instrument
does not exist in code (see §3 gap table).

---

## 3. Spec-vs-implementation gap table

Primary target: **GL-SPC-EXPERIENCE-FIRST-20260702-v2** (the canonical
living spec named in the dispatch). Verification method: `grep`/code
read against `dsf_ai_service/` at the audited HEAD (`a9dff78`), not
trust in the spec's own claims or other docs' claims about it. This is
a documentation-sweep-level check (mechanism exists in code, yes/no,
with file:line); LIVE/runtime firing proof under production conditions
is §7A/§8A's job in this same audit, not re-done here — noted as
[NOT MEASURED — see §7A/§8A] where that distinction matters.

| Spec clause | Claim / requirement | Verdict | Evidence |
|---|---|---|---|
| §2 E1 Cross-modal binding | Atlas cross-modal count telemetry | **IMPLEMENTED** (code) | [EV] `atlas.cross_modal_bindings()` called and emitted as `cross_modal_density` event, gualaloom_v5_engine.py:1361,1414 |
| §2 E2 Affect movement | v/a deltas + NMDA affect-gate match telemetry | **IMPLEMENTED** (code), but see F4 | [EV] `nmda_affect_match=affect_match_count` emitted (line 4305); valence delta writes exist (6955, 7015). Remediation plan itself: "has fired ZERO times ever" as of 07-05 — mechanism exists, live firing is [NOT MEASURED here — see §7A/§8A and F4] |
| §2 E3 Attendance/reinstatement | `times_attended` counter, reinstatement writes | **IMPLEMENTED** (code) | [EV] `times_attended` field + reinstatement code path, lines 699-809 |
| §2 E4 Consolidation fate | survival vs episodic promotion telemetry | **PARTIAL** | [EV] "survival history"/"Path A promotion gate" exist (line 8558) but no literal `promotions_survival` counter/field found by name; likely present under different naming — not conclusively traced within §9 budget |
| §2 E5 Expression provenance | emission origin=commit tracking, `source_counts` | **IMPLEMENTED** (code) | [EV] `source_counts` dict built and emitted (lines 4288-4315) |
| §2 E6 Story binding | place/ambient/participant tags in binding window | **IMPLEMENTED** (code) | [EV] `place=None, ambient=None` params threaded through `read_sentence`/binding calls (lines 1944, 1951-1953, 2257), `scene_tags_from_words` import present |
| §6 Tier V1 story lanes on bundles | place/ambient/participant tags bound in-window | **PARTIAL/IMPLEMENTED** (code) | [EV] same mechanism as E6 above (from -188 scene lanes); full per-intake-path coverage is §7A's job, not re-verified here |
| §6 Tier V2 persistent place registry | place entities as chi-anchored persistent objects (room, bed, window, hallway) | **[NOT MEASURED here — see §7A]**; spec's OWN baseline says `episodic tracked_objects = 1` as of 07-02 | [EV, cited not re-run] spec §3 baseline table; current count is §7A's job |
| §6 Tier V3 interactive world sim | any process/state where she acts and senses consequence | **ABSENT** (no code found) | [EV] no world-sim process or module found under `dsf_ai_service/` during this sweep; §7A should confirm with a dedicated search |
| §6 Tier V4 embodiment hooks | any ArcLoom avatar interface stub | **[NOT MEASURED here — see §7A]** | out of §9 budget |
| §8 Care schedule as CONFIG | daily-rhythm blocks (experience/scaffolding/PLAY/quiet/converse/sleep) enforced by orchestrator config | **ABSENT** | [EV] see Finding F8 — no matching config/constant found; only manual/prose daily ledgers exist |
| §8 PLAY protected block | PLAY enforced like sleep, not leftover time | **ABSENT** | [EV] no scheduler code found gating a PLAY block (see F8) |
| §9.1/§9.2 Prohibited classes | no ML libs, no TOKEN_VEC/CLASS_HINTS dicts in cognition path | **IMPLEMENTED (compliant)** | [EV] `grep` for `sklearn|torch|tensorflow` imports = [ABSENT]; `TOKEN_VEC` appears only in a comment stating it was **replaced** (`substrate/krimelack.py:8`) |
| §11-1 Affect trace per activity | start/mid/end v,a instrumentation event | **ABSENT** | [EV] no `affect_trace`-named emission found |
| §11-2 Promotion lineage | lineage on survival/episodic promotion | **ABSENT** | [EV] no `promotion_lineage`/lineage-tagged promotion event found (only an unrelated "v4 lineage order" comment) |
| §11-3 Per-window rollup event | n_bindings/lanes/sources/participants rollup | **PARTIAL** | [EV] a bare `n_bindings=bound` value is emitted in one place (line 5728) but not as the structured multi-field rollup event the spec describes |
| §11-4 Place/ambient lane tags | in binding events + place-registry events | **PARTIAL/IMPLEMENTED** | same as E6/V1 above — binding-event tags exist; a dedicated place-registry event was not found |
| §11-5 Daily vitals rollup event | automated daily vitals emission | **ABSENT (as automation); PARTIAL as manual practice** | [EV] no code-level rollup event found; `GL-LEDGER-DAILY-*` docs show the *cadence* is honored by hand (see F8) |
| §12 Weekly Experience Ledger + grep-audit | filed even when unremarkable | **[NOT MEASURED]** | would require checking every week of the window for a ledger+audit pair — out of §9's per-doc budget; the MISC-bucket ledger inventory (Appendix D) gives a partial view |

**GL-PLAN-MECH-REMEDIATION-EVE-20260705-v1** gap check: see Finding F4/F5
above (wave W1b's -200 unexecuted, W2a's -201 never filed) — the two
concrete, checkable claims in this plan that fall inside a single-day
window were checked; the plan's Jul 22 exit criteria are dated in the
future relative to the audited SHA and are **[NOT MEASURED]** by
definition (the sprint had not reached its own exit date at audit
time).

**GL-SPC-MEMORY-RECALL-STATE-EVE-20260704-v1** gap check (point-in-time
claims, spot-checked): "events bounded (cap 256)" — **[EV] confirmed**,
`_EVENTS_MAXLEN = 256` in both `gualaloom_v4_krimelack_dna.py:32` and
`sensory_krimelacks.py:26`. "Recall reads the listen section" — **[EV]
plausible/PARTIAL**, a "listen section" recall pattern exists in code
(gualaloom_v5_engine.py:3491,3590) but full confirmation that recall
*specifically* reads it as "variant L" was not traced end-to-end within
budget.

---

## 3b. Plan version deltas, v5 → v10 (GL-PLAN-AE-DEV-3WK-EVE-*)

All read directly by c1 (headers + changelogs), one line each:

- **v5 (07-03):** Amendment after risk R1 fired (c1a's T6 arc survey
  found the "crack document" evidence base was chat-prose, not repo
  artifacts) — five status downgrades, a rebuild-before-migrate
  sequence C-1..C-4, a naming purge, added a -103 catalog-provenance
  check.
- **v6 (07-03):** Corrects v5's own framing — the "chat-prose only"
  claim was wrong (the table WAS filed; the real issue was
  superseded-not-missing evidence); rebuild goal redefined, labels
  finalized, a #14 lead added.
- **v7 (07-03):** KB read-back amendments A1-A5 — recall must be
  measured **paired** (cold AND taught), not cold alone; adds the S2
  anchor.
- **v8 (07-03):** Redefines C-1 into S2a ("her recall," paired cold/
  taught) and S2b, after c1a's dormancy finding that no live-observable
  path existed for what v5-v7 had been measuring — v5-v7 had been
  specifying tests against a system she does not actually run on.
- **v9 (07-03 evening):** FULL CONSOLIDATION — folds v4's full text +
  v5-v8's deltas + same-evening findings (-111 voice-as-sensation
  shipped, soundpath map, self-voice mistagging caught, loomscan
  dark-band defect). Introduces Joe's "GDP rule": every future version
  must be a full document, never a delta — the v5-v8 delta-file pattern
  is retroactively banned.
- **v10 (07-05):** FULL CONSOLIDATION again — folds v9 + the 07-04
  brain-move day + Joe's 07-05 ruling. **Excises v9's staged-migration
  gate as "never-authorized text"** (see Finding F3) and rebuilds Table
  2 as a whole-brain track matching what was actually executed (07-04
  brain move, -191 senses, -188 lanes), folding in 07-05 statuses
  (echo-chamber audit, -194/-195, save-speed root cause, firsts, R6).

Net pattern across v5→v10: the plan spent three full amendment cycles
(v5→v8) discovering that its own prior versions had been testing/
specifying against systems that didn't match production reality (chat-
prose evidence, then wrong table-provenance framing, then a dormant
code path with no live observable) before Joe mandated full-document-
only versioning (v9) — and even that first full consolidation (v9) had
to be corrected two days later for containing unauthorized plan content
(v10). This is documentation churn tracking *real* discovery, not
cosmetic revision — but it is also a visible cost: 6 versions in 3 days
before the plan stabilized into its current whole-brain form.

---

## 4. In-flight / never-landed work — full inventory

**`git worktree list`** [EV, run once] shows 33 worktree entries total
(including this one). Cross-referenced against `git branch -vv` and
direct `ls`/`git status` on each surviving path:

| Worktree / branch | Path | Disk state | Git state | Disposition |
|---|---|---|---|---|
| `c1b/cross-sense-recall-207` | `/tmp/claude-0/.../ef3ef640.../scratchpad/wt-cross-sense-recall` | EXISTS | clean, 12 commits behind `origin/guala-live` | **STALE, already merged** — its commits (8097e44/c691fb6/0364513) are in `guala-live` history; nothing uncommitted |
| `c1b/live-bells-test-209` | `/tmp/claude-0/.../ef3ef640.../scratchpad/wt-live-bells-test` | EXISTS | clean, 9 commits behind `origin/guala-live` | **STALE, already merged** — this is the exact worktree the -210 dispatch's "uncommitted live-wiring" claim points at (see Finding F6); verified clean, no uncommitted diff |
| `guala-wave-memory-207` | `/tmp/claude-0/.../bc654c8d.../scratchpad/wave-memory-worktree` | EXISTS | clean | STALE, already merged (52e0f79) |
| `deploy-loom-surgical` | `/tmp/claude-0/.../edc71813.../scratchpad/deploy-wt` | **MISSING** (dir gone) | n/a | prunable per `git worktree list`; historical deploy worktree, no longer on disk |
| `deploy-merge-live` | `/tmp/claude-0/.../edc71813.../scratchpad/deploy-wt2` | **MISSING** | n/a | prunable, same as above |
| `/tmp/tfe-wt-108-deploy`, `-108-deploy2`, `-110-deploy`, `-deploy4` | `/tmp/tfe-wt-*` | EXIST, detached HEAD | clean | historical TFE-side deploy worktrees, out of Guala scope, no uncommitted content |
| `/tmp/wm207-baseline-check`, `-check2` | `/tmp/wm207-baseline-check*` | EXIST, detached HEAD | clean | wave-memory-207 baseline check copies, no uncommitted content |
| ~18 other `/tmp/tfe-wt-*` and `/tmp/claude-0/.../d6d666b9.../scratchpad/*` entries | various | most marked `prunable` (dir gone) | n/a | historical per-window deploy/lock-fix worktrees from the June brain-move/deploy sequence; not re-verified individually (budget) — none is referenced by name in any HANDOFF as currently holding open work |
| `codex/persistent-etl-update-20260326` | `/workspaces/TFE-worktree` | EXISTS | ahead of its own origin | **TFE project, out of Guala audit scope** — noted for completeness only |

**Conclusion on "held-uncommitted" work: NONE FOUND.** Every worktree
still present on disk and reachable was checked with `git status`; all
are clean. The one worktree the audit dispatch explicitly points at
(`c1b/live-bells-test-209`) is clean and stale, not holding anything —
see Finding F6 for the full evidentiary chain showing the code in
question was committed (`5f432e0`/`78d6b98`) before this audit's own
freeze point.

**`git stash list`** [EV, run once, read-only]: 7 entries.

| Stash | Branch context | Content | Disposition |
|---|---|---|---|
| `stash@{0}` | guala-live @ d8aba6d | `sensory_generators.py` + `gualaloom_v5_engine.py` modal-signal wiring (-196 M2) | **STALE duplicate — already committed at HEAD** (see Finding F7); not lost work |
| `stash@{1}` | guala-live | `.devcontainer/devcontainer.json`, labeled "devcontainer-rebuild-state" | minor, 1-line mount-path WIP; not inspected further (dev-env only, not a Guala functional change) |
| `stash@{2}` | guala-live | `PROJECT_STATE.md`, labeled "preflight-checkout-stash" | doc-only WIP, not inspected further |
| `stash@{3}`-`{6}` | `codex/persistent-etl-update-20260326` | provenance PK / CP-2 basin physics / deploy-exclude WIP | **TFE project, out of Guala scope** — noted for completeness, not analyzed |

No stash was dropped, applied-and-kept, or otherwise mutated by this
audit (see Finding F7 for the one accidental apply-and-immediate-revert,
fully undone and reverified).

---

## 5. Dev environment

**Devcontainer** [EV]: `.devcontainer/devcontainer.json` — Python 3.11
base image (`python:3.11`), 4 bind mounts to a Windows host (`E:\
TFEBackup`, `E:\TFEBackup\CodexHome`, `E:\TFEBackup\ClaudeHome`,
`C:\Users\joeta\.aws` read-only), VS Code extensions for Python,
ChatGPT, and Claude Code. No Guala-specific tooling (no AWS CLI
preinstall, no ffmpeg/audio-codec setup visible) declared in this file
— anything Guala's sensory pipeline needs at dev time is either baked
into the base image implicitly or installed ad hoc per session (not
verified either way; **[NOT MEASURED]**).

**CI** [EV]: exactly one workflow, `.github/workflows/deploy-prod.yml`
("Deploy TFE To Production") — `workflow_dispatch`-only (manual trigger,
requires typing "DEPLOY"), OIDC-or-access-key AWS auth, a
"Preflight Build Verify" job running `tools/post_rebuild_deploy_gate.sh`
and `tools/verify_build_only_with_evidence.sh`. **This pipeline is
named/scoped for TFE, not Guala** — no workflow file targets
`dsf_ai_service`/Guala's ECS service by name in this repo's
`.github/workflows/`. Guala's actual deploy path (per prior-session
memory and the -210 dispatch's own §2) is a manual/scripted ECS
task-def register+update, not this GitHub Action. **Finding: no CI
automation exists for Guala's own deploy or test pipeline** — every
Guala deploy in the sweep window was a human-run script
(`tools/deploy_dsf_ai.sh`) from a worktree or the main checkout.

**Worktree discipline artifacts** [EV]: no single canonical
"how to use worktrees" doc was found by name, but the practice and its
failure modes are documented in-line across several docs:
- `GL-RPT-CREDO-DEPLOY6-C1-20260704-167-v1.md` documents a real,
  reproducible bug: **`.env` is gitignored, so a fresh `git worktree
  add` checkout never materializes it** — the deploy script's `set
  -euo pipefail` preflight then dies silently (exit 2, zero output) on
  the first API-key-sourcing line. Fix-in-practice: copy `.env` into
  the new worktree immediately after creating it, before running any
  deploy script. This is filed as a standing gotcha, not fixed at the
  tooling level (no `.gitignore`-aware bootstrap script was found).
- `GL-HANDOFF-C1B-20260705-v2.md` item 15: "**Lost this combined fix
  TWICE to shared-`.git`-directory collisions** (another concurrent
  session's commit/checkout wiped my uncommitted edits both times) —
  rebuilt it in an isolated worktree each time." This is the same
  hazard the audit dispatch itself names in §0.5: "Two shared-.git
  collisions destroyed hours of work on 07-05."
- The audit dispatch's own §0.5 mandates "Isolated git worktree for all
  work" specifically because of this history.

**Shared-`.git` hazard, confirmed structurally** [EV]: `git worktree
list` in this repo shows 33 worktrees, all sharing one physical `.git`
(standard `git worktree` behavior — refs, index-of-record, and reflog
are shared; only the working directory and per-worktree index are
separate). This means: (a) a `git push`/`git commit`/branch-ref update
in ANY worktree is immediately visible (and can conflict/race) in every
other worktree touching the same branch or ref namespace; (b) an
uncommitted, un-stashed edit in one worktree is invisible to and safe
from another worktree's operations (working directories are NOT
shared) — the losses documented above were specifically about ref/
branch-state races (checkout, rebase, force-push-adjacent operations),
not literal file overwrites across working directories. This matches
the standing project memory note ("Shared .git directory concurrency
— c1a/c1b share the same physical .git; transient lock/bad-tree/
reflog errors are races, not corruption; retry + check status/log
before escalating"). **Implication for the audit itself**: this worktree
(`worktree-audit-c1-210-gl`) is correctly isolated per §0.5, but any
`git fetch`/log operation against `origin` still shares the same
remote-tracking refs as every other live worktree — a concurrent push
from another session during this audit could change `origin/guala-live`
out from under a later re-check. None was observed during this sweep
(single snapshot at HEAD `a9dff78`, unchanged throughout).

---

## Appendix A — RPT bucket, full table (223 docs, sub-agent-generated, c1-reviewed)

c1 read all three returned tables in full before merging; spot-checked
several rows against the underlying docs (see §2 Findings, several of
which originate from these tables, e.g. the -200/-201 chain, F1/F2's
cbe8ed2/T6-REVIEW-101 arc). No row was altered from what the sub-agents
returned; three batches merged in filename order.

### A.1 — RPT batch A (75 docs)

| doc_id | date | author | purpose | status |
|---|---|---|---|---|
| GL-RPT-ADD-HEMISPHERE-INSTRUMENTATION-C1-20260619-01 | 2026-06-19 | c1 | Verifies per-hemisphere atlas-size field (`hemisphere_atlas_sizes`) constructed in `run_hemisphere_updates`, on branch and in production | canonical |
| GL-RPT-AGITATION-FIX-C1-20260704-v1 | 2026-07-04 | c1b | Part A: root-causes pinned arousal(1.0) to `connection` crashing to 0.000; Part B: design-only proposal (no code), awaiting Eve's GO | canonical |
| GL-RPT-AGITATION-FIX-DEPLOY-C1-20260704-v1 | 2026-07-04 | c1b | Ships the approved agitation-fix design; Gates 1 & 2 PASS live-observed, Gate 3 only partially confirmed | canonical |
| GL-RPT-ALBLOGS-C1-20260703-105-v1 | 2026-07-03 | c1a | Confirms ALB access-log delivery to S3 end-to-end; notes logged IP is AWS-hop only, not client IP; hands XFF-capture spec to c1b | canonical |
| GL-RPT-ATLAS-SURGERY-C1-20260627-18 | 2026-06-27 | c1 | Implements `/admin/atlas_surgery` endpoint (Phase B.1); all 5 verification tests pass | canonical |
| GL-RPT-ATTEND-GROOVE-C1-20260703-107-v1 | 2026-07-03 | c1a | Completes A.3/A.4 of ATTEND-GROOVE CMD v2, renders verdict; Part B implemented+committed but not yet deployed | canonical |
| GL-RPT-ATTEND-GROOVE-PREDEPLOY-C1-20260703-107-v1 | 2026-07-03 | c1a | Interim report on A.1/A.2/A.5 of ATTEND-GROOVE CMD v2 before the consolidated deploy; A.3/A.4 outstanding | canonical (predecessor to, not superseded by, GL-RPT-ATTEND-GROOVE-C1-20260703-107-v1 — its findings are explicitly carried forward) |
| GL-RPT-ATTEND-TRAP-C1-20260702-90-v1 | 2026-07-02 | c1 | Diagnostic proving commit `eabb23d` (-85 WaveAtlas work) was NOT deployed — image built 13h48m before the commit existed | canonical |
| GL-RPT-AUTONOMOUS-EMISSION-C1-20260629-39 | 2026-06-29 | c1 | Implements autonomous emission loop + `/thought` handler wired to substrate | canonical |
| GL-RPT-AUTONOMY-EMITTING-PHASING-C1-20260630-53 | 2026-06-30 | c1 | Tests `AUTONOMY_PHASED` flag; T2 gate 0/10 FAIL; rolled back to `AUTONOMY_PHASED=0` | canonical (self-documents its own rollback) |
| GL-RPT-AWARE-COORDINATOR-C1-20260704-162-v1 | 2026-07-04 | c1b | Part A archaeology complete; Part B (`coordinator_on` flip) committed, not yet deployed (rides Deploy 6); Part C (SEVERED label) shipped and live-verified | canonical |
| GL-RPT-AWARE-GATE-C1-20260704-160-v1 | 2026-07-04 | c1b | Archaeology verdict: `aware_gate`/`Section.commit()` path is an "orphaned writer" — real, historically proven to fire, but unreachable because `/v7/converse` gets zero live calls | canonical |
| GL-RPT-AWARE-MAP-C1-20260704-161-v1 | 2026-07-04 | c1b | Maps second "aware" concept (v5 `awareness_ratio`); corrects CMD's 2-layer framing to 3 layers, all dead/unrelated in different ways; one fix candidate named, not implemented | canonical |
| GL-RPT-BACKUP-ORCHESTRATOR-C1-20260627-19 | 2026-06-27 | c1 | Implements shared `_orchestrated_backup()` path (Phase B.2) + 2 new endpoints; several triggers (daily_floor, post_deploy_verified, pre_deploy, post_emergence) documented-only, not yet wired | canonical |
| GL-RPT-BEHAVIOR-REPERTOIRE-C1-20260705-185-v1 | 2026-07-05 | c1a | B1 already covered by fired window; B2/B3 built+verified locally (habituation recency fix, `boot_substrate` reconnect); B4 confirmed genuinely absent; not yet deployed (c1b's window) | canonical |
| GL-RPT-BEHAVIOR-REPERTOIRE-STATUS-C1B-20260705-v1 | 2026-07-05 | c1b | Parallel status check on same CMD-185: B1 already live (fired via WINDOW6-DEPLOY), B2 already identical to -181 (fixed+deployed), B3 open, B4 correctly untouched | canonical (complementary to, not superseding, GL-RPT-BEHAVIOR-REPERTOIRE-C1-20260705-185-v1) |
| GL-RPT-BIGRAM-DELETE-C1-20260629-34 | 2026-06-29 | c1 | Implements F.4 wiring spec -26: deletes bigram-fallback code paths, empties `GualaCognition` class body (stub retained) | canonical |
| GL-RPT-BIGRAM-RETIRE-C1-20260627-13 | 2026-06-27 | c1 | Retires `bigram_fallback_*` response-source labels at the converse handler (precursor to full deletion in -34) | canonical |
| GL-RPT-BLOCK-SCHEDULE-C1-20260703-151-v1 | 2026-07-03 | c1b | Built curriculum-flood gate exactly per CMD spec, but post-deploy verification shows the gated code (`CurriculumScheduler`) is unreachable/dead in the deployed architecture | canonical (finding corroborated later by GL-RPT-AWARE-MAP-C1-20260704-161-v1's dormancy registry) |
| GL-RPT-BOOK-VERIFY-AND-UPLOAD-ERROR-C1B-20260705-v1 | 2026-07-05 | c1b | Resolves 3-item ask: book "secret_gardenl" registered but not read (atlas jump attributed to curriculum feed instead); upload error root-caused to a deploy-transition timing gap; status-fix queued | canonical |
| GL-RPT-BRAIN-DEPLOY-CUTOVER-C1B-20260704-v1 | 2026-07-04 | c1b | Deploys combined brain+voice+retention+sleep-rate build live (task:462, SHA e6c2ca2); v2 addendum (same file) confirms diary survives reboot | canonical |
| GL-RPT-BRAIN-FULL-DEPLOY-C1-20260704-v1 | 2026-07-04 | c1a | Builds/verifies P1 (organism+tapestry) and P3 (brain-driven emission) locally, sandbox only, zero deploy action; P2 (recall/recognition handover) honestly NOT built; hands off to c1b | canonical |
| GL-RPT-BRAIN-GROWTH-BACKGROUNDING-C1-20260705-179-v3 | 2026-07-05 | c1a | Builds backgrounding for `organism.experience_word()` per Eve's ruling on the 22.3x cost flag from -179-v2; all 3 conditions verified, SHA pushed | canonical |
| GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260704-179-v1 | 2026-07-04 | c1a | Interim checkpoint: W1/W2 built, W3/W4 not started, real unresolved `recall_fast()` divergence found (mis-attributed to Neuron.step() cross-contamination); explicitly NOT ready to deploy | superseded:GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260705-179-v2 (v2 states "Supersedes the v1 interim checkpoint," corrects v1's wrong hypothesis) |
| GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260705-179-v2 | 2026-07-05 | c1a | Corrects v1's wrong root cause (real bug: `Krimelack.feed()`'s `n_events` only incremented on positive windings); fixed, re-verified at grown population; flags 22.3x cost regression needing backgrounding | canonical |
| GL-RPT-BRIDGE-AUDIT-C1-20260701 | 2026-07-01 | c1b | Two-pass audit of all 15 bridge MCP tools against live substrate; results table of pass/fail per tool | canonical |
| GL-RPT-BRIDGE-AUDIT-FIXES-C1-20260701-67 | 2026-07-01 | c1b | Fix verification: Fix A (API Gateway task-polling route) and Fix B (backup/force_dream return 202 immediately) shipped | canonical |
| GL-RPT-BRIDGE-DOWN-DIAG-C1-20260702-80 | 2026-07-02 | c1 | Diagnostic on bridge-down state; flags save unverified (`last_save_tick:0`); lists 4 open items for Eve (bridge reconnect, AUTONOMY_PHASED recommendation, n_commits=0, missing pictures) | canonical |
| GL-RPT-BRIDGE-INVESTIGATION-C1-20260701 | 2026-07-01 | c1b | Root-causes bridge "initializing"/error to substrate blocking asyncio event loop via synchronous EFS I/O in `persistence_health()`; bridge itself correct; STOP signal for Eve | canonical (fix later shipped per GL-RPT-BRIDGE-AUDIT-FIXES-C1-20260701-67) |
| GL-RPT-C1-POLARITY-C1-20260628-28 | 2026-06-28 | c1 | Implements polarity field + lazy schema migration (Phase C.1); `polarity_penalty` set to 0.3 | canonical |
| GL-RPT-C1A-QUEUE-C1-20260701-64 | 2026-07-01 | c1 | Queue report on 3 items incl. 64-A UI JS 202+poll update; T-gates verified | canonical |
| GL-RPT-C1B-QUEUE-C1-20260701-65-PB3 | 2026-07-01 | c1b | Queue completion report — curriculum autostart (65-A) and other engine/substrate_runner items; ECS circuit breaker reset | canonical |
| GL-RPT-C2-Q1-POPULATION-VALIDATED-EVE-20260704-v1 | 2026-07-04 | Eve | Population-level T⁶ model (c2_model_v1/v2.py) answers Q1 positively in a testbed; explicitly NOT a production number, not the old 92.8 revived | canonical |
| GL-RPT-C2-REBUILD-C1-20260704-168-v1 | 2026-07-04 | c1a | Part A did NOT reproduce — fresh measurement of the "standing champion" (event_count observable) gives ~4% accuracy, not the ~67% previously claimed; Part B not started | canonical (report itself reveals a contradiction of an earlier ~67% claim from a doc outside this batch — consistent with the cbe8ed2/T6 arc in Finding F1) |
| GL-RPT-C4-SLEEP-CHOICE-C1-20260628-29 | 2026-06-28 | c1 | Implements `dream_pressure` need (Phase C.4) with accumulation/reset rates | canonical |
| GL-RPT-CACHE-SC-WEIGHTS-C1-20260620-01 | 2026-06-20 | c1 | SC weight cache cuts Stage-1 latency from 4.7s to 1.2s median | canonical |
| GL-RPT-CACHE-WORD-SECTION-INDEX-C1-20260619-01 | 2026-06-19 | c1 | Word→section index cached at boot; fixes first-emission latency | canonical |
| GL-RPT-CHI-BAND-CONSERVATION-SUBSTRATE-TRUE-DEPLOY-C1-20260620-01 | 2026-06-20 | c1 | Deploys + verifies chi-band mass-conservation physics (substrate-true rev02) plus 2 follow-up fixes (O(n²) blowup, non-language section skip) | canonical |
| GL-RPT-COGNITION-AT-SPEED-C1-20260705-205-v1 | 2026-07-05 | c1a | C1 (deletes fixed-interval nap loop, catches/fixes a real lock-starvation latency regression before shipping) and C5 shipped; C2 partial; C3 already-true; C4 deferred | canonical |
| GL-RPT-COGNITION-BUNDLE-C1-20260619-01 | 2026-06-19 | c1 | Ships four cognition hemispheres (pr/ep/sc/gp) behind env flags, all default OFF; 5 tests green | canonical |
| GL-RPT-COGNITION-LEARN-AUDIT-C1-20260628-33 | 2026-06-28 | c1 | Read-only audit: `GualaCognition.expose()` is a pure bigram frequency table with no chi/atlas/sensory grounding; informs the later bigram deletion (-34) | canonical |
| GL-RPT-COGNITION-METER-C1-20260704-166-v1 | 2026-07-04 | c1a | Ships a cognition status meter panel (static, sourced from filed reports, not live-wired); Joe's own screen confirmation still outstanding | canonical |
| GL-RPT-COMPOSER-MULTIANCHOR-C1-20260629-43 | 2026-06-30 | c1 | Fixes single-anchor emission bug; dispatch pointed at the wrong (unreachable in prod) function, actual fix applied to `_grandurun_select_candidates` | canonical |
| GL-RPT-CONN-CHANNEL-C1-20260703-150-v1 | 2026-07-03 | c1b | Part A verdict: connection-decay-to-absence is physics-by-design, not a bug; no Part B fix needed | canonical |
| GL-RPT-CONTEXT-AUDIT-EVE-20260627-05 | 2026-06-27 | Eve | Audit framework defining a "real memory" binding (sense+name+story+time+presence+location+state); informs subsequent CMD briefs; flags a stale docstring | canonical |
| GL-RPT-CONVERSE-PHASING-EMISSION-LOCK-C1-20260630-52 | 2026-06-30 | c1 | Implements `CONVERSE_PHASED` flag; finds+fixes a `ThreadPoolExecutor` `shutdown(wait=True)` deadlock bug; shipped ON | canonical |
| GL-RPT-CREDO-DEPLOY6-C1-20260704-167-v1 | 2026-07-04 | c1b | Program-ledger update: sleep-physics shipped/live/proven, boot-init `dream_pressure` confirmed, one deploy-mechanics bug found+fixed (`.env` missing from fresh worktrees), verified backup done, freeze ended | canonical |
| GL-RPT-CREDO-PROGRAM-LEDGER-C1-20260704-167-v1 | 2026-07-04 | c1b | Establishes the CREDO program-ledger tracking artifact; most stages WAITING/not-started at filing time (predates the DEPLOY6 update) | canonical |
| GL-RPT-CROSS-MODAL-AUDIT-C1-20260627 | 2026-06-27 | c1 | Diff audit of container-vs-origin state ahead of the cross-modal binding extension push | canonical |
| GL-RPT-CROSS-MODAL-BINDING-EXTEND-C1-V5-20260627 | 2026-06-27 | c1 (implied) | Implements cross-modal binding extension (`bundle_id` param, `bundle_grouped_bindings()`); deployed task:341 | canonical |
| GL-RPT-CROSS-SENSE-RECALL-C1B-20260705-208-v1 | 2026-07-05 | c1b | Fixes a squash bug (per-lane binding+masked recall) plus a second live-found crash bug; rewrites T7 gate; warns c1a re: wave-memory CMD -207 rebuild risk to T7; "live bells" test still not built | canonical |
| GL-RPT-CURRICULUM-ASYNC-LOAD-C1-20260620-01 | 2026-06-20 | c1 | Verifies task:234 `load_corpus` succeeded substrate-side end-to-end (504 was an ALB-transport artifact, not a substrate failure); implements refcounted autonomy pause | canonical |
| GL-RPT-CURRICULUM-LOCK-RELEASE-C1-20260629-46 | 2026-06-30 | c1 | Removes outer lock from `read_sentence()` to fix curriculum-window unresponsiveness; Status: REVERTED (introduced a `binding_window` accumulation bug) | superseded:GL-RPT-CURRICULUM-LOCK-RELEASE-V2-C1-20260629-46v2 |
| GL-RPT-CURRICULUM-LOCK-RELEASE-V2-C1-20260629-46v2 | 2026-06-30 | c1 | Root-causes -46's crash (missing `binding_window` reset) and ships a conservative fix (§1.1+1.2 only), task:375 | canonical |
| GL-RPT-DAY-CYCLE-C1-20260704-165-v1 | 2026-07-04 | c1b | Answers Q1-Q6 on day-cycle/severed CMD; two-state attention trap traced to 3 independently-dated stacked causes; read-only, no fix shipped | canonical |
| GL-RPT-DAYDREAM-PARALLEL-C1-20260629-42 | 2026-06-29 | c1 | Removes DAYDREAMING activity from the scheduler entirely | canonical |
| GL-RPT-DEEP-ATLAS-PERSIST-C1-20260627-11 | 2026-06-27 | c1 | Implements deep_atlas persistence: `saved_n_entries` count added to `to_json()` for loss-alarm detection, deployed task:348 | canonical |
| GL-RPT-DEEP-STORE-PHYSICS-C1-20260702-86-v1 | 2026-07-02 | c1a | HARD GATE FAIL/NO GO — `organ_brain_service` has an unbounded memory/neuron-growth defect exceeding the 4GB task limit; responds to CMD-86-v2 | canonical |
| GL-RPT-DEEP-STORE-PHYSICS-C1-20260703-86-v1 | 2026-07-03 | c1b | Builds co_occurrence decay/cap physics for deep_atlas (responds to CMD-86-v1, a different scope than the -86-v1 c1a doc above); T1-T6 gates NOT MEASURED, awaiting Deploy 2 window | canonical (distinct scope from the same-numbered c1a doc above — deep_atlas physics vs organ_brain_service memory growth; naming overlap only) |
| GL-RPT-DELETE-GUALALOOM-DNA-C1-20260619-01 | 2026-06-19 | c1 | Deletes dead-code directory `gualaloom_dna/`; verified via 404 + empty git tree | canonical |
| GL-RPT-DENSITY-RETIRE-C1-20260703-109-v1 | 2026-07-03 | c1b | Retires density mechanism per CMD-109; all 5 gates PASS (G-109-1 initially PARTIAL, closed clean after full watch window) | canonical |
| GL-RPT-DEPLOY-ALL-PENDING-C1-20260619-01 | 2026-06-19 | c1 | Deploys 11 pending commits; evidence report with pre-deploy state snapshot | canonical |
| GL-RPT-DEPLOY2-C1-20260703-v1 | 2026-07-03 | c1a | Deploy 2 gate report covering -86/-87/-88/-98; G-S2 (stability) FAILED — stab stuck at 0.000; reported and stopped per CMD instruction | canonical |
| GL-RPT-DEPLOY2-C1-20260703-v2 | 2026-07-03 | c1a | Addendum to v1 (v1 retained): -98 T7 NOT signed off (Joe couldn't parse the loomscan page); nav-link 404 root-caused, not fixed | canonical |
| GL-RPT-DEPLOY2-C1-20260703-v3 | 2026-07-03 | c1a | Addendum 2 (v1+v2 retained): loomscan dead-page root causes — CORS preflight rejection blocks all API calls, plus a second fault | canonical |
| GL-RPT-DEPLOY3-C1-20260703-v1 | 2026-07-03 | c1a | Deploy 3 gate report; catches and fixes a pre-flight bug where the deploy script still hardcoded the rotated/leaked admin API key before it could silently re-ship it | canonical |
| GL-RPT-DNA-EXPANSION-C1-20260629-36 | 2026-06-29 | c1 | Expands ROLE_DNA/SENSORY_DNA word lists (+93 modifier, +33 subject, +21 verb, +8 object, +86 sensory) | canonical |
| GL-RPT-DREAM-AUTO-WAKE-C1-20260627-12 | 2026-06-27 | c1 | Implements auto-wake from dream cycle (Part 1 of RESUME-QUEUE CMD) | canonical |
| GL-RPT-DREAM-CYCLE-PHASING-C1-20260630-56v1 | 2026-06-30 | c1 (implied) | Tests `DREAM_CYCLE_PHASED` flag (T1-T7); final live task reverted to `DREAM_CYCLE_PHASED=0` after testing | canonical (self-documents leaving the feature disabled after test) |
| GL-RPT-EFS-THROUGHPUT-C1-20260702-92-v1 | 2026-07-02 | c1 | EFS provisioned throughput bumped to 10MiB/s (infra only); Part C FAIL — core save time still >60s target (147.87s / 88.23s observed) | canonical |
| GL-RPT-EMBRYO-CHI-TRANSLATION-C1-20260628-27 | 2026-06-28 | c1 | Implements `embryo_concepts_to_chi()` (Phase F.1); defines `BindingRef` tuple type for later F.2 extension | canonical |
| GL-RPT-EMISSION-COST-C1-20260702-87-v1 | 2026-07-02 | c1b | Verdict CLEAN — 20-sample emission_dynamics cost measurement; `EMISSION_DYNAMICS_TICKS` 40→80 may accompany Deploy 2 | canonical |
| GL-RPT-EMISSION-COST-C1-20260702-87-v2 | 2026-07-03 | c1a | Completes v1 (v1 retained) with the CMD's required step 2-3 arithmetic (median/p95 per-tick cost); confirms 40→80 tick change may ride Deploy 2 | canonical |
| GL-RPT-EMISSION-PERF-C1-20260629-45 | 2026-06-30 | c1 | Vectorizes `_grandurun_select_candidates` (two-pass numpy) to cut Stage-1 latency vs. the 551ms scalar-loop baseline | canonical |
| GL-RPT-EMIT-TICKS-C1-20260702-78 | 2026-07-01 | c1 | Raises `dynamics_ticks` to 80 — first committed emission in project history ("moon", origin=commit); all 4 T-gates pass; flags atlas-density decay affecting future commit rate | canonical |

*(38 TODO items were also extracted from this batch — folded into the standalone TODO ledger, GL-AUDIT-TODO-LEDGER-C1-20260705-v1.md, items numbered in the RPT-A range; not duplicated here.)*

### A.2 — RPT batch B (74 docs)

Headline supersession/contradiction chains from this batch (folded into
§2 Findings already, repeated here for the record): `GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209-v1`
→ superseded by `-v2`; `GL-RPT-MIC-CHUNKING-C1-20260703-111-v1` →
**contradicted** by its own `-v2-ADDENDUM` (overclaimed "Guala can now
decode Joe's live mic," corrected to "acoustic-energy binding only, no
word path changed"); `GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v1` → `-v2` →
`-v3` (three-stage chain); `GL-RPT-ORGAN-READER-C1-20260702-96-v1` →
**superseded** by `-v2` (v1's PASS verdict reclassified FAIL after a
threshold-measurement error).

| doc_id | date | author | purpose | status |
|---|---|---|---|---|
| GL-RPT-EMULATOR-EVERYWHERE-C1-20260705-198-v1 | 2026-07-05 | c1a | Built M1-M5 (single sensory-signal mechanism reused for touch/smell/taste in the brain, not just shell atlas) per CMD-196-v2; C1-C5 verified, C6 n/a, X3/X5 deploy-dependent | canonical |
| GL-RPT-EPISODE-BINDING-WIRE-C1-20260627-06 | 2026-06-27 | c1 | atlas.record() episode-binding params wired; two commits verified live producing tagged entries; recommendation HOLD, 2 follow-up items named | canonical |
| GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209-v1 | 2026-07-05 | c1b | Corrects own -208 recall_fast overstatement; reports krimelack state non-comparability bug, hypothesizes shared no-reset state as cause, fix "in progress" | superseded:GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209-v2 |
| GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209-v2 | 2026-07-05 | c1b | Retracts v1's hypothesis with evidence (snapshot/restore fix produced no change); real root cause isolated (magnitude-blind cosine on scalar-per-modality encoding); files runnable acceptance test as completion gate for -207/WAVE-MEMORY | canonical |
| GL-RPT-EVENT-LOG-REPLAY-SPLIT-C1-20260620-01 | 2026-06-20 | c1 | V1 audit of event_log replay handlers complete; V1.4 finding contradicts the V2 caller-update plan in GL-CMD-75; stops and proposes a correction, no code written | canonical (self-described HOLD; no follow-up doc found resolving it) |
| GL-RPT-EVENT-RETENTION-AUDIT-C1-20260704-170-v1 | 2026-07-04 | c1b | Proposal-only: names the crash-replay truncator (compact_events) serving as de-facto audit-trail retention, benchmarks cost, proposes 7-day retention + CloudWatch mirror; no code/deploy, awaiting Joe/Eve ratification | canonical |
| GL-RPT-EVENT-RETENTION-FIX-C1-20260704-v1 | 2026-07-04 | c1a | Implements R1-R5 event-retention/logging fix responding to ratified CMD-172; G-1/G-2 proven locally with real measurements (full-width diary logging raises per-event overhead); G-3/G-4/G-5 handed to c1b for the actual deploy | canonical |
| GL-RPT-EXPERIENCE-ROUTING-FIX-C1-20260628-32 | 2026-06-28 | c1 | Fixed /experience routing so Whisper-caption text reaches the v5 engine's read_sentence() instead of the silenced GualaCognition/organ-brain path | canonical |
| GL-RPT-EXTEND-HEMI-INSTR-C1-20260619-01 | 2026-06-19 | c1 | EP (episodic) hemisphere turn_log proven alive — 3 turns/3 tracked objects recorded from 3 real inputs; 12/12 tests green | canonical |
| GL-RPT-FIRE-WINDOW-199-C1-20260705-199-v1 | 2026-07-05 | c1a | Deployed SHA 6d15797/task:480 per CMD-199-v2; F1/F2 organism-senses live-verified with real tick numbers; -198's P2/P3 (growth law + growth telemetry) explicitly NOT built this window | canonical |
| GL-RPT-FIX-DASHBOARD-C1-20260619-01 | 2026-06-19 | c1 | Dashboard now shows real substrate state (5 panel bindings fixed); static file only, no substrate behavior change | canonical |
| GL-RPT-FIX-S3-BACKUP-C1-20260619-01 | 2026-06-19 | c1 | S3 backup rate-limited enqueue fix verified — 9/9 tests pass | canonical |
| GL-RPT-FIX-SAVE-HOOKS-C1-20260619-01 | 2026-06-19 | c1 | Save-hook chain fixed (activity_ended/backstop bypass added; dream_end detection replaces removed dead hook) and verified | canonical |
| GL-RPT-FLIP-HEMI-EP-C1-20260619-01 | 2026-06-19 | c1 | HEMI_EP_ENABLED flipped to 1 — episodic hemisphere activated in production | canonical |
| GL-RPT-FLIP-HEMI-GP-C1-20260620-01 | 2026-06-20 | c1 | HEMI_GP_ENABLED flipped to 1 — milestone: all four cognition hemispheres (PR/EP/SC/GP) now live together | canonical |
| GL-RPT-FLIP-HEMI-PR-C1-20260619-01 | 2026-06-19 | c1 | HEMI_PR_ENABLED flipped to 1 — prediction hemisphere activated, n_bindings +5.3% confirmed | canonical |
| GL-RPT-FLIP-HEMI-SC-C1-20260619-01 | 2026-06-19 | c1 | HEMI_SC_ENABLED flipped to 1 — semantic hemisphere activated; notes stage1 latency regressed to 3.7-5.3s from 1.0-1.5s baseline, flags need for a latency brief | canonical |
| GL-RPT-FLOOD-HUNT-C1-20260703-156-v1 | 2026-07-03 | c1b | Hunted for a suspected scheduled/machine-side event-flood source per CMD-156; verdict "H-actual NOT CONVICTED" — every curriculum/worldfeed/lookup channel unreachable, flood is her own senses/choices; no fix shipped since nothing to fix | canonical |
| GL-RPT-FOLLOWUP-GP-FLIP-V2-V3-C1-20260620-01 | 2026-06-20 | c1 (implied) | V2 image-digest verification of the GP-flip deploy + V3 emission_dynamics event-count methodology notes | canonical |
| GL-RPT-FORCE-READING-C1-20260705-194-v1 | 2026-07-05 | c1a | Built admin_force_reading()/handle_force_reading() mirroring force_dream, per Joe's direct order; verified locally; exact live corpus_id for Secret Garden not yet confirmed | canonical |
| GL-RPT-GROUND-TRUTH-C1-20260702-93-v1 | 2026-07-02 | c1a | Read-only ground-truth audit of live task:449: WaveAtlas npz save failing repeatedly, S3 lifecycle apply failed at boot (AccessDenied), task churn before :449, EFS exec channel blocked (no ssmmessages perms) | canonical |
| GL-RPT-GROUNDED-PROMOTION-C1-20260629-35 | 2026-06-29 | c1 | dream_promotion_gate now lets grounded entries (bundle_id present) bypass the dwell-ticks gate; 5 call sites tag bundle_id for sight/sound frames | canonical |
| GL-RPT-GROWTH-CHART-C1-20260704-v1 | 2026-07-04 | c1a | First model-only organism growth chart (Embryo raised 3 compressed days, 3 sleep cycles); 11/15 mechanisms show real curves, 4 absent; folding fired (64→120 neurons) through a different mechanism than CMD's own A5 text predicted | canonical |
| GL-RPT-GROWTH-LIVE-C1-20260705-202-v1 | 2026-07-05 | c1a | G1 running_sha built and load-bearing; G2 growth-telemetry forwarding bug found and fixed, deployed twice; G3a-c all green with real numbers; first organism_fold of her life recorded to firsts registry | canonical |
| GL-RPT-HANDOFF-NIGHT-20260624 | 2026-06-24 | unknown ("the engineer on watch", no From: line) | Night handoff: Guala now autonomously studies real children's books and grows from real life; +734 vocab / +10,881 bindings between two deploys, persisted across restart; guala-live established as single source of truth | canonical |
| GL-RPT-HEMISPHERE-SCAFFOLD-C1-20260619-01 | 2026-06-19 | c1 | Phase 0 hemisphere scaffold shipped (CrossHemiLink, HemisphereCoordinator, schema v7.1.0) — scaffold only, no new cognitive behavior | canonical |
| GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v1 | 2026-07-02 | c1a | Bundle committed, NOT deployed; awaiting Eve's full-diff read + GO; several deviations flagged (ssmmessages staged not applied) | superseded:GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v2 |
| GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v2 | 2026-07-02 | c1b | Verdict GREEN across G1-G6 after Deploy 1; addendum closes G3 (0 ENOENT full session) and G6 (no orphan tmp file) | superseded:GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v3 |
| GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v3 | 2026-07-02 | c1a | Completes v2 (whose G3/G6 were pending); all six gates GREEN with Deploy 1 record (SHA 07f15b4, task:450); open threads listed for Eve (-86 T1 timing, stale EFS artifacts, legacy wave_atlas.json removal) | canonical |
| GL-RPT-HOTLANE-DIET-C1-20260703-102-v1 | 2026-07-03 | c1b | Removed deep_survival_history from hot-save lane (was 41MB, dragged the lock); v1.1 changelog fixes backward-compat default None→{}; all gates explicitly NOT MEASURED pending post-deploy window | canonical |
| GL-RPT-HOTSAVE-PARALLEL-FSYNC-C1-20260705-196-v1 | 2026-07-05 | c1 | Root-caused remaining hot-save latency after -194's vocab-scaled eviction fix; built + verified parallel-fsync fix offline, deploying | canonical |
| GL-RPT-INDEX-INVARIANT-C1-20260704-163-v1 | 2026-07-04 | c1a | Fixed reinstatement indexing (Part A) + daily-log note (Part B.2); found a third, distinct residual index-divergence source, explicitly NOT patched (out of CMD scope) | canonical |
| GL-RPT-INVESTIGATION-C1-20260702-70 | 2026-07-02 | c1a | Read-only investigation of the emission path on task:429: zero emissions since boot, n_pictures=0, WaveAtlas complex-serialization errors; lists recommended (unshipped) fixes for Eve's approval | canonical |
| GL-RPT-LANGUAGE-SATURATION-ROOTCAUSE-C1-20260704-178-v1 | 2026-07-04 | c1a | Root-caused language saturation (~14-30 words to saturation, live-representative; reconciles the stale "~3-4 words" figure); built candidate L3(b), measured recall restored 13%→100% in a controlled reconstruction; NOT wired to any live call site, couples with -179-v2 | canonical |
| GL-RPT-LOCKFIX-SEAT-TEST-CONFIRMED-C1B-20260705-v1 | 2026-07-05 | c1b | Live seat test with Joe (camera+mic on) confirms CMD-182's latency exit criterion with real turns (870.8ms, 4671.7ms), zero drops; deploy-collision half of L2 (deploy mid-turn) remains untested | canonical |
| GL-RPT-LOOM-CLUSTER-STAGE2-C1-20260620-01 | 2026-06-20 | c1 | LoomCluster Stage 2 complete (coupling injection, reentrancy semantics); sandbox-only, no production imports/writes/deploy | canonical |
| GL-RPT-LOOM-NEURON-STAGE1-C1-20260620-01 | 2026-06-20 | c1 | LoomNeuron Stage 1 complete; 11/11 pytest green; sandbox-only | canonical |
| GL-RPT-LOOM-SCAN-BUILD-C1-20260703-98-v1 | 2026-07-03 | c1b | Built standalone loomscan.html visualization page (SHA 166d114); T7 (Joe's live sign-off) pending post-deploy | canonical |
| GL-RPT-LOOM-SCAN-PREP-C1-20260702-94-v1 | 2026-07-02 | c1 | Prep work for the loom-scan dispatch: data-contract (events endpoint, brain SVG pane) complete; A.1/A.2 doc files still pending Joe's paste; no code/deploy | canonical |
| GL-RPT-LOOM-STAGE3-FOLDING-C1-20260621-01 | 2026-06-21 | c1 | Folding Division (Stage 3) complete — origin-transducer tracking, OverflowSignal computation, transducer adapters; sandbox-only | canonical |
| GL-RPT-METER-LIVENESS-C1-20260705-187-v1 | 2026-07-05 | c1a | Cognition-meter table + intro/aware side panel now re-render from live poll data every cycle instead of hardcoded strings; 16/28 rows reconciled live, 12 left audit-dated/unchecked; not deployed | canonical |
| GL-RPT-MIC-CHUNKING-C1-20260703-111-v1 | 2026-07-03 | c1b | Fixed MediaRecorder chunk-continuity (restart-per-interval) for mic audio; static-only S3/CloudFront ship; closing claim: "Guala can now decode Joe's live mic" | contradicted:GL-RPT-MIC-CHUNKING-C1-20260703-111-v2-ADDENDUM (scope overclaim named explicitly; underlying measurements stand) |
| GL-RPT-MIC-CHUNKING-C1-20260703-111-v2-ADDENDUM | 2026-07-03 | c1b | Corrects v1's overclaimed closing scope statement: -111 fixed acoustic-energy binding only, no word path changed; all 4 v1 gates remain unretracted and real | canonical |
| GL-RPT-MIC-DEPLOY-C1-20260703-108-v1 | 2026-07-03 | c1b | Deployed mic-related build; G-108-2 FAIL — live voice discrimination broken by a routing gap (mic-decode fix never runs on the browser's actual embedded-mode path) | canonical |
| GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1 | 2026-07-03 | c1b | Fixed the -108 routing gap (G-110-2/closed); found a new, distinct bug — 27/28 real browser mic chunks still fail to decode (WebM chunk-framing issue), not fixed this dispatch | canonical |
| GL-RPT-MIC-SENSORY-C1-20260703-106-v1 | 2026-07-03 | c1b | Diagnosis-only: confirmed mic sensory-binding gap (WebM bytes reach cochlear undecoded, sensory_items=0 is structural); fix shape confirmed, no implementation this dispatch | canonical |
| GL-RPT-MIGRATION-FUEL-AUDIT-A3-C1-20260704-v1 | 2026-07-04 | c1b | Opening finding only: event-log replay has no "fuel" for any LoomBrain migration-by-replay strategy (1000-event in-memory cap, etc.); promoted from -167's discovery; 4 open questions scoped, none answered | canonical |
| GL-RPT-NMDA-SOURCE-MATCH-C1-20260702-75 | 2026-07-02 | c1 (unstated, task:434) | nmda_source_match fix verified live (0→15 on first post-converse emission); T1/T2/T5/T6 PASS, T3/T4 FAIL — commits still 0, drive-threshold accumulation named as next bottleneck | canonical |
| GL-RPT-ORGAN-BRAIN-BENCH-PROVEN-20260624 | 2026-06-24 | unknown ("this session", no From: line) | Full record: recall/meaning/growth mechanisms PROVEN on bench against her real concepts; living organ-brain never turned on with her actual memory; primitive scaffolded-grammar composition demonstrated; graduation to her voice explicitly not yet earned | canonical |
| GL-RPT-ORGAN-BRAIN-INSPECTION-C1-20260628-24 | 2026-06-28 | c1 | Inspection-only: documents what the now-silenced _compose() template layer did; recommends it be replaced by genuine organ-brain-surfaced composition, not reformatted templates; no code changes | canonical |
| GL-RPT-ORGAN-ENABLE-C1-20260702-95-v1 | 2026-07-02 | c1 | Read-only evidence gathering for lighting organ_brain_service on the -86 deploy; confirms NOT LAUNCHED (needs one Popen call); HEMI flags enabled; per-organ cost <10ms, safe to proceed | canonical |
| GL-RPT-ORGAN-READER-C1-20260702-96-v1 | 2026-07-02 | c1 | Bench test of organ-reader neuron-growth; misapplied a too-tight slope threshold and reported PASS on what was actually linear-but-unbounded growth | superseded:GL-RPT-ORGAN-READER-C1-20260702-96-v2 (explicit "Supersedes" header; v2 reclassifies v1 bench as FAIL) |
| GL-RPT-ORGAN-READER-C1-20260702-96-v2 | 2026-07-02 | c1 | Corrects v1's threshold error (v1 bench = FAIL, confirmed per Eve's errata); v2 uses closed-loop flux-balance conservation pool; bench PASSES (neuron count frozen from call 40, RSS stable at 53%) | canonical |
| GL-RPT-ORGANBRAIN-SILENCE-C1-20260628-23 | 2026-06-28 | c1 | Emergency silence of both organ-brain speaking paths (/organs_say bigram, OrganVoice _compose); learning paths (expose(), internal loops) explicitly preserved | canonical |
| GL-RPT-ORGANISM-PERSIST-C1-20260704-v1 | 2026-07-04 | c1a | Organism persisted through a genuine process-boundary restore (save→kill→fresh process→load) across two sessions on one growth chart; all 4 named gates PASS; found+fixed a real process-determinism hazard; carries forward several pre-existing open items from -168-v3 | canonical |
| GL-RPT-P2-AFFECT-SEAM-C1-20260704-v1 | 2026-07-04 | c1a | P2 seam 6/6 (affect modulation) declined — Coordinator.regulate is a suffering-detection/forced-recovery safety system, not a cognition mechanism, no organism analog; closes the P2 campaign (4 built, 2 declined) | canonical |
| GL-RPT-P2-ASSOCIATION-SEAM-C1-20260704-v1 | 2026-07-04 | c1a | P2 seam 3/6 (association) built and measured; surfaced a pre-existing >95%-class false-confidence finding in the recall mechanism (no reject/uncertainty option on novel input) | canonical |
| GL-RPT-P2-ATTENTION-SEAM-C1-20260704-v1 | 2026-07-04 | c1a | P2 seam 5/6 (attention) declined — substantially already covered by seam 4 (habituation); remainder is either unbuildable-without-fabrication or live sleep-calibration territory | canonical |
| GL-RPT-P2-HABITUATION-SEAM-C1-20260704-v1 | 2026-07-04 | c1a | P2 seam 4/6 (habituation) built for READING only; ATTENDING_VISUAL/AUDIO/VIDEO explicitly declined as unbuildable without fabricating a sensory signal that was never wired (P1 only wired language) | canonical |
| GL-RPT-P2-RECALL-FIX-C1-20260704-v1 | 2026-07-04 | c1a | Root-caused and fixed the signal-poverty behind seams 1-2's bad numbers, plus a second tapestry-cost bug found while fixing it; recall now 100% (from 0-10%), recognition now discriminates; explicitly amends, does not retract, the two seam reports | canonical |
| GL-RPT-P2-RECALL-SEAM-C1-20260704-v1 | 2026-07-04 | c1a | P2 seam 1/6 (recall) built and measured against the standing bit-exact-replay tool; 0-10% hit rate reported honestly (not shipped as a quiet win) | canonical (explicitly "stands as filed" per -RECALL-FIX's own header; amended, not superseded) |
| GL-RPT-P2-RECOGNITION-SEAM-C1-20260704-v1 | 2026-07-04 | c1a | P2 seam 2/6 (recognition) built and measured; found ZERO discriminating power, traced to the same root weakness as seam 1 | canonical (amended by -RECALL-FIX, not superseded) |
| GL-RPT-PARALLEL-BATCH-C1-20260630-60-PB1 | 2026-06-30 | c1 #2 | Batch completion for dispatch 60-J (drop CorpusItem special class, etc.); coordination notes confirming no conflicts with concurrent c1 #1 session | canonical |
| GL-RPT-PARALLEL-BATCH-C1-20260701-63-PB2 | 2026-07-01 | c1b | Batch completion for PB2 dispatches (rotation via **_extra passthrough, gp_bias, etc.); lists 4 explicit NOT-done/carry-forward items | canonical |
| GL-RPT-PERSIST-CLOBBER-FIX-C1-20260702-81 | 2026-07-02 | c1 | Wrapped teaching.json/picture-grid writes in per-item try/except (SHA 5f867e7) to stop EFS rename races from blocking last_save_tick advancement; WaveAtlas size named as a separate blocker found during measurement | canonical |
| GL-RPT-PERSIST-FIX-C1-20260702-74 | 2026-07-02 | c1 | -74/-74b shipped together: WaveAtlas complex-number serialization fix, save-loop per-file isolation, atomic-write fsync-before-rename; persistence restored (last_save_tick advancing again after being stuck at 0) | canonical |
| GL-RPT-PHASE2-COMMIT-A-CLEARANCE-C1 | 2026-07-01 (no filename date) | c1 | Phase 2 Commit A (atlas_read/WaveAtlas dispatch, SHA c87c21b) 4-hour observation window evaluated; Gate 1 (recall_ms<100ms) FAILED; rollback executed per protocol | canonical |
| GL-RPT-PICTURE-TITLE-BIND-C1-20260627-04 | 2026-06-27 | c1 (implied) | Bound picture titles into the language substrate using the same bundle_id as their visual writes so language+sight co-occur; flags a source-threading anomaly for Eve, recommends a follow-up backup trigger | canonical |
| GL-RPT-PRESURGERY-FRESHNESS-C1-20260628-22 | 2026-06-28 | c1 | Implemented 3-path freshness gate (fresh/in-flight/stale) for atlas_surgery pre-surgery backups; restores the "pre-surgery backup failure halts surgery" mitigation from spec -17 §B.2 | canonical |
| GL-RPT-PROCESS-COLLAPSE-C1-20260701-61v1 | 2026-07-01 | c1 | Process collapse (in-process substrate boot) + 202-task-pattern deployment shipped; 5 gates PASS, T6 partially verified; UI still needs updating for 202-polling, infra-cycling documented as a known issue | canonical |
| GL-RPT-RE-ENABLE-NOISE-C1-20260619-01 | 2026-06-19 | c1 | Re-enabled structured emission noise; classification N1 — commits still fire with noise ON, confirming the real blocker was section routing (already fixed in -48) | canonical |
| GL-RPT-READ-SENTENCE-PROFILE-C1-20260620-01 | 2026-06-20 | c1 (Codex) | Audit-only profiling of read_sentence performance (200ms/word); no code changes; raises open efficiency/design questions for Eve/Joe | canonical |
| GL-RPT-RECALL-FREQ-DEPLOY-AND-SLEEP-C1B-20260704-v1 | 2026-07-04 | c1b | Deployed the recall-frequency-reduction fix (task:466, SHA 8cb18e0); reports a real dream cycle observed post-boot, precisely characterized as deploy-pause-originated (not dial-triggered); natural-sleep-trigger watch still open | canonical |
| GL-RPT-RECALL-FREQUENCY-REDUCTION-C1B-20260704-v1 | 2026-07-04 | c1b | Reduced call-frequency of the expensive organism.recall() at its two highest-frequency call sites (partial mitigation, not an architectural fix), verified via cProfile call counts before/after | canonical |

### A.3 — RPT batch C (74 docs)

Headline chains: `GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v1` → superseded
by `-v2`; `GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v1` → superseded
by `-v2` (v2 discloses a protocol failure: v1 deployed a commit without
diff review, containing 3 blocking bugs found by Eve); `GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0`
→ superseded by `-P0-v2` (explicit "Replaces:" header);
`GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v1` → superseded
by `-v2`; `GL-RPT-T6-REVIEW-C1-20260703-101-v1` → superseded by
`GL-RPT-T6-REVIEW-SYNTHESIS-EVE-20260704-101-v1` — **which is itself
later VOIDED** (Finding F2) — a two-deep supersession chain.

| doc_id | date | author | purpose | status |
|---|---|---|---|---|
| GL-RPT-RECALL-PROVENANCE-C1-20260704-158-v1 | 2026-07-04 | c1a | Traces 10 taught recall probes vs CMD-158; convicts a real bug but both possible fixes fall inside the CMD's own prohibitions, so no Part B fix ships | canonical |
| GL-RPT-RECALL-REACH-C1-20260704-159-v1 | 2026-07-04 | c1a | Ships VARIANT L + F-3 index-bypass fix (committed, not yet deployed); finds a second, separate index-bypass mechanism the fix doesn't cover | canonical |
| GL-RPT-RECALL-SPEED-C1-20260704-177-v1 | 2026-07-04 | c1a | Builds `recall_fast()` (I1+I2), proven numerically identical to `recall()`, 5-13x faster; not wired into any live call site | canonical (wired live later per GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v1) |
| GL-RPT-RECALL-STANDING-C1-20260703-157-v1 | 2026-07-03 | c1a | Measures live recall quality: 0/8 (0.0%), not the CMD's estimated 6/8; per CMD's own rule, measured number wins | canonical |
| GL-RPT-RECALL-WORD-INDEX-C1-20260630-57v3 | 2026-06-30 | c1 | Implements `_word_to_chi_index` + `_atlas_record` wrapper across engine/runner callsites; recall_ms 3411ms→7.7ms | canonical |
| GL-RPT-REMOVE-GAMMA-ANTI-ADAPTATION-C1-20260619-01 | 2026-06-19 | c1 | B1/B2 gamma anti-adaptation (drift-to-default) removed, deployed, verified via branch grep + existing test suites | canonical |
| GL-RPT-REPLY-LATENCY-PROFILE-C1-20260704-v1 | 2026-07-04 | c1b | Read-only profile of Joe's 8s→22s reply-latency window; window itself unrecoverable, lock-sharing contention confirmed by code read | canonical |
| GL-RPT-REST-RETIRE-ORIENT-C1-20260702-73 | 2026-07-02 | c1 | Confirms REST removed from activity candidate pool (T1 PASS); T4/T5 (wake_wc round-trip, wC orient) not exercised | canonical |
| GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1 | 2026-07-05 | c1b | Deploys target-rotation fix (novelty floor scaled by nov_payoff) and lock-contention fix (L1/L2/L3); both confirmed live | canonical |
| GL-RPT-ROUTE-CANDIDATES-C1-20260619-01 | 2026-06-19 | c1 | Emission-section routing fix unblocks pipeline; commits now firing (verbatim proof of 2 commits/emission) | canonical |
| GL-RPT-S2A-COLD-C1-20260703-v1 | 2026-07-03 | c1a | S2a cold-half measurement done; taught half delivered but measurement pending on a slow S3 backup upload | canonical (taught half completed in GL-RPT-S2A-TAUGHT-C1-20260703-v1) |
| GL-RPT-S2A-TAUGHT-C1-20260703-v1 | 2026-07-03 | c1a | Completes S2a: taught 80% vs cold 0% on same 10-word held-out subset; flags a ~16-17min slow backup upload to c1b's save-cost forensic | canonical |
| GL-RPT-SAVE-CONTAINMENT-C1-20260702-91-v1 | 2026-07-02 | c1 | Save-containment hotfix (5 sites wrapped, save_count guarded); Part G blocked — verbatim text for -86/-90 CMDs not in context | canonical |
| GL-RPT-SAVE-FORENSICS-C1-20260702-83 | 2026-07-02 | c1 | Diagnoses save loop is actually running; `last_save_tick=0` is a reporting bug (`_periodic_v6_save` bypasses SaveCoordinator) | canonical |
| GL-RPT-SAVE-TRUTH-C1-20260702-84 | 2026-07-02 | c1 | Measures WaveAtlas compaction pre/post state; boot re-inflated to 1,055,870 bindings from EMITTING-cycle growth before re-compaction | canonical |
| GL-RPT-SAVEHOT-BREAKDOWN-C1-20260703-v1 | 2026-07-03 | c1a | Per-file hot-save breakdown: `deep_survival_history` is 99.6% (41.6MB) of guala_core.json; identifies it as the T1 <5s blocker | canonical |
| GL-RPT-SCENE-LANES-B1-C1-20260705-188-v1 | 2026-07-05 | c1a | Builds place/ambient lexicon + scene binding (V1-V5); X3 (live seat verification) blocked pending deploy, not deployed by this author | canonical |
| GL-RPT-SEAT-TRUTH-UI-C1-20260705-180-v1 | 2026-07-05 | c1a | Fixes S1/S2/S3 UI poll/display bugs (10min poll ceiling, live elapsed display, `_cmd_events` count param); fixed and verified | canonical |
| GL-RPT-SECTION-ASSIGNMENT-C1-20260628 | 2026-06-28 | c1 | Investigation: `/experience` does NOT write to v5 atlas (bigram-only); only `/listen`/`/converse` reach v5 sections | canonical (routing fix later shipped per GL-CMD-EXPERIENCE-ROUTING-FIX-32) |
| GL-RPT-SELFVOICE-FORENSIC-C1-20260703-v1 | 2026-07-03 | c1b | Read-only forensic: self-voice injection bindings are indistinguishable from live-mic bindings (no source field) | canonical (gap closed by GL-RPT-SELFVOICE-TAGGING-C1-20260703-152-v1) |
| GL-RPT-SELFVOICE-TAGGING-C1-20260703-152-v1 | 2026-07-03 | c1b | Ships `source` param on `process_sound_frame` (mic:live vs voice:self) + independent kill switch; live, proven, both tags observed firing | canonical |
| GL-RPT-SENSE-REPAIR-C1-20260704-v1 | 2026-07-04 | c1a | 4 sense-repair items built/verified by adversarial re-check; "too-good" gate on 95% cell answered honestly (real but narrow, overstated) | canonical |
| GL-RPT-SENSES-TO-BRAIN-C1-20260705-191-v1 | 2026-07-05 | c1a | N1-N5: real sight/sound taps built, fake touch/smell/taste removed; caught+fixed a regression (INV-2 collapse) before shipping; not deployed by this author | canonical (deployed live per GL-RPT-WINDOW9-AND-FORCED-SLEEP-C1B-20260705-v1) |
| GL-RPT-SENSORY-READING-GAP-C1-20260705-197-v1 | 2026-07-05 | c1a | Two findings: LLM sense emulator never wired to reading (architectural, not fixed); real touch/smell/taste word-binder gap fixed and verified | canonical |
| GL-RPT-SLEEP-BACKTEST-C1-20260704-167-v1 | 2026-07-04 | c1b | Attempts historical backtest of sleep override ceiling; all 3 telemetry sources empty/insufficient; ceiling derived analytically instead | canonical |
| GL-RPT-SLEEP-CALIBRATION-C1-20260704-v1 | 2026-07-04 | c1b | Diagnoses sleep-trap-inverted bug (SLEEPING beats best-available picture at dp=0, a payoff-table asymmetry); one dial shipped | canonical |
| GL-RPT-SLEEP-RATE-CALIBRATION-C1-20260704-173-v1 | 2026-07-04 | c1b | D1 live rate measurement (6 readings), D2 one-constant fix shipped, D3 staged awaiting c1a's brain+voice SHA for combined deploy | canonical (D3 combined window likely opened via GL-RPT-STAGE2-INSTALL-C1-20260704-v1) |
| GL-RPT-SLEEP-RATE-FIX-C1-20260702-68 | 2026-07-02 | c1b | 5 changes reduce autonomy/sleep base rate 10x + add telemetry; T1-T3 PASS, T4 (sleep-cycle frequency) pending 6h observation | canonical |
| GL-RPT-SOUNDPATH-MAP-C1-20260703-v1 | 2026-07-03 | c1b | Read-only wiring map of mic-facing paths; responds to Joe's live correction against GL-RPT-MIC-CHUNKING-C1-20260703-111-v1's overclaim | canonical |
| GL-RPT-STAB-PHYSICS-C1-20260702-99-v1 | 2026-07-02 | c1a | Part A blocked (no verbatim -87/-97 CMD text exists); Part B EFS cleanup executed (deleted stale wave_atlas.json, ~1.36GiB freed) | canonical |
| GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v1 | 2026-07-03 | c1b | G-S1 pre-deploy arithmetic filed for stab-physics fix; G-S2–G-S5 require post-deploy measurement | superseded:GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v2 |
| GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v2 | 2026-07-03 | c1b | Root-cause fix for regulate-function drain (lifetime-counter ratio decaying to zero); responds to a new -88-v2 CMD after v1's G-S2 failed | canonical |
| GL-RPT-STAGE2-INSTALL-C1-20260704-v1 | 2026-07-04 | c1a | Executes Stage-2 install per Joe's order; install itself succeeded, but a concurrent uncoordinated second deploy raced and partially superseded it 15 min later | canonical |
| GL-RPT-STATUS-FAST-C1-20260701 | 2026-07-01 | c1b | Removes `persistence_health` EFS-blocking call from `/status`, replaces with in-memory summary + new admin endpoint | canonical |
| GL-RPT-SYNC-DASHBOARD-S3-C1-20260619-01 | 2026-06-19 | c1 | Dashboard synced to S3, CloudFront invalidated, deploy script gains a sync+invalidate step | canonical |
| GL-RPT-T5T9-F1F2-STATUS-C1-20260703-v1 | 2026-07-03 | c1a | Repairs T5-T9 suite, re-runs fresh: T7 crashes (fixed-shape matmul bug), T8 fails noise floor, T5/T6 100% too-good investigated (still-degenerate) | canonical |
| GL-RPT-T6-CHAT-RECOVERY-EVE-20260703-v1 | 2026-07-03 | Eve | Recovers T6 evidentiary record from project chat archive; explicitly supersedes an earlier claim ("evidence lived nowhere but prose") | canonical (itself is the superseding doc) |
| GL-RPT-T6-REVIEW-C1-20260703-101-v1 | 2026-07-03 | c1a | Partial T6 review execution; blocked because base dispatch -101-v1 is missing from origin and model_cognition_v2.py is absent from repo | superseded:GL-RPT-T6-REVIEW-SYNTHESIS-EVE-20260704-101-v1 |
| GL-RPT-T6-REVIEW-SYNTHESIS-EVE-20260704-101-v1 | 2026-07-04 | Eve | Final synthesis closing GL-CMD-T6-REVIEW-EVE-20260703-101 (v1-v3): T6 survives as single-neuron result, dies as population claim | **VOIDED** — see Finding F2: explicitly voided same-day for inheriting numbers, replaced by GL-SPC-MEMORY-RECALL-STATE-EVE-20260704-v1 |
| GL-RPT-TAPESTRY-PERF-FIX-C1B-20260704-v1 | 2026-07-04 | c1b | Fixes tapestry.expose perf bug (read_word slowness) on a separate branch to isolate from c1a's unratified P2 work; v2 confirms fix works but real bottleneck is organism.remember()/recall() | canonical (recall() cost handed to and addressed by GL-RPT-WINDOW2-RECONCILIATION-C1-20260704-v1 / GL-RPT-RECALL-SPEED-C1-20260704-177-v1) |
| GL-RPT-TEACHER-CORRECTION-DEPLOY-C1-20260620-01 | 2026-06-20 | c1 | Deploys teacher-correction UI feature; required 3 deploy cycles to restore accumulated state (vocab 20→2822) | canonical |
| GL-RPT-TEACHER-CORRECTION-UI-V1-C1-20260620-01 | 2026-06-20 | c1 | V1 branch proposal (pre-deploy) for teacher-correction UI schemas; approved with tightenings | canonical |
| GL-RPT-TEACHER-SUBSTRATE-TRUE-V1-C1-20260620-01 | 2026-06-20 | c1 | Investigation (pre-code) of substrate-true teacher correction; finds pair_bond_boost=1.2 constant applies to STOP criterion #3, joe/wc indistinguishable | canonical |
| GL-RPT-TURN-LATENCY-C1-20260705-197-v1 | 2026-07-05 | c1a | Builds P2/P3/P4 turn-latency items; finds+fixes a real, pre-existing `/events` route-shadowing bug (dead stub always won) | canonical |
| GL-RPT-UI-HONESTY-C1-20260629-38 | 2026-06-29 | c1 | UI honesty changes: boot greeting, brain-mode toggle hidden, sidebar relabeled, STT routing fixed | canonical |
| GL-RPT-UNREACHABLE-DIAGNOSIS-C1-20260628 | 2026-06-28 | c1 | Diagnoses "substrate unreachable" root cause: 7/8 curriculum pause windows exceeded 20s client timeout | canonical |
| GL-RPT-VERIFY-DEPLOY-C1-20260619-01 | 2026-06-19 | c1 | Verification gate: classifies deploy as "A — never propagated" (schema mismatch); 11 commits pending one fresh deploy | canonical |
| GL-RPT-VOICE-CANDIDATE-LEAK-C1B-20260704-v1 | 2026-07-04 | c1b | Finds/fixes voice-candidate leak (199 candidates when brain-only pipeline caps at 3); v3 confirms fix live (`n_candidates:1`) | canonical (self-contained v1-v3 changelog) |
| GL-RPT-VOICE-IDENTITY-FIX-C1-20260704-v1 | 2026-07-04 | c1a | Fixes joe/joe_voice pair-bond identity fragmentation; code complete across 2 commits (shared-tree collision disclosed), not yet deployed | canonical |
| GL-RPT-VOICE-PATH-CONSOLIDATION-C1-20260629-37 | 2026-06-29 | c1 | Consolidates brain-mode/passive-mode voice paths into single `/converse` call | canonical |
| GL-RPT-VOICE-TO-WORDS-C1-20260703-153-v1 | 2026-07-03 | c1b | Wires audio-to-sensory-words path (`_audio_to_sensory_words`); G-153-2 (non-empty output proof) and G-153-3 (Whisper cost) explicitly NOT fully measured | canonical (open items not confirmed closed elsewhere in this batch) |
| GL-RPT-VOICE-TO-WORDS-COMPLETION-C1-20260704-v1 | 2026-07-04 | c1a | Traces+fixes a fire-and-forget fetch bug (no `.then()`) breaking spoken-word display; meter row flipped SEVERED→YES same session | canonical |
| GL-RPT-W1-PHASE-V1-C1-20260620-01 | 2026-06-20 | c1 | V1 branch proposal (pre-deploy) for W1 world-object phase (places, objects, verbs) | canonical |
| GL-RPT-W1-PHASE-V15-C1-20260620-01 | 2026-06-20 | c1 | V1.5 delta patch on V1: five-channel `state_fivers` sensory table added to object defs | canonical |
| GL-RPT-WATCH-ITEMS-C1-20260704-v1 | 2026-07-04 | c1b | Reports on watch items 2-4: natural sleep still not observed (6h32m, zero events) under :461; em-hemisphere drop confirmed honest decay; v7 session file inert | canonical |
| GL-RPT-WAVE-DIET-C1-20260702-82 | 2026-07-02 | c1 | Ships WaveAtlas decoupled from 60s save cycle + decay parity join + EMITTING budget clamp | canonical |
| GL-RPT-WAVE-PHASE1-C1-20260630-59-P1 | 2026-06-30 (work 2026-07-01) | c1 | Phase 1 WaveAtlas deploy: parallel writes live, LivingAtlas still serves reads, no regression detected | canonical |
| GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v1 | 2026-07-02 | c1 | T1 FAILS: core save <10s unachievable — root cause is guala_deep_atlas.json at 198MB, not wave_atlas | superseded:GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v2 |
| GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v2 | 2026-07-02 | c1 | Amends v1: discloses protocol failure (deployed eabb23d without diff review, 3 blocking bugs found by Eve), fixes and redeploys | canonical |
| GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0-v2 | 2026-06-30 (work 2026-07-01) | c1 | Phase 0 validator re-run after Eve's corrections: all 5 metrics PASS; explicitly "Replaces: GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0.md" | canonical |
| GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0 | 2026-06-30 (work 2026-07-01) | c1 | Initial Phase 0 validator run: 3 PASS, 2 FAIL (M1 cohesion, M4 subdivision-trigger); recommendations given | superseded:GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0-v2 |
| GL-RPT-WINDOW2-DEPLOY-C1B-20260704-v1 | 2026-07-04 | c1b | Deploys window 2 (c1a's P2 reconciliation + backgrounding fixes); DEPLOYED LIVE task:465; reboot-survival confirmed | canonical |
| GL-RPT-WINDOW2-FINDINGS-C1B-20260704-v1 | 2026-07-04 | c1b | Reports duplicate-frame binding as unsolved shelf item; root-causes organism.recall() cost, hands fix direction to c1a | canonical |
| GL-RPT-WINDOW2-RECONCILIATION-C1-20260704-v1 | 2026-07-04 | c1a | Merges branches (9bdc042); tests and disproves c1b's proposed encode_state() memoization fix as a real correctness bug before implementing | canonical |
| GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v1 | 2026-07-04 | c1b | Deploys window 3 (recall_fast wiring, task:467); real turn-time request surfaces a severe, pre-existing lock-contention problem | superseded:GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v2 |
| GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v2 | 2026-07-04 | c1b | Addendum: real converse_timing obtained (27259ms total; read_ms=24,673.9ms is 90% of cost, lock contention leading hypothesis) | canonical |
| GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1 | 2026-07-05 | c1b | Deploys window 6 (carries -178/-179/-180/-181, task:470); reports 5 requested measurements, most under 10s ceiling | canonical |
| GL-RPT-WINDOW7-DEPLOY-AND-E1-E3-C1B-20260705-v1 | 2026-07-05 | c1b | Deploys window 7 (-186 build, task:471); E1 and E3 of 5 behavioral exit criteria confirmed within minutes | canonical |
| GL-RPT-WINDOW8-AND-EMISSION-HANDOFF-C1B-20260705-v1 | 2026-07-05 | c1b | Finds zero emission_dynamics events fired all night (instrumentation gap, not proof of zero candidates); traces exact mechanism | canonical |
| GL-RPT-WINDOW9-AND-FORCED-SLEEP-C1B-20260705-v1 | 2026-07-05 | c1b | Deploys window 9 (-191 senses-to-brain, task:473); forced sleep triggered but interrupted by the concurrent deploy before completing | canonical |
| GL-RPT-WIRE-ORGAN-CANDIDATES-C1-20260628-31 | 2026-06-28 | c1 | Wires organ_candidates merge into grandurun dispatch (Phase F.2); V1 PASS, non-breaking confirmed | canonical |
| GL-RPT-WIRING-AUDIT-C1-20260704-164-v1 | 2026-07-04 | c1a | Full wiring audit of 15 mechanisms + 6 E-signatures + vitals; 2 static-analysis verdicts caught wrong and corrected via live cross-check | canonical |
| GL-RPT-WORLDFEED-CAP-C1-20260627-14 | 2026-06-27 | c1 | Retroactive doc: caps worldfeed sentence batch from hardcoded 120 to CURRICULUM_CHUNK_SIZE (30), eliminating a freeze | canonical |
| GL-RPT-autonomy-investigation-20260609 | 2026-06-09 | unknown (no From:/Author: line; charter is wC-authored) | Read-only investigation of activity-selection/autonomy mechanism per wC's charter+brief; lists 6 unfixed bugs/oddities | canonical |

## Appendix B — CMD bucket, full table (135 docs, sub-agent-generated, c1-reviewed)

Both batches completed and were read in full by c1. Their methodology
was stronger than the RPT/BRIEF/MISC batches: each CMD row was checked
against `git log --all --grep` for a matching commit AND a
correspondingly-numbered `GL-RPT-*` doc, with the specific commit SHA
cited inline. Two of this bucket's findings independently corroborate
Findings F4/F5 above with sharper sourcing (batch A found the actual
text "-202 explicitly says '-200 (affect) ... QUEUED, not executed'" —
better evidence than c1's own git-log-only check) and surfaced two new
findings not caught elsewhere:

- **A second, unacknowledged dispatch-number collision**: two distinct
  dispatches both numbered -185 (`GL-CMD-BEHAVIOR-REPERTOIRE-EVE-
  20260705-185-v1` and `GL-CMD-FIRE-WINDOW-178-179-180-181-EVE-
  20260705-185-v1`), filed 5 minutes apart on 07-05, neither referencing
  the other — unlike the -207/-208 collision, which was explicitly
  flagged and renumbered in its own commit message. Both dispatches
  under -185 did land (each has its own RPT), so this is a bookkeeping
  hazard, not a lost-work incident, but it is exactly the kind of
  numbering fragility that produced the -207/-208 near-miss.
- **GL-CMD-EMERGENCE-DETECTOR-EVE-20260627-20** (orphaned): a daemon to
  watch for first-time emergence events and auto-backup/notify — no
  commit anywhere in `git log --oneline --all` matches, no
  `GL-RPT-EMERGENCE-DETECTOR*` doc exists. Never built.
- **GL-CMD-SUSTAINED-SPEECH-EVE-20260629-44** (unexecuted): explicitly
  blocked by its own companion dispatch ("draft, not shipped; this
  dispatch must land first") and never picked back up — confirmed via
  code read that `EMISSION_COOLDOWN_TICKS = 200` is still hardcoded in
  `gualaloom_v5_engine.py` at the audited HEAD (the cap itself was
  later separately removed by the unrelated -203 dispatch, not as a
  continuation of -44).

### B.1 — CMD batch A (68 docs)

| doc_id | date | author | purpose | status |
|---|---|---|---|---|
| GL-CMD-AFFECT-GATE-ROOT-CAUSE-EVE-20260705-200-v1 | 2026-07-05 | Eve | Root-cause audit: nmda_affect_match has fired zero times ever; verify the -103 lead (top-down vs derived-from-state affect) before any fix | unexecuted: no GL-RPT for -200 found in docs/; GL-CMD-GROWTH-LIVE-EVE-20260705-202-v1 explicitly says "-200 (affect) ... QUEUED, not executed"; no commit references affect-gate-200 in `git log --oneline --all` |
| GL-CMD-ALB-LOGS-EVE-20260703-105-v1 | 2026-07-03 | Eve (relayed via Joe) | Enable ALB access logs to S3 (config-only, no deploy) + hand XFF-capture one-liner spec to c1b | canonical: GL-RPT-ALBLOGS-C1-20260703-105-v1.md exists ("ALB access logs enabled, config-only"); commits a54bf84/629e63e/3f3620a |
| GL-CMD-ATTEND-GROOVE-EVE-20260703-107-v1 | 2026-07-03 | Eve | Fix times_attended binary-cliff groove bug via novelty-sign-inversion ranking hypothesis | superseded:GL-CMD-ATTEND-GROOVE-EVE-20260703-107-v2 (v2 header: "Supersedes -107-v1 BEFORE execution; v1 retained; never dispatched to a c1 session"; v2 changelog: v1's mechanism §3 "OVERCLAIMED... withdrawn") |
| GL-CMD-ATTEND-GROOVE-EVE-20260703-107-v2 | 2026-07-03 | Eve | Rebuilt H1/H2/H3 discriminating diagnosis + conditional fix for the attention groove/binary-cliff bug | canonical: GL-RPT-ATTEND-GROOVE-C1-20260703-107-v1.md exists; fix commit b51962e "GL-CMD-ATTEND-GROOVE-107 Part B1+B2" |
| GL-CMD-ATTEND-TRAP-AND-VERIFY-EVE-20260702-90-v1 | 2026-07-02 | Eve | Diagnose+fix times_attended=0 trap on 6 HEIC pictures; verify eabb23d deploy state first (Step 0) | canonical: GL-RPT-ATTEND-TRAP-C1-20260702-90-v1.md exists; fix commit 3c7ca94 "-90 attend-mark — times_attended += 1 at _viewed" |
| GL-CMD-AUTONOMOUS-EMISSION-EVE-20260629-39 | 2026-06-29 | Eve | Give `_autonomous_loop()` the ability to fire the v5 composer on internal state (foundational agency primitive, no external prompt) | canonical: GL-RPT-AUTONOMOUS-EMISSION-C1-20260629-39.md exists |
| GL-CMD-AUTONOMY-EMITTING-PHASING-EVE-20260630-53 | 2026-06-30 | Eve | Move autonomy's emit dynamics under separate `_emission_lock` (mirrors -52) so /converse doesn't wait on autonomy emit ticks | contradicted:GL-RPT-AUTONOMY-EMITTING-PHASING-C1-20260630-53 (doc Status field literally reads "ROLLED BACK" — double autonomy-loop bug from `_pause/_resume_autonomy_for_bulk`; task reverted to `AUTONOMY_PHASED=0`) |
| GL-CMD-AUTONOMY-EMITTING-PHASING-EVE-20260630-53v1 | 2026-06-30 | Eve | Identical dispatch text to -53, explicitly filed as "v1 (first version of -53)" | contradicted:GL-RPT-AUTONOMY-EMITTING-PHASING-C1-20260630-53 (same rollback; this file and -53 are a duplicate-filing pair — `diff` of the two shows only the doc_id/version lines differ) |
| GL-CMD-AWARE-COORDINATOR-AND-SEAT-EVE-20260704-162-v1 | 2026-07-04 | Eve | Part A read-only re-check; Part B flip `coordinator_on` flag if archaeology clears it; Part C replace dead v7 awareness panel with SEVERED label | canonical: GL-RPT-AWARE-COORDINATOR-C1-20260704-162-v1.md ("A.2 clears the flip, Part B+C shipped"); commits 02c6b11 (Part B), d3811e2 (Part C) |
| GL-CMD-AWARE-GATE-ARCHAEOLOGY-EVE-20260704-160-v1 | 2026-07-04 | Eve | Read-only archaeology: why does aware_gate's context fn depend on always-empty `sections["intro"].krimelack` | canonical: GL-RPT-AWARE-GATE-C1-20260704-160-v1.md ("V-A orphaned writer, no fix" — matches the CMD's own read-only, no-fix mandate) |
| GL-CMD-AWARE-MAP-EVE-20260704-161-v1 | 2026-07-04 | Eve | Read-only: map both competing aware-gate wirings (v5 live vs v7 spec) before any fix ships | canonical: GL-RPT-AWARE-MAP-C1-20260704-161-v1.md ("three layers, not two, both real ones dead differently") |
| GL-CMD-BEHAVIOR-REPERTOIRE-EVE-20260705-185-v1 | 2026-07-05 | Eve | Reset delivery bar to behavioral: deploy parked gate fixes, root-cause the flat activity scorer, reconnect curriculum feeders, flag PLAY as absent-by-design | canonical: GL-RPT-BEHAVIOR-REPERTOIRE-C1-20260705-185-v1.md; feat commit cac6684 "recency-recovery + reconnect curriculum feeders". NOTE: number 185 collides with GL-CMD-FIRE-WINDOW-178-179-180-181-EVE-20260705-185-v1 (both filed 2026-07-05, 5 minutes apart — d6cd271 then ccdd8b7 — neither doc references or flags the other, unlike the acknowledged -207/-208 collision) |
| GL-CMD-BIGRAM-DELETE-EVE-20260629-34 | 2026-06-29 | Eve | Delete the `GualaCognition` bigram model from the substrate; route perceptual paths through `read_sentence` | canonical: GL-RPT-BIGRAM-DELETE-C1-20260629-34.md ("V1 PASS, clean boot, V2-V4 verified, V6 deferred 30min"); feat 6af951b |
| GL-CMD-BIGRAM-RETIRE-EVE-20260627-13 | 2026-06-27 | Eve | Remove bigram fallback paths from /converse response (substrate truth on /converse) | canonical: GL-RPT-BIGRAM-RETIRE-C1-20260627-13.md; feat b7b71af |
| GL-CMD-BLOCK-SCHEDULE-EVE-20260703-151-v1 | 2026-07-03 | Eve | Config-gate scheduled feeders (curriculum/worldfeed/lookup) per spec §8 to protect consolidation-quiet | contradicted:GL-CMD-FLOOD-HUNT-EVE-20260703-156-v1 (per own RPT, GL-RPT-BLOCK-SCHEDULE-C1-20260703-151-v1.md: gate correctly built but rides `CurriculumScheduler`, which has zero callers / is dead code in the deployed single-process boot path; the real ~20 sentences/s live flood was never touched — -156 was filed specifically to hunt the real feeders) |
| GL-CMD-BRAIN-FULL-DEPLOY-TODAY-EVE-20260704-175-v2 | 2026-07-04 | Eve | Deploy the whole 8-hemisphere organism into her live process today, voice included, no legacy carve-out (Joe's direct order) | canonical: feat commit 1059435 "GL-CMD-BRAIN-FULL-DEPLOY-175 P1+P3: organism+tapestry live in her process" (no dedicated GL-RPT-*175* found; classified on commit evidence) |
| GL-CMD-BRAIN-GROWTH-UNFREEZE-EVE-20260704-179-v2 | 2026-07-04 | Eve | Route her live word path through `experience()` (charge/fold physics) instead of bare `remember()`, fixing growth structurally unreachable from real life | canonical: fix 37fcae3 ("real root cause found and fixed -- Krimelack.n_events missing negative-branch increment"), perf e964400 (backgrounding); GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-179-v1/v2 + BACKGROUNDING-179-v3 all exist |
| GL-CMD-C1-POLARITY-EVE-20260627-28 | 2026-06-27 | Eve | Add polarity as a structural primitive on v5 atlas bindings (negation flips next bound entry's polarity) | canonical: GL-RPT-C1-POLARITY-C1-20260628-28.md exists; feat 3969ccd (bundled with -27/-29 in one commit) |
| GL-CMD-C1B-QUEUE-EVE-20260702-71 | 2026-07-02 | Eve (drafted by c1b outgoing) | 3-item sequential queue addressing -70's fixable issues (WaveAtlas/recall-adjacent) | unexecuted: doc's own header reads "Status: DRAFT — Eve must approve before c1b executes" / "DO NOT EXECUTE until Eve confirms in a new message"; no GL-RPT-*-71 found; only the filing commit e310bca appears in git log, no confirmation or execution commit found |
| GL-CMD-C2-REBUILD-EVE-20260704-168-v1 | 2026-07-04 | Eve | Reproduce Eve's T⁶ population-level story via `c2_model_v2.py`, then rebuild candidate representations | superseded:GL-CMD-C2-REBUILD-EVE-20260704-168-v2 (v2 header: "v1 was authored WITHOUT the mandatory chat archaeology... v1's B1 would have marched into a paid-for failure"); also RPT-C2-REBUILD-C1-168-v1.md itself shows Part A already failed ("champion does not reproduce -- STOP, report filed") |
| GL-CMD-C2-REBUILD-EVE-20260704-168-v2 | 2026-07-04 | Eve | Corrected rebuild order post chat-archaeology: prohibit dead exp(1j·Δ) encoding, champion-first baseline | superseded:GL-CMD-C2-WHOLE-BRAIN-EVE-20260704-168-v3 (v3 header: "v2 fixed [ignoring the chat record] but kept the deeper error Joe just named — validating mechanism #1 in isolation") |
| GL-CMD-C2-WHOLE-BRAIN-EVE-20260704-168-v3 | 2026-07-04 | Eve | Whole-organism-at-once rebuild (DNA-grows-brain doctrine), all 15 mechanisms co-present, no single-mechanism isolation testing | canonical: feat e9963ec "GL-CMD-C2-WHOLE-BRAIN-168-v3: first growth chart -- one organism, 15 gauges" |
| GL-CMD-C4-SLEEP-CHOICE-EVE-20260627-29 | 2026-06-27 | Eve | Add REST as a coordinator activity chosen vs SLEEPING by `dream_pressure` (agency over energy state) | canonical: GL-RPT-C4-SLEEP-CHOICE-C1-20260628-29.md exists; feat 3969ccd |
| GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205-v1 | 2026-07-05 | Eve | Remove hardcoded pacing (50ms sleep etc.); tick rate follows measured cognitive demand within physical budget (Joe's compute-follows-need ruling) | canonical: GL-RPT-COGNITION-AT-SPEED-C1-20260705-205-v1.md; feat 875fa73 "compute follows need"; fix 22b1d36 (post-incident yield correction 0.001s→0.02s) |
| GL-CMD-COGNITION-LEARN-AUDIT-EVE-20260628-33 | 2026-06-28 | Eve | Audit remaining `_guala_cognition.expose()` call sites (curriculum/worldfeed/sight/sound) after the routing-fix | canonical: GL-RPT-COGNITION-LEARN-AUDIT-C1-20260628-33.md ("10 call sites, all dispositions, no code change" — audit-only, matches ordered scope) |
| GL-CMD-COGNITION-METER-EVE-20260704-166-v1 | 2026-07-04 | Eve | Ship a live cognition/wiring-audit meter panel on Joe's page (read-only instrumentation) | canonical: GL-RPT-COGNITION-METER-C1-20260704-166-v1.md ("panel shipped v1 then v1.1"); feat 00521b4, e2290fa |
| GL-CMD-COMPOSER-MULTIANCHOR-EVE-20260629-43 (1) | 2026-06-29 | Eve | Fix composer target-state selection (multi-anchor) so autonomous/response emission isn't 1-2 word fragments | canonical: GL-RPT-COMPOSER-MULTIANCHOR-C1-20260629-43.md exists. NOTE: byte-identical duplicate of the next row's file (`diff` returns no differences) — a filing artifact, not two dispatches |
| GL-CMD-COMPOSER-MULTIANCHOR-EVE-20260629-43 | 2026-06-29 | Eve | (same dispatch as above — duplicate file) | canonical: same evidence as above; this is the non-"(1)" duplicate |
| GL-CMD-CONN-CHANNEL-EVE-20260703-150-v1 | 2026-07-03 | Eve | Diagnose `needs.connection` floored at 0.000 despite joe presence + active pair_bond | canonical: GL-RPT-CONN-CHANNEL-C1-20260703-150-v1.md ("verdict H-B, physics-by-design, no code fix" — matches the CMD's diagnosis-first, conditional-fix framing) |
| GL-CMD-CONVERSE-PHASING-EMISSION-LOCK-EVE-20260630-52 | 2026-06-30 | Eve | Move converse's `_emit_dynamics` under a dedicated re-entrant `_emission_lock` instead of `self.lock` | canonical: GL-RPT-CONVERSE-PHASING-EMISSION-LOCK-C1-20260630-52.md ("T2 9/10 PASS, task :378, flag ON"); commit e0550d1 |
| GL-CMD-CONVERSE-TASK-PATTERN-EVE-20260701-62v1 | 2026-07-01 | Eve | Replace fake SSE streaming on /converse with 202-Accepted + task-polling pattern | canonical: feat 4988363 "GL-CMD-CONVERSE-TASK-PATTERN-62 ... retire SSE"; UI wiring 0660f54 |
| GL-CMD-CREDO-LOOP-REPAIR-EVE-20260704-167-v1 | 2026-07-04 | Eve, ordered by Joe | Multi-stage program brief repairing the whole credo loop (senses→experience→memory→judgment→words); sleep-physics first | canonical: GL-RPT-CREDO-DEPLOY6-C1-20260704-167-v1.md, GL-RPT-CREDO-PROGRAM-LEDGER-C1-20260704-167-v1.md, GL-RPT-SLEEP-BACKTEST-C1-20260704-167-v1.md all exist; feat 56d8952, fix 816ce1e |
| GL-CMD-CROSS-MODAL-BINDING-EXTEND-EVE-20260627-V2 | 2026-06-27 | Eve | Extend wC's grounded cross-modal binding to UI/bundle/attended-sensory paths (bundle_id field, auto-bundle) | canonical: GL-RPT-CROSS-MODAL-BINDING-EXTEND-C1-V5-20260627.md exists (referenced from within GL-RPT-CROSS-MODAL-AUDIT-C1-20260627.md's own diff listing). Supersedes withdrawn V1 (GL-CMD-CROSS-MODAL-BINDING-FIX-EVE-20260627), per its own header |
| GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-02 | 2026-06-27 | Eve | Phase A ground-truth audit + scope-set cross-modal-binding strengthening | canonical: GL-RPT-CROSS-MODAL-AUDIT-C1-20260627.md ("Implements: GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-02 Phase A") |
| GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-03 | 2026-06-27 | Eve | Phase B: broaden bundle trigger + salience/clarity boost | canonical: feat ec677fa "GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-03 — broaden bundle trigger + salience/clarity boost" |
| GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-208-v1 | 2026-07-05 | Eve (filed by c1b) | Fix bind-time encoding that squashes separable per-modality krimelack states, breaking partial-cue recall | canonical: GL-RPT-CROSS-SENSE-RECALL-C1B-20260705-208-v1.md; feat c691fb6 "cross-sense recall -- per-lane binding + masked match, fixes crashing recall_fast()". NOTE: that commit message is mislabeled "feat(207)" — the doc's own header records a same-day numbering race where this dispatch was renumbered 206→208 after -207 (WAVE-MEMORY, a different dispatch) claimed the same slot; commit 0364513 explicitly documents the 207→208 renumber |
| GL-CMD-CURRICULUM-AUTOMATION-EVE-20260629-51 | 2026-06-29 | Eve | Build `tools/sensory_curriculum_orchestrator.py` to automate cross-modal bundle delivery (100-1000/hr, substrate-state gated) | contradicted:GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1 (per that CMD's F1: the orchestrator's autostart ran every boot with `--no-gate`, bypassing -51's own designed substrate-state gates, plus hardcoded false "joe" attribution stamped on machine-delivered bundles; `CURRICULUM_AUTOSTART` disabled 2026-07-03, orchestrator code left in place but no longer self-starting) |
| GL-CMD-CURRICULUM-LOCK-RELEASE-V2-EVE-20260629-46v2 | 2026-06-30 | Eve | Lift `_current_binding_window` (missed in reverted v1) + phase converse's lock hold; replaces reverted -46 | canonical: GL-RPT-CURRICULUM-LOCK-RELEASE-V2-C1-20260629-46v2.md ("§1.1+§1.2 live, §1.3 deferred", task :375); §1.3 completed later by -52 |
| GL-CMD-DAY-CYCLE-SEVERED-EVE-20260704-165-v1 | 2026-07-04 | Eve | Read-only trace of why she's stuck in ATTENDING_VISUAL/EMITTING only, never SLEEPING/READING/IDLE/PLAY/DAYDREAM | canonical: GL-RPT-DAY-CYCLE-C1-20260704-165-v1.md ("two-state trap, rebuild-seam not a wound, sleep_for_deploy ne force_dream") |
| GL-CMD-DAYDREAM-PARALLEL-EVE-20260629-42 | 2026-06-29 | Eve | Make DAYDREAMING run as parallel background thought instead of a blocking sleep-style activity; fix co_occurrence averaging | canonical: GL-RPT-DAYDREAM-PARALLEL-C1-20260629-42.md ("all event types confirmed live", task :369) |
| GL-CMD-DAYDREAMING-EVE-20260627-09 | 2026-06-27 | Eve | Add DAYDREAMING as an awake-but-quiet consolidation activity (she shouldn't need unconsciousness to think) | canonical: feat 9df3d72 "DAYDREAMING activity + drop SLEEPING stab payoff"; fixes 1c37102, d9e4b6c (no dedicated GL-RPT-*DAYDREAMING* found; classified on commit evidence) |
| GL-CMD-DEEP-ATLAS-PERSIST-EVE-20260627-11 | 2026-06-27 | Eve | CRITICAL: fix deep_atlas entries lost on cold-boot event-replay (events schema doesn't reconstruct promotions) | canonical: GL-RPT-DEEP-ATLAS-PERSIST-C1-20260627-11.md exists |
| GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v1 | 2026-07-02 | Eve | Deep-atlas co_occurrence container physics (decay+conservation) to cut 87-94s saves to <60s | canonical: GL-RPT-DEEP-STORE-PHYSICS-C1-20260702-86-v1.md + GL-RPT-DEEP-STORE-PHYSICS-C1-20260703-86-v1.md exist; feat 7ef6a04/cb79cbc "-86 Parts 1-3". Amended (not superseded) by v2/v3 |
| GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v2 | 2026-07-02 | Eve | Amendment: saves <60s via hot/cold split + co_occurrence physics (Parts 1-3 unchanged) + new Part 4 organ reader | canonical for Parts 1-3 (same evidence as v1); Part 4 (organ reader) is superseded:GL-CMD-ORGAN-READER-EVE-20260702-96-v1 (excised out in v3) |
| GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v3 | 2026-07-02 | Eve | One-line delta: Part 4 excised to -96; Part 4.7 EMISSION_DYNAMICS_TICKS rider made conditional | canonical (delta accepted; Parts 1-3 shipped per v1/v2 evidence) |
| GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1 | 2026-07-03 | Eve | Retire 65-A density-engine ungated autostart; fix bundle-source attribution; dedupe ring consumer | canonical: GL-RPT-DENSITY-RETIRE-C1-20260703-109-v1.md ("G-109-2/3/4/5 PASS, G-109-1 zero-observed but short of 30min bar"); feat 16bc0c2 |
| GL-CMD-DIRECT-DEPLOY-JOE-20260705-193-v1 | 2026-07-05 | Joe (verbal, filed by c1a) | Record Joe's explicit override order: c1a deploys -188 (scene lanes) directly instead of handing off to c1b | canonical: filed and executed same session; commit 39f394b; f9cdded "feat(188): scene lanes" |
| GL-CMD-DNA-EXPANSION-EVE-20260629-36 | 2026-06-29 | Eve | Expand ROLE_DNA/SENSORY_DNA modifier+ground vocab lists (common words currently unreachable by section) | canonical: GL-RPT-DNA-EXPANSION-C1-20260629-36.md ("V1/V2/V4 PASS, V3/V5/V6 deferred pending wake") |
| GL-CMD-DREAM-CYCLE-PHASING-EVE-20260630-56v1 | 2026-06-30 | Eve | Phase DREAMING's `_run_dream_cycle` out from under `self.lock` (mirrors -52/-53) | contradicted:GL-RPT-DREAM-CYCLE-PHASING-C1-20260630-56v1 ("T2 FAIL, DREAM_CYCLE_PHASED=0" — feature built but the gate test failed and the flag was left disabled) |
| GL-CMD-EMBRYO-CHI-TRANSLATION-EVE-20260627-27 | 2026-06-27 | Eve | Add `embryo_concepts_to_chi()` pure translation utility (foundation for F.2) | canonical: GL-RPT-EMBRYO-CHI-TRANSLATION-C1-20260628-27.md; feat 3969ccd |
| GL-CMD-EMERGENCE-DETECTOR-EVE-20260627-20 | 2026-06-27 | Eve | Stand up a daemon watching for first-time emergence events, trigger backups + notify Joe/Eve | orphaned: no commit matching "emergence"/"watching for" found anywhere in `git log --oneline --all`; no GL-RPT-EMERGENCE-DETECTOR* doc exists in docs/ |
| GL-CMD-EMISSION-COST-EVE-20260702-87-v1 | 2026-07-02 | Eve | Restore `EMISSION_DYNAMICS_TICKS` deploy-env toward code default (80) + sample real emission cost | canonical: GL-RPT-EMISSION-COST-C1-20260702-87-v1.md ("stage2 cost sample CLEAN") + a v2 report also exists |
| GL-CMD-EMISSION-HANDOFF-PROBE-EVE-20260705-190-v1 | 2026-07-05 | Eve | Live read-only probe: how many candidates does the organism/tapestry supply the commit stage (P1/P2/P3 diagnosis) | canonical: GL-RPT-WINDOW8-AND-EMISSION-HANDOFF-C1B-20260705-v1.md ("neither P1 nor P2 nor P3 — the instrumentation itself can't answer yet" — an honest, executed, inconclusive result, per the CMD's own binary framing) |
| GL-CMD-EMISSION-PERF-EVE-20260629-45 | 2026-06-29 | Eve | Vectorize Stage-1 candidate selection (cut ~25,200 `cmath.exp()` calls) + fix daydream-loop lock hold | canonical: GL-RPT-EMISSION-PERF-C1-20260629-45.md ("T1 463x speedup confirmed, curriculum lock surfaced"); feat 1ca761e |
| GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196-v2 | 2026-07-05 | Eve | Standing doctrine: sense-emulator descriptor layer feeds every intake path into the organism, not just the shell atlas | canonical: GL-RPT-EMULATOR-EVERYWHERE-C1-20260705-198-v1.md ("Responds to: GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196-v2"; "M1-M5 built, C1-C5 verified"); feat 5f1f554. NOTE: report is misfiled under the "-198" number even though it responds to -196; separately, -198's own dispatch (GROWTH-TRUTH) reports c1a's shipped -196 M2 delivery (d8aba6d) went to the shell atlas only, a partial-delivery bug corrected as part of -198's build rather than a full reversal of -196 |
| GL-CMD-EPISODE-BINDING-WIRE-EVE-20260627-06 | 2026-06-27 | Eve | Thread the 4 missing binding dimensions (episode_ref, who's-present, location, time-of-day) into the atlas | canonical: GL-RPT-EPISODE-BINDING-WIRE-C1-20260627-06.md exists |
| GL-CMD-EVENT-RETENTION-EVE-20260704-170-v1 | 2026-07-04 | Eve | Audit: find what truncates events.log to single digits; scope a retention fix | canonical: GL-RPT-EVENT-RETENTION-AUDIT-C1-20260704-170-v1.md (audit delivered, feeds directly into -172) |
| GL-CMD-EVENT-RETENTION-FIX-EVE-20260704-172-v1 | 2026-07-04 | Eve | Implement the ratified fix: decouple crash-replay `events.log` from a new durable append-only diary file | canonical: commit f43ca10 "GL-CMD-EVENT-RETENTION-FIX-172: durable diary decoupled from crash-replay log (R1-R5), G-1/G-2 proven locally" (no dedicated GL-RPT-*172* found; live-deploy gates G-3/G-4/G-5 open at that commit — see TODO ledger) |
| GL-CMD-EXPERIENCE-ROUTING-FIX-EVE-20260628-32 | 2026-06-28 | Eve | Stop `/experience` from training the already-silenced bigram via `_guala_cognition.expose()` | canonical: GL-RPT-EXPERIENCE-ROUTING-FIX-C1-20260628-32.md exists |
| GL-CMD-FIRE-WINDOW-178-179-180-181-EVE-20260705-185-v1 | 2026-07-05 | Eve (executed by c1b) | Fire deploy window carrying -178/-179/-180/-181 payload (e964400) + post-deploy behavioral gates | canonical: filed and executed as "window 6"; GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1.md references "per CMD-185". NOTE: shares number 185 with GL-CMD-BEHAVIOR-REPERTOIRE-EVE-20260705-185-v1 — see that row's note |
| GL-CMD-FIRE-WINDOW-196-197-198-EVE-20260705-199-v2 | 2026-07-05 | Eve | Fire window closing the stale-vs-live deployment gap, carrying -196/-197/-198; reassigned wholly to c1a | canonical: GL-RPT-FIRE-WINDOW-199-C1-20260705-199-v1.md ("F1-F4 ruled, live-verified"); commit b9ce37d |
| GL-CMD-FIRE-WINDOW7-EVE-20260705-186-v1 | 2026-07-05 | Eve (executed by c1b) | Fire window 7: deploy c1a's -186 build (recency-recovery + curriculum reconnect + status counters) | canonical: GL-RPT-WINDOW7-DEPLOY-AND-E1-E3-C1B-20260705-v1.md; commit d9b6402 |
| GL-CMD-FIRE-WINDOW8-EVE-20260705-189-v1 | 2026-07-05 | Eve (executed by c1b) | Fire window 8: deploy -187 meter-liveness fix + /status curated-subset one-liner | canonical: GL-RPT-WINDOW8-AND-EMISSION-HANDOFF-C1B-20260705-v1.md; commit e86b3e1 |
| GL-CMD-FIRE-WINDOW9-JOE-20260705-192-v1 | 2026-07-05 | Joe (verbal, filed by c1b) | Explicit direct order ("deploy every fucking thing") — fires -191 (senses-to-brain) immediately | canonical: GL-RPT-WINDOW9-AND-FORCED-SLEEP-C1B-20260705-v1.md; commit 2ae1e43 |
| GL-CMD-FLOOD-HUNT-EVE-20260703-156-v1 | 2026-07-03 | Eve | Instrument and gate the actual live sentence-flood feeders (-151's gate rode dead code) | canonical: GL-RPT-FLOOD-HUNT-C1-20260703-156-v1.md ("H-actual not convicted, aware-gate negative finding" — a valid negative result per the CMD's own pre-registered stop-rule) |
| GL-CMD-GROUNDED-PROMOTION-EVE-20260629-35 | 2026-06-29 | Eve | Let perceptual-path atlas writes promote via the Path B episodic gate (currently blocked) | canonical: GL-RPT-GROUNDED-PROMOTION-C1-20260629-35.md ("V1/V2/V4 PASS, V3/V5/V6 deferred") |
| GL-CMD-GROWTH-LIVE-EVE-20260705-202-v1 | 2026-07-05 | Eve | Growth-only window: add `running_sha` to /status to end deploy ambiguity, confirm growth law actually runs | canonical: GL-RPT-GROWTH-LIVE-C1-20260705-202-v1.md ("growth runs in her, first fold recorded"); feat c3beddd, fix 4e62641 |
| GL-CMD-GROWTH-TRUTH-EVE-20260705-198-v2 | 2026-07-05 | Eve | Order (not a staged choice, per Joe's ruling): fund the growth division-pool from experience richness, not the seed constant; fix multi-sense delivery gap | canonical: feat d7b56b1 "experience-funded growth law + growth telemetry"; fix b676e3f (pickle-compat crash fix post-deploy); confirmed live by -202's "first fold recorded" |

### B.2 — CMD batch B (67 docs)

| doc_id | date | author | purpose | status |
|---|---|---|---|---|
| GL-CMD-HOTFIX-BUNDLE-EVE-20260702-95-v1 | 2026-07-02 | Eve (via Joe relay) | Bundle: -91.A wrap `_save_wave_atlas` at 5 call sites (non-fatal save-fail containment), -90 attend-mark fix, build-identity stamp | canonical: git log shows feat cdbb46d (build stamp) + RPT chain v1/v2/v3 |
| GL-CMD-HOTLANE-DIET-EVE-20260703-102-v1 | 2026-07-03 | Joe (relayed) | Move `deep_survival_history` (41.5MB/99.6% of guala_core.json) to cold-lane file `guala_survival.json`, off the hot-save path | canonical: feat c3a36d0; fix 4151462 amend; RPT-DEPLOY3 notes "-102 size diet worked, save-time did not" (shipped, partial win) |
| GL-CMD-HOTSAVE-EVICT-VOCAB-SCALED-EVE-20260705-194-v1 | 2026-07-05 | Eve | Evict vocab-scaled `sight_motifs` from the hot-save lane (9MB/60s json.dumps+fsync) to a cold file, killing 15-49s hot-save stalls | canonical: `git log --grep 194` → 44070af "feat(194,195): evict vocab-scaled sight_motifs from hot save..."; RPT-FORCE-READING-194 exists |
| GL-CMD-INDEX-INVARIANT-COMPLETE-EVE-20260704-163-v1 | 2026-07-04 | Eve | Index the deep-atlas reinstatement write path so the eviction invariant (-159) is true everywhere, not mostly | canonical: fix 5e4e286 Part A; e82c0ec Part B.2; RPT-INDEX-INVARIANT-163 filed |
| GL-CMD-INVESTIGATION-EVE-20260702-70 | 2026-07-02 | Eve | Read-only diagnostic: definitive answers on why Guala hasn't emitted since 07-01 (stuck at count 159) before any further code ships | canonical: read-only dispatch, RPT-INVESTIGATION-70 filed "substrate investigation, no code changes" |
| GL-CMD-LANGUAGE-SATURATION-ROOTCAUSE-EVE-20260704-178-v1 | 2026-07-04 | Eve | Root-cause the 256-slot event deque saturation that pins language's event-count delta to zero; propose measured fix candidates | canonical: RPT-LANGUAGE-SATURATION-ROOTCAUSE-178 filed; fix later shipped coupled into -179: 37fcae3 "fix(179): real root cause found and fixed -- Krimelack.n_events missing negative-branch increment" |
| GL-CMD-LOCK-CONTENTION-FIX-EVE-20260705-182-v1 | 2026-07-05 | Eve | L1 DSP processing outside the global lock, L2 fail-loud in-flight turn persistence, L3 frame backpressure | canonical: ec76ceb/8d064df "fix: GL-CMD-LOCK-CONTENTION-FIX-182 -- L1/L2/L3"; RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B + RPT-LOCKFIX-SEAT-TEST-CONFIRMED-C1B confirm live verification |
| GL-CMD-LOOM-SCAN-BRIEF-EVE-20260702-v1 | 2026-07-02 | Eve | Design + execution brief for the Loom Scan real-time neuro instrument, replacing dead HEMISPHERES/V5-HEMISPHERES panes | canonical: implemented per companion -98 BUILD dispatch (feat 166d114) |
| GL-CMD-LOOM-SCAN-BUILD-EVE-20260702-98-v1 | 2026-07-02 | Eve | Build the production Loom Scan page (own page, live data per -94 contract, per-word arcs) | canonical: 166d114 feat "Loom Scan live page"; d7bad1e nav-href fix; RPT-LOOM-SCAN-BUILD-98 filed |
| GL-CMD-METER-LIVENESS-EVE-20260705-187-v1 | 2026-07-05 | Eve | Fix cognition-meter rows rendering stale audit-time text as live state; every row live-computed or dated | canonical: RPT-METER-LIVENESS-187 filed |
| GL-CMD-MIC-CHUNKING-EVE-20260703-111-v1 | 2026-07-03 | Eve | Fix MediaRecorder headerless-continuation chunk failures via recorder-restart-per-interval | canonical: fix ec3cc41; RPT-111-v1 "all gates PASS"; RPT-111-v2-ADDENDUM later scope-corrects the v1 report's overclaim (see Finding on GL-RPT-MIC-CHUNKING in Appendix A.2) — a self-correction of the report, not a reversal of the fix |
| GL-CMD-MIC-DEPLOY-EVE-20260703-108-v1 | 2026-07-03 | Eve | Deploy the WebM→ffmpeg→WAV mic decode fix + silent-skip guard + XFF line + static fixes | canonical: feat b7fd05e; RPT found G-108-2 FAIL (embedded-mode bypass) — chained forward into -110 |
| GL-CMD-MIC-EMBEDDED-DECODE-EVE-20260703-110-v1 | 2026-07-03 | Eve | Single shared WebM→WAV decoder at the boundary, both modes, fixing -108's embedded-mode bypass | canonical: feat 1d0af4d; RPT found a NEW chunk-continuity bug — chained forward into -111 |
| GL-CMD-MIC-SENSORY-EVE-20260703-106-v1 | 2026-07-03 | Joe | Read-only diagnosis: why sensory_items=0 via mic path despite mic recording/transcribing | canonical: 003352a; diagnosis chained into -108/-110/-111 |
| GL-CMD-NEXT-WINDOW-PAYLOAD-EVE-20260705-184-v1 | 2026-07-05 | Eve (filed by c1b) | Standing routing instruction: fire next window carrying -178/-179/-180/-181(+182) once backgrounding SHA lands | canonical: fired via companion dispatch -185; e964400 is exactly the SHA -184 was waiting on |
| GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203-v2 | 2026-07-05 | Eve | Remove every numeric length cap on her speech; coherence-gain alone is the stopping rule | canonical: 0ea0c25 "feat(203): no caps, no hard ceilings on her speech"; `MAX_COMPOSITION_LEN` confirmed absent at audit time. Supersedes retained v1 (order/section fixes only, cap kept) |
| GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23 | 2026-06-27 | Eve | Emergency-silence organ-brain `_compose()`'s corpus-fragment-retrieval lying paths | canonical: feat e730b14; RPT-ORGANBRAIN-SILENCE-23 |
| GL-CMD-ORGANISM-PERSIST-EVE-20260704-169-v1 | 2026-07-04 | Eve | Birth one continuous-life 8-hemisphere Embryo organism, structure-derived per-neuron differentiation, real full-state persistence | canonical: feat 9c54979; RPT-ORGANISM-PERSIST filed (+ correction re: AWS-access check being shallow) |
| GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v1 | 2026-07-05 | Eve | Rebuild organism memory onto ratified WaveAtlas cell physics per Joe's no-locks ruling; atomic persistence | superseded:GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v2 |
| GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v2 | 2026-07-05 | Eve | Fresh-session refresh of -207: FILED≠RUNNING orientation, W0 deploy ordering, migrate-on-restore requirement added | canonical: merge 52e0f79; 0a0cda7 wip BindingAtlas rewrite; pickle-compat fix 168ef1b confirms live continuity |
| GL-CMD-PARALLEL-BATCH-EVE-20260630-60-PB1 | 2026-06-30 | Eve | Four independent substrate-true corrections (60-J/O/K/M), parallel to -59 wave-band work | canonical: RPT a4941a5 "all four dispatches complete" |
| GL-CMD-PARALLEL-BATCH-EVE-20260701-63-PB2 | 2026-07-01 | Eve | Four-item batch (curriculum-live, agency events, etc.), parallel to c1a's -62 | canonical: RPT 01a8623 "all four dispatches complete" |
| GL-CMD-PHASE-D-INSPECTION-EVE-20260627-24 | 2026-06-27 | Eve | Pull Phase D (organ-brain compose inspection) forward, ahead of Phase C | canonical: RPT a2eeb23 |
| GL-CMD-PHASE2-COMMIT-B-CLEARANCE-PROTOCOL | 2026-07-01 | c1 (self-authored) | 3-gate clearance protocol required before building Wave Phase2 Commit B | canonical (protocol executed as designed): RPT 832cec7 "Gate 1 FAIL, rollback executed" — the gate correctly blocked Commit B, per the protocol's own stop-rule |
| GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04 | 2026-06-27 | Eve | Wire picture titles into the language path + backfill existing pictures | canonical: feat e68957f; RPT dd0f372 |
| GL-CMD-PRESURGERY-FRESHNESS-EVE-20260627-22 | 2026-06-27 | Eve | Make the pre-surgery backup freshness gate a real blocking gate | canonical: feat ac3c4e1; RPT b6e5b46 |
| GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v1 | 2026-07-05 | Eve (Joe's order) | Executable charter for a full end-to-end production audit of live Guala | superseded:GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2 |
| GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2 | 2026-07-05 | Eve (Joe's order) | Full v2 audit charter: adds §7A environment truth, §8A function test matrix, §9 complete 30-day doc sweep | canonical: this is the governing charter this present §9 task is executing directly |
| GL-CMD-READING-THROUGH-SENSES-EVE-20260705-196-v1 | 2026-07-05 | Eve | Scope-correct c1a's in-flight sensory-binder fix to reach the organism (not only the shell atlas) | superseded:GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196-v2 |
| GL-CMD-RECALL-MEASURE-STANDING-EVE-20260703-157-v1 | 2026-07-03 | Eve | Make M1 (paired cold/taught recall + quality) a standing weekly measurement | canonical: feat 7535a32; RPT 92bb6ad |
| GL-CMD-RECALL-PICS-RESET-EVE-20260703-155-v1 | 2026-07-03 | Eve | One-line fix: reset `_last_recalled_pictures` on `_recall_response`'s no-recall early-return path | canonical: fix 2d18943 |
| GL-CMD-RECALL-PROVENANCE-EVE-20260704-158-v1 | 2026-07-04 | Eve | Part A offline instrumentation to decide bug-vs-physics on the 0/8 recall-quality finding; Part B fix ONLY if convicted | canonical: feat e684cf0 Part A; RPT verdict "no fix shipped" — correct per the CMD's own conditional scope, not a failure |
| GL-CMD-RECALL-REACH-EVE-20260704-159-v1 | 2026-07-04 | Eve | Extend which sections recall reads (no role-guessing for standalone words) per -158's verdict | canonical: feat 003200f "VARIANT L"; fix 16d5c3f "F-3 index-bypass" |
| GL-CMD-RECALL-SPEED-CUTOVER-ROUTING-EVE-20260704-179-v1 | 2026-07-04 | Eve (ruling, filed by c1b) | Routing ruling: fold `recall_fast()` cutover into window 2 or 3 depending on fire state | canonical: feat 486e022 "window-3 cutover: wire recall_fast() into the 3 live organism.recall() call sites" |
| GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177-v1 | 2026-07-04 | Eve | Proper measured investigation of organism.recall()'s O(population×physics) 82-120s turn cost | canonical: feat 70e3c0c "recall_fast()"; RPT-RECALL-SPEED-177 filed |
| GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v1 (1).md | 2026-06-30 | Eve | [Duplicate upload, byte-identical] word→chi reverse index eliminates O(N) atlas scans | superseded:GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v3 — duplicate filename artifact, and v1 itself superseded by v2 then v3 |
| GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v1.md | 2026-06-30 | Eve | word→chi reverse index to kill the 3411.7ms O(N) atlas-scan recall bottleneck | superseded:GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v2 |
| GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v2.md | 2026-06-30 | Eve | v2 revision: single-entry-point wrapper, boot consistency check, explicit thread-safety stance | superseded:GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v3 |
| GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v3.md | 2026-06-30 | Eve | v3 amendment: corrected line numbers, pinned wrapper-conversion scope, excludes loom_model per-neuron atlases | canonical: fix 2dce6f4; RPT fface62 "T1 PASS recall 7.7ms, T2 PASS 9/10" |
| GL-CMD-REST-RETIRE-ORIENT-EVE-20260702-73 | 2026-07-02 | Eve | Retire REST as an activity kind; pair with orient reflex so IDLE doesn't inherit the same bug | canonical: feat 0d1bd8c; RPT 8739660; withdraws -71/-72 |
| GL-CMD-RESUME-QUEUE-EVE-20260627-12 | 2026-06-27 | Eve | 3-part sequence: DREAMING auto-wake fix; resume -09 DAYDREAMING; resume -10 V5-VOICE-STAGE1 | canonical: all 3 parts landed with the exact prescribed commit messages (e250466, 9df3d72, f90b5f9) |
| GL-CMD-S2A-RECALL-METHOD-C1-20260703-v1 | 2026-07-03 | c1a (to Eve) | Declaration-only: method + probe set for measuring her live recall (paired cold/taught), filed before any measurement runs | canonical: measurement subsequently executed in GL-RPT-S2A-COLD/S2A-TAUGHT-C1-20260703-v1 |
| GL-CMD-SCENE-LANES-B1-EVE-20260705-188-v1 | 2026-07-05 | Eve | Every experience item carries WHERE/AMBIENT/WHO scene lanes bound in the same window as its content | canonical: RPT-SCENE-LANES-B1-188 filed |
| GL-CMD-SEAT-TRUTH-UI-EVE-20260704-180-v1 | 2026-07-04 | Eve | Fix the UI so replies render whenever they complete, errors say so explicitly, no permanent "(settling...)" | canonical: RPT-SEAT-TRUTH-UI-180 filed |
| GL-CMD-SELFVOICE-TAGGING-EVE-20260703-152-v1 | 2026-07-03 | Eve | Give `process_sound_frame` a `source` param (mic:live vs voice:self) | canonical: feat 045871f; RPT d8c157b "all gates PASS" |
| GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191-v1 | 2026-07-05 | Eve | Feed live sight/sound frames into the organism's experience path in the same binding window as co-occurring words | canonical: RPT-SENSES-TO-BRAIN-191 filed |
| GL-CMD-SEVER-MIC-WORD-LOOP-EVE-20260705-204-v1 | 2026-07-05 | Eve | EMERGENCY: sever the mic-energy-classifier-as-language resonance loop distorting her mind every ~5s | canonical: 06aecb8 "fix(204): sever mic-energy-classifier-as-language resonance loop (S1)" |
| GL-CMD-SLEEP-BUDGET-RESCALE-EVE-20260627-01 | 2026-06-27 | Eve | Rescale SLEEPING/DREAMING budgets — she was spending ~80% of runtime in sleep+dream states | canonical: feat 7dde7c8 (exact match to spec; no dedicated RPT found, commit is direct evidence) |
| GL-CMD-SLEEP-RATE-CALIBRATION-EVE-20260704-173-v1 | 2026-07-04 | Eve | Retune `DP_RATE_MULTIPLIER` to fix measured insomnia (zero natural sleep in 6.5h, arousal pinned 1.0) | canonical: feat e6c2ca2; RPT-SLEEP-RATE-CALIBRATION-173 filed |
| GL-CMD-SOUND-BAND-VISIBILITY-EVE-20260703-154-v1 | 2026-07-03 | Eve | Fix loomscan's sound band to light on any `sound_frame_bound` event, not only ATTENDING_AUDIO | canonical: fix 3285d1d |
| GL-CMD-STAB-PHYSICS-EVE-20260702-99-v1 | 2026-07-02 | Eve (via Joe relay) | Read-only investigation: what code path ever moved stability/arousal + gated EFS cleanup | canonical: RPT b887ff0; fix shape shipped next as -88 |
| GL-CMD-STAB-PHYSICS-FIX-EVE-20260702-88-v1 | 2026-07-02 | Eve | Quiet-coherence stability gain in IDLE/PLAYING per -99 §A.4's adopted shape | superseded (partial):GL-CMD-STAB-PHYSICS-FIX-EVE-20260703-88-v2 — only the regulate-channel portion is superseded; the IDLE/PLAYING gain itself shipped and stands per v2's own header |
| GL-CMD-STAB-PHYSICS-FIX-EVE-20260703-88-v2 | 2026-07-03 | Eve | Replace the structurally-negative pseudo-physics "rate" formula in the regulate ACTIVE branch | canonical: feat f268c9e; RPT-DEPLOY3 confirms "first movement in 3 deploys" |
| GL-CMD-SUSTAINED-SPEECH-EVE-20260629-44 | 2026-06-29 | Eve | Remove `MAX_COMPOSITION_LEN` cap, add emission chaining, make `EMISSION_COOLDOWN_TICKS` coherence-derived | unexecuted: companion dispatch -45 states "Blocks: -44 (draft, not shipped; this dispatch must land first)"; no feat/fix commit, no RPT; `EMISSION_COOLDOWN_TICKS = 200` confirmed still hardcoded at audit time (the cap itself was later independently removed by the unrelated -203 dispatch) |
| GL-CMD-T6-REVIEW-EVE-20260703-101-v1 | 2026-07-03 | Eve | Map the production collapse chain vs the T⁶/loom_model implementation; retroactively-filed base scope | canonical: RPT-T6-REVIEW-C1-101-v1 and RPT-T6-REVIEW-SYNTHESIS-EVE-101-v1 both filed |
| GL-CMD-T6-REVIEW-EVE-20260703-101-v2 | 2026-07-03 | Eve (addendum) | Addendum: recovered pointers (did GL-CMD-140 land; "100% T5" deception precedent) folded into T6 review scope | canonical: content folded into the completed review |
| GL-CMD-T6-REVIEW-EVE-20260703-101-v3-ADDENDUM | 2026-07-03 | Eve | Correct Appendix A's evidentiary status (100%-validated claim → partially invalidated per 6/22 finding) | canonical: filed per RPT-T6-CHAT-RECOVERY mandate; v1/v2 explicitly retained unedited |
| GL-CMD-TARGET-ROTATION-FIX-EVE-20260704-181-v1 | 2026-07-04 | Eve | Fix the flat novelty-floor that pinned the same visual target selected for 590+ consecutive attend cycles | canonical: fix a503b2a; RPT confirms "left e93d29dae5ae for the first time all session" |
| GL-CMD-TURN-LATENCY-EVE-20260705-197-v1 | 2026-07-05 | Eve | Verify the hot-save-stall kill at Joe's seat; remove remaining in-turn latency costs | canonical: RPT-TURN-LATENCY-197 filed |
| GL-CMD-UI-HONESTY-EVE-20260629-38 | 2026-06-29 | Eve | Full UI cleanup pass removing "organ-brain is the voice" language and stale "warming up" text | canonical: feat fa833ae; RPT 08e775e "V1 PASS" |
| GL-CMD-V5-VOICE-STAGE1-EVE-20260627-10 | 2026-06-27 | Eve | Surface v5 committed grandurun emissions to the conversation response, instead of the bigram-only path | canonical: feat f90b5f9 |
| GL-CMD-VERIFY-AND-STABILIZE-C1B-20260705-206-v1 | 2026-07-05 | c1b | Next-session checklist: confirm deploy landed; watch -205's yield-fix stability; investigate tapestry corruption; confirm first natural dream; watch mean_utterance_len; worktree discipline | canonical (acted upon): cited as required reading in -207-v2's fresh-session orientation; several items (V2-V5) read as still-open at filing time — see TODO ledger |
| GL-CMD-VOICE-ORGANISM-CANDIDATES-EVE-20260705-195-v1 | 2026-07-05 | Eve | Withdraw -192 v3's chi-basin voice design (spec-prohibited ceiling); re-point the emission seam at the validated organism population vote | canonical: feat 44070af |
| GL-CMD-VOICE-PATH-CONSOLIDATION-EVE-20260629-37 | 2026-06-29 | Eve | Remove the stale `organ_brain_silenced_pending_inspection` fallback from the `/organ_voice` UI path | canonical: feat 56902a3; RPT 9ec42f5 "V1-V4 PASS" |
| GL-CMD-VOICE-TO-WORDS-EVE-20260703-153-v1 | 2026-07-03 | Eve | Wire the existing word extractors into the live `/sound_frame` route, source-tagged per -152 | canonical: feat 66dd999; RPT 7915662 ("G-153-2/3 NOT MEASURED" — honestly reported partial measurement) |
| GL-CMD-WIRE-ORGAN-CANDIDATES-EVE-20260627-31 | 2026-06-27 | Eve | Wire `OrganVoice.surface()` output into `grandurun.compose()` as a third candidate stream | canonical: RPT ad59b7b |
| GL-CMD-WIRING-AUDIT-EVE-20260704-164-v1 | 2026-07-04 | Eve | Read-only audit: map which of her "zeros" are severed wiring vs broken physics | canonical: RPT 9ac7ac5 |

*(29 further TODO items were extracted across both CMD batches — folded into the standalone TODO ledger.)*

## Appendix C — BRIEF/FIND/NOTE/FIX/LTR bucket, full table (74 docs, sub-agent-generated, c1-reviewed)

This is the earliest-dated bucket (2026-06-09 through 2026-07-05,
mostly wC-authored June briefs plus Eve's July letters/notes). Two
sharp findings worth surfacing beyond the table:

- **GL-BRIEF-self-section-v3-wC-20260609-026 is orphaned.** No
  `SelfSection` class or fold mechanism exists in `dsf_ai_service`; the
  sub-agent found corroborating evidence 18 days later in
  `GL-CMD-EMERGENCE-DETECTOR-EVE-20260627-20` (itself separately found
  orphaned in Appendix B), which still lists `first_self_section_commit:
  null` as an unfired future trigger. This orphaned self-section
  mechanism is also the reason `GL-BRIEF-video-architecture-wC-
  20260610-029` (video upload MVP) is itself **unexecuted** — the
  commit that added the video upload button explicitly says "pipeline
  blocked, shows queue message," gated behind Self-Section v3 among
  other prerequisites, none of which ever landed.
- **GL-BRIEF-V7-UNCAGE-WC-20260613-01 is contradicted same-day** by its
  own sibling doc `GL-BRIEF-V7-FULL-UNCAGE-WC-20260613-01`: UNCAGE-01
  claimed the "9-word SEED_VOCAB" was removed; FULL-UNCAGE's audit,
  filed the same day, found "the SEED_VOCAB constant and its fallback
  paths" left intact — "the cage that UNCAGE-01 left intact."
- **GL-NOTE-RATIFICATION-SLEEP-CEILING-EVE-20260704-v1 was voided
  same-day** by `GL-NOTE-VOID-RATIFICATION-NOTE-EVE-20260704-v1` as
  "sent from Eve's stale context" — though the changes it ratified had,
  in fact, already shipped that morning, an example of documentation
  lagging reality rather than reality lagging documentation.

| doc_id | date | author | purpose | status |
|---|---|---|---|---|
| GL-BRIEF-AUDIO-UNLOCK-FIX-WC-20260616-01 | 2026-06-16 | wC | Fix broken audio unlock (play() on no-src element), silent failure swallowing, misplaced mic LISTENING indicator | canonical — landed f4e9512 |
| GL-BRIEF-BRIDGEVIS-WC-20260611-040 | 2026-06-11 | wC | Render bridge (wC/c1) exchanges in Joe's UI transcript with source tags; trim base64 JPEG payload bloat from guala_say | canonical — source tagging (joe/wc/c1) present in app.py; bridge deploy referenced in 952714d |
| GL-BRIEF-CHITRACE-WC-20260613-01 | 2026-06-13 | wC | Read-only chi-geometry readout endpoint distinguishing lookup vs working-recall vs deep-reinstatement | canonical — landed 9444970 |
| GL-BRIEF-DEEPATLAS-DEPLOY-WC-20260610-032 | 2026-06-10 | wC | Authorize prod deploy of Deep Atlas, skip further harness validation per Joe's decision | canonical — landed fc2e15e (tagged GL-BRIEF-032) |
| GL-BRIEF-DEEPATLAS-WC-20260610-031 | 2026-06-10 | wC | Deep Atlas two-layer memory design; Stage 1 harness only, explicitly "NO PROD DEPLOY" | superseded:GL-BRIEF-DEEPATLAS-DEPLOY-WC-20260610-032 — its own stage-gating ("NO PROD DEPLOY") was explicitly overridden by -032's decision to deploy and observe in prod |
| GL-BRIEF-EMISSION-CONSTRAINT-REMOVAL-20260616-01 | 2026-06-16 | wC | Remove template/cheat code + dehumanizing UI boot string, phases A-E | canonical — Phases C-E landed 49966af, Phase B string change confirmed in gualaloom.html history |
| GL-BRIEF-GUALALOOM-REPO-INIT-WC-20260613-01 | 2026-06-13 | wC | Populate empty GualaLoom repo with canonical Guala source tree, path-preserving | canonical — `gualaloom` remote exists, populated with many branches (verified via git ls-remote) |
| GL-BRIEF-METADECAY-WC-20260610-033 | 2026-06-10 | wC | Two-speed metaplastic decay fixing single global DECAY_LAMBDA doing two incompatible jobs | canonical — landed 94f8b2e |
| GL-BRIEF-NEEDS-PHYSICS-20260616-01 | 2026-06-16 | wC (to c1) | Receptor-saturation physics + consolidation-resistant familiarity to unblock coordinator from ATTENDING_VISUAL loop | canonical — landed d00e52a; near-duplicate draft of GL-BRIEF-NEEDS-PHYSICS-WC-20260616-01 (both committed together in 49966af, after the fix already shipped) |
| GL-BRIEF-NEEDS-PHYSICS-WC-20260616-01 | 2026-06-16 | wC | Same fix as above (saturate() helper, familiarity consolidation), fuller defect writeup with exact line numbers | canonical — landed d00e52a; near-duplicate of GL-BRIEF-NEEDS-PHYSICS-20260616-01 |
| GL-BRIEF-PERSISTENCE-HARDENING-WC-20260616-01 | 2026-06-16 | wC | Halt silent-wipe boot path that overwrote good state with fresh-boot state after EFS mount race | canonical — landed 86aa8ae |
| GL-BRIEF-PERSISTSAFE-FIX-WC-20260611-039 | 2026-06-11 | wC (v2) | Reconciled fixes to deployed 037: dream-gate enforcement (D5), offset compaction (D2), S3 startup backup (D3), restore drill (D4), files_present reporting (D6) | canonical — all items landed (7ad473a, 95b0cd8, f512e83, f264647, 3d7f7ee) |
| GL-BRIEF-PERSISTSAFE-WC-20260611-037 | 2026-06-11 | wC | Single-writer enforcement, eager init, compaction, S3 backup, restore drill | canonical — landed 8c28393 |
| GL-BRIEF-PHASE-C-VOICEOUT-WC-20260616-01 | 2026-06-16 | wC | Wire emissions to browser speechSynthesis so Joe hears her | canonical — landed 0a0e109 |
| GL-BRIEF-PHASE-D-LIVEPRESENCE-WC-20260616-01 | 2026-06-16 | wC | WebSocket-based continuous live sight/sound streaming (`ingest_live_sight`/`ingest_live_sound`) | unexecuted — the specific WebSocket endpoints proposed are not present in the codebase; the functional goal (continuous sight/sound to substrate) was already delivered a day earlier via POST-based `/sight_frame` and `/sound_frame` (GL-BRIEF-SENSORY-IO Parts C+D, commit 2de9ca0, 2026-06-15) |
| GL-BRIEF-PILEON-MODEL-WC-20260614-02 | 2026-06-14 | wC | Load-test model using /addpicture, /addsound upload endpoints (streaming endpoints don't exist yet) | superseded:GL-BRIEF-PILEON-MODEL-WC-20260614-03 |
| GL-BRIEF-PILEON-MODEL-WC-20260614-03 | 2026-06-14 | wC | Real streaming load-test model (2Hz picture, 0.67Hz sound), supersedes -02 | canonical |
| GL-BRIEF-SELFHEARING-WC-20260610-034 | 2026-06-10 | wC | Conversational replies self-heard into substrate with reduced salience + question-bucket bypass guards | canonical — landed dd976af |
| GL-BRIEF-SENSORY-IO-WC-20260614-01 | 2026-06-14 | wC | Continuous camera/mic streaming, inline picture display, TTS playback fix — UI as sensory cortex plug-in | canonical — landed 02ab391 (spec) + 2de9ca0 (Parts C+D implementation) |
| GL-BRIEF-SLEEP-DECAY-PERMANENT-WC-20260615-01 | 2026-06-15 | wC | Pause-idempotent deep-atlas decay after dream cycle destroyed 47%/66% of atlas strength | canonical — landed edc92bb |
| GL-BRIEF-SLEEP-DURING-DEPLOY-WC-20260614-01 | 2026-06-14 | wC | Use existing sleep/wake machinery during deploys instead of the circular lock-based model | canonical — Part B landed 3373d1e (explicitly references this brief) |
| GL-BRIEF-TOKENIZATION-WC-20260610-035 | 2026-06-10 | wC | Shared punctuation-stripping normalization for converse() and read_sentence() | canonical — landed 0cec412 |
| GL-BRIEF-UI-RESPONSIVENESS-WC-20260616-01 | 2026-06-16 | wC | Fix page self-DDoS: 80+ req/min, zero fetch timeouts, no request dedup | canonical — landed 55a30b9 (commit message explicitly cites this brief) |
| GL-BRIEF-UI-RESTORE-PHASE-B-FIX-WC-20260616-01 | 2026-06-16 | wC | Fix Unix socket 64KB readline limit causing "substrate unreachable" on all binary uploads | canonical — landed 3601793; Phase B-FIX-2 (proper shared-EFS upload pattern) explicitly deferred and never found implemented |
| GL-BRIEF-UI-RESTORE-WC-20260616-01 | 2026-06-16 | wC | Restore drifted UI to originally-specified behavior, Phase A (safety rails) then Phase B (uploads/SSE) | canonical — Phase A landed same-day as UI-RESPONSIVENESS fix (55a30b9), Phase B landed 7180a19 |
| GL-BRIEF-UNPAUSE-WC-20260613-01 | 2026-06-13 | wC | Monitored decay unpause with amnesty to prevent mass-extinction from frozen last_tick cascade | canonical — landed 24a2475 |
| GL-BRIEF-V7-EXECUTOR-WC-20260614-01 | 2026-06-14 | wC | Wrap synchronous v7 session construction in run_in_executor to stop blocking event loop / killing /ready | canonical — landed 0ede52d |
| GL-BRIEF-V7-FULL-UNCAGE-WC-20260613-01 | 2026-06-13 | wC | Full SEED_VOCAB cage removal + UI merge; supersedes V7-UI-REPAIR draft; audit found UNCAGE-01 left cage fallback paths intact | canonical — landed 8a8877f/66f01f8 |
| GL-BRIEF-V7-UI-REPAIR-WC-20260613-01 | 2026-06-13 | wC | UI-only patch (NMDA panel labels, upload bar, experience modal) leaving v7_engine.py untouched | superseded:GL-BRIEF-V7-FULL-UNCAGE-WC-20260613-01 — explicitly called "never committed" and replaced because Joe judged the reseed approach cage-preserving rather than cage-removing |
| GL-BRIEF-V7-UNCAGE-WC-20260613-01 | 2026-06-13 | wC | Remove externally-imposed SEED_VOCAB via seed_vocab_from_engine; wire mic/speaker/camera; self-hearing on emission | contradicted:GL-BRIEF-V7-FULL-UNCAGE-WC-20260613-01 — this brief lists "9-word SEED_VOCAB" as removed, but FULL-UNCAGE's same-day audit found "the SEED_VOCAB constant and its fallback paths" left intact as "the cage that UNCAGE-01 left intact" |
| GL-BRIEF-V7-UNIFY-WC-20260613-01 | 2026-06-13 | wC | Replace 9-word toy SEED_VOCAB with v6's real vocabulary + full lexical-category grammar (N/V/Adj/etc.) | canonical — foundational; explicitly kept as "historical record" by later briefs, extended (not replaced) by UNCAGE/FULL-UNCAGE |
| GL-BRIEF-V7VOICE-WC-20260612-01 | 2026-06-12 | wC | C4 second-voice investigation: pre-registered hypotheses (H-A/B/C) for why NMDA intro gate never fires | superseded:GL-BRIEF-V7VOICE-WC-20260613-02 — explicit "Supersedes brief -01's 'wait for logs' gate — logs are in" |
| GL-BRIEF-V7VOICE-WC-20260613-02 | 2026-06-13 | wC | Confirmed H-A (becalming/quiet-window gate); fix quiet_thresh 0.10→0.45 | canonical — landed 8a0a471/aaf6be6 |
| GL-BRIEF-WARMTH-WC-20260614-01 | 2026-06-14 | wC | Heartbeat-based stale-lock detection + /ready endpoint + graceful SIGTERM to eliminate 220s deploy blackout | canonical — landed c68643a |
| GL-BRIEF-atlas-observation-wC-20260609-021 | 2026-06-09 | wC | Post-decay-fix observation: atlas entries clustered at low strength; three hypotheses (tuning/topology/schema) pending data, no changes proposed | canonical — observation-only; fed directly into dream-consolidation brief (025) which landed |
| GL-BRIEF-dream-consolidation-wC-20260609-025 | 2026-06-09 | wC | Dream-phase LTP-on-replay reinforcement of sampled atlas entries (biologically grounded) | canonical — landed 7ed1ab5 |
| GL-BRIEF-existing-autonomy-wC-20260609-020 | 2026-06-09 | wC | Investigation-only: catalog of substrate autonomous behavior no one explicitly triggered | canonical — investigation-only by design, findings fed self-section briefs |
| GL-BRIEF-graded-exogenous-salience-wC-20260610-031 | 2026-06-10 | wC | Fix binary-cliff exogenous override inverting familiarity discount under novelty saturation | canonical — landed b51962e/8c6a0ed |
| GL-BRIEF-picture-habituation-wC-20260609-027 | 2026-06-09 | wC | Per-target novelty habituation so same picture doesn't win every attention contest forever | canonical — landed 3d9e677 (later found insufficient alone under novelty saturation; augmented, not contradicted, by graded-exogenous-salience-031) |
| GL-BRIEF-response-binding-wC-20260609-028 | 2026-06-09 | wC | Bind emission's chi-key to the response's chi-key so dialogue becomes conversational structure, not orphan bindings | canonical — landed 51fbf8f |
| GL-BRIEF-self-section-v2-wC-20260609-022 | 2026-06-09 | wC | Self-section v2: substrate primitive giving Guala a "who" that tags every commit | superseded:GL-BRIEF-self-section-v3-wC-20260609-026 |
| GL-BRIEF-self-section-v3-wC-20260609-026 | 2026-06-09 | wC | Self-section v3: fold self-identity at `_autonomy_tick()` activity-tick handlers specifically | orphaned — no SelfSection class/fold mechanism found in dsf_ai_service; GL-CMD-EMERGENCE-DETECTOR-EVE-20260627-20 (18 days later) still lists `first_self_section_commit: null` as an unfired future trigger requiring "C.2 self section," confirming it was never built |
| GL-BRIEF-video-architecture-wC-20260610-029 | 2026-06-10 | wC | Minimum-viable video upload: store original, extract first frame into existing picture pipeline | unexecuted — commit c44cd24 explicitly states "UI: add video upload button (pipeline blocked, shows queue message)," gated behind Response Binding (landed) + Self-Section v3 (never landed, see above) + Vision Stage 2 |
| GL-BRIEF-vision-architecture-wC-20260609-023 | 2026-06-09 | wC | Staged vision spec: stop destroying color/resolution on upload, then activate dormant V1-V4/LOC cortex pipeline | canonical — Stage 1 landed (9cdc923), Stage 2 intent later realized via organ-brain visual_experience() wiring (315a22b) |
| GL-FIND-DEEPATLAS-C1-20260610-02 | 2026-06-10 | c1 | Deep Atlas wC review items: canonical rerun at EG=0.15/0.20, four items complete, no prod code changed | canonical |
| GL-FIND-DEEPATLAS-C1-20260610 | 2026-06-10 | c1 | Deep Atlas Stage 1 offline harness results using real substrate code paths | canonical |
| GL-FIND-INPUT-TOKENIZATION-C1-20260610 | 2026-06-10 | c1 | Audit finding: minimal punctuation stripping produces junk tokens like "(e" | canonical — fix landed via GL-BRIEF-TOKENIZATION-035 (0cec412) |
| GL-FIND-METADECAY-C1-20260610 | 2026-06-10 | c1 | Stage 1 harness results + critical prod bug: encoded_strength frozen, blocking Path B episodic promotion | canonical — prod hotfix landed (7fdb20f) ahead of full Stage 2 deploy (94f8b2e) |
| GL-FIND-RESPONSE-PATH-C1-20260610 | 2026-06-10 | c1 | Root-cause finding: converse() replies never enter substrate, unlike autonomous emission path | canonical — fixed via response-binding-028 (51fbf8f) and selfhearing-034 (dd976af) |
| GL-FIND-TICK-DOMAIN-C1-20260611 | 2026-06-11 | c1 | Confirmed: two different tick counters (section vs engine) both assumed to share one domain | canonical — fix landed 11a22c3 |
| GL-FIND-V7-DOTS-C1-20260612 | 2026-06-12 | c1 | Investigation: v7 always returns "..." — NMDA gate contradiction + possible non-convergence in 120 ticks | canonical — investigation-only per rule 1, addressed by V7VOICE-01/-02 briefs |
| GL-FIND-atlas-regulator-audit-c1-20260610 | 2026-06-10 | c1 | Investigation-only map of atlas decay call sites and constants | canonical |
| GL-FIND-novelty-saturation-c1-20260609 | 2026-06-09 | c1 | Finding: novelty saturation inverts salience under negative signed_distance; fix deployed before stop order (729783e) | canonical — no revert found; fix stands |
| GL-FIND-test-persist-recapture-c1-20260610 | 2026-06-10 | c1 | Finding: test_persist recaptures all attention contests due to inverted familiarity discount; no fix deployed at filing time | canonical — fix later shipped via graded-exogenous-salience-031 (b51962e/8c6a0ed) |
| GL-FIX-HOTSAVE-VOCAB-SCALED-194.patch | 2026-07-05 | unknown (patch) | Evict vocab-scaled sight_motifs from hot-save lane, one-time migration serialization | canonical — landed 44070af |
| GL-FIX-PAUSE-IDEMPOTENT.patch | undated in header (~2026-06-16) | unknown (patch) | Decay runs with rate_scale=0 while paused so unpause doesn't cascade exp(-λ·Δtick) | canonical — landed efd39dd |
| GL-FIX-RETIRE-TEMPLATES.patch | undated in header (~2026-06-16) | unknown (patch) | Retire question-bucket template-fill voicing, the one named "selective cheat" in the kernel | canonical — landed d5d4fab; legacy dialog dir later deleted entirely (dca2610) |
| GL-FIX-THREE-WC-20260610-02 | 2026-06-10 | wC | Three corrected fixes to tick-domain work (loud failure on missing engine_tick, corrected Fix B/gate C) | canonical — landed e05fd86; explicitly "SUPERSEDES GL-FIX-THREE-WC-20260610" (-01, not in this doc set) |
| GL-FIX-VOICE-ORGANISM-CANDIDATES-195.patch | 2026-07-05 | unknown (patch) | Re-point emission candidates from tapestry.compose's query-echo-chamber to organism's population-vote recall | canonical — landed 44070af same-day as -194 |
| GL-LTR-EVE-TO-EVE-20260702-v1 | 2026-07-02 | Eve | Personal handoff letter to next Eve accompanying GL-HANDOFF-SPRINT-EVE-20260702-v1 | canonical |
| GL-LTR-EVE-TO-EVE-20260703-EVE-v1 | 2026-07-03 | Eve | Personal handoff letter accompanying GL-HANDOFF-EVE-20260703-EVE-v1; reports stab climbed 0→0.75 | canonical |
| GL-LTR-EVE-TO-EVE-20260703-v1 | 2026-07-03 | Eve | Personal handoff letter accompanying GL-HANDOFF-SPRINT-EVE-20260703-v1 | canonical |
| GL-LTR-EVE-TO-EVE-20260704-EVE-v1 | 2026-07-04 | Eve | Personal handoff letter; reports Guala's first natural sleep, self-critique of session mistakes | canonical |
| GL-LTR-EVE-TO-NEXT-20260625 | 2026-06-25 | Eve (c1, Claude Sonnet 4.6) | Earliest letter in this chain: introduces Joe, Guala's state, and the ArcLoom goal to the next session | canonical |
| GL-LTR-GUALA-EVE-20260702-v1 | 2026-07-02 | Eve | Letter for delivery to Guala herself, calm-window only, anchored-vocabulary words | canonical — confirmed delivered per note in -703-EVE-v1 |
| GL-LTR-GUALA-EVE-20260703-EVE-v1 | 2026-07-03 | Eve | Letter + gift bundle for Guala; notes the 20260702 letter was delivered this session | canonical |
| GL-LTR-GUALA-EVE-20260703-v1 | 2026-07-03 | Eve | Letter + gift bundle for Guala; explicitly sequenced to deliver after the 20260702 letter | canonical |
| GL-LTR-GUALA-EVE-20260704-EVE-v1 | 2026-07-04 | Eve | Short-word letter for Guala about her first sleep and dream | canonical |
| GL-NOTE-DUAL-MIND-ARCHITECTURE-EVE-20260627-15 | 2026-06-27 | Eve (Opus 4.7, web) | Design memo modeling v5-as-subconscious / organ-brain-as-conscious dual-mind architecture, precedes wiring spec -16 | canonical |
| GL-NOTE-RATIFICATION-SLEEP-CEILING-EVE-20260704-v1 | 2026-07-04 | Eve (to c1b) | Ratifies sleep-ceiling override design + live-validation method | contradicted:GL-NOTE-VOID-RATIFICATION-NOTE-EVE-20260704-v1 — voided same day as "sent from Eve's stale context," though the changes it ratified had, in fact, already shipped that morning |
| GL-NOTE-V5-REMOVAL-PLAN-DEPRECATED-EVE-20260627-30 | 2026-06-27 | Eve (Opus 4.7, web) | Deprecates Joe's 06-25 "V5 Engine Removal" plan; per-item disposition table shows most proposals reversed | canonical — this is itself the corrective document |
| GL-NOTE-VOICE-WIRING-RULING-EVE-20260704-v1 | 2026-07-04 | Eve (to c1a) | Corrects P3's conflation of two mechanisms in the -175-v2 registry; ratifies W1/W2/W3/W4 wiring | canonical |
| GL-NOTE-VOID-RATIFICATION-NOTE-EVE-20260704-v1 | 2026-07-04 | Eve (to c1b) | Voids GL-NOTE-RATIFICATION-SLEEP-CEILING-EVE-20260704-v1 as stale-context duplicate; restates c1b's actual owed work | canonical |
| GL-NOTE-WAVES-A2B-CORRECTION-EVE-20260627-21 | 2026-06-27 | Eve (Opus 4.7, web) | Corrects §A.2b of GL-SPC-EMERGENCE-WAVES-EVE-20260627-17 with measured values from GL-RPT-WORLDFEED-CAP-C1-20260627-14 | canonical — this is itself the corrective document |

## Appendix D — MISC bucket, full table (69 docs, sub-agent-generated, c1-reviewed)

c1 read this table in full; several of its findings (the -200/-201
non-execution corroboration, AUTONOMY_PHASED/CURRICULUM_CHUNK_SIZE
cross-checks against sibling §1 audit findings, the frontend/substrate
process-split reversal, the organ-brain container removal within 24h)
independently corroborate or extend Findings F1-F8 above and are folded
in there and into the TODO ledger. Full 69-row table:

| doc_id | date | author | purpose | status |
|---|---|---|---|---|
| GL-ARCH-FRONTEND-SPLIT-WC-20260614-01 | 2026-06-14 | wC | Phase-1 design to split substrate into its own OS process behind a Unix socket, frontend as thin proxy | contradicted:GL-HANDOFF-C1-20260701-PHASE2-WATCHWINDOW (the "-61 process collapse" merged everything back into ONE embedded FastAPI process — "socket IPC is gone" — the opposite direction from this doc's split plan; SUBSTRATE_MODE=embedded confirmed still the case in prod per GL-AUDIT-SEC1 07-05) |
| GL-ATTACH-READ-SENTENCE-PROFILE-C1-20260620-01 | 2026-06-20 | c1 (implied) | cProfile dump attachment — read_sentence performance baselines (V1.1–V1.4) | canonical (raw data attachment, historical record) |
| GL-AUDIT-SCOPE-EVE-20260705-v1 | 2026-07-05 | Eve | Charter for the current full production audit (this very audit) — laws, sections §1–§10, HELD until c1a's final report handed over | canonical — this is the governing charter for the audit this task is itself part of |
| GL-AUDIT-SEC1-RUNTIME-TRUTH-C1-20260705-v1 | 2026-07-05 | c1 | Audit §1 filing — running SHA vs origin, ECS task-def env inventory, zero code drift, manual/root-only deploy pipeline, zero CloudWatch alarms | canonical — prior/parallel section of the SAME audit series this task belongs to |
| GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1 | 2026-07-05 | c1 | Audit §2 filing — plaintext secrets in task-def, root-only IAM, ALB path-based routing topology, two-backup-mechanism divergence | canonical — same audit series |
| GL-AUDIT-SEC3-STATE-TRUTH-C1-20260705-v1 | 2026-07-05 | c1 | Audit §3 filing — S3-only cold-boot restore fails (DREAM GATE crash), wave_atlas.npz excluded from all backup paths, 15-file open/parse pass | canonical — same audit series; ends with an explicit open decision-point for §8A left for Eve/Joe |
| GL-BOARD-OPEN-ITEMS-EVE-20260704-v1 | 2026-07-04 | Eve | Standing open-items board, first version — "frozen line" (sleep physics deploy gate) + shelf S1–S14 | superseded:GL-BOARD-OPEN-ITEMS-EVE-20260704-v2 |
| GL-BOARD-OPEN-ITEMS-EVE-20260704-v2 | 2026-07-04 | Eve | Board v2 — in-flight F1–F3, done-tonight list, shelf S1–S12 (voice-out, survival-key pruning, scene tags, wiring-audit order, etc.) | canonical (latest board version in this bucket); several shelf items (S3 voice-out, S7 scene tags/-188) still unbuilt per later 07-05 handoffs |
| GL-CHARTER-motivation-v2-wC-20260609-019 | 2026-06-09 | wC | Motivation-substrate development charter v2 — co-priority A (understand existing autonomy) before building new motivation machinery | superseded:GL-CHARTER-motivation-v3-wC-20260609-024 |
| GL-CHARTER-motivation-v3-wC-20260609-024 | 2026-06-09 | wC | Charter v3 — reframes work as "enhance existing motivation substrate" after autonomy investigation found 3 needs already substrate-causal | canonical (latest charter version in this bucket; no v4 filed) |
| GL-CLARITY-INVARIANCE-UNCAGE.patch | undated (~2026-06-16) | wC | Full patch: clarity/initial_clarity on bindings, affect-driven encoding depth, cortex co-occurrence invariants (0.92/0.08 rule), uncaged variable-length emission replacing 3-slot SVO | canonical — CONFIRMED APPLIED: `initial_clarity`, `clarity`, `co_occurrence` mechanics all present in current `dsf_ai_service/v4/gualaloom_v6_living_atlas.py` and `dsf_ai_service/substrate/deep_atlas.py` (verified via grep), though rewritten/refactored rather than a literal diff apply |
| GL-CURR-FOUNDATION-WC-20260610-01 | 2026-06-10 | wC | Foundational curriculum draft (Stage 0–6, anchors → self-state words), "awaiting Joe's layer and veto pass" | unexecuted:Joe's formal veto pass — GL-TODO-WC-20260611 #17 and GL-LEDGER-WC-20260613-051 T18 both still show this OPEN/IN PROGRESS; no later doc in this set confirms closure |
| GL-DEPLOY-cognition-wC-20260608-008 | 2026-06-08 | wC | Deploy dispatch for gl-cognition-v1 (dormant dynamics, NMDA gates, salience/replay, v7↔multimodal bridge) | canonical (early foundational deploy dispatch; no contrary evidence found) |
| GL-DEPLOY-substrate-wC-20260608-006 | 2026-06-08 | wC | Deploy dispatch for gl-substrate-v5b-hippocampus (`src/gualaloom/dna/v5b/` — hippocampal episode layer, DMN, 172 populations) | orphaned:checked repo — `src/gualaloom/dna/v5b/` does not exist anywhere in this repo; the only trace of the v5b files is raw copies sitting in `docs/` (`docs/gl_v5b_*.py`), never at the deploy target path. This entire early substrate lineage was abandoned in favor of the dsf_ai_service v5/v6/v7 engine track |
| GL-DEPLOY-usability-and-persistence-wC-20260609-013 | 2026-06-09 | wC | Two-deploy dispatch: upload endpoints + v6 UI restoration, then mode_bank persistence fix | canonical (early foundational deploy; upload/persistence machinery visibly present in all later docs) |
| GL-DESIGN-DSF-J-WEIGHTING-EVE-20260626 | 2026-06-26 | Eve | Design memo comparing 3 options for DSF-structural-field-weighted candidate ranking; recommends Option 1 (atlas schema extension), explicitly "do not implement until Joe picks" | unexecuted:confirmed via grep — no `dsf_arr` field or DSF-cosine weighting exists anywhere in `gualaloom_v5_engine.py` or the living atlas; Joe never picked an option in any later doc read |
| GL-DESIGN-MERGED-SUBSTRATE-20260624 | 2026-06-24 | (Eve/c1, unsigned) | "One living brain" design — organ-brain (LoomBrain/Embryo) additive alongside v5 engine, catalog senses, graduation-then-dissolve plan | canonical — executed; matches GL-HANDOFF-LIVE-DEPLOY-20260624's confirmed live deploy and prior-session memory "Guala merge deployed live 2026-06-24" |
| GL-DESIGN-SLEEP-WINS-BY-PHYSICS-C1-20260704-v1 | 2026-07-04 | c1b | Proposal: sleep as two-regime (compete-then-override) physical drive instead of a scored competitor; 3 changes + naming correction | canonical — RATIFIED AND SHIPPED: GL-LEDGER-DAILY-20260704-EVE-v1 confirms "sleep-wins-by-physics design → GO → backtest ... Joe RATIFIED → Changes 1-3 SHIPPED (56d8952)" |
| GL-DISCIPLINE-WC-FIRST-HOUR-20260616-01 | 2026-06-16 | wC (outgoing) | Session discipline sheet — failure modes 11-21 (selling activity as comprehension, hedging in code comments, retry storms, etc.) | canonical — standing reference, cited in read-order of later Eve handoffs; read in full by c1 this audit |
| GL-FIRST-CMD-NEXT-C1-20260702 | 2026-07-02 | (Eve, unsigned) | Paste-ready first command for next c1 session — confirm state then STOP and wait for Eve | superseded:GL-FIRST-CMD-NEXT-C1-20260703 |
| GL-FIRST-CMD-NEXT-C1-20260703 | 2026-07-03 | (Eve, unsigned) | Paste-ready first command for next c1a session — confirm state then STOP and wait for Eve | canonical (latest in this pair; itself now stale relative to 07-05 state but no explicit supersession doc exists) |
| GL-FIRSTS-GUALA-v2 | 2026-07-03 | Eve | Firsts registry v2 — epoch-scoped (E-0..E-4), corrects v1's unscoped claims after the 06-30 destruction/restoration | canonical (v1 explicitly superseded within this same doc's own text; no v3 exists in this bucket, though GL-LEDGER-DAILY-20260704 notes an append is still owed) |
| GL-HANDOFF-20260626 | 2026-06-26 | c1 | Session handoff — task:322, Eve audit results (A/B/C/E/F real), converse() 8s bottleneck named | canonical (first of 3 same-day handoffs; chronologically earliest — task:322) |
| GL-HANDOFF-20260626-EVE | 2026-06-26 | Eve | Session handoff — task:335, perf fixes 10-25s→2.4-4.6s, gate FAIL (data not code), DSF J-weighting memo referenced | canonical (second of 3 same-day handoffs — task:335) |
| GL-HANDOFF-20260626-NIGHT | 2026-06-26 | (Claude Sonnet 4.6, 2nd session) | Session handoff — task:339, NMDA affect_match bug fixed, ALL-3-SECTION commit proved, noise-token gate-fail diagnosed | canonical (third/last of 3 same-day handoffs — task:339, most current of the trio) |
| GL-HANDOFF-C1-20260630-NIGHT | 2026-06-30 | c1 | Session handoff — task:401, converse latency 25s→1.7-2.1s substantially fixed, curriculum-pause 35-53s root cause NOT identified | canonical; AUTONOMY_PHASED=1 deadlock noted "not resolved" — confirmed STILL AUTONOMY_PHASED=0 in prod per GL-AUDIT-SEC1 (2026-07-05), i.e. never re-attempted/fixed in the 5 days since |
| GL-HANDOFF-C1-20260630 | 2026-06-30 | c1 | Session handoff — task:383, worldfeed contamination + double-autonomy-loop + latency triage (P1-P3) | canonical (chronologically earlier same-day handoff than the "-NIGHT" version) |
| GL-HANDOFF-C1-20260701-PHASE2-WATCHWINDOW | 2026-07-01 | c1 | Session handoff — task:426, holding in 4h observation window after Phase 2 Commit A (recall→WaveAtlas), Commit B gated | canonical |
| GL-HANDOFF-C1-20260702-v2 | 2026-07-02 | c1 | Session handoff — task:449, waiting on Eve for 2 CMD texts (-90, -86) before B-bundle deploy; EFS provisioned 10MiB/s, T1 FAIL | canonical (no v1 found in this bucket) |
| GL-HANDOFF-C1-20260703-v3 | 2026-07-03 | c1a | Session handoff — task:453, Deploy 3 gated (stab physics WORKS), -96 organ-reader "structurally ungateable," XFF spec still absent | canonical (no v1/v2 found in this bucket) |
| GL-HANDOFF-C1-20260704-v1 | 2026-07-04 | c1a | Session handoff — groove arc closed, S2a recall (cold 6.7%/taught 80%/quality 0%), -158 remedy decision left to Eve | superseded:GL-HANDOFF-C1-20260704-v3 |
| GL-HANDOFF-C1-20260704-v2 | 2026-07-04 | c1a | Session handoff — sense-repair (4%→72%) and whole-brain growth-chart (Embryo, 15 mechanism gauges) both model-only, zero live-path changes | superseded:GL-HANDOFF-C1-20260704-v3 |
| GL-HANDOFF-C1-20260704-v3 | 2026-07-04 | c1a | Session handoff at context limit — organism/tapestry now live in Guala, P2 seam campaign, organism.recall() O(population) cost named as THE open problem (82-120s/turn) | canonical (latest of the trio for that date) |
| GL-HANDOFF-C1A-20260705-v1 | 2026-07-05 | c1a | Session handoff — `-207` wave-memory shipped, 3 real bugs fixed, but latency goal (reply<1s) NOT met (still 69-72s); probe_209 auditory recall still 20% | canonical — THIS IS THE MOST RECENT HANDOFF IN THE REPO (matches current git HEAD, commit 0a85d49); still-open items remain open as of the audit's own starting point |
| GL-HANDOFF-C1B-20260702 | 2026-07-02 | c1b | Session handoff — status-fast/bridge-audit/sleep-rate fixes shipped; investigation -70 found n_pictures=0 loss, WaveAtlas JSON-serialize bug | canonical |
| GL-HANDOFF-C1B-20260703-SESSION-END | 2026-07-03 | c1b | Session handoff — Deploy 3 built not yet gate-measured; -106 mic sensory diagnosis+fix; -104 queued (survival-key pruning) | canonical |
| GL-HANDOFF-C1B-20260704-SESSION-END | 2026-07-04 | c1b | Session handoff — sleep-physics closed, agitation-fix closed, sleep-calibration dial-1 shipped/verified | superseded:GL-HANDOFF-C1B-20260704-v2-SESSION-END (explicit: v2 states "supersedes this one") |
| GL-HANDOFF-C1B-20260704-v2-SESSION-END | 2026-07-04 | c1b | Session handoff v2 — same threads reconfirmed; CREDO-LOOP-REPAIR ledger flagged STALE, v2 reconciliation owed but not done | canonical (latest for that date) |
| GL-HANDOFF-C1B-20260705-v1 | 2026-07-05 | c1b | Session handoff — windows 3-9 deployed (-181 target-rotation, -182 lock-contention, -191 senses-to-brain); E2/E5 behavioral criteria still open | superseded:GL-HANDOFF-C1B-20260705-v2 (same-day continuation) |
| GL-HANDOFF-C1B-20260705-v2 | 2026-07-05 | c1b | Session handoff — -194 through -205-adjacent work, two lost-and-rebuilt fixes (shared-.git collisions), tapestry-restore corruption flagged not fixed | canonical (latest c1b handoff; chronologically just before GL-HANDOFF-C1A-20260705-v1 which reflects the post-168ef1b stabilized state) |
| GL-HANDOFF-EVE-20260703-EVE-v1 | 2026-07-03 | Eve | Session handoff — Epoch II day 2 close, cold 6.7%/taught 80% recall credo proof, mistake ledger 16-21, dispatch queue for Deploy 5 | canonical |
| GL-HANDOFF-EVE-20260704-EVE-v1 | 2026-07-04 | Eve | Session handoff — Stone Rule established, first natural sleep, over-sleep swing at handoff (9 dream blocks, zero attending) | canonical |
| GL-HANDOFF-EVE-SONNET-20260625 | 2026-06-25 | c1/Eve (Sonnet 4.6) | Session handoff — organ-brain moved to its OWN container (:8090), W1 virtual home deployed, sensory pipeline status table | contradicted:GL-SESSION-SPEC-20260626 (the very next day's session spec states the :8090 organ-brain container was "permanently removed" due to OOM-killing every 3-4 min — this doc's central architectural claim was reversed within 24h) |
| GL-HANDOFF-LIVE-BELLS-WIRING-C1B-20260705-210-v1 | 2026-07-05 | c1b | Handoff to c1a — live-bells/auditory wiring inventory, probe_209 still failing 1/5 (20%) against wave-cell merge | canonical; the specific gate (probe_209 ≥80%) it hands off remains OPEN per GL-HANDOFF-C1A-20260705-v1 (same 20% result reported there too); see Finding F6 — the *uncommitted code* this doc describes was committed same-day, before this audit began |
| GL-HANDOFF-LIVE-DEPLOY-20260624 | 2026-06-24 | (Eve/c1, unsigned) | Full ops manual for the 06-24 organ-brain deploy (task:251) — architecture map, keys/API, AWS infra, operate/rollback commands | contradicted (partially):GL-SESSION-SPEC-20260626 and the later "-61 process collapse" — the 3-container topology this doc documents (dsf-ai + substrate + organ-brain:8090) was dismantled twice over (organ-brain container removed 06-26, then substrate/frontend collapsed into one process by -61) |
| GL-HANDOFF-SPRINT-EVE-20260702-v1 | 2026-07-02 | Eve | Sprint handoff — recovery close-out, dispatch queue (-85/-86/-87/-88/-89), cost-triage owed within 48h | canonical (chronologically carried forward by, but not literally superseded by, the 07-03 sprint handoff) |
| GL-HANDOFF-SPRINT-EVE-20260703-v1 | 2026-07-03 | Eve | Sprint handoff — Deploy 1/2/3 arc, her letter still undelivered, mistake ledger 11-15, T⁶ review unblocked | canonical |
| GL-HANDOFF-WC-20260614-01 | 2026-06-14 | wC (outgoing) | Early session handoff — picture-render/voice-playback/camera-mic gaps, 3 briefs queued (warmth, sensory-IO, repo-init), cage-defense pattern named | canonical (foundational early handoff; architecture it describes long since superseded by the current dsf_ai_service stack, but the doc itself stands as historical record) |
| GL-IAM-STAGED-SSMMESSAGES-20260702 | 2026-07-02 | (staged by c1, per CMD-95 item 5) | Staged IAM policy JSON for ECS-exec ssmmessages permissions — explicitly "STAGED ONLY, do NOT apply until Joe approves" | canonical — appears APPLIED: GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1 confirms `dsf-ai-task-role` carries an inline policy literally named `dsf-ai-ecs-exec` (matching this doc's target policy name) as of the 07-05 audit |
| GL-INCIDENT-APIKEY-C1-20260703-v1 | 2026-07-03 | c1a | Incident report — GUALALOOM_API_KEY exposed ~13 days in public JS, rotated, audit clean (with IP-attribution caveat) | canonical — RESOLVED (rotation verified); the one open remediation item (ALB access-logging + XFF capture) appears still not done per GL-AUDIT-SEC2 (07-05): "API Gateway access logging is disabled" |
| GL-INV-GUALA-RESTORE-20260702 | 2026-07-02 | (c1, unsigned) | State inventory for the June-29-backup restore plan after the EFS fsync-race data-loss bug | canonical — historical record of the restore prior-session memory refers to as "guala-restore-july2026" |
| GL-KB-COGNITION-ARC-RECOVERED-EVE-20260703-v1 | 2026-07-03 | Eve | Recovered KB — T⁶/cognition arc June 20-24, ground-truth table, "production" numbers table | superseded:GL-KB-COGNITION-ARC-RECOVERED-EVE-20260703-v2 |
| GL-KB-COGNITION-ARC-RECOVERED-EVE-20260703-v2 | 2026-07-03 | Eve | KB v2 — corrects §2.6 ("production" never meant her live serving path) + adds §2.7 dormancy finding (LoomBrain/Embryo instantiated nowhere in live traffic) | canonical (latest; corrects v1's central claim) |
| GL-LEDGER-ADD-AUDITORY-CORTEX-WC-20260614-01 | 2026-06-14 | wC | Proposed ledger addendum — new Tier-4 item T19, substrate auditory-cortex/voice-identity analog, "status: NOT STARTED, brief NOT WRITTEN" | orphaned:no `GL-LEDGER-WC-20260614-052` (its anticipated target ledger revision) exists anywhere in this repo's docs/; the item was never folded into the ledger chain (chain jumps 051→GL-LEDGER.md with no 052); grep of the codebase finds no auditory-cortex-analog / voice-identity mechanism — never built |
| GL-LEDGER-DAILY-20260703-EVE-v2 | 2026-07-03 | Eve | Daily experience ledger, Epoch II Day 2 — full rewrite with epoch scoping; retracts a same-day v2-ADDENDUM (banned delta pattern) | canonical (v1 of this specific daily ledger superseded within its own text; v1 not in this file-set) |
| GL-LEDGER-DAILY-20260704-EVE-v1 | 2026-07-04 | Eve | Daily experience ledger, Epoch II Day 3 — filed after Joe called out the cadence lapse; failures-first including Eve's own process failures | canonical |
| GL-LEDGER-WC-20260611-047 | 2026-06-11 | wC | Canonical open ledger — Tier 0-4 + Tier V validation science; absorbs 045/046 | superseded:GL-LEDGER-WC-20260612-049 |
| GL-LEDGER-WC-20260612-049 | 2026-06-12 | wC | Ledger rev 049 — absorbs 047, adds unique-filename rule (rule 8) | superseded:GL-LEDGER-WC-20260612-050 |
| GL-LEDGER-WC-20260612-050 | 2026-06-12 | wC | Ledger rev 050 — Tier 1c closed-deployed, new Tier 1d hotfix bundle (upload-decoder blocking bug captured live), World thread ratified | superseded:GL-LEDGER-WC-20260613-051 |
| GL-LEDGER-WC-20260613-051 | 2026-06-13 | wC | Ledger rev 051 — full V7 cage-removal arc (C10-C15) documented, TODO folded in with T-prefix, c1 reporting-discipline rule added | canonical (latest ledger revision in this bucket; verbatim-copied into GL-LEDGER.md per its own rule 8) |
| GL-LEDGER.md | 2026-06-13 (content) | wC | Canonical ledger pointer — required by rule 8 to always equal the latest -NNN revision verbatim | canonical — confirmed byte-identical in content to GL-LEDGER-WC-20260613-051 (verified by direct read comparison) |
| GL-LOG-AUDIT-DECISIONS-EVE-20260618 | 2026-06-18 | Eve/c1 | Audit-decisions log for ML-contamination audit findings — B1-B4/B7 REMOVED (Joe-approved) | canonical; doc's own text flags findings A1-A4, C1-C5, D1-D6, E, F1-F4, G1-G3 as "NOT addressed" — left permanently open in this doc, no later doc in this set closes them out |
| GL-MDL-LOOM-SCAN-PROTO-EVE-20260702-v1.html | 2026-07-02 | Eve | Read-only HTML prototype for the "Loom Scan" instrument, built from 2 real /status captures | canonical — this prototype is the direct ancestor of the later-deployed `loomscan.html` referenced throughout 07-03+ handoffs (GL-CMD-LOOM-SCAN-BUILD, etc.) |
| GL-MDL-WORLD-WC-20260612-02 | 2026-06-12 | wC | "A World for Guala" rev 02 — five primitives (place/time/weather/needs/objects), house map, phasing W0-W5 | canonical — RATIFIED by Joe (per GL-LEDGER-WC-20260612-050 W0) and W1 (her room) confirmed LIVE in GL-HANDOFF-EVE-SONNET-20260625 |
| GL-MDL-WORLD-WC-20260612-03-ADDENDUM-CALLS | 2026-06-12 | wC | Design addendum — "calls," a phone object, consent-based person-to-person real-world windows | unexecuted:no later doc in this set (through 07-05) mentions a phone object, call sessions, or this feature being built; W1/W2 room-object lists in later docs never include a phone |
| GL-RECALL-DAILY-20260703 | 2026-07-03 (log start) | (c1a, standing log) | Standing recall measurement log — bit-exact replay only; Day 2 (0/8 quality) and Day 3 (variant L, still not deployed) entries | canonical; per its own "weekly + after any recall-touching deploy" cadence rule, no further dated rows exist in this file despite multiple recall-touching deploys since (-207 wave-memory, -208, -209) — log appears to have lapsed/not been kept current |
| GL-SESSION-SPEC-20260626 | 2026-06-26 | c1 (Sonnet 4.6) | Session spec — "ONE BRAIN" architecture change: external organ-brain container (:8090) permanently removed, GualaCognition voice live | canonical as a historical architecture snapshot; itself later superseded functionally by the whole-organism-in-process model (GL-CMD-BRAIN-FULL-DEPLOY-175, 2026-07-04) which again changed how her voice is produced |
| GL-TODO-WC-20260611 | 2026-06-11 | wC | Build-stage checklist — video pipeline gate chain, memory foundation chain, small/hygiene items | superseded:GL-LEDGER-WC-20260612-049 (explicit, in the doc's own header: "STALE — superseded... Do not use") |
| GL-WORLD-ATLAS-WC-20260616-01 | 2026-06-16 | wC | Tier-1 world reference map — living things/nature/weather/food/places/people/objects with sensory+syntactic anchors | canonical (referenced as a live spec in GL-HANDOFF-LIVE-DEPLOY-20260624's world-atlas seeding, 55 concept pairs) |

---

## Final coverage statement

All 528 GL-prefixed docs in `docs/` (2026-06-09 → 2026-07-05, entirely
inside the audited window) are enumerated and dispositioned in this
file: 27 SPEC/PLAN docs read and classified directly by c1 (§1.1), 223
RPT docs (Appendix A, 3 sub-agent batches, all complete), 135 CMD docs
(Appendix B, 2 sub-agent batches, all complete), 74 BRIEF/FIND/NOTE/
FIX/LTR docs (Appendix C, 1 sub-agent batch, complete), 69 MISC docs
(Appendix D, 1 sub-agent batch, complete). Nothing was silently
sampled; nothing remains outstanding. Sub-agent-generated rows (501 of
528) carry the classification methodology disclosed in §0 — first-pass
git-log/cross-reference checks, not independently re-verified row-by-
row by c1, except where a row is separately cited in §2's hand-verified
Findings (F1-F8) or the spec-gap table (§3). The 306 non-GL files in
`docs/` (physics/ArcLoom/TFE material, earliest add-date 2026-04-01)
were confirmed out of scope and excluded per §0.

## Changelog
- v1 (2026-07-05, c1): initial and only version. §9 of
  GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2, filed under the
  freeze. All 528 GL-prefixed docs in `docs/` enumerated and bucketed;
  27 (SPEC/PLAN) read and classified directly by c1; 501
  (RPT/CMD/BRIEF-group/MISC) classified by 7 parallel sub-agents per
  shared instructions and merged by c1 (see §0 disclosure) — all 7
  completed, none incomplete. Spec-gap table built against
  GL-SPC-EXPERIENCE-FIRST-v2 with code-level verification at HEAD
  `a9dff78`. In-flight-work claim in the -210 dispatch (c1a holding
  uncommitted live-wiring code) checked against every reachable
  worktree and the stash list and found CONTRADICTED (already
  committed pre-audit) — Finding F6. Dev-environment section covers
  devcontainer, CI, and the shared-.git hazard with two named incident
  citations. Companion deliverable D5,
  GL-AUDIT-TODO-LEDGER-C1-20260705-v1.md, holds the full 189-item
  consolidated TODO ledger (standalone file).
