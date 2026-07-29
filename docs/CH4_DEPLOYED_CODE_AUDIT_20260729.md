# CH4 Deployed Code Audit — 2026-07-29

**Scope:** every file in the CH4 paper channel as deployed, verified by
reading current working-tree state and live runtime checks (process list,
book state, git history). Not from memory.

---

## 1. System inventory (deployed trading path)

| # | File | Role | Status |
|---|------|------|--------|
| 1 | `tools/isolated_market_vtvr_side_kernel.py` | The joint-field kernel: exact rational L0–L4, full retention (share, volume, all pair relations per time), SHA-256 layer receipts | **Frozen** — byte-identical to first commit `b847124d` (git-verified); 6/6 retention contracts green |
| 2 | `tests/test_isolated_market_vtvr_side_kernel.py` | Walk-up contracts; test 1 asserts full structural retention through L4 (anti-flattening tripwire) | Passing |
| 3 | `tools/vtvr_structure_search.py` | Supplies `build_field` (data fetch → kernel invocation, explicit universe + `min_days`) and the descriptor layer (`per_step_arrays`, `window_desc`) | Active; descriptor layer is the flattening point (§3) |
| 4 | `tools/vtvr_ch4_paper_sim.py` — `live()` | The paper book: entry/exit/cash mechanics, persistent state | Active; audit defects 1–6 fixed in `b1f751c9` |
| 5 | `tools/vtvr_daily_observer.py` | Logs daily state memberships to the observation ledger | Active |
| 6 | `tools/vtvr_ch4_daily_runner.sh` | Detached loop: weekdays 21:10 UTC → observer + book update | Running (started 2026-07-29 15:08 UTC); dies with container; restart line in header |
| 7 | `tools/vtvr_ch4_page.py` | Renders book → TFE-style side page HTML | Manual publish by session |

**State files** (gitignored, local): `artifacts/vtvr_observer/ch4_book.json`
(the book), `observations.jsonl`, `daily_runner.log`, plus backtest JSONs.

**Research files, NOT in the trading path:** analog engines v1/v2,
full-scale/null-book/replication/walkforward/forward-study harnesses,
universe builder + frozen 300-name list, capture tool.

## 2. Data flow (one daily cycle)

```
21:10 UTC weekday (runner)
  → source .env (Alpaca DATA keys — read-only market data, no trading API)
  → observer: cohort-A joint field → 3 state memberships → ledger append
  → paper book live():
      build cohort-A field (min 1200 bars/symbol; HALTS if composition
        changes — no silent reshaping)
      same-bar guard (bar processed at most once; holidays are no-ops)
      fill previous pending signals at this bar's close
      age positions by MARKET-bar arithmetic (entry-date index)
      exits: 90-bar horizon or −15% failsafe
      new pending = today's state members (20-bar cooldown per ticker)
      write ch4_book.json
  → page regenerated/published manually in session
```

## 3. Full-field vs flattened classification

- **Kernel (files 1–2): full-field.** ~14,160 exact values retained per
  stock-day through L4, receipted, deterministic.
- **Entry decision (files 3–4): FLATTENED.** The decision input is 3
  rank-band bits derived by: fractions→floats → per-step edge collapse
  (partner identity discarded) → windowed sums/means (Δt unused; time =
  bar count) → cross-sectional rank thirds → band conjunction.
  14,160 → 3. Selection of the 3-band rule was search-contaminated
  (~26k candidates, 25 holdout-peeked).
- Every entry and closed trade is stamped `bands_v1_flattened` so the
  record can never claim otherwise.

## 4. Findings and disposition

| Defect | Severity | Disposition |
|---|---|---|
| 1. Position age counted runner invocations, not market bars | High | **Fixed** `b1f751c9` |
| 2. No same-bar guard (every holiday aged positions on stale prices) | High | **Fixed** `b1f751c9` |
| 3. Dead `restore_run` machinery under a misnamed variable in live path | Med | **Fixed** (removed) |
| 4. Docstring misdescribed sizing, exits, and universe (4 ways) | Med | **Fixed** (rewritten) |
| 5. `min_days` could silently reshape the ranked field | Med | **Fixed** (hard halt) |
| 6. No engine-version stamp on trades | Med | **Fixed** (stamped) |
| 7. Entry engine itself is the flattened 3-band rule | **Open** | Replacement = whole-object field engine; v2 (tempo-tolerant, dimension-budgeted) in walk-forward test; wired in only on evidence, version-stamped |
| Cooldown dict unbounded | Low | Accepted (cosmetic) |
| Stale-price fallback in equity mark | Low | Accepted (display only) |
| No file lock on book JSON | Low | Accepted (single scheduled writer) |
| Observer logs 2 states from contaminated search, unlabeled | Low | Accepted as raw data collection |

## 5. Evidence status of the traded rule

The bands_v1 rule has **no demonstrated money edge**: its selection was
contaminated, its cross-universe replication failed, and it lost to a
blind book at full scale. It trades PAPER only, on its home field, as a
live forward hypothesis. The forward record (this book + side page) is
the only evidence channel left that nothing in this audit can corrupt.

## 6. Isolation & boundaries (verified)

- No production imports; no database writes; no Alpaca trading
  endpoints — market-data API only.
- Zero contact with the production TFE portfolio page (standing rule:
  CH4 is a side page only).
- Zero contact with Guala / `dsf_ai_service` / the Sol agent's files.

## 7. Current runtime state (at audit time)

Book: $100,000 cash, 0 open, 0 closed, 0 pending; last processed bar
2026-07-28. Runner alive (PID logged 15:08 UTC). Today's bar processes
at 21:10 UTC. v2 engine walk-forward in progress; result to be filed raw.
