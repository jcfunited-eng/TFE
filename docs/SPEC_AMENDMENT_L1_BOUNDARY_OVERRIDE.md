# TFE Specification v3.0 Amendment — L1 Boundary Operator Override

## Status: APPROVED (in code since Feb 2026, needs spec documentation)

## Amendment
Add to Section 4.3 (Gate Boundary Operator), after "D(t) ≥ τ_D ⇒ boundary":

### 4.3.1 Boundary Comparator Override

The Financial Domain Adapter (Section 16) overrides the canonical boundary
comparator from D(t) ≥ τ_D to:

    D(t) > τ_D  ⇒ boundary  (strict inequality)

This override is controlled by the configuration parameter
`gate_boundary_strict_gt` (default: True for financial domain).

**Rationale:** Preferred convention for the financial domain. In the
continuous limit, D(t) = τ_D exactly is measure-zero and the two
comparators are equivalent. In the discrete-bar implementation, exact
equality is rare (<0.1% of bars across the production universe). The
strict inequality is adopted as the financial domain default for consistency.

**Compliance:** This override is:
- Documented in `uf_core/config.py` as `gate_boundary_strict_gt`
- Approved as a domain condition per Section 16.2 (UF Invocation Rules)
- Version-controlled (boolean flag, not a silent semantic change)
- Deterministic and auditable

**Impact:** Marginally fewer gate boundaries than the canonical form.
All downstream operators (L2-L4) are unaffected — they consume gates
regardless of how boundaries are detected.

## Implementation Reference
```python
# uf_core/config.py
gate_boundary_strict_gt: bool = True  # Approved domain override

# uf_core/layer1.py, segment_gates()
if strict_gt:
    boundary = D[i] > tau_D    # Financial domain
else:
    boundary = D[i] >= tau_D   # Canonical UF-Spec
```
