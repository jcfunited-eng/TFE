# DSF Clean Walk-Forward Replay With Symbol Memory V1

This run exists to replace the earlier smoke backtest with a cleaner replay.

It does not change the frozen primitive.
It does not touch `uf-dynamic-decision.ts`.

## Architecture

- Vendor-direct daily bars only.
- Raw daily bars rebuild DSF fields in strict time order.
- Adjusted daily bars drive:
  - next-open execution
  - daily equity valuation
  - 5-bar forward outcome labeling
- No helper transport fields.
- No filled-forward primitive fields.
- No governance overlays.

## Primitive Surface

Each replay bar rebuilds exactly:

- `S_UF`
- `R_UF`
- `D_k`
- `M_k`
- `R_rev_k`
- `U_star_k`
- `C_k`
- `P_k`
- `B_k`

from raw daily bars only.

## Replay Window

- Replay start anchor is the earliest recovered historical snapshot timestamp:
  - `2026-02-17T17:26:01.305330Z`
- A strict 252-trading-day warm-up is taken before that anchor.
- Replay then walks forward on the SPY trading calendar through the latest vendor bar available in the run.

## Honest Tradable Universe

The symbol source universe is the approved fixed snapshot CSV used by the frozen primitive family.

A symbol is kept only if:

- vendor-direct raw daily bars exist across the full warm-up plus replay window
- vendor-direct adjusted daily bars exist across the same window
- raw and adjusted dates both align to the SPY replay calendar
- the symbol has enough history for:
  - 252 warm-up bars
  - next-open execution
  - 5-bar forward outcome labeling where required

Symbols that fail any of those checks are excluded and recorded explicitly.

## Symbol Memory V1

Each kept symbol gets one frozen memory card from the first 252 bars only.

Stored fields:

- `warmup_bars`
- `carry_threshold`
- `n_protected`
- `n_contested`
- `n_rupture`
- `n_continue`
- `n_bend`
- `n_reversal`
- `n_reversal_success`
- `n_reversal_eval`
- `n_contested_up`
- `n_contested_eval`
- `n_carry_success`
- `n_carry_eval`
- `profile`

No other learned state is allowed.

## Decision Lanes

1. `primitive_only`
   - frozen primitive exactly as already approved

2. `primitive_plus_symbol_memory`
   - memory may only demote `Accumulate -> Hold`
   - memory may not promote `Hold -> Accumulate`
   - memory may not rewrite `Avoid`

## Benchmarks

1. `spy_buy_and_hold`
2. `equal_weight_same_tradable_universe`

The equal-weight universe benchmark is a passive equal-weight buy-and-hold basket over the exact replay-kept universe, entered at the first replay execution open.

## Execution

- Starting capital: `100000`
- Trade at next market open after signal
- Slippage is explicit and reported in the summary
- Equal-weight current `Accumulate` positions
- `Hold` keeps existing positions
- `Avoid` exits existing positions
- Cash is allowed

## Output Contract

The runner emits:

- summary json/md
- equity curve csv/json
- trade log csv/json
- symbol memory v1 artifact
- geometry contribution table
- ablation table

## Discipline

- Not canonical
- Not full governed L5
- No primitive tuning in this run
