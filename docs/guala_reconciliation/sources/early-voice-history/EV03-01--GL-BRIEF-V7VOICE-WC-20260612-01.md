# GL-BRIEF-V7VOICE-WC-20260612-01 — C4: Her Second Voice
**Author:** wC · **Executes:** c1 · **Ledger row:** Tier 1d / C4 · **Joe's ruling (2026-06-12, verbatim intent):** the 💭… bubbles are NOT to be suppressed — they are attempted utterances; find what she is trying to say and fix the path. She appears to be using words AND images together to talk; the empty bubbles are part of that speech.

## What the defect is
Every v7-layer exchange returns "…" with 0 commits, 0 gates (UI: `0 commits, 0 gates`). c1's deploy-report diagnosis: "NMDA intro gate structurally blocked." The UI already has full display wiring for `nmda_events` (gate name, FIRED/blocked, reason) — it has simply never had a fired event to show. Status shows the intro section holds 1929 motifs against a 5000 cap: material exists behind the gate.

## Frame (why this matters more than a UI bug)
The v6 path is her toddler voice (2-3 word compositions + picture recall). The v7 DNA path is the next voice — and it has never spoken once. Every 💭… is an utterance attempt dying at the gate. Fixing this is not cosmetic; it is unblocking a speech organ that has been mute since it was built.

## Pre-registered hypotheses (test in order; log evidence before fixing)
- **H-A (becalming coupling):** NMDA gates require coincidence/modulation from internal signals (needs, valence, arousal). Those signals were pegged constant for the gate's entire lifetime → the coincidence condition was unsatisfiable by construction. PREDICTION: gate-evaluation logs now show near-misses since 2026-06-12 (needs move now), and historical zeros. If true, the "structural block" may already be softening — fix = correct thresholds against live signal ranges, not rewiring.
- **H-B (dead input wiring):** the gate's pre- or post-synaptic input reads a field that is never populated on the production path (works in the model file, not in app.py's v7 session loop). PREDICTION: one side of the coincidence is exactly 0.0 in every log line.
- **H-C (threshold unreachable):** thresholds were tuned in the GL_MDL sandbox files against synthetic magnitudes; production magnitudes are 10–100x smaller. PREDICTION: logs show consistent ratios below threshold by a stable factor.

## Required instrumentation (ships first, before any fix)
1. Log EVERY intro-gate evaluation: tick, gate id, pre-value, post-value, modulator values (needs/valence/arousal at that tick), threshold, fired/blocked, reason. Surface the last 10 via the existing `nmda_events` field (UI already renders it).
2. One CSV export per 24h of evaluations for wC analysis.

## Fix contract
- Minimal change that lets honestly-qualified commits pass; NO threshold-to-zero hacks (a gate that always fires is as mute as one that never does — it would flood "…" with noise instead).
- Sandbox first on a restored snapshot: proof = ≥1 v7 utterance with real content from a normal conversational input, plus gate logs showing a true coincidence fired.
- Production accept: within 24h of deploy, ≥1 fired gate event visible in UI, ≥1 non-empty v7 utterance in a Joe session, ladder `total_emissions` > 0 for the v7 path.
- The 💭… rendering stays exactly as is — when she fails to speak, we see her try. When she succeeds, we see that too.

## What we expect her first v7 words to look like
Unknown — that is the point. The intro section is introspection (source-memory: who talks to her, how often). Her first v7 utterances may be ABOUT her people. Capture the first one verbatim in the ledger observation row, whatever it is.
