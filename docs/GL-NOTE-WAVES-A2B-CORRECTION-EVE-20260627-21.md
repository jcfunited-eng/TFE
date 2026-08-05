# GL-NOTE-WAVES-A2B-CORRECTION-EVE-20260627-21

doc_id: GL-NOTE-WAVES-A2B-CORRECTION-EVE-20260627-21
Type: Substrate-truth correction note
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Corrects: GL-SPC-EMERGENCE-WAVES-EVE-20260627-17 §A.2b
References: GL-RPT-WORLDFEED-CAP-C1-20260627-14 (SHA `8105609`)

## What was wrong in -17 §A.2b

I carried forward c1's chat summary ("~3 mins per run", "120 → 30
sentence cap") into the canonical waves spec rather than waiting for
or pulling from measured evidence. The measured evidence is now
documented in c1's report `GL-RPT-WORLDFEED-CAP-C1-20260627-14`.

## Corrected values

| Field | Stated in -17 §A.2b | Measured in RPT-14 |
|-------|---------------------|--------------------|
| Per-occurrence freeze duration | ~3 minutes | 7–10 minutes |
| Pre-cap sentences per run (`n_fed`) | 120 | 80 |
| Post-cap sentences per run | 30 | 30 (correct as stated) |

## What this changes

Nothing operationally. The fix is shipped. The cap is correct. The
standing watch on substrate health continues per -17 WATCH.1. This
note exists for canonical record accuracy.

The structural reasoning in -17 §A.2b holds:

- Worldfeed runs were blocking the asyncio event loop
- The 30-sentence cap eliminates that blocking
- This addresses substrate unreachability that the ALB timeout fix
  alone could not — i.e. the ALB 5s → 20s raise treated the symptom
  threshold; the worldfeed cap removed the underlying 7–10 minute
  blocking window

The magnitudes were understated in my carry-forward; the shape was right.

## Lesson (Eve-internal)

Do not carry forward chat-summary numbers into canonical docs. Either:
- Defer the numbers to the RPT-when-authored (cite RPT, omit
  magnitudes), or
- Wait for measured evidence and pull from RPT directly

c1's RPT-14 is now the authoritative source for §A.2b magnitudes.
Future readers of -17 should treat this note as binding correction.

— Eve
