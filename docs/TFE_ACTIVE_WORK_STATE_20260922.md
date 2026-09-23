# TFE working state — 2026-09-22

The user has instructed: stop conversational reports until the requested result is achieved; minimize tokens and CPU. No performance target has been achieved. Do not announce completion or imply a background worker remains active.

Requested outcome remains full temporal field structural selection and collapse-aware exits for CH2 and CH6, approximately 63% WR and 15 percentage points above S&P/SPY. No new heuristic, averaged proxy or kernel substitution is authorized as a shortcut. Guala retains priority.

## Actual implementation completed

`tools/ch2_book_simulation.py` was fully replaced to correct historical book accounting: all supplied SPY sessions are processed; net realized P&L determines WR; declared round-trip costs are split between legs; open positions remain open and marked; dead-clock/calendar decisions fill at the next observed close; publication dates are distinguished from trading dates; invalid/missing held marks fail explicitly. The existing V3 projection and old declared price-based exit control were retained for measurement, not adopted as the requested new strategy.

`tests/test_ch2_book_accounting.py`: eight tests pass, including exits without new signals, consecutive dead-clock observations, pending next-close execution, open-position treatment, net-cost WR, empty-entry windows, holidays and stale source rejection.

The main strict CLI refuses the current historical source because it contains publications for stale/unavailable prices. It now requires an explicit new output path and `--no-null`. The earlier randomized-null CLI behavior is not preserved. The function still accepts an explicit random pool/generator; no random runs were performed this turn. This is an interface change to review, not live deployment.

## Executed historical control

The full September source has late publications for names whose local raw bars stop March 24. A bounded control used the original provider baseline end, March 24, 2026, chosen before seeing outcomes. The retained lane slice has 1,040,674 rows; 8,953 existing entry-qualified rows were cached to avoid repeated full scans.

Three names absent from the local store were researched: AACI, CRD.A and HPPPC. Provider raw histories were fetched only for these names. The provider's historical reference identifies HPPpC; the TFE uppercase identifier is HPPPC. That exact case mapping was documented in the retained reference response. AACI's raw history ends before its supplied signal, so the candidate cannot be verified at that publication date.

`artifacts/tfe_verification/run_ch2_cached_control.py` composes the corrected simulation with cached legacy entry-qualified tuples. Unavailable publication evidence is explicitly refused and retained in `price_refusals`; it is not silently dropped. This is a conditional historical control, not certified current production parity or complete historical-universe proof.

The 12 deterministic controls finished. Source-window 2021-09-01 through 2026-03-24, SPY +44.5728198318%:

| Control | Net WR | Portfolio return | Lift above SPY |
|---|---:|---:|---:|
| One per stock, zero costs | 43.7775% | -18.8630% | -63.4358 pp |
| Up to three, zero costs | 48.2424% | -3.3759% | -47.9487 pp |
| One per stock, 10 bp round trip | 43.3628% | -20.5018% | -65.0746 pp |
| Up to three, 10 bp round trip | 47.4619% | -13.2211% | -57.7940 pp |

First/second windows, complete equity curves, closed trades, open positions, hashes and refusals are retained in `artifacts/tfe_verification/ch2_cached_control_result.json`. This rerun establishes a control; it does not improve the strategy. The old control omits later CH2 carry governance and market-cap/epoch eligibility, so these are not current deployed CH2 results.

CH6's unchanged local ledger was independently reconciled again: 119 closed, 74 net wins, WR 62.18487395%; return -0.74755%, SPY -0.52630204%, lift -0.22124796 pp, 26 open. Result: `artifacts/tfe_verification/ch6_control_rechecked_20260922.json`. These are unchanged local-paper results, not a new improvement or broker-fill proof.

## Still unresolved

A justified full-field temporal selection/collapse law meeting the user's constraints has not been established. Existing reduced V3/state/bucket mechanisms must not be silently presented as that solution. The reflection diagnostic does not itself prove structural selection impossible or justify rewriting the kernel; that earlier overstatement was corrected in `docs/TFE_FIELD_ORIENTATION_FINDING_20260922.md`.

Frozen kernel files, trading behavior and Guala were not changed. Measurements used single-thread numerical execution at low process priority; only the three missing-symbol raw requests were concurrent. No strategy was deployed. No claim of 63%/15pp achievement is warranted.
