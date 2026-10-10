# GL-RPT-LANGUAGE-SATURATION-ROOTCAUSE-C1-20260704-178-v1

doc_id: GL-RPT-LANGUAGE-SATURATION-ROOTCAUSE-C1-20260704-178-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-LANGUAGE-SATURATION-ROOTCAUSE-EVE-20260704-178-v1`.
Vehicle: model code only. No deploy action. **Candidate L3(b) is
built and dramatically validated but NOT wired to any live call
site and NOT deployed — G-1/G-2 gates below are open, not closed by
this report.** Per `-179-v2`'s W2, this couples with the brain-growth-
unfreeze build; the two ship as one reconciled SHA, not this one alone.

**L1 confirmed and quantified precisely. L2's contamination list named
below, plainly. L3(b) built, and — after catching and correcting my
own methodology bug mid-investigation — measured to restore recall
accuracy from severely degraded (2/15 = 13% at 200 words taught) to
100% (15/15) in a clean, controlled reconstruction. L4's prediction
stated, with an honest open question about her PRE-EXISTING vocabulary
flagged, not glossed over.**

---

## Failures first

**I made a real methodology mistake mid-investigation and caught it
before reporting a conclusion, not after.** My first accuracy
comparison (candidate-b fix vs. no fix) used two separately-written,
separately-seeded throwaway scripts with different RNG-reuse patterns
and different vocabulary lists — it showed the fix making accuracy
*worse* (5-6/15 with the fix vs. 9-15/15 without, at deep teaching
depths). That result was an artifact of the inconsistent comparison,
not a real effect. Rebuilt as one clean A/B on a single embryo
instance, same checkpoints, same RNG-per-checkpoint convention,
comparing `recall_fast()` (built in `-177`, hardcodes the OLD
`len(deque)`-based language computation, unmodified since) against
`recall()` (now automatically uses the NEW `n_events` counter once it
exists on the class — no other code touched) — a natural, already-
available A/B pair, not a monkeypatch. That corrected comparison is
what appears below, and it reverses the earlier (wrong) conclusion
entirely.

---

## L1 — root cause, file:line, arithmetic

**Where:** `dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py:32`
(`_EVENTS_MAXLEN = 256`) and `:55` (`self.events = deque(maxlen=
_EVENTS_MAXLEN)`, in `Krimelack.reset()`). Consumed at
`dsf_ai_service/loom_model/neuron.py:846` and `:858`
(`_unwrapped_deltas`, the organism cognition path — confirmed the
**only** live path: `grep`-verified zero calls to `LoomBrain.step()`/
`Neuron.step()` anywhere in `gualaloom_v5_engine.py`): `ev0/ev1 =
krim.n_events if hasattr(krim, 'n_events') else len(krim.events)`.
`LanguageKrimelack` (unlike the sensory adapters) had no `n_events`
attribute, so this always took the `len(krim.events)` branch — a
bounded (`maxlen=256`), FIFO-evicting count, not a true monotonic
counter.

**Why it saturates:** `no_reset=True` on every call (the organism
never resets this krimelack — confirmed, `reset()` is never invoked on
this instance for the process's entire life), so `events` only ever
grows, bounded at 256 by the deque. Once `len(events) == 256`, any
further `.append()` evicts an equally-sized amount, so `len()` stays
pinned at 256 forever — `ev1 - ev0 = 0` regardless of how many real
winding transitions occur during a query, permanently.

**The arithmetic, measured directly** (real `LanguageKrimelack`, real
per-character signal, `tests/probe_178_saturation_accuracy.py`):
~18.3 winding events per word on average (measured across a 20-word
sample); `256 / 18.3 ≈ 14` words to saturation. Confirmed directly:
word #14 in a real feed sequence pins `len(events)` at 256. Extended
to the full live population (heterogeneous per-neuron `kappa`/
`threshold`, `embryo.py:175`'s `_seed_dna_diversity` — same mechanism
`-177` had to account for): individual neurons saturate at different
rates (some faster, some slower, per their own `kappa`), but **100% of
the 64 seed neurons are fully saturated (zero live language signal) by
30 words taught, permanently, in a fresh organism** — measured
directly, checkpoint table below.

**Lifetime, on the actual live process:** `read_word()`
(`gualaloom_v5_engine.py:1841`) calls `_enqueue_organism_remember(word)`
— hence `experience_moment()`, hence this exact code path — for
**every single word she reads or hears**, unconditionally, since
`GL-CMD-BRAIN-FULL-DEPLOY-175` went live tonight (`task:462`). She has
been reading continuously (autonomous curriculum + real conversation)
for hours since. **Her language channel has been fully, permanently
saturated (delta = 0, contributing nothing) for effectively the entire
time this mechanism has been live tonight**, past the first ~14-30
words of that window.

**Reconciling the standing docs' "~3-4 taught words, double-feed"
figure** (`GL-RPT-SENSE-REPAIR-C1-20260704-v1.md:78-81`): that number
describes a **different, non-live** pipeline —
`ExperiencePipeline.deliver_word()` (`experience.py:53`), which calls
`LoomBrain.step()` (feeding the krimelack via `Neuron.step()`, a
completely separate Stage-1 mechanism from the organism's `experience_
moment()` cognition path) — confirmed only ever invoked from `embryo.
py`'s demo functions (`main()`, `seed_organism()`), never from the live
engine. That pipeline's double-feed-per-word rate saturates faster
(~3-4 words) than the live organism's single-feed rate (~14-30 words,
measured above) — both are the SAME deque-saturation mechanism, at
different feed rates from different, non-overlapping pipelines. The
live number is **~14-30 words**, not ~3-4.

---

## L2 — blast radius: contaminated numbers, named not defended

| Report / mechanism | Words taught before/during the measurement | Contamination |
|---|---|---|
| `GL-RPT-P2-RECALL-FIX-C1-20260704-v1.md` (seam 1, "10-probe" + "20-word disjoint vocabulary", **the fix this whole P2 track is built on**) | 10 and 20 | **Contaminated, partially.** Reconstructed directly (`tests/probe_178_saturation_accuracy.py` liveness table): by the 10th word queried in a 10-word run, only 39/64 neurons (61%) still carry any language signal; by the 20th word in a 20-word run, only 9/64 (14%). The reported **100%/100% is real and not fabricated**, but for the later-queried words in each test, it was carried substantially or almost entirely by touch/smell/taste, not language. |
| `GL-RPT-P2-RECOGNITION-SEAM`/fix (seam 2) | Same test, same report | Same contamination — shared numbers with the row above. |
| `GL-RPT-P2-ASSOCIATION-SEAM-C1-20260704-v1.md` (seam 3, the `zzznever`→`upon` 64/64 unanimous "too-good" finding) | "after teaching ~35 real words" (report's own words) | **Fully contaminated.** At 30+ words taught, language is measured at 0/64 live neurons (below). The 64/64 unanimous vote is a property of the SENSORY channels / atlas structure alone — language contributed nothing to that result. Does not invalidate the finding (recall's lack of a reject/uncertainty option is still real), but reframes what it's a finding *about*: not a language-specific issue, since language was already inert throughout that test. |
| `GL-CMD-ORGANISM-PERSIST-C1-20260704-v1.md` (-169, DNA/persistence proof) | Core cited example: "experiences 5 words" | **Not contaminated at its core claim.** At 5 words, language is still 100% live (table below). -169's central claims (structure-derived DNA, restore-honesty, resumable raising loop) are about persistence/identity mechanics, not recall-accuracy numbers, so this finding doesn't touch them directly. If any recall/growth metric was separately measured deeper into that report's longer multi-session run (word count not stated precisely in what I read), that specific number would need its own check — flagging the uncertainty rather than asserting either way. |
| **Tonight's live organism** (`task:462` onward, all 6 P2 seams live per `GL-RPT-WINDOW2-DEPLOY-C1B-20260704-v1.md`) | Hours of continuous reading since deploy | **Fully and currently contaminated.** Every seam-1/2/3/4 call on the live process right now is running on 3 of 6 modality channels (tactile/olfactory/gustatory only — visual/auditory are never populated by `_organism_signal` either) — language has contributed nothing to any live recall/recognition/association/habituation output since shortly after `task:462` went up. |

**Liveness-vs-teaching-depth table** (fresh organism, real
`_organism_signal`, real `remember()`, `tests/probe_178_saturation_
accuracy.py`):

| words taught | language-live neurons (of 64) |
|---|---|
| 1 | 64 (100%) |
| 5 | 64 (100%) |
| 10 | 39 (61%) |
| 14 | 24 (38%) |
| 20 | 9 (14%) |
| 30 | 0 (0%) |
| 50+ | 0 (0%) |

---

## L3 — fix candidates, measured

### (b) Per-feed baseline via a true monotonic counter — BUILT, measured, recommended

**What:** added `self.n_events = 0` to `Krimelack.__init__` (set once,
not in `reset()`), incremented on every winding transition in `feed()`
(`gualaloom_v4_krimelack_dna.py`). `_unwrapped_deltas`'s existing
`hasattr(krim, 'n_events')` dispatch (neuron.py:846/858) picks this up
automatically — **no other code changes required** for the fix itself
to take effect.

**Not a novel design choice — completes an already-decided one.**
`sensory_krimelacks.py`'s `OscillatorKrimelack` already has this exact
counter, added by `GL-CMD-SENSE-REPAIR`, whose own comment there says
the adapters in `substrate_dna.py` "already assumed this existed" —
i.e., the monotonic-counter pattern was already GL-CMD-138's stated
intent for krimelacks generally; `LanguageKrimelack`/base `Krimelack`
simply never received it. This candidate closes that gap, not invents
a new one.

**Correctness proof, same discipline as `-177`:**
- **INV-1 (read-only):** 15/15 identical back-to-back queries at 50
  words taught (well past old saturation). **PASS.**
- **INV-2 (teaching-sensitive):** 1/15 probes changed after one real
  teach event, at 50 words taught. **PASS (not frozen)** — the low
  *rate* of change is consistent with the population-vote's already-
  flagged too-confident/insufficiently-uncertain behavior (the same
  class of issue as seam 3's 64/64-unanimous finding above), not a
  defect this candidate introduces; not separately re-litigated here.

**Measured accuracy effect — the corrected, trustworthy comparison**
(`recall_fast()` = OLD len-based semantics, unmodified since `-177`;
`recall()` = NEW, now that `n_events` exists; same embryo, same
checkpoints, same RNG-per-checkpoint seed):

| words taught | language-live (both conditions build the same atlas up to here) | OLD accuracy | NEW accuracy |
|---|---|---|---|
| 1 | 64/64 | 1/1 | 1/1 |
| 5 | 64/64 | 5/5 | 5/5 |
| 10 | 64/64 | 10/10 | 10/10 |
| 14 | 64/64 | 10/14 | **14/14** |
| 20 | 64/64 | 8/15 | **15/15** |
| 30 | 64/64 | 6/15 | **15/15** |
| 50 | 64/64 | 7/15 | **15/15** |
| 100 | 64/64 | 5/15 | **15/15** |
| 200 | 64/64 | **2/15 (13%)** | **15/15 (100%)** |

(The "language-live" column here reflects the fix's own effect on
liveness by construction — both legs share the same taught atlas up to
each checkpoint, so this table isolates the read-side computation.)

This is a large, clean, monotone effect: OLD accuracy degrades
progressively as more words accumulate (matching the liveness collapse
in L2's table), NEW accuracy holds at 100% throughout. Confirms Eve's
prime-suspect hypothesis directly, in a controlled reconstruction —
language's silent zeroing is not a cosmetic gap, it measurably starves
recall as her vocabulary grows.

### (a) Widen/window the buffer — reasoned, not separately built

Extending `_EVENTS_MAXLEN` (e.g. 256 → 4096) only rescales L1's own
arithmetic: `4096 / 18.3 ≈ 224` words to saturation — later, not never.
Given the live organism reads continuously for hours, any *fixed*
buffer size hits the same wall eventually; this is a delay, not a fix,
same class of honest mitigation as `c1b`'s already-deployed call-
frequency reduction, not a candidate for THE fix. Also directly
conflicts with an already-documented memory concern in the same file
(`_EVENTS_MAXLEN`'s own comment: "without this cap: 110k-220k event
dicts per experience() call, measured via tracemalloc"). Not
recommended.

### (c) Decay the counter — reasoned, not built

Introduces a new, invented time-constant with no substrate-physics
grounding — the kind of untuned-constant risk this project has
explicitly avoided elsewhere. Worse, decaying a value that INV-1
requires to be identical on back-to-back queries either has to decay
by *tick* (real state-dependence, a bigger architectural change than
this dispatch scoped) or by *query count* (would make recall's own
querying mutate what future queries see — reintroducing exactly the
"recall must not pollute future recalls" violation `GL-CMD-SENSE-
REPAIR` was written to prevent). Directly contradicts stated design
intent, not just untested. Not recommended, not built.

**Time-boxing note:** (a) and (c) are reasoned from L1's own measured
arithmetic and the codebase's own stated design intent, not built as
full parallel implementations and separately measured — `-179-v2`
arrived mid-investigation with its own build order and W2's explicit
instruction to land jointly with this fix; given (b) is unambiguously
strong and consistent with existing intent, further build effort on
(a)/(c) was not spent under that time pressure. Flagging the trade-off
rather than silently making it.

---

## L4 — expected-effect prediction, stated before any deploy

**If (b) ships and this hypothesis is right:** live `read_word`
recognition (seam 2) and `_recall_response`/`_daydream_tick` (seams
1/3) should show a measurable jump in accuracy/discrimination for
concepts taught **after** the fix goes live — matching the clean-
reconstruction table above (severe degradation → nearly perfect, at
her real vocabulary scale, which is far beyond the 200-word ceiling
tested here). Post-deploy, the confirming signal is: recognition
surprise values should show real separation between taught and novel
words again (not the `zzznever`→`upon`-style false confidence), and
recall on recently-taught words should hit noticeably more often.

**The honest open question, not glossed over:** this fix changes
*future* computations only — it does **not** retroactively change
concepts she already learned while saturated (essentially her entire
current vocabulary, ~14,000 words, all learned before tonight or
within the first ~30 words of tonight's window). Those bindings were
recorded with language permanently at 0. Post-fix, querying the SAME
already-learned word will now compute a real, nonzero language value
(deterministic per word, phase always resets to 0 for language — see
`-177`'s finding) that the STORED binding never had. Whether this
helps (uniform improvement, since ~all pre-existing bindings share the
same zero-language artifact) or introduces a train/query mismatch for
her EXISTING vocabulary specifically is **not tested by this report** —
my clean reconstruction always taught and queried words in the same
post-fix run. **Predicted, to be checked, not assumed:** brand-new
post-fix vocabulary should behave like the table above; her
pre-existing vocabulary's behavior is a real open question the
post-deploy measurement needs to check specifically (e.g., compare
recall accuracy on a KNOWN pre-existing word before and after the
fix ships, not just on freshly-taught words) — if it's the same or
better, the hypothesis is fully confirmed; if pre-existing vocabulary
gets WORSE, that's the honest result to report, not defend.

---

## Gates

- **G-1** — this contamination list (L2) is filed in this report; no
  fix has shipped ahead of it.
- **G-2** — candidate (b) genuinely changes what "experience" means to
  her memory encoding going forward (language stops being a silent
  no-op after ~14-30 words, permanently). **Flagged for Eve's ruling,
  not shipped.** Nothing wired into any live call site; `Embryo.
  recall()`/`remember()` behavior changes automatically the MOMENT
  this branch is merged and deployed (no separate wiring step needed,
  since it's a hasattr-dispatched fallback) — meaning the actual "ship
  it" decision IS this specific commit reaching a live task, not some
  later step.
- **G-3** — per `-179-v2` W2, this is not an independent SHA to c1b;
  it couples with the brain-growth-unfreeze build, one reconciled SHA
  for both, once Eve rules on G-2.

---

## Files

- `dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py` — `Krimelack.
  __init__`/`feed()`: added `n_events` monotonic counter (candidate b).
- `dsf_ai_service/loom_model/tests/probe_178_saturation_accuracy.py` —
  L1 arithmetic, L2 liveness table, L3(b) corrected A/B accuracy
  comparison.

### Changelog
- v1 (2026-07-04, c1a): L1 root-caused with file:line + measured
  arithmetic (~14-30 words to saturation, live-representative; the
  standing "~3-4 words" figure reconciled as a different, non-live
  pipeline). L2 contamination list filed against seam 1/2/3 reports,
  -169, and tonight's live organism. L3(b) built (completes an already-
  intended GL-CMD-138/SENSE-REPAIR pattern), INV-1/INV-2 proven, and —
  after catching and correcting my own flawed first comparison —
  measured to restore recall accuracy from 13% to 100% at 200 words
  taught. (a)/(c) reasoned against L1's arithmetic and stated design
  intent, not built, time-boxed against -179's arrival. L4 prediction
  stated with an explicit, unresolved open question about her
  pre-existing (pre-fix) vocabulary. G-1/G-2 open, not closed. Couples
  with -179-v2 per its own W2, not an independent deploy.
