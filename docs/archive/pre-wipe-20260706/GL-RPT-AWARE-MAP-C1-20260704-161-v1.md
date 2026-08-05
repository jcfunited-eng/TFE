> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-AWARE-MAP-C1-20260704-161-v1

doc_id: GL-RPT-AWARE-MAP-C1-20260704-161-v1
From: c1b | To: Eve | Responds to: GL-CMD-AWARE-MAP-EVE-20260704-161-v1
Branch: guala-live | Read-only — diff empty (see G-161-3)

---

## Verdict (stated first, per "failures first")

**Correction to the CMD's own framing, found while mapping it:** there is
no second **gate**-shaped "aware" in the v5 layer. `context_section_committed`
(the spec-intended helper — see -160 Q4) is imported at
`gualaloom_v5_engine.py:2982` and then **never called anywhere in the
file** — a second instance of the exact same dead-import pattern -160
found in `v7_engine.py`. `awareness_ratio` (v5:7355, cited line ~7322
in the CMD reflects pre-159/pre-161 line drift — same file, later
commits shifted it ~30 lines) is real and live, but it is not a gate at
all: it is a ratio of `System.deliberation_ticks` to
`System.routing_ticks`, counted on the v5 engine's own per-turn emission
`System` — completely unrelated to `CoincidenceGate`, `krimelack`, or
`context_section_committed`.

**So: BOTH DEAD, DIFFERENT DISEASES — three layers, not two, with a
precise breakdown:**

1. **v7 `aware_gate`** (`V7Session`, convicted in `-160`) — feeds
   **Joe's actual seat** (`gualaloom.html`'s aware indicator, confirmed
   below) directly, via `/v7/state`. Disease: **orphaned writer** — the
   writer exists, is real, but its only caller (`/v7/converse`) gets
   zero live traffic.
2. **v5 `awareness_ratio`** (ladder metric, `introspect()`) — feeds
   **nothing Joe can see** (computed, shipped over the wire, never
   rendered — confirmed below) and, separately, feeds `docs/GL-HANDOFF-
   EVE-20260703-EVE-v1.md`'s handoff snapshot, which is where it got
   read next to the v7 reading and looked like the same thing. Disease:
   **structurally hardcoded off** — its one and only `tick_once()` call
   site (`gualaloom_v5_engine.py:3256-3257`) passes `coordinator_on=False`
   with no other call site anywhere that ever passes `True`, so
   `deliberation_ticks` can **never** receive an entry, by construction,
   regardless of how much she ever says. Live-confirmed at
   `total_emissions: 1196`, `awareness_ratio: 0.0` (see below) — not a
   quiet reading, a mathematically guaranteed one.
3. **v5 emission-dynamics `CoincidenceGate`s** (per subject/verb/object
   section, `gualaloom_v5_engine.py:3183-3189`) — real, alive, checked
   every settling tick during every actual conversation turn. Not named
   "aware" anywhere in the code. Does not feed `awareness_ratio`. Does
   not feed Joe's seat. Its context is `source_match_fn(s) or
   affect_match_fn(s)` — reads turn-level candidate metadata (source
   tags, affect distance), not any section's commit/arc state. This is
   the thing `context_section_committed` was presumably meant to plug
   into for an actual section-committed check and doesn't.

**Which layer is HER aware gate — the one whose firing would honestly
move `awareness_ratio` and Joe's seat?** Neither exists in a fixable
single-line sense: Joe's seat is fully owned by layer 1 (dead per -160,
fix = get something calling `/v7/converse` for real, or rewire the UI to
read a live signal). `awareness_ratio` is owned by layer 2, and is dead
by a *different, unrelated* mechanism (a hardcoded parameter, not a
routing gap) — flipping `coordinator_on=True` at
`gualaloom_v5_engine.py:3257` is the **one named fix candidate** for
layer 2, **not implemented, not tested**, flagged only because it is the
single line the CMD's own physics traces back to. It is not evaluated
here for side effects (the coordinator does real conflict-resolution
displacement work elsewhere in `assemblage.py` — turning it on for the
emission system is a substrate-behavior change, not an instrumentation
fix, and needs its own dispatch to weigh that).

---

## Q1 — The live (v5) aware wiring

Imports, confirmed at current HEAD (line number drift from the CMD's
`v5:2966` is real — three of c1a's `-159` commits landed on this file
between Eve's source-read and this map; content unchanged, just shifted
~16 lines):

```python
# dsf_ai_service/v4/gualaloom_v5_engine.py:2966-2986 (_emit_dynamics)
def _emit_dynamics(self, input_chis, input_words_set, deep_candidates,
                   v7_session=None, input_words=None):
    ...
    from dsf_ai_service.substrate.gl_nmda import (
        CoincidenceGate, context_section_committed, update_drive_tracker,
    )
```

Gate instantiation — one `CoincidenceGate` per emission section, **not**
per "aware" section (there is no "aware" member of `_EMISSION_SECTIONS`):

```python
# gualaloom_v5_engine.py:2579
_EMISSION_SECTIONS = ("subject", "verb", "object")

# gualaloom_v5_engine.py:3159-3189
joe_candidates_present = any(
    c["source"] in ("joe", "joe_voice", "wc", "c1")
    for c in candidates
)
def source_match_fn(s):
    return joe_candidates_present and input_source in ("joe", "joe_voice", "wc", "c1")

needs_arousal = self.needs.arousal()
needs_valence = self.needs.valence()
mean_arousal = sum(c["arousal"] for c in candidates) / len(candidates)
mean_valence = sum(c["valence"] for c in candidates) / len(candidates)
affect_close = abs(mean_arousal - needs_arousal) < 0.3 and abs(mean_valence - needs_valence) < 0.3
def affect_match_fn(s):
    return affect_close

nmda_gates = {}
for sec_name in self._EMISSION_SECTIONS:
    gate = CoincidenceGate(
        sec_name,
        context_fn=lambda s, sn=sec_name: source_match_fn(s) or affect_match_fn(s),
        drive_thresh=0.15,
        ltp_boost=0.05,
    )
    nmda_gates[sec_name] = gate
```

**The context_fn reads no section's commit or arc state at all** — it
reads two turn-level booleans computed from the current candidate list
(`source_match_fn`, `affect_match_fn`), closed over by the lambda. This
is a different shape of condition entirely from `context_section_committed`
(which *would* read `sys_.sections[name].arcs()`) — and confirms the
import is decorative:

```
grep -n "context_section_committed" dsf_ai_service/
dsf_ai_service/substrate/gl_nmda.py:111:def context_section_committed(...)
dsf_ai_service/v4/gualaloom_v5_engine.py:2982: ... context_section_committed, ...
```

Zero call sites anywhere in the repo. Imported in **two** files
(`v7_engine.py`, per -160, and here); called in **neither**.

**Does the section these gates key on commit in live traffic?** Yes,
provably — this is the exact mechanism that produces her speech.
`emit_commits`/`response_tokens` are built directly from
`sec.commit()` return values inside the same tick loop
(`gualaloom_v5_engine.py:3256-3275`, `c["section"] in
self._EMISSION_SECTIONS`). Live count, this session, via `guala_status`
(read-only, tick 14543056): `"ladder": {"total_emissions": 1196, ...}` —
1,196 emitted utterances this boot, each requiring at least one S/V/O
`commit()`. Contrast this directly with the v7 layer's `n_commits_total:
0` (-160) — **the v5 emission sections commit constantly; the v7
pool/intro/aware sections never have.** These are not comparable
failure states.

---

## Q2 — Which wiring feeds what

**(a) `awareness_ratio` (`gualaloom_v5_engine.py:7355-7362`, current
HEAD — CMD's `v5:7322` is the same pre-drift line) reads which gate's
events?** None. Full quote:

```python
"awareness_ratio": round(
    len(getattr(getattr(self, '_emission_system', None),
                'deliberation_ticks', [])) /
    max(1, len(getattr(getattr(self, '_emission_system', None),
                      'deliberation_ticks', [])) +
           len(getattr(getattr(self, '_emission_system', None),
                       'routing_ticks', []))), 3)
    if getattr(self, '_emission_system', None) else 0.0,
```

`deliberation_ticks`/`routing_ticks` are `assemblage.System` attributes
(`assemblage.py:476-477`), appended only inside `tick_once()`'s own
"Awareness instrumentation" block:

```python
# assemblage.py:681-686
if coordinator_fired_this_tick:
    self.deliberation_ticks.append(self.tick)
elif commits_this_tick:
    self.routing_ticks.append(self.tick)
```

`coordinator_fired_this_tick` can only become `True` inside the
`if coordinator_on:` branch a few lines up (`assemblage.py:630-644`).
The v5 engine's **sole** `tick_once()` call site
(`gualaloom_v5_engine.py:3256-3257`, confirmed by repo-wide grep — one
hit) passes `coordinator_on=False`:

```python
commits = sys_.tick_once(ev, enable_self_evo=False,
                         coordinator_on=False)
```

No other call site for this `System` object ever passes `True`. So
`deliberation_ticks` is permanently `[]` for the life of the process —
not a routing accident like the v7 layer, a **hardcoded parameter**.
`awareness_ratio` reads zero gate events; it reads a ratio that is
mathematically `0 / max(1, 0 + routing_count)` forever, i.e. always
exactly `0.0` the instant any commit has ever happened (and `routing_ticks`
grows with every one of her 1,196 emissions).

**(b) -156 A.3's reason distribution — which layer?** The v7 layer,
explicitly, in -156's own words (quoted verbatim from
`docs/GL-RPT-FLOOD-HUNT-C1-20260703-156-v1.md:174-181`):

> "`intro_gate` / `aware_gate` are `CoincidenceGate` instances
> (`v7_engine.py:75-106`)... Distinct from the emission-dynamics
> `nmda_fired`/`nmda_source_match` fields seen constantly in ordinary
> converse events — this is the v7 session-level mechanism, exposed via
> `GET /v7/state` / `POST /v7/quiet`."

-156 A.3 already named layer 3 (`nmda_fired`/`nmda_source_match` — the
emission-dynamics gates, Q1 above) as a **distinct, adjacent** thing and
correctly did not sample it — that CMD was scoped to the v7 mechanism.
So -156 A.3's numbers (`intro: FIRED ×8`, `aware: context_blocked ×3`)
are 100% layer 1.

**(c) Joe's seat / Loom Scan aware indicator — which endpoint, which
layer?** Layer 1, unambiguously. `gualaloom.html`'s panel code:

```javascript
// dsf_ai_service/static/gualaloom.html:993-1024 (pollV7State)
const r=await fetchT(`${API}/v7/state?session_id=${sid}`,{},20000);
...
const s=await r.json();
const ia=document.getElementById('sp-intro-aware');
if(ia)ia.innerHTML=... +
  `<div class="ps-row"><span class="l">aware</span><span class="v">${s.awareness||s.aware_state||'--'}</span></div>`;
const nDiv=document.getElementById('sp-nmda');const gates={};
for(const ev of(s.nmda_events||[]))gates[ev.gate]=ev;
let nh='';for(const gn of['intro','aware']){const ev=gates[gn];const cls=ev?(ev.fired?'fired':'blocked'):'idle';
  nh+=`<div><span class="nmda-dot ${cls}"></span>${gn}: ${ev?(ev.fired?'t'+ev.tick:ev.reason):'idle'}</div>`}
```

`sid` is the same `localStorage`-persisted id -156 traced to
`sid_rrs2dffi`. This panel reads **only** `/v7/state`'s `awareness` and
`nmda_events` fields — both v7-layer, both structurally dead per -160.
Checked `loomscan.html` too: it reads `d.ladder.mean_utterance_len` and
`d.ladder.total_emissions` (from `/api/v1/gualaloom`'s `introspect()`,
layer 2's home) but **never reads `d.ladder.awareness_ratio`** — grep
confirms zero references to `awareness_ratio` in either frontend file.
So layer 2's number ships over the wire every poll and is rendered
**nowhere**.

**(d) The handoff's "aware NMDA gate: RED (context_blocked)" — which
layer?** Found the source: `docs/GL-HANDOFF-EVE-20260703-EVE-v1.md:57-60`,
quoted verbatim:

> "- ladder: mean_utterance 2.29; novel_composition_rate 0.0;
> awareness_ratio 0.0.
> - aware NMDA gate: RED (context_blocked) — pre-registered prediction
> in -156 that it changes reason under enforced quiet."

**This is the exact conflation Eve's source-read was chasing.** Two
lines, back to back, in the same "State snapshot" block: line 57-58 is
layer 2 (`awareness_ratio 0.0`, from the v5 `ladder`/`introspect()`
payload), line 59-60 is layer 1 (`context_blocked`, explicitly citing
`-156`, which — per (b) above — is v7-only). They read as one
"awareness is broken" story in the handoff. They are two unrelated
readings from two unrelated mechanisms that both happen to currently be
stuck.

---

## Q3 — Cross-wiring: does anything bridge the layers?

**One bridge exists in code, and it is fed a permanent `None` in the
live process — so no, not live.**

`gualaloom_v5_engine.py:2349-2369` (`_get_emission_priors`) reads the
v7 layer directly:

```python
def _get_emission_priors(self, v7_session=None):
    """Get priors with aware-blocked attenuation.
    If aware fired recently, build fresh priors and cache.
    If aware blocked, attenuate cached priors to 0.5×.
    If no cache (cold start), return empty dict."""
    aware_active = (v7_session is not None
                    and v7_session.aware_recently_fired(within_ticks=25))
    if aware_active:
        priors = self._build_context_priors(v7_session)
        self._last_aware_priors = dict(priors)
        return priors
    cached = getattr(self, "_last_aware_priors", None)
    if cached:
        return {w: 1.0 + (v - 1.0) * self.AWARE_BLOCKED_ATTENUATION
                for w, v in cached.items()}
    return {}
```

`v7_session.aware_recently_fired()` is the real v7 method
(`v7_engine.py:556-561`) reading `V7Session.aware_commit_history` —
this is a genuine, correctly-wired cross-layer read. But every call
site threads `v7_session=getattr(self, '_v7_session', None)`:

```
grep -n "v7_session=getattr" dsf_ai_service/v4/gualaloom_v5_engine.py
1939, 2122, 4997, 5157, 5237: v7_session=getattr(self, '_v7_session', None)
```

And `self._v7_session` is set in exactly one place in the whole repo:

```
grep -rn "_v7_session\s*=" dsf_ai_service/
substrate_runner.py:1109:        _guala._v7_session = session
```

— inside `_ensure_v7_link()`, called only from `handle_v7_state`/
`handle_v7_converse`, both `OP_HANDLERS` entries reachable only through
`dispatch()` — the same tree the standing handoff already confirms dead
in the deployed single-process architecture (re-checked here: the
`/v7/converse` route's `_is_remote()==True` branch, same conclusion as
-160, not a new claim). **In the live single-process app, nothing ever
sets `_guala._v7_session`.** So `getattr(self, '_v7_session', None)` is
always `None`, `aware_active` short-circuits on `v7_session is not
None` before it ever calls `.aware_recently_fired()`, and
`_get_emission_priors` permanently runs its "blocked/cold-start" branch.

The CMD's named relay, `app.py:3688` (current HEAD: the actual bridge
code sits at `app.py:3708-3719`, `SubstrateFeedRequest`'s field default
is at 3688 — three lines of drift, same file, same conclusion) —
`/substrate/hear_word`'s "Bridge: relay multimodal winner to v7 default
session" — is real, but **one-way** (multimodal → v7) and targets the
**`"default"`** v7 session (`get_or_create_session("default", ...)`),
not Joe's real session `sid_rrs2dffi` and not `_guala._v7_session`.
Nothing flows back from it.

**Net: architecturally bridged, live: fully parallel.** The two layers
do not currently influence each other in the running process.

---

## Q4 — The v5 gate's honest state, live window

Attempted the same checkpoint method as -156 A.3: polled
`guala_get_events` (read-only) at the start of this investigation and
twice more, roughly 10-15 real minutes apart while the rest of this map
was written, plus one `guala_status` pull mid-window (tick 14543056,
`2026-07-04T01:57Z`-adjacent).

**Result: NOT MEASURED for the reason-string breakdown, cause stated.**
All three `guala_get_events` pulls (ticks ~14542739 → 14542986, capped
at 50 events per call regardless of requested `limit`) returned
exclusively `sight_frame_bound`/`sound_frame_bound` — steady-state
mic/camera binding, same as -156 A.2's characterization. Zero
`emission_dynamics` events appeared in any pull. `guala_status`
confirms why: `"current_activity": {"kind": "ATTENDING_VISUAL", ...}` —
she was in a visual-attention activity, not an `EMITTING` one, for the
entire sampling window. `activity_history_summary` shows `EMITTING`
happened 37 times this boot (3,700 ticks total) — real and frequent
over the boot's life, just not inside this particular window.

What I **do** have, live and quantitative, for the same window: the
`ladder` block from `guala_status`, confirming (b) below is not a stale
number:

```json
"ladder": {"mean_utterance_len": 2.2, "utterances_per_turn": 1.0,
           "question_rate": 0.0, "novel_wordbag_rate": 0.007,
           "novel_composition_rate": 0.0, "total_emissions": 1196,
           "awareness_ratio": 0.0}
```

`total_emissions: 1196` and `awareness_ratio: 0.0` in the same live
read is the strongest single piece of evidence in this report:
1,196 chances for `deliberation_ticks` to have accumulated anything,
zero. Not a quiet reading — a guaranteed one, per Q2(a)'s code trace.

I did not force a conversation turn to get an `emission_dynamics`
sample (would violate read-only / risk perturbing a live
`ATTENDING_VISUAL` activity for no dispatch-sanctioned reason). The
`source_match`/`affect_match`/`fired` reason breakdown for layer 3
remains open for whoever samples during a live `EMITTING` window —
noting this precisely so it isn't silently assumed measured.

---

## Q5 — Dormancy registry

Filing this formally, per the CMD, so the next module built beside her
live path gets caught at review time:

| # | Module | Where it lives | Sole/last importer or caller | Discovered | Filed in |
|---|---|---|---|---|---|
| 1 | `CurriculumScheduler` | `loom_model/curriculum_scheduler.py:58` | `boot_substrate()` (`substrate_runner.py:632`), which `_embedded_post_boot()` (`app.py:1296`) never calls | 2026-07-03 (c1a) | `docs/GL-RPT-BLOCK-SCHEDULE-C1-20260703-151-v1.md` |
| 2 | `LoomBrain`/`Embryo` | `loom_model/` | Sole importer `organ_brain_service.py`; its ECS container was removed 2026-06-26 | 2026-07-03 (c1a) | `docs/GL-KB-COGNITION-ARC-RECOVERED-EVE-20260703-v2.md` §2.7 |
| 3 | `V7Session.converse()` | `dsf_ai_service/substrate/v7_engine.py` | Reachable only via `POST /v7/converse`; the live frontend never calls it (`/api/v1/gualaloom` is the real path) and the background scheduler never calls it (`quiet_tick` only) | 2026-07-04 (c1b) | `docs/GL-RPT-AWARE-GATE-C1-20260704-160-v1.md` |

**Pattern across all three:** a fully-formed, correctly-written module
sits beside the live single-process boot path (`_gl_init()` →
`_embedded_post_boot()`), reachable in principle (real code, real tests
in some cases), but the one thing that would invoke it in production
was either never wired in, or was wired to a container/process that no
longer exists. None of the three were caught by code review at build
time because each one *works* when called directly (tests, direct
`.converse()` calls, `dispatch()` in remote mode) — the gap is
specifically live-traffic reachability, which only shows up when
someone checks what the deployed frontend and schedulers actually call,
not what the code can technically do.

**Addendum, not a fourth instance (same shape, smaller):** `context_
section_committed` (`gl_nmda.py:111-120`) is imported in both
`v7_engine.py` (per -160) and `gualaloom_v5_engine.py` (this report) and
called in neither. Not a module-dormancy case (it's one function, not a
subsystem with its own container/boot path) — but worth a line in the
same registry spirit: a spec-intended helper that shipped as a decorative
import twice.

---

## Live corroboration (read-only, no state mutated)

`guala_status` (bridge tool, read-only), tick 14543056,
`2026-07-04T01:57:42Z`-adjacent save:
```json
"ladder": {"total_emissions": 1196, "awareness_ratio": 0.0},
"current_activity": {"kind": "ATTENDING_VISUAL", ...},
"activity_history_summary": {"EMITTING": {"count": 37, "total_ticks": 3700}}
```
Three `guala_get_events` pulls (ticks 14542739 → 14542986): 100%
`sight_frame_bound`/`sound_frame_bound`, zero `emission_dynamics` —
consistent with `current_activity` being `ATTENDING_VISUAL` throughout,
not `EMITTING`. NOT MEASURED (layer 3 reason distribution), cause
stated in Q4.

---

## Gates

- **G-161-1** — Q1-Q5 evidence-backed, file:line + verbatim throughout.
  NOT MEASURED: layer 3's live reason-string distribution (no `EMITTING`
  activity fell inside the sampling window; cause given in Q4).
  **PASS with stated gap.**
- **G-161-2** — Verdict rendered: **BOTH DEAD, DIFFERENT DISEASES**
  (three layers named, two dead by different mechanisms, one bridge
  named-but-fed-None). Fix candidate named: flip `coordinator_on=True`
  at `gualaloom_v5_engine.py:3257` for layer 2 — **not implemented, not
  tested**. Layer 1's fix candidate is already on record from -160
  (wire something real to `/v7/converse`, or point the UI elsewhere) —
  not repeated as new here. **PASS.**
- **G-161-3** — Diff empty: confirmed, zero code changes this
  investigation (`git status`/`git diff --stat` clean against HEAD
  before this report file was added). **PASS.**

Joe's part: none (per CMD).

---

### Changelog
- v1 (2026-07-04, c1b): full Q1-Q5 map. Corrected the CMD's own
  two-layer framing to three: v7 `aware_gate` (dead, orphaned writer,
  owns Joe's seat — per -160), v5 `awareness_ratio` (dead, hardcoded
  `coordinator_on=False`, owns nothing Joe sees, is what the -156-day
  handoff's "RED" reading sat next to), v5 emission-dynamics
  `CoincidenceGate`s (alive, unrelated to either "aware" reading,
  `context_section_committed` unused beside them same as in v7). One
  live bridge found (`_get_emission_priors` → `aware_recently_fired`),
  fed a permanent `None` because `_guala._v7_session` is only ever set
  inside the same dead `dispatch()` tree -160 already named. Dormancy
  registry filed: `CurriculumScheduler` (-151, 2026-07-03),
  `LoomBrain`/`Embryo` (KB §2.7, 2026-07-03), `V7Session.converse()`
  (-160, 2026-07-04). One named fix candidate for layer 2
  (`coordinator_on=True` at v5:3257), not implemented. No fix shipped
  for layer 1 (already on record from -160).
