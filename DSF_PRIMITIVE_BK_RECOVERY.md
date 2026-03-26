# DSF Primitive B_k Recovery

Purpose:
- resolve the faithful mathematical meaning of `B_k` on the approved primitive surface
- do one element only
- do not resume the rejected full-field candidate
- do not derive a final primitive formula here

Status:
- audit completed on the approved latest fixed snapshot
- verdict: `ambiguous`

Scope:
- fixed snapshot only
- primitive surface only:
  - `S_UF`
  - `R_UF`
  - `D_k`
  - `M_k`
  - `R_rev_k`
  - `U_star_k`
  - `C_k`
  - `P_k`
  - `B_k`

Out of scope:
- final primitive formula
- runtime rewrite
- transport/helper fields
- price / volume / external metadata
- synthetic paths

## 1. Approved Definitions Used In This Audit

Approved:
- `M_hat = max(-1.0, min(1.0, M_k))`

Derived exactly as instructed:
- `s = S_UF - U_star_k`
- `r = R_UF - U_star_k`
- `w = min(s, r)`
- `e = max(s, r)`
- `covered_two_sided = (w > 0)`
- `covered_one_sided = (w <= 0 and e > 0)`
- `rupture = (e <= 0)`
- `D_pos = max(D_k, 0.0)`
- `D_neg = max(-D_k, 0.0)`
- `M_cont = (1.0 + M_hat) / 2.0`
- `M_bend = (1.0 - M_hat) / 2.0`
- `raw_carry = -B_k`

Important honesty boundary:
- `raw_carry` was treated only as a nonnegative latent magnitude for audit
- this note does not claim it is already “live carry” or already “exhaustion”

## 2. Snapshot Used

Approved latest fixed snapshot used for the audit:
- `/workspaces/Tao_Financial_Engine/backups/runtime/canonical_real_snapshot_production_fixed_snapshot_latest_20260321T013943Z.csv`

Schema confirmed:
- `symbol`
- `decision_timestamp`
- `bar_count`
- `S_UF`
- `R_UF`
- `D_k`
- `M_k`
- `R_rev_k`
- `U_star_k`
- `C_k`
- `P_k`
- `B_k`

## 3. Exact Raw Carry Range

`raw_carry = -B_k`

Exact range:
- `min = -0.0`
- `max = 1.0`
- `p01 = -0.0`
- `p10 = -0.0`
- `p25 = 0.20036242092887646`
- `p50 = 0.8191436591900761`
- `p75 = 1.0`
- `p90 = 1.0`
- `p99 = 1.0`

Histogram / bin counts:
- `0.0-0.1 = 892`
- `0.1-0.2 = 459`
- `0.2-0.3 = 394`
- `0.3-0.4 = 278`
- `0.4-0.5 = 214`
- `0.5-0.6 = 185`
- `0.6-0.7 = 156`
- `0.7-0.8 = 114`
- `0.8-0.9 = 112`
- `0.9-1.0 = 111`
- `1.0 = 2498`

Important truth:
- `raw_carry` is heavily top-loaded
- exact saturation at `1.0` is common

## 4. Bucket Table

Buckets were built without using `B_k` itself:

- `covered_forward`
  - `count = 73`
  - `mean = 0.3205077621923792`
  - `median = 0.26539170810624835`
  - `std = 0.21860074298654322`
  - `p10 = 0.1631058541599484`
  - `p25 = 0.17735963560897905`
  - `p75 = 0.3413280243722517`
  - `p90 = 0.4855733082800793`

- `covered_bending`
  - `count = 50`
  - `mean = 0.35525559151394903`
  - `median = 0.23433034347373632`
  - `std = 0.28982485448464507`
  - `p10 = 0.10175937551338197`
  - `p25 = 0.15335995679909564`
  - `p75 = 0.4125723188072117`
  - `p90 = 1.0`

- `covered_adverse`
  - `count = 404`
  - `mean = 0.23289884359726598`
  - `median = 0.06981198689420975`
  - `std = 0.31302898969884657`
  - `p10 = 0.0678057142496773`
  - `p25 = 0.06870042073836075`
  - `p75 = 0.2093832226295888`
  - `p90 = 1.0`

- `covered_reversal`
  - `count = 61`
  - `mean = 0.39907006620335006`
  - `median = 0.27510835173097986`
  - `std = 0.30750292175693633`
  - `p10 = 0.1074338061150763`
  - `p25 = 0.1529345500824823`
  - `p75 = 0.5348101765158083`
  - `p90 = 1.0`

- `one_sided_forward`
  - `count = 355`
  - `mean = 0.5503000524403017`
  - `median = 0.5083009795349328`
  - `std = 0.331767474972784`
  - `p10 = 0.06620156207613598`
  - `p25 = 0.2697549320197734`
  - `p75 = 0.9142633843775854`
  - `p90 = 1.0`

- `one_sided_break`
  - `count = 541`
  - `mean = 0.5708910771812662`
  - `median = 0.5280523064520292`
  - `std = 0.3351308150120286`
  - `p10 = 0.132433590469354`
  - `p25 = 0.2605303491089988`
  - `p75 = 1.0`
  - `p90 = 1.0`

- `rupture_rows`
  - `count = 3259`
  - `mean = 0.8190948247331512`
  - `median = 1.0`
  - `std = 0.29941169177834787`
  - `p10 = 0.2500320761242855`
  - `p25 = 0.6652673821440052`
  - `p75 = 1.0`
  - `p90 = 1.0`

Unclassified rows:
- `count = 670`

## 5. Pairwise Comparisons That Matter

- `covered_forward vs covered_bending`
  - `median_delta = 0.031061364632512023`
  - `mean_delta = -0.034747829321569834`

- `covered_forward vs covered_adverse`
  - `median_delta = 0.1955797212120386`
  - `mean_delta = 0.08760891859511322`

- `covered_forward vs covered_reversal`
  - `median_delta = -0.009716643624731514`
  - `mean_delta = -0.07856230401097086`

- `one_sided_forward vs one_sided_break`
  - `median_delta = -0.019751326917096357`
  - `mean_delta = -0.020591024740964525`

- `covered_forward vs rupture_rows`
  - `median_delta = -0.7346082918937517`
  - `mean_delta = -0.498587062540772`

## 6. Correlations

Diagnostic only:

- `corr(raw_carry, D_k) = -0.008217808392110205`
- `corr(raw_carry, M_hat) = -0.06380948468849737`
- `corr(raw_carry, R_rev_k) = 0.34805280608648115`
- `corr(raw_carry, C_k) = -0.13124635401040474`
- `corr(raw_carry, P_k) = 0.3007311459021968`
- `corr(raw_carry, s) = -0.5891219483349089`
- `corr(raw_carry, r) = -0.35539307787217717`

Important truth:
- `raw_carry` rises as coverage weakens
- `raw_carry` rises with reversal and persistence stress more than it aligns with forward motion

## 7. Interpretation Tests

### T1

Test:
- if `raw_carry` is materially higher in `covered_forward` than in `covered_adverse` / `covered_reversal` / `rupture_rows`,
  then `B_k` supports a live-carry reading

Result:
- `covered_forward` is higher than `covered_adverse`
- but not higher than `covered_reversal`
- and far lower than `rupture_rows`

Conclusion:
- `T1` does not win

### T2

Test:
- if `raw_carry` is materially higher in `covered_adverse` / `covered_reversal` / `rupture_rows` than in `covered_forward`,
  then `B_k` supports an exhaustion / break reading

Result:
- `covered_reversal` is slightly higher than `covered_forward`
- `rupture_rows` is much higher than `covered_forward`
- but `covered_adverse` is lower than `covered_forward`

Conclusion:
- `T2` does not win cleanly

### T3

Test:
- if `raw_carry` is high in both `covered_forward` and `covered_adverse/reversal`,
  then `B_k` is unsigned persistence magnitude and must be aligned with `D_k / M_hat / R_rev_k`

Result:
- `covered_forward` is only moderate
- `covered_reversal` is similar or slightly higher
- `covered_adverse` is not high in the same way
- `rupture_rows` dominates the entire distribution

Conclusion:
- `T3` also does not win cleanly

## 8. Verdict

Exact verdict:
- `ambiguous`

Stop rule:
- `B_k semantics remain ambiguous on this snapshot; do not build formula v2 yet.`

## 9. Honest Read

What the audit does support:
- `B_k` is not behaving like a clean bipolar signed carry term
- `raw_carry = -B_k` is strongly associated with loss of coverage
- `raw_carry` also rises with reversal and persistence stress

What the audit does not support cleanly:
- a pure live-carry reading
- a pure exhaustion reading
- a clean unsigned-persistence reading

The strongest fact is:
- `raw_carry` is largest in rupture-like rows
- but it is not cleanly ordered across the covered regimes in a way that resolves its semantics by itself

## 10. Recommendation

Concise recommendation:
- `stop because B_k is still not honestly resolved`

Do not:
- build formula v2 yet
- reuse the rejected `B_pos / B_neg` split
- promote `raw_carry` into a signed action term

Next approved direction:
- only proceed when the next element is audited cleanly enough to resolve whether `B_k` must stay relational and aligned to the rest of the field rather than entering on its own
