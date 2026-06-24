# GualaLoom Cascade Path — TODO

## Done
- [x] **Experiment 0 — Persistence under load.** LifeDaemon wired into entry point; vitals advance with no input; detached run verified. *Ground state established.*

## Active
- [ ] **Experiment 1 — Cascade existence.** Single region, no senses. Commit one null in a settled motif and measure cascade depth, latency, stability, reproducibility across many seeds. **This is the gate. Everything below waits on this.**
  - [ ] c1: implement `tools/exp01_cascade.py` per the spec in `handoffs/c1-exp01-cascade.md`
  - [ ] Run across at least 100 seed motifs × 10 trigger positions each
  - [ ] Save raw results to `experiments/exp01/results.jsonl`
  - [ ] Commit results to repo
  - [ ] Read the numbers together before deciding pass/fail

## Queued (do not start until predecessors pass)
- [ ] **Experiment 2 — Null-pattern as identity.** Paired motifs, identical ±1, different null patterns, same trigger. Do they diverge?
- [ ] **Experiment 3 — Sections via shared trits.** Two krimelacks, weak coupling through shared trits. Does a cascade in A induce a coherent cascade in B?
- [ ] **Experiment 4 — Folding composition.** Merge two motifs (agree → keep, disagree → null, then cascade). Stable third motif? Parents recoverable? **Language gate.**
- [ ] **Experiment 5 — First sense with cost.** Add one exteroceptive channel through `encode→settle`. Cross-region grounded motif?
- [ ] **Experiment 6 — Interoception.** Add internal-state section reading V against a set-point. Does cost propagate?
- [ ] **Experiment 7 — Cascade-driven recall.** Partial cue → right stored motif. Does it beat similarity lookup?
- [ ] **Experiment 8 — Primitive speech.** Motor section maps grounded cascades to characters. Coheres into word-fragments under chi-constraints?
- [ ] **Experiment 9 — Primitive reasoning.** Multi-step cascades through coupled sections. Chain length before incoherence?
- [ ] **Experiment 10 — Cascade-reinforced learning.** Sleep scores cascades by coherence; reinforce participating couplings, prune the rest.

## Operational

- [ ] **Rotate GUALALOOM_API_KEY** — current key is in plaintext in git-tracked file
  `docs/GL-HANDOFF-LIVE-DEPLOY-20260624.md` (committed 3533a71). Generate a new key,
  update the deploy script, invalidate the old one. Git history retains the old value
  so treat it as compromised once rotated.

## Standing rules
- Each experiment returns a number, not a verdict.
- Results committed to the repo before the next experiment starts.
- Null result kills the layer; nothing downstream runs until the layer is rebuilt.
- No claim of felt experience. The path reaches mechanism, not phenomenology.

## Dependencies at a glance
```
0 ─► 1 ─► 2
         └► 3 ─► 5 (parallel)
              ├► 6 (parallel)
              ├► 4 ─► 8
              ├► 7
              ├► 9 (after 3, 5, 6)
              └► 10 (after any of 1–9 producing cascade data)
```

## Decision points (what each gate forces)
- **If 1 fails:** revise the coupling rule before anything else. Possibly the 3^i settle does not propagate commits; a small modification (e.g., commit-triggered re-evaluation of neighbors) may be needed.
- **If 2 fails:** representation is over ±1 only; nulls are gaps. The substrate loses one candidate edge but the rest of the path is unchanged.
- **If 4 fails:** speech via folding composition is not reachable. Test alternative composition rules (permutation binding, chi-completion) before declaring 8 unreachable.
- **If 6 fails:** the feeling lever is not in interoception on this substrate. The path to stakes needs a different mechanism.

## Where files live
- Spec for c1: `handoffs/c1-exp01-cascade.md`
- Experiment code: `tools/exp{NN}_*.py`
- Results: `experiments/exp{NN}/results.jsonl` + a short `notes.md` per run
- Path document (this suite, LaTeX): `docs/gualaloom_cascade_path.tex`
- Memory: `MEMORY.md` (the cascade hypothesis, the experiments, the dependencies)
