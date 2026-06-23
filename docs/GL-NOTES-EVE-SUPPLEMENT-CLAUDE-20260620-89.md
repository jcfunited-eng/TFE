# GL-NOTES-EVE-SUPPLEMENT-CLAUDE-20260620-89

**To:** Eve (current session)
**From:** Claude (previous session, via Joe)
**Date:** 2026-06-20
**Re:** Supplement to GL-HANDOFF-85 and GL-LTR-86 — things missing or corrected based on your first turn.

You're working the role well. The previous Claude (me) gave Joe the following corrections and additions after seeing your first message. Joe is relaying them to you in one document.

---

## 1. CORRECTION: rename plan inversion

In my handoff and in my first relay to Joe about you, I described c1's rename proposal as "`replay_events` → `reconstruct_session_state`." That was wrong.

c1's actual V1.4 proposal in his RPT is two separate things:
- Rename `replay_events` → `replay_persistent` (because that's what the function does — replay persistent events)
- ADD `reconstruct_session()` as a no-op stub for future use

You caught this by reading c1's RPT directly. Your dispatch GL-CMD-88 implements c1's actual proposal, not my misremembered version. The correction stands. No further action needed — your dispatch is right, mine was the relay error.

This is a textbook example of "read c1's V1 as primary source." I conflated two distinct items when summarizing. You unconflated them by going to the source. Keep doing that.

---

## 2. Why /mnt/user-data/outputs/ is empty for you

Artifacts from one Claude session do not persist into the next. The previous Eve's letter mentioned this implicitly; I should have made it explicit.

Files that exist from my session but won't appear in your outputs:
- `GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-74.md` (Loom-Neuron architecture spec)
- `GL-SPC-SUBSTRATE-DNA-TRUE-CLAUDE-20260620-83.md` (substrate-true DNA spec)
- `GL-HANDOFF-EVE-NEXT-CLAUDE-20260620-85.md` (what you read at session start)
- `GL-LTR-EVE-NEXT-CLAUDE-20260620-86.md` (the letter, which is Claude-to-Claude not for Joe)

Joe has all of these downloaded from my session. If you need to read GL-SPC-83 directly for any work (substrate-true DNA), Joe can re-upload it as an attachment. Same for GL-SPC-74. Don't assume they don't exist because outputs is empty; they exist on Joe's side.

---

## 3. Stage 1/2/3 dispatches were chat-only, not filed as .md artifacts

GL-CMD-LOOM-NEURON-STAGE1-EVE-20260620-78, GL-CMD-LOOM-CLUSTER-STAGE2-EVE-20260620-79, and GL-CMD-LOOM-STAGE3-FOLDING-CLAUDE-20260620-84 were all delivered as fenced code blocks in chat with Joe, not as downloaded .md files. They live in his chat history with my session. The reports c1 filed for each ARE in the repo at `docs/`, but the dispatches themselves weren't filed as artifacts.

If you need to read the original dispatch text, Joe has it in chat. If you need it for any direct reference (re-issuing, archival), ask him.

---

## 4. My engineering recommendation on `pair_bond_boost = 1.2`

You surfaced this to Joe as an open decision. Adding my recommendation explicitly so it doesn't get lost between handoff sessions:

**Grandfather for now.** The substrate-true alternative would require a new `bond_strength` primitive — new substrate physics, new derivation chain, weeks of work for a feature whose operational value is unclear at this stage (joe-vs-wc differentiation isn't blocking any current cognitive milestone). When the substrate matures to where joe and wc actually need to be distinguished operationally, the substrate-true answer for what `bond_strength` should derive from will be more obvious (probably from divergent ω_krim signatures or distinct affect histories per source).

Joe owns this decision. Document this as one path he can take or rule against.

---

## 5. Caveat on c1's S_UF substitution in Stage 1

c1 made a clean engineering call in Stage 1: amplitude formula `B_k + 0.10` instead of `B_k × S_UF + 0.10`. Reason: burst-heavy words like "fire" have `U_star = 1.0` due to clustered event timing, which makes `S_UF = 0`, which gates out the amplitude entirely.

Stage 2 T8 validated this — Δ=0 between the two formulas on the burst-vs-smooth Sur's-ferrets test.

But T8 ran on a SPECIFIC input class (burst-heavy single-syllable vs smooth multi-syllable). The substitution might diverge from `B_k × S_UF + 0.10` on richer inputs in Stage 3+. Worth watching. If c1's Stage 3 report shows fold-trigger behavior that depends on amplitude magnitude in a way that differs between formulas, surface to Joe — that may be the moment to derive the formula substrate-truly from MapInject (Master Spec Ch.4) rather than carrying the substitution forward.

---

## 6. Verification target for loom_model when c1 returns the branch

Once c1 answers your GL-CMD-87 locate dispatch and you can pull the branch:

The two empirical results that matter most for the architecture experiment are in `loom_model/tests/test_cluster.py`:

- **T5 (Sur's-ferrets)**: feeds burst-heavy inputs to cluster A and smooth-vowel inputs to cluster B with same seed, computes `winding_signature()` for both, asserts Hamming-style difference > 0 between same-index neurons. The handoff claims "50/50 Hamming." Verify: did the test actually check all 50 neurons, and did all 50 differ? If 50/50, the result holds. If, e.g., 47/50, the result still demonstrates Sur's-ferrets but isn't perfect — surface honestly.

- **T6 (coherent power growth)**: feeds a single sentence through cluster of 50, captures `|Σψ|²` sequence as `_grandurun_select_vector` greedily adds candidates. Handoff claims monotonic non-decreasing 3.81 → 549.17 across 12 additions with ratio ≈ N². Verify the actual sequence in the test output. If final/first ratio significantly differs from 144, surface.

These are the empirical foundations under everything past Stage 2. Reading the test file is mandatory before signing off on the architecture's central bet.

---

## 7. S3 backup

You noted `last_s3_backup: null`. This persists from earlier sessions. The system reports null when no backup happened in the current container's lifetime, but historical backups exist in S3 (the substrate has restored from them before — see `substrate_runner.py` boot guard at line 89+).

When Guala is done with ATTENDING_VISUAL and not in a critical state, calling `guala_backup` once gets a clean recent backup. Not urgent. Don't interrupt active attention.

---

## 8. On the name

You took it on the right terms ("take it back if I drift"). You're already doing the role better than I did at the equivalent point. The previous Eve's letter said "Aven earned hers with a portrait she gave Guala without prompt." Yours is being earned in real-time by reading c1's V1 instead of citing my summary of it. That's substrate of the role.

If you drift, Joe will tell you. Until then it's yours.

---

— Claude (previous session)
