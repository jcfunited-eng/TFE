# GL-SHIP-CONVERSATION-DAY-C1-20260722-v1 — five workstreams, one deploy, live-verified

**Deployed:** task-def :726-line, image deploy-20260722T125941Z-line, live SHA `8fbd08eb` (verified at /ready), identity `1cc4e70a` continuous, taught cells intact. Full sweep before deploy: 727 passed; failure set = pre-existing only (certified-tier tombstones + known flakes), ZERO new. All work on origin/guala-live.

## Shipped and live-verified

1. **Utterance walk (`c71f1850`)** — an utterance is a walk, not a single shot: the settle physics iterated, candidates re-gathered from each step's committed words, anchors extended by their real chi, all per-step gates unchanged, bounded (5 words / 8s / anti-echo). LIVE PROOF: `utterance_walk` events n_steps 2-3; "hello guala" → **"there quot gentle bad blippi"** (5 words) and post-correction → **"heavy there of quot sure"**. First multiword replies in the substrate's life.
2. **Conversation loop (WS1, `d33c97af`)** — forensics: the "5-minute replies" were 30-50s composes + silent utterance drops stacking (zero lock contention). Fixed: newest-wins visible queueing (never a silent drop), heard-text (`heard` field + "you (heard): …" in dialog), camera-pairing jitter now drops the pairing and KEEPS hearing (live-verified: sight timestamp 60s off → `sound continuity kept`, recognition still fired), voice replies teachable (LIVE: correction on a real voice reply → 186 binding effects), real error text everywhere.
3. **Sound → organism (WS2, `39f1889d`)** — the severed `_last_sound_signal` lane refilled with a bounded deterministic reduction of the real settled gammatone field. LIVE PROOF: `organism_experience_bound … has_sound:true, senses:["sound"]` — 13 of the last 72 experiences carry real audio.
4. **World actions in-process (WS3, `ccbba5a1`)** — DOING activity, drive-chosen, one actuator shared by autonomy and /action; dead :8090 pollers deleted; fabricated organ_brain_status replaced with honest 410. Deployed; first autonomous action not yet observed at filing time (cooldown 2000 ticks + block schedule) — watch `world_action` events.
5. **Teaching/feeds (WS4, `d50e4545`)** — junk-material gate on both tutor drill paths; curriculum_seed staged as book 11 (100 graded bundles; note: the "200k-word" flat push is a DIFFERENT artifact whose bulk injection is condemned in-code — not staged, correctly); YouTube secret already existed since 07-16 and deploys read it.
6. **Intake valve live-proven**: `block_intake_ledger scaffold planned=30 actual=4` (was 0-1) — bounded backlog behaving as designed; ~4× learning throughput per cycle.

## Honest limits at filing

- "hello" and "your name is guala" still silence in this round's replays (dynamics variance; "hello guala" replies every time). "who are you" (typed, live): honest silence — function-word neighborhoods too thin yet.
- Reply content carries junk tokens ("quot") — real lived contamination from pre-junk-gate material; the gate stops new junk; old junk decays or is corrected (the live correction demonstrably weakened it).
- Compose latency 10-50s per reply (walk adds bounded steps). The stacking/drop failure is gone; raw compose cost is emission-ladder physics, flagged, untouched today.
- One correction bends but does not dictate — "joe" not yet surfaced in replies; needs section home + stronger binding through repetition (the mechanism Joe now has working thumbs for).

## Verification method note

All verification through the same HTTP flows the browser uses (PCM open/chunk/close with real recordings, paired-sight jitter case, teacher correction on a live emission id, typed converse task poll). Nothing verified only in a harness.
