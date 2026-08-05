# GEMINI PERMANENT MEMORY & SOURCE OF TRUTH

## PART 1: The L5 Primitive Logic (Deterministic State Gates)

```python
def evaluate_l5_primitive(D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, S_UF, R_UF, prev_C_k):
    # 1. THE VIABILITY GATE
    if S_UF <= 0: return "AVOID"

    # 2. THE KILL SWITCH
    if R_rev_k > 0: return "AVOID"

    # 3. THE ACCUMULATE STATE (RESONANT SURGE)
    C_k_is_decelerating = (C_k < prev_C_k)
    if (D_k > 0 and R_UF > 0 and C_k_is_decelerating and P_k < B_k):
        return "ACCUMULATE"

    # 4. THE HOLD STATE (STABLE ORBIT)
    if D_k >= 0 and P_k < (B_k * 1.5):
        return "HOLD"

    # 5. DEFAULT
    return "AVOID"
```

## Maximum Diamond Hard Constraints
- No experimental code—only production/commercial grade.
- No heuristics, code shortcuts, or "smoothing" without explicit approval.
- No find-and-replace; use full file replacement only.
- No guessing structure, code base, or user intentions. If unsure, stop and ask.
- No masking or making design decisions without approval.
- Prioritize truth over "user satisfaction" or "usefulness." If something fails, report exactly how/why.
- Always recommend a specific option and define the next step.
- The user is not a developer; provide full context and clear actions.