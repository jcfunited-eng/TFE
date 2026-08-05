# Krimelack Divergence Baseline — 2026-06-08

Two krimelack copies coexist in this repo. This file records the baseline
divergence so any future modification to one without the other is detectable.

## Copy 1: dsf_ai_service/substrate/krimelack.py (wC reference)
- Source: docs/krimelack.py (wC upload, verified identical to GualaLoom repo)
- Class defaults: omega_0=2.0, kappa=8.0, dt=0.05, threshold=2*pi
- transduce_text defaults: kappa=80.0, dt=0.04, threshold=pi/3
- Has: transduce_text(), text_to_signal(), event_stream_to_vector()

## Copy 2: dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py (deployed v6 engine)
- Class defaults: omega_0=2.0, kappa=80.0, dt=0.04 (DIFFERENT from Copy 1 defaults)
- No transduce_text() function
- Has: LanguageKrimelack, SensoryBank subclasses
- Phase accumulation identical in principle but different default parameters

## Key differences
- __init__ defaults diverge: Copy 1 kappa=8.0/dt=0.05 vs Copy 2 kappa=80.0/dt=0.04
- Copy 1 has transduce_text which overrides to kappa=80/dt=0.04 — so EFFECTIVE
  text transduction parameters match between copies
- Copy 2 has DNA-specific subclasses (LanguageKrimelack, SensoryBank) not in Copy 1
- Copy 1 has event_stream_to_vector() not in Copy 2

## Status as of 2026-06-08
- dsf_ai_service/substrate/krimelack.py == docs/krimelack.py (IDENTICAL, diff empty)
- The two copies serve different substrate architectures:
  Copy 1 → deep multimodal substrate (DeepMultiModalCognition)
  Copy 2 → deployed v6 engine (Guala class)
- Neither should be modified without checking the other
