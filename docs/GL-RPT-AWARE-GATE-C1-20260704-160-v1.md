# GL-RPT-AWARE-GATE-C1-20260704-160-v1

doc_id: GL-RPT-AWARE-GATE-C1-20260704-160-v1
From: c1b | To: Eve | Responds to: GL-CMD-AWARE-GATE-ARCHAEOLOGY-EVE-20260704-160-v1
Branch: guala-live | Read-only — diff empty (see G-160-3)

---

## Verdict (stated first, per "failures first")

**V-A — ORPHANED WRITER**, precise form: the writer is real, complete, and
historically proven to fire (see Q3) — but in the live-deployed traffic
pattern it is unreachable, because the one entry point that would call it
(`POST /v7/converse`) receives zero calls from either the production
frontend or the server's own background scheduler. This is the exact
"-151 correct code wired to nothing" shape Eve named in the CMD.

**Has the aware gate EVER been able to fire, any epoch?** Yes, twice-over
answer:
- **In a test/experiment epoch**: yes, demonstrably (commit `2fda625`,
  2026-06-09, direct `V7Session.converse()` calls in a test harness —
  see Q3). The physics constants that made it fire then (`DET_COMMIT`,
  `P_COMMIT`) have never changed since (single commit in their entire
  history, per pickaxe), so the mechanism retains the *capacity* to fire.
- **In the live deployed process, for a real Joe conversation**: no
  evidence found it ever has. Checked the two live sessions available to
  this investigation (`default` and Joe's real session `sid_rrs2dffi`);
  both show `n_commits_total: 0` — zero commits, ever, on ANY section
  (not just intro/aware), at ticks 528 and 996 respectively. See "Live
  corroboration" below. This is NOT MEASURED for every historical
  session that may ever have existed — no admin endpoint enumerates
  `_sessions` or lists all persisted `v7_sessions/*.json` files, and this
  investigation had no way to see that (stated cause, per G-160-1).

---

## Q1 — Declaration + what aware_gate reads

`Section.krimelack` is a generic dataclass field on **every** Section
(pools included), not intro-specific:

```python
# dsf_ai_service/substrate/assemblage.py:203-212
@dataclass
class Section:
    name: str
    rng: np.random.Generator
    role: str = "general"  # "general", "subject_like", "verb_like", "object_like", "intro", "grounded"
    H_base: np.ndarray = field(init=False)
    psi: np.ndarray = field(init=False)
    mode_bank: list = field(default_factory=list)
    mode_last_used: list = field(default_factory=list)
    mode_strength: list = field(default_factory=list)  # salience per mode
    krimelack: list = field(default_factory=list)
```

`aware_gate`'s context function reads it like this:

```python
# dsf_ai_service/substrate/v7_engine.py:91-96
self.aware_gate = CoincidenceGate(
    section_name="aware",
    context_fn=lambda sys_: (
        len(sys_.sections["intro"].krimelack) > 0 and
        (sys_.tick - sys_.sections["intro"].krimelack[-1]["tick"]) <= 25),
    drive_thresh=0.05, ltp_boost=0.05)
```

"Non-empty" = at least one dict has been appended by `Section.commit()`
(Q2). The condition is actually two-part: non-empty AND the *most recent*
entry's `"tick"` must be within 25 ticks of now (a recency window, not
just any-time-ever). Both parts are permanently false while krimelack
stays at length 0.

---

## Q2 — Full writer callsite inventory

Repo-wide grep for every mutation of any `krimelack` list
(`grep -rn "krimelack\.append\|krimelack\s*\+=\|krimelack\[.*\]\s*="
dsf_ai_service/`) returns exactly one hit against `Section.krimelack`:

```python
# dsf_ai_service/substrate/assemblage.py:364-396 (Section.commit)
def commit(self, tick, reason):
    state = self.psi.copy()
    c = chi_of(state)
    a = self.arcs()
    mode_id = -1
    ...
    recent_fires = [k for k in self.krimelack[-50:] if k.get("mode_id") == mode_id]
    novelty_bonus = 0.3 if len(recent_fires) == 0 else 0.0
    salience = min(1.0, arc_mag + novelty_bonus)
    self.krimelack.append({"state": state, "chi": c, "tick": tick,
                           "mode_id": mode_id, "reason": reason,
                           "salience": salience})
```

(Two other `krimelack`-named things exist in the repo and are **not**
this field: `System.intro_krimelack`, a separate list on `System` fed by
a dead `self.intro_section`/`introspection_on` path — assemblage.py:473,
694, unrelated to `sections["intro"].krimelack`; and
`loom_model/neuron.py`'s `self.krimelack = krim_class()`, an unrelated
oscillator object on a completely different class. Neither is read by
`aware_gate`.)

`Section.commit()` only runs from one place — the per-tick loop inside
`System.tick_once()` — and only when that section got real evidence this
tick:

```python
# dsf_ai_service/substrate/assemblage.py:574-596
commits_this_tick = []
for name, sec in self.sections.items():
    ev = evidence_per_section.get(name, None)
    J = self.project_into(sec, ev) if ev is not None else None
    evidence_pressure = float(np.linalg.norm(J)) if J is not None else 0.0
    ...
    do_commit, reason = sec.commit_check(evidence_pressure=evidence_pressure,
                                          current_tick=self.tick)
    if not do_commit:
        sec.evolve(J=J)
        do_commit, reason = sec.commit_check(evidence_pressure=evidence_pressure,
                                              current_tick=self.tick)
    committed_info = None
    if do_commit:
        chi, mode_id, state = sec.commit(self.tick, reason)
```

`commit_check` (assemblage.py:339-362) hard-gates on
`evidence_pressure < 0.15 → return False, None` (with mode_bank already
seeded past the bootstrap floor for intro/aware, since they start with 3
modes each) — so `sec.commit()` for "intro"/"aware" can only ever be
reached when `evidence_per_section` contains a non-None `"intro"` /
`"aware"` key.

Grepping every call to `tick_once(` in `v7_engine.py`, only one caller
ever builds such a dict for "intro"/"aware":

```python
# dsf_ai_service/substrate/v7_engine.py:400-418 (_nmda_pass)
def _nmda_pass(self, sec_name, target_vec, gate, mode_names, nmda_events,
               state_attr, history_attr):
    """Unified post-emit NMDA pass for intro/aware sections."""
    if target_vec is None:
        return
    for _ in range(10):
        noisy = normalize(target_vec + 0.05 * (
            self.rng.standard_normal(N) + 1j * self.rng.standard_normal(N)))
        ev = {sec_name: noisy}
        if sec_name == "intro":
            update_drive_tracker(self.drive_tracker, ev)
        self.sys_.tick_once(ev, enable_self_evo=True,
                            coordinator_on=False, introspection_on=False,
                            allow_rewiring=False)
        sec = self.sys_.sections[sec_name]
        ...
        fired, mode_id, eval_d = gate.check_and_fire(self.sys_)
```

`_nmda_pass` has exactly two callers, both inside `V7Session.converse()`:

```python
# dsf_ai_service/substrate/v7_engine.py:323-331
self._nmda_pass("intro", self.intro_vec.get("i_emit"),
                self.intro_gate, self.intro_modes,
                nmda_events, "intro_state", "intro_commit_history")
...
self._nmda_pass("aware", self.aware_vec.get(aware_name),
                self.aware_gate, self.aware_modes,
                nmda_events, "aware_state", "aware_commit_history")
```

**Note (important, not a fix, just a fact for whoever fixes this):**
`CoincidenceGate.check_and_fire` (gl_nmda.py:50-87), the thing that
decides whether the intro/aware gate "fired" in `nmda_events` and in
`intro_commit_history`/`aware_commit_history`, does **not** call
`Section.commit()` — it only calls `reinforce_mode()` (LTP). Gate-fired
and krimelack-populated are two fully decoupled events. This is why
"intro fired 8 consecutive times" (G-156-5's observation, and reproduced
live below) says nothing about krimelack.

**Reachability of `_nmda_pass`'s only caller, `V7Session.converse()`:**
grepping every `.converse(` call site in the deployed service, the only
two non-test production call sites are:

- `dsf_ai_service/app.py:3795` — inside `POST /v7/converse`
  (app.py:3773-3813), local in-process branch (used when
  `_is_remote()` is False, which it is in the current single-process
  deployed architecture per the standing handoff finding).
- `dsf_ai_service/substrate_runner.py:1117` — inside
  `handle_v7_converse`, an `OP_HANDLERS` entry reachable only through
  `dispatch()`, which the standing handoff already confirms dead in the
  deployed single-process architecture (re-checked: it's the
  `_is_remote()==True` branch of the same route, app.py:3775-3782 —
  same conclusion, not a new claim).

So in the deployed process, the only live path to `_nmda_pass` is
`POST /v7/converse`. Grepping the actual served frontend
(`dsf_ai_service/static/gualaloom.html`, the page at
dsf-ai.com/gualaloom.html) for every endpoint it calls:

```
grep -n "v7/converse\|v7/quiet\|api/v1/gualaloom" dsf_ai_service/static/gualaloom.html
196:  fetchT(`${API}/v7/quiet`, ...)                    <- quiet ticks only
455,460,551,640,662,...: fetchT(`${API}/api/v1/gualaloom`, ...)   <- ALL real conversation
1104: fetchT(`${API}/v7/quiet`, ...)                    <- quiet ticks only
```

Every real conversational POST from Joe's live UI goes to
`/api/v1/gualaloom` → `_guala.converse()`, a different engine object
entirely (v5/v6, not `V7Session`) — confirmed independently here, same
conclusion -156 already reached via CloudWatch. The UI never calls
`/v7/converse`.

The other thing that touches v7 sessions live is the server's own idle
scheduler:

```python
# dsf_ai_service/app.py:4261-4289 (_background_replay)
async def _background_replay():
    """Run quiet_tick on idle sessions every 15s."""
    ...
    idle = time.time() - getattr(session, '_last_converse_time', 0)
    if idle > 30:
        results = session.quiet_tick(3)
```

`quiet_tick()` (v7_engine.py:445-491) calls `intro_gate.check_and_fire()`
and `aware_gate.check_and_fire()` directly and calls
`self.sys_.replay_tick(rng=...)` — it never calls `_nmda_pass` and never
builds an `{"intro": ...}` / `{"aware": ...}` evidence dict. So the
background scheduler cannot populate krimelack either.

**Net: the writer (`Section.commit()`, fed real evidence via
`_nmda_pass`) is real, wired, and would fire — it is just never called,
because its only caller `V7Session.converse()` is never invoked by
anything in Joe's actual live path.**

---

## Q3 — History (git log -S pickaxe)

```
git log -S "krimelack: list = field" --oneline -- .../assemblage.py
  979564e feat: v7 DNA recipe substrate — NMDA gates, plasticity, rhythm, awareness
```
The field was born generic, alongside the entire v7 architecture — not a
leftover of something removed, and not intro-specific at birth.

```
git log -S 'sections["intro"].krimelack' --oneline -- .../v7_engine.py
  a2cfe98 Wire NMDA gates: intro/aware as real substrate sections (cognition spec 5)
  f02055c Runtime/UI fixes: persistence, background replay, real substrate state
```

`a2cfe98` (2026-06-08) is the commit that first wired `aware_gate`'s
krimelack-based context. At the time it ran on a **separate 2-section
"meta-observer" System** (`self.meta_sys`), not the main conversation
system — commit message quotes its own test results:

> "Separate 2-section meta-observer system (intro + aware) with NMDA
> gates... Real krimelack commits accumulate in intro/aware sections...
> Intro NMDA: fires 10x on first turn. Aware: 11 commits by turn 5."

Commit `2fda625` ("Item 5 respec: integrated 6-section System with
post-emit intro/aware evidence pass", 2026-06-09) folded `meta_sys` into
the single main `System` — a mechanical rename
(`self.meta_sys.sections[...]` → `sys_.sections[...]`, the parameter
already passed into `check_and_fire`), same evidence-feeding pattern
(10 noisy post-emit ticks), same gate logic. Its own commit message
reports it *still worked* immediately after the merge:

> "cow jumped fence: 10/10 S/V/O, 2.3 intro commits/trial, 2.8 aware/trial
> moon ran milk: 10/10 S/V/O, 2.1 intro/trial, 1.2 aware/trial
> 20-turn mixed: 10.0 intro/turn, 0.45 aware/turn (steady accumulation)"

`f02055c` (2026-06-09, later same day) only touched the `get_state()`
reporting fields (added `intro_krimelack_recent`/`aware_krimelack_recent`
to the UI panel payload) — no logic change.

`_nmda_pass` itself (the shared helper) was introduced in `400d8ac`
("V7 UNIFY: real vocab + phrase-structure grammar + single view",
2026-06-13, "Joe's ruling: never toy in prod") — a full-file rewrite that
consolidated the by-then 6/16-lexical-section architecture down to the
current 3-pool + listen/intro/aware layout. The `_nmda_pass`/evidence
mechanics carried forward unchanged in shape from `2fda625`'s pattern.

**So: the mechanism was never orphaned by a code regression.** It was
proven live (in test-harness conditions, calling `.converse()` directly)
on 2026-06-08/09/13 across three separate commits. What changed since is
*which object the real conversation runs through* — production chat
moved onto `_guala`/`/api/v1/gualaloom` as the live path (confirmed this
session and by -156), and `V7Session`/`/v7/converse` was left as a
structurally-intact but untraveled side road. `DET_COMMIT`/`P_COMMIT`
(the thresholds `commit_check` gates on) have exactly one commit in
their entire history — never edited since — so nothing in the physics
degraded either.

---

## Q4 — Design intent (quoted)

`docs/GL-SPEC-cognition-wC-20260608-007.md`, "Item 5 — Wire NMDA gates in
v7_engine (intro/aware as real substrate sections)" (lines 530-635), the
spec `a2cfe98` was implementing:

> "Aware gate: fires when intro recently committed (noticing one's own
> noticing)"
>
> ```python
> self.aware_gate = CoincidenceGate(
>     section_name='aware',
>     context_fn=context_section_committed('intro', min_arc=0.4),
>     ...
> )
> ```

The spec's intended condition checks intro's **current arc/overlap
level** (a cheap, always-computable quantity — every section has arcs as
soon as it has a psi and a mode_bank) via a purpose-built helper,
`context_section_committed` (gl_nmda.py:111-120):

```python
def context_section_committed(section_name, min_arc=0.30):
    """Context condition: another section has a committed-level arc."""
    def check(sys_):
        if section_name not in sys_.sections:
            return False
        arcs = sys_.sections[section_name].arcs()
        if len(arcs) == 0:
            return False
        return float(arcs.max()) > min_arc
    return check
```

**The shipped code never called this helper.** Grep confirms
`context_section_committed` has exactly one caller in the entire repo,
and it's not in `v7_engine.py`:

```
dsf_ai_service/substrate/gl_nmda.py:111:def context_section_committed(...)
dsf_ai_service/v4/gualaloom_v5_engine.py:2966: ... context_section_committed, ...
```

(That v5-engine usage is a different engine, out of this CMD's scope —
noted, not chased.) `a2cfe98` instead hand-wrote the krimelack-recency
lambda quoted in Q1, and every commit since (`2fda625`, `f02055c`,
`400d8ac`) kept that hand-written version. This divergence from the spec
existed from the very first shipped commit — it is not a later
regression of a once-spec-compliant implementation.

The spec's own acceptance test (5.4) is explicit that regular krimelack
population was the intended bar for "done":

> ```python
> for _ in range(10):
>     s.converse('cow jumped fence')
> intro = s.system.sections['intro']
> assert len(intro.krimelack) > 0, 'NO REAL INTRO COMMITS'
> aware = s.system.sections['aware']
> assert len(aware.krimelack) > 0, 'NO REAL AWARE COMMITS'
> ```

No design statement anywhere in `docs/` describes the *recency-window*
condition actually shipped (`krimelack non-empty AND last tick within
25`) — that specific shape appears to be `a2cfe98`'s own implementation
choice, not traceable to any spec/brief/dispatch.

---

## Q5 — Blast radius (every consumer of `Section.krimelack`)

Full grep, `dsf_ai_service/` only, everything that reads `.krimelack` off
a `Section` object (excludes the two unrelated same-named things noted
in Q2):

| Consumer | File:line | Effect of intro/aware krimelack staying empty |
|---|---|---|
| `aware_gate` context fn | v7_engine.py:94-95 | Permanently `context_blocked` — this CMD's subject |
| `get_state()` → `n_commits_total` | v7_engine.py:529 | Sums krimelack len across **all** sections (pools included) — 0 live means pools aren't committing either, not just intro/aware (see live corroboration) |
| `get_state()` → `intro_krimelack_count`/`aware_krimelack_count` | v7_engine.py:530-531 | Always 0 in the served `/v7/state` payload — feeds whatever UI panel or metric (CMD names "awareness_ratio 0.0, plan v9 #15's wall") reads these |
| `get_state()` → `intro_krimelack_recent`/`aware_krimelack_recent` | v7_engine.py:532-539 | Always `[]` |
| `Section.commit()` itself (`recent_fires`/novelty bonus) | assemblage.py:391 | Self-referential, generic to every section — irrelevant while krimelack for intro/aware is empty since commit() is what's not running |
| `System.replay_tick()` quiet-time consolidation | assemblage.py:795-796, 802-823 | Nothing to sample for intro/aware ever — confirmed live below (`last_replay: {"replayed": 0, "commits": 0}`) |

No other file under `dsf_ai_service/` reads `.krimelack` on a `Section`.
(`System.intro_krimelack` and `neuron.py`'s `self.krimelack` are separate
objects, not in this blast radius — see Q2.)

---

## Live corroboration (read-only GETs, no state mutated)

Two live `/v7/state` snapshots pulled this session via the ALB
(`http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com/v7/state`):

**`session_id=default`** (tick 528):
```json
"n_commits_total": 0, "intro_krimelack_count": 0, "aware_krimelack_count": 0,
"intro_krimelack_recent": [], "aware_krimelack_recent": [],
"last_replay": {"replayed": 0, "commits": 0, "ticks": 3}
```

**`session_id=sid_rrs2dffi`** (Joe's real live v7 session id, tick 996):
```json
"n_commits_total": 0, "intro_krimelack_count": 0, "aware_krimelack_count": 0,
"intro_krimelack_recent": [], "aware_krimelack_recent": [],
"last_replay": {"replayed": 0, "commits": 0, "ticks": 3},
"routing_log": [], "last_response_tokens": []
```
Also 13,907 vocab words seeded across the three pools with **zero**
nontrivial `mode_strength` values (all exactly `1.0`) — consistent with
this `V7Session` never having processed a real `.converse()` call in its
life: vocab gets seeded from `_guala.vocab` at construction
(`seed_vocab_from_engine`), independent of whether `.converse()` ever
runs.

Live `nmda_events` tail from that same snapshot reproduces G-156-5 fresh,
today:
```json
{"gate": "intro", "reason": "drive_below_thresh", "top_val": 0.018654,
 "threshold": 0.05, "drive_ok": false, "context_ok": false, "tick": 988,
 "fired": false, "source": "quiet_tick"}
{"gate": "aware", "reason": "context_blocked", "top_val": 0.077286,
 "threshold": 0.05, "drive_ok": true, "context_ok": false, "tick": 990,
 "fired": false, "source": "quiet_tick"}
```
`aware`'s own drive_ok is `true` at tick 990 (top arc 0.077 clears the
0.05 threshold) — it is `context_ok` alone that blocks it, and
`context_ok` can only ever be true if `sections["intro"].krimelack` is
non-empty. It is not, and per the above, structurally cannot become
non-empty via any path Joe's live session actually exercises.

**NOT MEASURED / stated cause:** could not enumerate every `V7Session`
that has ever existed (no admin endpoint lists `_sessions` or
`v7_sessions/*.json` on EFS; this investigation had no filesystem access
to EFS directly). Checked the two sessions reachable by known id
(`default`, `sid_rrs2dffi`); both show the same result. A CloudWatch
`filter-log-events` query for historical `/v7/converse` hit-count timed
out (2 min) before returning — not re-run, to avoid hammering; the
frontend grep (above) is conclusive on its own that the *current* served
UI never issues that call.

---

## Gates

- **G-160-1** — Q1-Q5 answered with pasted evidence, file:line for every
  claim. NOT MEASURED item stated above (couldn't enumerate all
  historical v7 sessions; cause given). **PASS with stated gap.**
- **G-160-2** — Verdict rendered with evidence: **V-A ORPHANED WRITER**
  (writer real, historically proven, unreachable in live traffic — see
  top). **PASS.**
- **G-160-3** — Diff is empty: confirmed, this investigation made zero
  code changes (`git diff --stat` against HEAD shows nothing from this
  session). Two files show pre-existing uncommitted modifications
  (`dsf_ai_service/v4/gualaloom_v5_engine.py`,
  `tools/guala_recall_bitexact_replay.py`) belonging to a concurrent
  c1a session per the shared-tree protocol — not touched, not staged,
  not part of this report's diff. **PASS.**

Joe's part: none (per CMD).

---

### Changelog
- v1 (2026-07-04, c1b): full Q1-Q5 archaeology. Verdict V-A ORPHANED
  WRITER — `Section.commit()` via `_nmda_pass()` via `V7Session.converse()`
  is real and historically proven (2026-06-08/09/13 commits) but
  unreachable because its only caller, `POST /v7/converse`, gets zero
  calls from the live frontend (`/api/v1/gualaloom` is the real path) or
  the background scheduler (`quiet_tick` only). Design intent
  (`docs/GL-SPEC-cognition-wC-20260608-007.md` Item 5) wanted
  `context_section_committed('intro', min_arc=0.4)` — an arc-level check
  — but the shipped `aware_gate` used a hand-written krimelack-recency
  condition instead, from its very first commit. Live snapshots from
  both `default` and Joe's real session (`sid_rrs2dffi`) corroborate:
  zero commits, ever, system-wide. No fix proposed, per CMD.
