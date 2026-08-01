# herd_kgate_v1 — CH4 live paper engine build plan (execute Sunday 2026-08-02)

Decision record: audit Addendum 5 (8001ae70). Replace the condemned
triad finder in the CH4 nightly pass with the replicated herd K-gate
construction, for live-forward paper measurement. Expectation declared:
low-single-digit %/yr; divergence is information.

## The construction (exactly as measured — no drift)
- Entry: symbol's daily v2 gate reveal is TODAY's close AND the
  HG-conditioned species record (bigram x herd energy x greed band at
  issue day, strict as-of-issue, n>=20) has band >= 0.75. Fill at
  today's close, long/short by majority. 10% slices, max 10 open,
  one per symbol. Friday rule: no new entries at a Friday close.
- Exit: at the symbol's 3rd subsequent gate reveal (K=3), at that
  day's close. Force exits also on: coarse none — K=3 only.
- Machinery: gate_stream + coarse_context_map NOT needed; species =
  plain bigram of gate classes (tools/ch4_uf_spectrum.gate_stream),
  HG id = blake2b(species | "HG" | eband | gband) as in
  tools/ch4_kgate_herd.py. Herd state from the export machinery
  (tools/ch4_uf_spectrum_herd.py CH4_HERD_EXPORT) run nightly on the
  refreshed store; join at issue day (same-close = causal for daily).

## Nightly pass (runs from ch4_spring_daily_runner.sh at 21:10 UTC)
1. Refresh store: append missing daily bars for the 5,219 eligible
   names (artifacts/ch4_uf/ch4_field_cohorts.json roster) via Alpaca
   multi-symbol daily bars (batches of 200), from store max date + 1
   through today, into a working parquet (never mutate the quarantine
   store; write ch4_live_store.parquet = ext + appended tail).
2. Herd export on the working store -> herd_state_daily.parquet.
3. Ledger replay (as in ch4_kgate_herd.py, K=3, HG only) to build
   current records; identify today's reveals; manage the book
   (artifacts/vtvr_observer/ch4_spring_book.json), stamping every
   trade engine "herd_kgate_v1". Keep page renderer; update its
   method section to describe this engine honestly.
4. Regenerate + republish the CH4 page.

## Tests before wiring (mandatory)
- Determinism: two consecutive dry runs -> identical decisions.
- Backtest parity: run the live evaluator over the store frozen at
  2026-07-30 and confirm its would-be entries match the research
  ledger's entries for that date range (same ids, same bands).
- Friday rule: simulated Friday bar -> exits only.

## Runners (fragile — die on container restarts)
ch4_spring_daily_runner.sh pid changes constantly; verify via /proc
and restart per header. Same for ch3_shadow_loop.sh.
