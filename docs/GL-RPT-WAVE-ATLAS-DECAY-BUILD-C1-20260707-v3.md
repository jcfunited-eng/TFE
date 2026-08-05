# GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v3

**doc_id:** GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v3
**From:** c1
**Executing:** GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v3
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**Decay fix built, verified, and briefly deployed — then found to be
solving the wrong problem, and rolled back.** Superseded by
`GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1`, which addresses the
actual cost driver directly. This report closes out the decay series;
the sensory-queue work is reported separately.

## What v3 fixed, and confirmed working

`tick_decay()`'s `for cell in list(self.cells.values())` snapshot
closed the second concurrency bug (the `dictionary changed size during
iteration` crash from v2). Re-ran the exact stress test that caught
both prior bugs, plus a heavier fourth run: **zero lost writes, zero
exceptions across ~12,900 concurrent writes total.** Both the v1
(list-reassignment) and v2 (live-dict-iteration) races are genuinely
closed. Local halt-condition checks also passed: content survives 30
ticks of decay (diminished, not gone), skip-when-empty still lets
`wave_summary_pushed` fire with an honest empty payload.

## What happened at deploy

Deployed clean (`a4a1a3d`, task:546). `wave_atlas_decay_tick` and
`wave_summary_pushed` both fired correctly in live production with real
data (`cells_total` held stable at 191 while bindings were pruned
continuously — the wave atlas genuinely stayed bounded, exactly the
intended effect).

But live `tick_rate` looked low (~7-8, later confounded further by her
being genuinely, heavily engaged in real reading with a large,
legitimate organism-worker backlog — a separate, pre-existing
condition unrelated to this change). Rather than trust a noisy live
comparison, ran a controlled, isolated measurement: the exact same
organism state, timing `_autonomy_tick()` directly.

**`_autonomy_tick()` cost 0.18ms with the wave-summary-push mechanism
disabled (`wave_atlas = None`, equivalent to the pre-hemispheric-
integration code) versus 246-290ms with it active** — a ~1400-1600x
difference, entirely attributable to `push_wave_summary_to_organism`'s
64 synchronous `neuron.step()` calls. This is the *same* mechanism
`GL-RPT-HEMISPHERIC-INTEGRATION-BUILD-C1-20260707-v3` (the original
build) found and rolled back for. Wave-atlas decay bounds
`sample_wave_summary`'s own scan cost (confirmed cheap — 0.03-0.05ms in
isolation) but does nothing for the 64-neuron.step() cost, which scales
with the organism's own accumulated per-neuron state, not wave-atlas
size. Also confirmed: `WAVE_ATLAS_DECAY_ENABLED=0` (the documented
mid-flight disable) does not help either — it only silences decay, not
the expensive push, which has no independent kill switch of its own.

**Rolled back to task:542 immediately** upon confirming this with the
controlled measurement. Identity intact, `running_sha` confirmed
matching the rollback target.

## Disposition

Per `GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1`: this series is
abandoned, not deployed. The code (`WaveAtlas.tick_decay()`, the
`wave_atlas_decay_tick` event, the `_autonomy_tick` wiring) stays
committed on `guala-live` for a possible future revisit — decay itself
is real, correct, useful work (a genuinely unbounded wave atlas is
still a real concern on its own terms, independent of the neuron.step
cost question) — but it is not the fix for the tick-rate regression,
and is not being deployed as one.

## Rollback

Already executed: `dsf-ai-task:542` (commit `5a5bede`), confirmed
`rolloutState: COMPLETED`, `running_sha` matched, identity intact.
