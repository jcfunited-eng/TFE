# GL-SPEC-LATENCY-NEIGHBORHOOD-C1-20260706-v1

**As-built spec for 7 changes shipped this session**
**Author:** c1
**Date:** 2026-07-06
**Live at:** task-def `dsf-ai-task:526`, SHA `983dfb3`, service
`dsf-ai-service-lb` / cluster `tfe-web-cluster`
**Companion doc:** `GL-HANDOFF-LATENCY-NEIGHBORHOOD-C1-20260706-v1.md` (narrative
handoff — what's still open, what to do next). This document is the precise
technical record of what each change actually does — read that one for
context, this one for exact mechanism.

Each section: **Where** (file/function/commit) · **Before** (exact prior
behavior) · **After** (exact new behavior + code) · **Verification**
(what was actually tested, not just reasoned about) · **Invariants**
(what deliberately did not change).

---

## 1. Whole-turn-only emission fallback

**Where:** `dsf_ai_service/v4/gualaloom_v5_engine.py`, `Guala._emit_dynamics()`.
Commit `a648dd8`.

**Before:** After the per-section commit loop, any section that did not
receive a real commit ran `arcs_fallback` unconditionally: took that
section's `arcs()` array, argmax'd it, and installed the top-scoring
*installed candidate* as if it had committed — regardless of whether the
settling dynamics ever actually converged there. This ran independently
per section, so a turn where e.g. only `subject` genuinely committed would
still get `verb`/`object`/`modifier`/`ground`/`intro` manufactured from
whatever candidates happened to be installed, every turn, because the
fixed six-section template (`_EMISSION_SECTIONS`) tries to fill all six.

**After:**
```python
if committed_word:
    per_section_dominant[sec_name] = (committed_mode, committed_word, "commit")
    ...
else:
    per_section_dominant[sec_name] = (None, None, "none")

# whole-turn fallback runs ONLY if nothing anywhere committed:
if not emission_words:
    best_fallback = None
    best_fallback_score = -1.0
    for sec_name in self._EMISSION_SECTIONS:
        sec = sys_.sections[sec_name]
        arcs = sec.arcs()
        if len(arcs) == 0:
            continue
        sorted_modes = sorted(range(len(arcs)), key=lambda i: -arcs[i])
        for mi in sorted_modes:
            w = self._emission_word_map.get((sec_name, mi))
            if w:
                if arcs[mi] > best_fallback_score:
                    best_fallback_score = arcs[mi]
                    best_fallback = (sec_name, mi, w)
                break
    if best_fallback is not None:
        fb_sec, fb_mi, fb_word = best_fallback
        per_section_dominant[fb_sec] = (fb_mi, fb_word, "arcs_fallback")
        if fb_word.lower() not in input_words_set:
            emission_words.append(fb_word)
```
A section with no real commit now reports `(None, None, "none")` and stays
silent. `arcs_fallback` fires at most once per turn, across all sections
combined, choosing the single highest-scoring candidate anywhere — and
only when the entire turn produced zero real commits.

**Verification:** Behavioral — deployed and confirmed live replies now
show variable role counts (`per_section_dominant` events show 1-4 real
commits per turn instead of 6 uniform fills) rather than the old
constant-six pattern.

**Invariants:** The per-section commit logic itself (settling dynamics,
threshold checks) is untouched — this only changes what happens to a
section *after* it fails to commit. `arcs_fallback`'s existence is
preserved as a genuine mute-turn safety net, not removed outright.

---

## 2. Whole-utterance query for emission candidates

**Where:** same file, `Guala._brain_emission_candidates()`. Commit `a648dd8`.

**Before:**
```python
query = (input_words[-1] if input_words else self._tapestry_prev_word)
if not query:
    return []
...
votes = self.organism.recall_fast(_organism_signal(query, self._organism_transducer))
```
Only the last word of the input utterance was used to query the organism's
population-vote recall (`Embryo.recall_fast`). A candidate had to
associate with that one word only.

**After:**
```python
queries = list(input_words) if input_words else (
    [self._tapestry_prev_word] if self._tapestry_prev_word else [])
if not queries:
    return []
_QUERY_WORD_CAP = 12
queries = queries[-_QUERY_WORD_CAP:]
input_words_lower = set(w.lower() for w in input_words) if input_words else set()
merged_votes = Counter()
n_queries_ok = 0
for q in queries:
    try:
        votes = self.organism.recall_fast(_organism_signal(q, self._organism_transducer))
    except Exception as _oe:
        continue
    if votes:
        n_queries_ok += 1
        merged_votes.update(votes)
if not merged_votes:
    return []
total = sum(merged_votes.values())
...
for w, n_votes in merged_votes.most_common():
    if not w or w.lower() in input_words_lower:
        continue
    ...
```
Every word of the input (capped at the most recent 12, to bound
worst-case cost on a pasted wall of text) is queried independently; the
returned `Counter` vote distributions are merged with `Counter.update()`
(additive). Self-echo exclusion is now against the *whole* input word set,
not just the query word.

**Verification:** `emission_diag` event's `n_voted_words` field confirmed
higher post-deploy (merged distribution across queries is larger than any
single-word query). Isolated logic check: `Counter.update()` on synthetic
vote dicts produces the expected additive merge.

**Invariants:** `recall_fast()` itself, vote-count semantics, and the
downstream candidate-filtering (`_word_to_emission_sections` lookup) are
unchanged. The cap of 12 is a new, explicit bound — prior behavior had an
implicit cap of 1.

---

## 3. v7 session memory eviction + disk retention + atlas dump cap

**Where:** `dsf_ai_service/app.py` (`_background_replay()`,
`_prune_old_v7_session_files()`) and
`dsf_ai_service/substrate/v7_engine.py` (`V7Session.to_json()`). Commits
`a648dd8`, `a7a6830`.

**Before:** `_sessions` (in-memory dict of live `V7Session` objects) never
evicted anything — every browser tab/reload created a permanent entry,
re-serialized to disk every 15s forever. No disk-retention pruning
existed. `V7Session.to_json()` dumped `self.sys_.atlas.entries` in full —
unbounded, since `ChiAtlas.add_claim()` (substrate/assemblage.py) has no
decay/forgetting/cap of its own.

**After, three independent bounds:**
- **Memory eviction:** `V7_SESSION_EVICT_AFTER_SECONDS = 3600`. In
  `_background_replay()`'s existing 15s loop, a session idle past this
  threshold gets one final `save_session()` call, then
  `_sessions.pop(sid, None)` — reloads from disk fine if it ever
  reconnects.
- **Disk retention:** `_prune_old_v7_session_files()`, rate-limited to
  once per UTC day via `_v7_last_prune_day[0]`. Deletes `.json`,
  `.json.tmp`, `.events.jsonl` files in the v7 `STATE_DIR` older than
  `V7_SESSION_RETENTION_DAYS`. Initially set to `7` (matching this
  codebase's existing `DIARY_RETENTION_DAYS` convention), then cut to `1`
  in the same session per Joe's explicit "much more aggressive" directive
  once live data showed 7 days still left 71 files / 1.2GB.
- **Per-session atlas cap:** `V7Session._ATLAS_ENTRIES_PER_CHI_CAP = 20`.
  `to_json()`'s atlas serialization changed from
  `{str(k): v for k, v in self.sys_.atlas.entries.items()}` to
  `{str(k): sorted(v, key=lambda e: -e.get("strength", 0.0))[:20] for k, v in ...}`
  — keeps each chi bucket's 20 strongest entries only, mirroring what real
  decay/forgetting would retain. This does not touch the live in-memory
  atlas or tick behavior, only what gets written to the save file.

**Verification (live, not just unit-tested):** Deployed and observed
directly — total v7 on-disk storage dropped from 1.2GB to 289MB within
minutes of deploy, with zero manual intervention, confirming the prune
logic actually ran and actually matched the intended files. Isolated test
also confirmed: capping a synthetic 500-entry chi bucket to its true
strongest 20 (via the same sort) reduces that bucket's serialized size
~25x, and leaves recent/unrelated files untouched by the age-based prune.

**Invariants:** v7's live tick behavior (`quiet_tick`, NMDA gating,
whatever drives the cognition-meter UI) is unaffected — all three bounds
operate on persistence/memory-lifecycle only. Confirmed by direct code
trace that v7 does not determine her actual spoken replies (that's fully
`_emit_dynamics()` in the v5 engine) — this subsystem's leak had no
bearing on conversation content, only on EFS write pressure and container
memory.

---

## 4. Read-pipeline timing instrumentation

**Where:** same file, `Guala.read_word()` and `Guala.read_sentence()`.
Commit `d5ffbab`. **Diagnostic only — explicitly no behavior change.**

**What it adds:** A closure-based profiler inside `read_word()`:
```python
_prof_t0 = time.monotonic()
_prof = {}
def _prof_mark(_key, _t_prev):
    _t_now = time.monotonic()
    _prof[_key] = _prof.get(_key, 0.0) + (_t_now - _t_prev) * 1000.0
    return _t_now
```
called at 10 phase boundaries: `transduce`, `organism_enqueue`,
`phase_dsf`, `salience_role`, `recognition`, `listen_receive`,
`primary_sections_receive`, `ground_modal`, `intro_receive`,
`decay_coordinator`. Result stored as `self._read_word_last_profile`
(overwritten, not accumulated, each call). `read_sentence()` sums this
dict across its whole per-word loop into `_read_profile_agg` and emits one
`read_sentence_timing` substrate event per sentence, gated to
`source in ("joe", "joe_voice", "wc", "c1", "gate_test")` — i.e. only real
conversational turns, not autonomous corpus/curriculum reading, to avoid
per-word event spam.

**Verification:** Timing-accumulation helper tested in isolation against
known `time.sleep()` durations to confirm it measures what it claims to.
No control-flow or value changes anywhere in the instrumented functions —
confirmed by diff inspection (every added line is either a profiler call
or the closure definition itself).

**Why this exists / what it enabled:** Every latency claim before this
commit (organism recall cost, tapestry expose cost, GIL contention) was
inference from reading code and comments, not a measurement of the live
system. This is what made items 5 and 6 possible to find and fix with
real numbers instead of another guess — it's also the mechanism a future
session should use to find the next cost (see companion handoff doc:
`recognition` at ~5s/call is the next unaddressed one).

---

## 5. Live conversation priority over autonomous curriculum reading

**Where:** `dsf_ai_service/app.py` (`_run_converse()`) and
`dsf_ai_service/substrate_runner.py` (`_curriculum_feed_chunk()`). Commit
`ddc014e`.

**Before:** Live conversation (`read_sentence()` via `/converse`) and
autonomous background curriculum reading both serialize through the same
`self.lock`, with no priority mechanism between them. A prior mitigation
(Eve, 2026-06-30) paused *other* autonomy during a curriculum feed, but
never gave live conversation priority over an *in-progress* feed.
Confirmed live this session: a clean single-user conversational test
stalled 100+ seconds while autonomous reading was actively churning in
the background.

**After:**
```python
# app.py, _run_converse():
task["phase"] = "processing"
if _guala is not None:
    _guala._live_converse_pending = True
try:
    ...
finally:
    if _guala is not None:
        _guala._live_converse_pending = False
```
```python
# substrate_runner.py, _curriculum_feed_chunk(), inside its per-sentence loop:
if getattr(_guala, "_live_converse_pending", False):
    break
```
A plain instance attribute (no lock needed — GIL-atomic set/read) flags
"a live turn is in progress." The curriculum feed loop checks it between
sentences and breaks early, reusing the exact same graceful
partial-chunk-completion pattern that function already uses for its own
rate-cap gate (`n_fed < planned`, `capped=True` logged) — an interrupted
chunk simply resumes next cycle, nothing is lost or corrupted.

**Verification:** Code-level — confirmed the `finally` block covers every
`_run_converse` exit path (sleep-quiet early return, remote-mode success,
embedded success, exception). Not yet re-verified under real concurrent
load in production (both a live conversation and an active curriculum
feed happening at the same moment) — flagged as an open item in the
companion handoff.

**Invariants:** `_atick_reading` (the single-sentence-per-tick autonomy
path) needed no change — only the multi-sentence chunk path was the
documented risk. Nothing about what she reads or learns changes; only the
order two lock-contenders are serviced in.

---

## 6. Modes-matrix cache-thrashing fix

**Where:** same engine file, `Section.receive()`. Commit `a64eedc`.

**Before:**
```python
avg = (old_dsf.to_array() * 0.9 + dsf.to_array() * 0.1)
new_dsf = DSF(*avg)
self.modes[word_match_idx] = (new_dsf, old_chi, old_word)
self._modes_dirty = True   # mode vector changed; matrix must rebuild
```
Reinforcing an *already-known* word (updating one existing mode's DSF
vector via a 90/10 blend) unconditionally marked the entire cached
similarity matrix (`_modes_matrix`) dirty, forcing a full `O(n_modes)`
rebuild the next time a genuinely new word needed a similarity scan
against that section. In an ordinary sentence mixing known and unknown
words, every known-word reinforcement invalidated a cache a moments-later
new word's scan needed — so cost that should have amortized to one
rebuild per sentence was paid repeatedly, at up to 14,000+ modes in the
`listen` section.

**After:**
```python
if self._modes_matrix is not None and word_match_idx < len(self._modes_matrix):
    _new_vec = new_dsf.to_array()
    self._modes_matrix[word_match_idx] = _new_vec
    self._modes_norms[word_match_idx] = np.linalg.norm(_new_vec) + 1e-12
else:
    self._modes_dirty = True
mode_idx = word_match_idx
committed = True
```
A reinforcement updates the existing row of the cached matrix and its
precomputed norm in place — since reinforcement changes one row's values,
not the matrix's shape, there is nothing to invalidate. Falls back to the
old mark-dirty behavior only if the cache doesn't exist yet or the index
is somehow out of range (defensive, not expected in practice). A genuine
new-word append is untouched and still marks dirty for a real rebuild,
since that does change the matrix's shape.

**Verification:** Unit-tested against a real `Section` instance (not
mocked): reinforcing a known word leaves the cache object identity
unchanged (same array, not rebuilt) and the updated row's values exactly
match the real 90/10 blend; a genuinely new word still correctly triggers
a real rebuild reflecting the new mode count. **Live result is honestly
mixed**, measured once: `listen_receive` phase dropped 12.6s→7.8s in the
same test sentence, but `primary_sections_receive` in that same turn went
13.6s→16.8s and total read time barely moved (31.1s→29.9s). The mechanism
is proven correct in isolation; whether the live wash is noise or a real
offsetting cost elsewhere is not yet settled — needs repeated-run
measurement, not a single before/after pair.

**Invariants:** The reinforcement blend formula itself (0.9 old / 0.1 new)
is unchanged. `committed = True` and `mode_idx` assignment are unchanged.
No new code path for the "new word" branch.

---

## 7. Chi-neighborhood distance-weighted familiarity matching

**Where:** `dsf_ai_service/v4/gualaloom_v6_living_atlas.py`,
`LivingAtlas.match_score()` + new module constant `CHI_DISTANCE_DECAY`.
Commit `983dfb3`. **This is the only change tonight that went through
adversarial review before shipping** — see verification section below for
why, and what that review actually caught.

**Before:**
```python
CHI_BAND = 2
...
def match_score(self, chi_value, section_name):
    score = 0.0
    for d in range(-self.band, self.band + 1):
        for e in self.entries.get(chi_value + d, []):
            if e["strength"] < FORGETTING_THRESHOLD:
                continue
            if e["section"] != section_name:
                score += 0.3 * e["strength"]
            else:
                score += 0.1 * e["strength"]
    return min(score, 1.0)
```
Every chi within the search band (`self.band`, always 2 in production)
counted identically regardless of distance from the query chi — an entry
exactly on-target and one at the band's far edge contributed the same
weight. The loop variable `d` was computed but never used for weighting,
only for indexing which bucket to read.

**After (final, post-review version):**
```python
CHI_DISTANCE_DECAY = 0.5   # module constant

def match_score(self, chi_value, section_name):
    score = 0.0
    offsets = range(-self.band, self.band + 1)
    decays = [math.exp(-CHI_DISTANCE_DECAY * abs(d)) for d in offsets]
    mean_decay = sum(decays) / len(decays)
    for d, decay in zip(offsets, decays):
        weight_scale = decay / mean_decay
        for e in self.entries.get(chi_value + d, []):
            if e["strength"] < FORGETTING_THRESHOLD:
                continue
            weight = e["strength"] * weight_scale
            if e["section"] != section_name:
                score += 0.3 * weight
            else:
                score += 0.1 * weight
    return min(score, 1.0)
```
Raw distance weight is `exp(-CHI_DISTANCE_DECAY * |d|)` (Shepard 1987,
"Toward a Universal Law of Generalization" — similarity decays as a
negative exponential of distance in the underlying representational
space). At `CHI_DISTANCE_DECAY = 0.5`, band = 2: raw weights are
`d=0 → 1.0`, `d=±1 → 0.6065`, `d=±2 → 0.3679`.

**The normalization (`weight_scale = decay / mean_decay`) is the load-bearing
part of this spec, not a cosmetic addition.** Raw weights are all ≤ 1.0,
and real production bindings for a given word are *not* concentrated at
`d=0` — a word's chi drifts slightly on every re-encounter (confirmed by
reading `read_word()`'s chi computation), so its accumulated memory is
smeared across the band. Applying raw exponential weights to that smeared
case would silently shrink the typical score for every word she already
knows, the instant this deployed, with no compensating change anywhere
downstream. Dividing by the band's own mean weight
(`mean_decay = 0.58976` for band=2, k=0.5) exactly cancels this: a hit
spread evenly across all 5 buckets scores identically to the old formula
(proven exactly, not approximately — see Verification), while a hit
concentrated exactly on-target now scores ~1.6956x higher than before,
and a hit sitting only at the band's edge scores ~0.6238x lower.

**Verification:**
1. **Unit-tested against a real `LivingAtlas` instance** (not mocked), 6
   cases: (a) uniform strength spread across all 5 band buckets scores
   *exactly* identically old vs. new (0.7500 both) — proves the
   normalization claim precisely, not approximately; (b) all strength
   concentrated at `d=0` scores higher post-fix (0.1500→0.2543, ratio
   1.6956, matching the derived constant exactly); (c) all strength
   concentrated at `d=band` scores lower post-fix (0.1500→0.0936, ratio
   0.6238, matching exactly); (d) below-`FORGETTING_THRESHOLD` entries
   still excluded; (e) same-section (0.1x) vs. different-section (0.3x)
   weighting still holds at the correct 3:1 ratio; (f) a concentrated
   on-target word scores higher per-unit-strength than a spread-out word
   with 5x the raw strength, confirming genuine distance-sensitivity.
2. **Adversarial review** (3 independent agents, run before deploy, given
   this function's blast radius — it's called throughout `read_word()`
   for familiarity/salience gating on every word she reads). All 3
   independently converged on `NEEDS_CHANGES` against the *first* version
   of this fix (raw, unnormalized), each empirically reproducing the same
   magnitude-shift finding by direct simulation against the real class
   (measured reductions of ~41% and ~59%-of-original in two independently
   constructed synthetic cases) and identifying the specific consumer this
   would break: the `fam_listen > 0.3` hard threshold gating the `intro`
   (introspection) section in `_read_word()`
   (`gualaloom_v5_engine.py` ~line 2248), plus `dead_zone = 0.20 + 0.5 *
   familiarity` and its `dead_zone_avg` monitoring metric. The
   normalization fix (this final version) was designed specifically to
   satisfy that finding and re-verified as above; not re-run through a
   second adversarial pass given the fix is an exact, provable correction
   to the identified defect rather than a new design needing fresh
   scrutiny.
3. **Live**: deployed, confirmed running SHA matches (`983dfb3` via
   `guala_status`), boot clean, `atlas_health` numbers post-deploy show no
   corruption (strength distribution shape, total strength, live-binding
   count all within normal range). No live conversational demo performed
   as verification — this fix changes a judgment threshold, not timing,
   so there's no single-turn stopwatch number to show; its effect is
   intended to show up gradually via `atlas_health` and introspection-gate
   firing rates over many conversations, not one test.

**Invariants:** Search radius (`self.band`) is completely unchanged — this
only reweights *how much* a hit at a given distance counts, not how far
the search reaches. The 0.1x (same-section) / 0.3x (different-section)
base weighting is unchanged and still applies on top of the distance
weight. `FORGETTING_THRESHOLD` exclusion is unchanged.

**Explicitly deferred (same defect pattern, not fixed here):**
`query_associations()` and `recall_scene()` in the same file, and
`deep_atlas.py`'s `_update_invariant()` / `dream_promotion_gate()` band
loops, all have the identical "every chi in the band counts equally"
pattern. `_update_invariant()` in particular feeds live daydream/
novel-jump writes and was flagged by review as worth a dedicated look, not
a cosmetic parity fix — see companion handoff doc for status (a concurrent
session may already be working this; check git log before starting fresh).

---

## Cross-cutting notes

- **Deploy mechanics** for every change above: `tools/deploy_dsf_ai.sh`
  builds+pushes and registers a default-sized task-def; killed
  (`pkill -f deploy_dsf_ai.sh`) immediately after it logs
  `Registered: dsf-ai-task:N`, before it reaches the pause/update-service
  step; manually re-registered at `cpu=4096`/`memory=16384` via `jq` +
  `aws ecs register-task-definition`; service swapped to that manually
  re-registered revision via `update-service --force-new-deployment`;
  confirmed via `aws ecs wait services-stable` and `guala_status`'s
  `running_sha` field matching the shipped commit exactly.
- **None of these 7 changes touch `_EMISSION_SECTIONS`, the six-role
  emission template itself, `deep_atlas.py`'s promotion-gate competition
  model, or chi's underlying phonetic (not semantic) computation** — all
  three were investigated this session and found to be real, separate
  gaps, documented in the companion handoff, not attempted here.
- Items 1-6 are all in `gualaloom_v5_engine.py` / `app.py` /
  `substrate_runner.py` / `v7_engine.py`. Item 7 is the only change in
  `gualaloom_v6_living_atlas.py`.

### Changelog
- v1 (2026-07-06, c1): initial as-built spec, 7 changes, commits `a648dd8`
  through `983dfb3`.
