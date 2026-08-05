# TFE Specification v3.0 Amendment Draft B — Log Transform Removed

## Status: DRAFT — pending backtest results

## Amendment
Restore L0 to strict spec compliance per Section 3.3 and 3.6.

### Change to uf_core/layer0.py

Remove:
```python
F_norm = np.log(F_raw + EPS)
```

Replace with:
```python
F_norm = F_raw  # Raw field per UF-Spec Section 3.3
```

### Rationale
UF-Spec v1.4.0 Section 3.3 defines the input as "a raw time-indexed field
F : T → R^d." Section 3.6 defines ΔF(t) = F(t) − F(t − Δt) directly on F.
No normalization step is specified between input and derived quantities.

The log transform was added as an undocumented modification. Per Section 1.5
(Compliance Principle): "the UF Kernel MUST match this specification exactly."
Per Section 19.1: "Deterministic Behavior Requirement" — all implementations
must be reproducible from the spec alone.

### Impact Assessment
- ΔF becomes a price delta (not log-return). Units change.
- σ(t) and κ(t) become scale-dependent. A $500 stock produces larger
  σ and κ than a $5 stock for the same percentage move.
- τ_D = 0.20 acquires units of dollars. For a $5 stock this is a 4% move;
  for a $500 stock this is 0.04%. Gate detection will work dramatically
  differently across the price range.
- Gate formation patterns will change across the entire universe.

### Migration
1. Modify `uf_core/layer0.py` to remove log transform.
2. Re-run full universe snapshot to regenerate all kernel outputs.
3. Validate gate count distribution and signal WR against baseline.
4. Determine whether τ_D becomes a per-symbol parameter (calibration table)
   or whether L1 needs additional normalization to restore scale-invariance
   without log. This is a non-trivial design decision.
5. Compare gate counts for $5 vs $500 stocks to quantify scale-sensitivity.

## Condition for Adoption
Adopt this amendment if backtest condition C (raw + r=1.0) produces WR
≥ 5 percentage points higher than condition A (log + r=1.0) on 20-day
returns, indicating the log transform is actively degrading signal quality.
