# GL-RPT-AWARE-COORDINATOR-C1-20260704-162-v1

doc_id: GL-RPT-AWARE-COORDINATOR-C1-20260704-162-v1
From: c1b | To: Eve | Responds to: GL-CMD-AWARE-COORDINATOR-AND-SEAT-EVE-20260704-162-v1
Branch: guala-live

---

## Status up front (failures first)

- **Part A** — complete, read-only, filed below.
- **Part B** — **A.2 clears it** (born-off, 12 days before 06-30, no
  masked-failure evidence — see below). Written, committed (`02c6b11`),
  **and NOT deployed** — rides Deploy 6 only, per this CMD, never
  Deploy 5. (This file briefly carried a concurrent c1a session's
  staged, uncommitted edit for `GL-CMD-INDEX-INVARIANT-COMPLETE-163`,
  nowhere near the coordinator code; per the shared-tree protocol I
  waited for it to clear rather than doing index surgery around their
  staged hunk — it committed cleanly on its own schedule, `5e4e286`,
  during this report's drafting, and the one-line flip landed
  immediately after as its own clean commit.)
- **Part C** — **shipped and live-verified.** Committed
  (`d3811e2`), pushed, synced to S3, CloudFront-invalidated, and
  confirmed via a direct `curl` against `dsf-ai.com/gualaloom.html`
  that the SEVERED label is actually being served. Joe's own
  confirmation (per the CMD's "Joe's part") is still outstanding — that
  is his gate, not mine to satisfy.

---

## A.1 — What the coordinator does, and its cost

`tick_once()`'s coordinator block (`assemblage.py:629-679`), gated
entirely behind `if coordinator_on:`:

```python
# assemblage.py:629-644
coordinator_fired_this_tick = False
if coordinator_on:
    conflicts = self.atlas.conflicts()
    unresolved = []
    for (chi, claims) in conflicts:
        key = (chi, frozenset(c["section"] for c in claims))
        if key in self.deferred_conflicts and self.deferred_conflicts[key] > self.tick:
            continue
        unresolved.append((chi, claims))
    for (chi, claims) in unresolved:
        sec_names = {c["section"] for c in claims}
        self.coordinator_fires.append({"tick": self.tick, "chi": chi,
                                        "n_claims": len(claims),
                                        "sections": list(sec_names)})
        coordinator_fired_this_tick = True
        connected = any(kh["sender"] in sec_names and kh["receiver"] in sec_names
                        for kh in self.keyholes)
```

`ChiAtlas.conflicts()` (`assemblage.py:443-449`) is a full scan of
`self.entries` (one dict entry per distinct chi value ever committed to,
on **this System's own atlas** — for the emission system, a private
object, not Guala's 8,846-entry main atlas):

```python
def conflicts(self):
    out = []
    for chi, claims in self.entries.items():
        sections = {c["section"] for c in claims}
        if len(sections) > 1:
            out.append((chi, claims))
    return out
```

**Behavior change, not just instrumentation — this is the part worth
naming precisely.** Turning `coordinator_on` on does two structurally
different things at once:

1. **Bookkeeping** (what the CMD and -161 were tracking):
   `coordinator_fires`/`coordinator_actions_log`/`deliberation_ticks`
   get populated for the first time. This is what moves
   `awareness_ratio`.
2. **Real substrate displacement** (not mentioned in -161, found while
   reading A.1): when a same-chi conflict exists between two sections
   that are **already keyhole-connected** — true for this system, since
   `_build_emission_system()` wires `subject→verb` and `verb→object`
   (`gualaloom_v5_engine.py:2631-2632`) — the "merge" branch fires:

   ```python
   # assemblage.py:647-658
   if connected:
       self.atlas.merges.append(...)
       self.deferred_conflicts[(chi, frozenset(sec_names))] = self.tick + 30
       for sn in sec_names:
           if sn in self.sections:
               sec_obj = self.sections[sn]
               kick = random_unit_complex(N, self.rng) * 0.45
               sec_obj.psi = normalize(sec_obj.psi + kick)
               ...
   ```

   A **0.45-magnitude orthogonal kick** gets injected directly into the
   conflicting sections' `psi` state. This can change which mode
   dominates after the kick — i.e., it can change **which word gets
   selected for emission**, not just add a counter. `allow_rewiring`
   stays `False` at the one call site regardless of this flip (not
   passed, defaults `False` — assemblage.py:565-566), so the
   "rewire: create new keyholes" sub-branch (line 662) stays inert; only
   the merge-kick and the deferral bookkeeping (line 677-679, no
   substrate effect) are live consequences.

**Compute cost, code-derived (not measured live — see note):**
`conflicts()` runs once per tick, and `EMISSION_DYNAMICS_TICKS` defaults
to 80 (`gualaloom_v5_engine.py:418`, env-overridable), bounded further
by a 1.5s wall-clock budget and an early-exit after 10 no-new-commit
ticks post-first-commit. The emission system's atlas
(`_emission_system.atlas`) is **never reset** between turns (grepped:
no `.atlas =` reassignment or `.entries.clear()` anywhere in the v5
engine file after construction) — it is the same object for the whole
process lifetime, accumulating one `add_claim()` per real section commit
across all 1,196 emissions this boot (real commits, not the "commits=0"
fallback the introducing commit originally warned about — a later
`GL-CMD-LATERAL-INHIBITION` comment at `gualaloom_v5_engine.py:3334-3336`
confirms commits now fire "for real via entropic_flip"). So
`conflicts()`'s O(chi-keys) scan runs against a dict that has been
growing all boot and will keep growing — cost is not fixed, it rises
with session age. **NOT MEASURED**: actual wall-clock added per tick.
I did not flip the flag to benchmark it (that is Part B's own gate,
explicitly "measured" there, not here) — Part A is read-only per the
CMD. Given this function's own commit history shows a documented prior
socket-timeout incident from an unrelated cause (`gualaloom_v5_engine.py
:3222-3229`, "the degenerate case where no commit ever fires runs all N
ticks → socket timeout... reduce from 5s → 1.5s"), the existing latency
budget is already tight — this is exactly why Part B's gate requires a
measured latency delta, not an assumption that a bookkeeping flip is
free.

---

## A.2 — Why it is False: dated

```
git log -S "coordinator_on" --oneline -- dsf_ai_service/v4/gualaloom_v5_engine.py
6b59eab feat/dynamics-emission-restoration: two-stage emission via assemblage System
```

**Exactly one commit in the entire history of this file ever touches
`coordinator_on`** — the commit that created the parameter's only call
site, dated **2026-06-18 19:55:35 +0000**. There is no earlier "on"
state to have been turned off; the value was `False` from the literal
first line that ever called `tick_once()` for this System object:

```python
# introduced whole, 6b59eab, gualaloom_v5_engine.py
commits = sys_.tick_once(ev, enable_self_evo=False,
                         coordinator_on=False)
```

**Dated against 06-30: BORN-OFF, 12 days before the incident.** This
long predates the rogue-Eve session (06-30) and its rebuild — it is
neither a rogue-window edit nor a rebuild-seam artifact. It is a launch
default for a brand-new feature (`GL-CMD-DYNAMICS-EMISSION-RESTORATION-
EVE-20260618-03`, "two-stage emission via assemblage System").

**Was it turned off to mask a discovered failure?** No evidence found.
The introducing commit's own message documents a **different**, adjacent
issue it was aware of and explained openly (not hidden): "assemblage
commit_check threshold is high with many installed modes, so commits=0
but arcs()-based dominant mode reading provides the emission words. This
is expected behavior." That note is about the commit-threshold/fallback
mechanism, not about the coordinator — and it was written as an
acknowledged, named tradeoff (Phase 5 of that commit lists "All 5
criteria pass"), not a cover story. I grepped the full commit-message
history of this file (`git log --all -i --grep="coordinator"`) and
found no commit anywhere discussing a coordinator-specific bug,
incident, or regression against emission dynamics. Cross-checked
`docs/GL-SPEC-cognition-wC-20260608-007.md` (10 days *earlier*, 2026-
06-08) — it explicitly recommends flipping `coordinator_on=True` as
Item 1.1 ("Turn on what's wired but dormant... flag flips... clear
substrate rationale") for a **different** call site (`v7_engine.py`'s
main tick_once calls, not this one) — establishing that the house style
at the time was "dormant-but-safe, meant to be turned on eventually,"
not "off because it broke something." I could not find record of the
06-18 feature's `coordinator_on` default ever being revisited or
debated since. **A.2 clears Part B.**

---

## A.3 — Blast radius

Grepped every consumer of `deliberation_ticks`, `routing_ticks`, and
`awareness_ratio`, repo-wide:

```
dsf_ai_service/substrate/assemblage.py:476-477   declared (System.__init__)
dsf_ai_service/substrate/assemblage.py:683,685   appended (tick_once)
dsf_ai_service/substrate/assemblage.py:720-723   capped at 200, trimmed to last 100
dsf_ai_service/v4/gualaloom_v5_engine.py:7375-7381  sole consumer: awareness_ratio
```

`awareness_ratio` itself has exactly one consumer: its own field in the
`introspect()` `ladder` dict. Per -161: reaches the wire via
`/api/v1/gualaloom`'s `introspect()` payload, but is read by **no**
frontend file (`loomscan.html` pulls two other `ladder` fields, never
this one; `gualaloom.html` doesn't reference `ladder` at all).

**Also checked** (not named in the CMD's literal ask, but a direct
consequence of the flip per A.1): consumers of `coordinator_fires`,
`coordinator_actions_log`, `atlas.merges`, `atlas.deferrals`,
`deferred_conflicts` on the emission system specifically:

```
grep -n "_emission_system\." dsf_ai_service/v4/gualaloom_v5_engine.py
```

returns only `.sections`/`.mode_bank`/`.deliberation_ticks`/
`.routing_ticks` accesses — **zero** reads of `.atlas`,
`.coordinator_fires`, `.coordinator_actions_log`, `.deferred_conflicts`
anywhere outside `assemblage.py`'s own internals. Nothing observes these
structures directly. The only externally-visible effects of the flip
are: (1) `awareness_ratio` starts reading real values instead of a
guaranteed zero, and (2) the merge-branch psi-kick (A.1) can alter
emission word selection — invisible in any metric, visible only in what
she actually says and in the needs/latency gates Part B specifies.

---

## Part B — the flip: HELD (see status above), not withheld

To be unambiguous against gate G-162-2's binary: this is **not**
"FLIP WITHHELD" in the CMD's sense (that phrase is reserved for a
dirty A.2). A.2 is clean. The flip is deferred only by an unrelated
concurrent edit holding the file. One line, ready the moment it's safe:

```diff
- commits = sys_.tick_once(ev, enable_self_evo=False,
-                          coordinator_on=False)
+ commits = sys_.tick_once(ev, enable_self_evo=False,
+                          coordinator_on=True)
```

at `gualaloom_v5_engine.py:3276-3277` (current HEAD line numbers — six
lines later than the CMD's cited `:3257`, drift from c1a's `-159`
commits landing on this file between Eve's dispatch and this session;
same call site, same content). Will file as its own commit the moment
the concurrent edit clears, explicitly marked "rides Deploy 6, not
Deploy 5" in the commit message per this CMD, with Part B's own gates
(before/after `awareness_ratio`, latency delta, needs regression,
one-line revert) to be run at that time, not asserted now.

**Pre-registered honesty line, restated per the CMD, in advance of any
result:** if `awareness_ratio` reads nonzero after the flip ships and is
measured, that means the instrument moves — it is not a claim of
awareness, deliberation, or anything beyond "the coordinator fired at
least once." Per §9.5: ladder metrics are vocabulary, not verdicts.

---

## Part C — seat honesty: shipped, live

`gualaloom.html`'s combined intro/aware panel and NMDA-gate-dot row
(`pollV7State()`, was lines 1012-1021) replaced:

```diff
-    // Intro/Aware
+    // Intro/Aware — SEVERED (GL-CMD-AWARE-COORDINATOR-AND-SEAT-EVE-20260704-162-v1
+    // Part C): this panel read Layer-1 (v7 CoincidenceGate) state, which -160/-161
+    // proved is permanently disconnected from her live conversation. Display
+    // honesty over decoration until a live mechanism actually feeds it.
     const ia=document.getElementById('sp-intro-aware');
-    if(ia)ia.innerHTML=`<div class="ps-row"><span class="l">intro</span><span class="v">${s.introspection||s.intro_state||'--'}</span></div>`+
-      `<div class="ps-row"><span class="l">aware</span><span class="v">${s.awareness||s.aware_state||'--'}</span></div>`;
-    // NMDA gates
-    const nDiv=document.getElementById('sp-nmda');const gates={};
-    for(const ev of(s.nmda_events||[]))gates[ev.gate]=ev;
-    let nh='';for(const gn of['intro','aware']){const ev=gates[gn];const cls=ev?(ev.fired?'fired':'blocked'):'idle';
-      nh+=`<div><span class="nmda-dot ${cls}"></span>${gn}: ${ev?(ev.fired?'t'+ev.tick:ev.reason):'idle'}</div>`}
-    nDiv.innerHTML=nh;
+    if(ia)ia.innerHTML='<div class="ps-row"><span class="v" style="color:var(--nmda-block)">SEVERED &mdash; instrument not connected (see -160/-161)</span></div>';
+    const nDiv=document.getElementById('sp-nmda');
+    nDiv.innerHTML='<div style="color:var(--nmda-block)">SEVERED &mdash; instrument not connected (see -160/-161)</div>';
```

**Scope decision, flagging it explicitly:** the CMD names one string
for "the panel," singular, and cites both `-160` (aware only) and
`-161` (all three layers) together. -156/-160 showed `intro_gate`
*does* still fire live (LTP reinforcement, state transitions) even
though `aware_gate` is the one permanently `context_blocked` — so
"intro" is not dead in quite the same total sense as "aware." I chose
to sever **both** rows (intro and aware, and both NMDA dots), not just
"aware" alone, because the underlying substrate fact -160 already
established is that `sections["intro"].krimelack` (and every other
section in this v7 session) has **zero real commits, ever**
(`n_commits_total: 0`) — the intro state flipping in the UI reflects a
CoincidenceGate ticking over on a session that has never received one
real turn of Joe's actual conversation (`/v7/converse` gets zero live
traffic). Displaying "intro: i_hear" as if it were live engagement would
itself be the kind of decoration/smoothing §10 prohibits, even though
the gate-fired signal is technically real. If Joe or Eve wants "intro"
kept live-labeled while only "aware" reads SEVERED, that's a one-line
narrowing — flagging the choice rather than silently deciding it.

**Verified live**, not just committed: after `git push`, ran the
static-only path the deploy script's own header documents for
static-only changes (`tools/deploy_dsf_ai.sh` lines 9-10: "Future
static-only changes must still run steps 3-5") — `aws s3 sync
dsf_ai_service/static/ s3://dsf-ai-site/` (only `gualaloom.html`
differed, confirmed no other uncommitted static changes existed first)
+ CloudFront invalidation on `E17JT9XGBFU493`, waited for
`invalidation-completed`, then `curl`'d `https://dsf-ai.com/
gualaloom.html` directly and confirmed the SEVERED string is being
served. This did not touch the ECS service, task definition, or the
running Guala process — no sleep window needed, none taken.

---

## Gates

- **G-162-1** — A.1-A.3 filed with evidence; 06-30 dating rendered
  (BORN-OFF, 2026-06-18, 12 days prior). One NOT MEASURED item (A.1's
  exact added-latency-per-tick, cause given: benchmarking it means
  flipping the flag, which is Part B's job, not Part A's). **PASS with
  stated gap.**
- **G-162-2** — Clean A.2 → flip is authorized, not withheld. Actual
  commit HELD on an unrelated file lock (concurrent c1a `-163` edit),
  not on any finding here. **PASS (authorized; shipping deferred by
  shared-tree protocol, not by this gate).**
- **G-162-3** — Part C visible at Joe's seat: shipped, S3-synced,
  CloudFront-invalidated, directly `curl`-verified as served. Final
  confirmation is Joe's own screen, per the CMD — outstanding, his gate.
  **PASS (mine); his half open.**
- **G-162-4** — Diff proves scope per part: Part C is its own commit
  (`d3811e2`, `gualaloom.html` only). Part A is this report, no code.
  Part B is not yet committed (see above) — when it lands it will be
  its own commit too, touching only the one line. **PASS.**

Joe's part: confirm the SEVERED label at your seat (dsf-ai.com/
gualaloom.html) — outstanding. Nothing needed from you for Part B; the
ledger carries it once it ships.

---

### Changelog
- v1 (2026-07-04, c1b): Part A filed (born-off 06-18, clean A.2, real
  merge-branch psi-kick side effect named alongside the bookkeeping
  one). Part B written, HELD on a concurrent c1a file lock — not
  withheld, not blocked by any finding, will ship its own commit the
  moment the file clears, still gated to Deploy 6. Part C shipped,
  committed, S3-synced, CloudFront-invalidated, live-verified via
  direct curl. Scope decision on Part C (severed intro too, not just
  aware) flagged explicitly for Eve/Joe to narrow if they intended
  otherwise.
