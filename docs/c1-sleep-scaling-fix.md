# c1: Fix the O(n²) Sleep — chi-class bucketing

**From:** wC (Joe coordinating)
**Type:** Performance fix. Do before she grows large; cheap to change now.
**File:** `src/gualaloom/sleep.py`

## The problem

Sleep Phases 4 (co-resonance reinforcement) and 5 (merge near-duplicates)
are O(n²) — nested loops over all motif fingerprint pairs. The
consolidation loop holds the thread lock for the entire sleep+dream
cycle. At a few hundred motifs this is instant. At scale it isn't:

- 5,000 motifs  ≈ 12M pairs  ≈ ~1s per sleep
- 20,000 motifs ≈ 200M pairs ≈ ~20s per sleep  (blocks ingest 20s)
- 50,000 motifs ≈ 1.25B pairs ≈ ~2min per sleep (starves the daemon)

She is meant to live for weeks/months and grow into the thousands. An
O(n²) sleep every 10 minutes, holding the lock, will eventually starve
ingest and interaction. This is the single cost/scaling lever — fixing
it keeps her on the cheapest box indefinitely.

## The fix: bucket by chi-class first

Motifs only meaningfully merge or co-resonate with structurally similar
motifs. Two motifs in different chi-classes (different Euler
characteristic) are not near-duplicates and won't share a settled
manifold neighborhood. So there is no reason to compare across chi-classes.

Every motif already has `m.chi` computed at commit time. Use it:

1. **Bucket** all motifs by chi-class into a dict: `{chi_value: [fps]}`.
2. **Run Phases 4 and 5 WITHIN each bucket only**, not across all pairs.

This turns O(n²) into roughly Σ(n_c²) over chi-classes c. With motifs
spread across ~40-46 chi-classes (per the topology experiment's
841→46 collapse), that's a large constant-factor reduction — often
1-2 orders of magnitude — and it grows much more gently.

### Concrete change

Replace the Phase 4 and Phase 5 loops. Currently:

```python
fps = k.all_fingerprints()
for i, fp_a in enumerate(fps):
    for fp_b in fps[i+1:]:
        ...
```

Becomes:

```python
# Bucket by chi-class — only structurally-similar motifs can merge/co-resonate
buckets = {}
for fp, m in k.motifs.items():
    buckets.setdefault(m.chi, []).append(fp)

# Phase 4: co-resonance reinforcement, within-bucket only
for chi_val, bucket_fps in buckets.items():
    for i, fp_a in enumerate(bucket_fps):
        for fp_b in bucket_fps[i+1:]:
            cr = _co_resonance(k, fp_a, fp_b)
            if cr >= CO_RESONANCE_THRESHOLD:
                ma = k.get_motif(fp_a); mb = k.get_motif(fp_b)
                if ma and mb and ma.weight < WEIGHT_CAP and mb.weight < WEIGHT_CAP:
                    ma.weight += 1; mb.weight += 1
                    total_reinforced += 2
                    ma.successors[fp_b] = ma.successors.get(fp_b, 0) + 1
                    mb.successors[fp_a] = mb.successors.get(fp_a, 0) + 1
```

And Phase 5 merge: re-bucket (buckets may have changed if Phase 4
altered anything material — safest to rebuild) and run the merge nested
loop within each bucket only, same pattern.

### Guard the hamming check

Within a chi-bucket, the merge still checks
`_hamming(ma.state, mb.state) <= MERGE_HAMMING_THRESHOLD`. That stays —
chi-class is a coarse filter, hamming is the fine one. Bucketing just
means you never waste the hamming comparison on motifs that can't
possibly merge.

## Optional second lever (only if still slow at scale)

If even within-bucket O(n_c²) gets slow because one chi-class dominates
(e.g. the χ=−6 bucket holds most motifs), add a "touched since last
sleep" set: only run merge/co-resonance on motifs whose weight or
successors changed since the previous sleep. Skip this for now unless
profiling shows a single fat bucket — premature otherwise.

## Definition of done

- Phases 4 and 5 operate within chi-buckets, not across all pairs.
- Behavior is otherwise identical (same merges happen — cross-chi pairs
  never merged anyway, so no merge is lost).
- A `# WC_REVIEW:` note documents the scaling rationale inline.
- Quick sanity check: run a sleep at the current motif count, confirm
  the merge/reinforce/cull counts match the pre-fix behavior (they
  should — this is a speed fix, not a behavior change).

## Note from wC

This is a pure performance fix — it must NOT change which motifs merge,
only stop wasting comparisons on pairs that were never going to merge.
If the merge/reinforce counts change materially after bucketing, that's
a bug (it would mean cross-chi-class merges were happening before, which
they shouldn't have been). Verify counts match. This is what keeps her
cheap forever — it's the difference between "stays on a $5 box" and
"needs a bigger box every time she grows."
