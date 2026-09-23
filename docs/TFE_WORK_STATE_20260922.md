# TFE implementation state — 2026-09-22

The objective remains open: improve CH2 long-duration and CH6 short cash-harvest WR and lift using complete field evolution through unchanged L0–L4. Lift is strategy return minus SPY return over matching intervals, expressed in percentage points. The earlier audit's statement that this definition was missing was wrong. No new strategy superiority is claimed.

## Delivered and checked

- `tools/tfe_book_benchmark.py` reconstructs a book on every supplied SPY session, including quiet days, reconciles cash, values open long/short exposure, counts net profitable closures, and refuses missing marks or incomplete ledgers. CH6's local reset book, August 21 close through September 18 close: 62.1849% closed WR, −0.74755% book return, −0.52630% SPY price return, **−0.22125 pp lift**. Uncharged open-position costs and SPY distributions are explicitly excluded. This is a local simulation book, not verified fills.
- `tools/tfe_field_receipt.py` preserves raw supplied closes, every L0 output, and the entire L2/L3/L4 gate history at a cutoff. Future bars are removed before L0. All seven L4 fields must match the local production adapter exactly. It does not relabel S_k as S_UF or invent L5 decisions. Input completeness back to listing remains unverified.
- `tools/tfe_readonly_observation.py` exports a bounded database view through TFE ECS Exec using a read-only, repeatable-read transaction, timeouts, ordered transport chunks and a digest. An open terminal is required; earlier nonterminal attempts truncated output and were rejected.
- `tools/ch4_store_refresh.py` now uses the broker's completed-session calendar, repairs interior missing dates, refuses fetch failures and historical price-basis discrepancies, preserves large genuine price moves, upserts exact provider volume revisions, serializes refreshes, and publishes atomically. The nightly runner stops dependent work on failure. No full-universe refresh or runner restart was launched.

There are **25 targeted passing tests** across book accounting, cutoff isolation, complete field delivery, truncated export rejection, failed/empty provider responses, interior gaps, real price jumps, volume revisions, atomic file failures, daylight-saving/early-close calendars and nightly dependency gates. A small real-provider refresh probe for SPY/AGNC passed and wrote only an isolated artifact. Its September 18 volumes required provider corrections; the September 21 session was added. The shared live store was not rewritten.

## Production correction

TFE service `tfe-web-task:635` was observed running. Its database had 11,685 current readings published September 22 at 00:17 UTC. Production SPY/AGNC source histories each contain 1,368 bars, April 12, 2021 through September 21, 2026; these are not whole listing histories.

Alpaca still held HTBK (67 shares) and CWAN (100 shares), while ledger rows 616/617 were closed with no exit price, time or P&L. Alpaca independently confirmed both assets inactive and nontradable. A guarded transaction restored their status to filled and set exit_blocked with preserved reconciliation evidence. No order was placed. An independent subsequent database export confirmed **21 filled and 36 closed** rows; Alpaca held 21 positions. The correction prevents these holdings being counted as completed trades or hidden exposure.

The 36 resolved closures include 21 manual resets. Do not report their combined WR as an isolated strategy result. The separate paper-account equity comparison for September 15–21 is −2.39324 pp versus SPY; it is labelled account-level, with cashflow and strategy attribution unresolved, not a CH2 performance claim.

Production-export replay matched most fields exactly; SPY B_k and AGNC M_k/U_star_k differ locally in the last floating-point digits. No tolerance was used to declare equality. Runtime provenance still needs reconciliation; `python` was absent from the web container, so no production Python parity proof was obtained.

## Remaining boundary

The full-field condition governing CH6 exhaustion is not established by the inspected source. Its prose rule describes crest/push/reversal/channel behavior; running code substitutes reduced screens. Joseph has been asked for the authoritative joint-field condition. Do not invent another threshold, revive model-based readings, modify the kernel, or treat these measurement repairs as completed strategy improvement.

All evidence is under `artifacts/tfe_verification/`, including before/after ledger receipts, provider comparisons and raw field captures. Guala code and processes were not modified. A concurrent workspace commit `e84aaa0b9` incorporated the first new TFE tools/tests; this session did not create that commit or alter its Guala work.

Provider contracts checked: [Alpaca calendar](https://docs.alpaca.markets/us/v1.1/reference/getcalendar-1), [portfolio history](https://docs.alpaca.markets/us/v1.1/reference/getaccountportfoliohistory-1), and [Massive bar adjustments](https://www.massive.com/docs/rest/stocks/aggregates/custom-bars).
