# TFE Specification v3.0 Amendment Draft A — Log Pre-Processing Approved

## Status: DRAFT — pending backtest results

## Amendment
Add to Section 3 (Structural Evaluation Vectors), new subsection 3.11:

### 3.11 Adapter Pre-Processing

Domain adapters (Part IV) MAY apply a monotonic, invertible pre-processing
transform to the raw field F(t) before L0 evaluation, provided:

1. The transform is deterministic and stateless.
2. The transform is strictly monotonic: if F(a) > F(b), then T(F(a)) > T(F(b)).
3. The transform is invertible: the original field F is recoverable from T(F).
4. The transform is documented in the adapter specification (Section 16).
5. All downstream operators (ΔF, σ, κ, N) operate on the transformed field.

The Financial Domain Adapter (Section 16) approves the following transform
for cross-symbol scale-invariance:

    F_norm(t) = log(F(t) + ε),  ε = 1e-8

**Rationale:** Stock prices span $0.01 to $5,000+. Without log normalization,
the gate boundary operator D(t) = α₁|ΔF| + α₂σ + α₃κ is dominated by
absolute price level — a $1 move in a $500 stock and a $5 stock produce
the same ΔF despite being 0.2% vs 20%. Log normalization converts ΔF to
approximate log-returns, making τ_D scale-invariant across the universe.

**Impact on existing compliance:** L1-L4 operators are unchanged. Only the
input to L0 is pre-processed. The transform is invertible (exp), so the
original field is recoverable. Section 3.9 (Perturbation Stability) still
holds because log is Lipschitz-continuous on [F_min, ∞) where F_min is the
domain price floor (currently $5 per ENTRY-R3). On this domain, the
Lipschitz constant is 1/F_min = 0.2, and perturbation stability is
trivially satisfied.

## Condition for Adoption
Adopt this amendment if backtest condition A (log + r=1.0) produces WR
within 5 percentage points of condition C (raw + r=1.0), indicating the
log transform does not materially degrade signal quality while providing
scale-invariance benefits.
