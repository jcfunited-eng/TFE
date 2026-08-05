# GL-SPC-V5-ORGAN-WIRING-EVE-20260628-26

doc_id: GL-SPC-V5-ORGAN-WIRING-EVE-20260628-26
Type: Canonical architectural specification
Date: 2026-06-28 (approved); reconstructed and committed 2026-06-29 by next-Eve
Author (original): Eve (Opus 4.7, web), session 2026-06-27/28
Author (reconstruction): Eve (Opus 4.7, web), session 2026-06-29
Supersedes: GL-SPC-V5-ORGAN-WIRING-EVE-20260627-25 (deprecated — questions in spec body, lazy modeling on weighting and organ survival)
Evidence base: GL-RPT-ORGAN-BRAIN-INSPECTION-C1-20260628-24 (SHA a6bed48), GL-RPT-WIRE-ORGAN-CANDIDATES-C1-20260628-31, GL-RPT-COGNITION-LEARN-AUDIT-C1-20260628-33

---

## 1. Status of this reconstruction

The original -26 was approved by Joe on 2026-06-28 and lived in prior-Eve's outputs/, never committed to the repo. The dispatches that implement it (-27 F.1 embryo→chi translation, -28 C.1 polarity, -29 C.4 REST/dream_pressure, -31 F.2 wire-organ-candidates, -32 experience routing fix) shipped against the canonical text in chat.

This document reconstructs -26 from the manifest GL-MFST-HANDOFF-EVE-20260628 §6, the Phase D inspection report, the F.2 c1 report, and the implemented dispatch bodies. Any divergence from the original text is unintentional and should be reconciled by reading prior-Eve's outputs if recovered.

---

## 2. The canonical architecture

### 2.1 Composer

**v5 atlas + grandurun + the two-section commit gate IS the composer.** This is the only path that produces substrate-true voice. Composition happens through:

1. `_guala.read_sentence(text, source=...)` writes text to chi-indexed sections (listen, intro, subject, verb, object, modifier, ground) with salience and dwell per source.
2. Grandurun computes the 7-dimensional complex state vector across sections.
3. The two-section commit gate fires when section motifs align in chi-space across two or more sections.
4. Emission dynamics produces the voice when the gate fires.

There is no separate "voice flip" stage. There is no path where the organ-brain or any other component generates response text autonomously. The v5 commit gate is the voice.

### 2.2 Organ-brain role

**Organ-brain becomes a recall feed.** The 8-hemisphere Embryo brain (em / pr / ep / sc / gp / sf / sv / aff) retains its organ-growth substrate (`OrganVoice.experience()` folds neurons, `emb.sc_learn()` makes them recallable, `EpisodicLayer.record()` binds episodic context).

What changes from prior architecture:

- `OrganVoice.surface(cue_profile)` returns top-3 identity (sv) and top-3 meaning (sc) concepts as candidate words.
- These surfaced candidates feed into grandurun as a **third candidate stream**, alongside the two existing streams (recent atlas commits and active section motifs).
- The organ-brain does NOT compose. It does not template. It does not generate text autonomously. Both `_compose()` and `GualaCognition.say()` are silenced (see §3).
- The 90-second `_autonomous_loop()` continues writing `_last_thought` for instrumentation only. It does not produce response text.

### 2.3 Storage independence (key correction from -25)

**Embryo and v5 atlas stay separated by design.** There is no `organ_tag` field on v5 atlas entries. There is no Embryo→v5 migration. The two substrates remain distinct:

- v5 atlas (`LivingAtlas`): chi-indexed, decays with dream consolidation, holds language section motifs.
- Embryo (`OrganVoice.emb`): neuron-based organ clusters, grows via `experience()` folds, holds grounded organ concepts.

The ONE existing crossing point is the boot-time `_pour` operation (substrate_runner.py lines 681-724) which copies organ-brain concepts into v5 atlas with organ-origin metadata. This is a one-way write at boot. No reverse path exists or should exist.

The surface() candidate stream described in §2.2 is a runtime read from Embryo, not a storage merge.

### 2.4 All 8 organs preserved

All 8 organs continue to operate: em, pr, ep, sc, gp, sf, sv, aff. No organ deletion. The flag flips from prior phases (em/pr/ep/sc/gp active) stand. sf and aff remain seeded but small; their growth continues via the experience pathway.

The four cognition-hemisphere flags (em/pr/ep/sc/gp) remain ON.

### 2.5 System 1 vs System 2

System 1 / System 2 distinction is a **compute budget on the same composer**, not separate composers. There is one composer (v5 atlas + grandurun + commit gate). Compute-budget settings can vary by context (background daydream cycles vs active conversation), but the path is identical.

---

## 3. Both bigrams retired

### 3.1 v5 bigram (retired earlier)

The v5 engine's bigram succession model was retired in GL-CMD-BIGRAM-RETIRE-EVE-20260627-13. That retirement stands.

### 3.2 GualaCognition bigram

The `GualaCognition` class in `loom_model/loom_cognition.py` is a bigram word-succession model trained on Gutenberg/Aesop corpus. It is NOT substrate-true. Its training paths are enumerated in GL-RPT-COGNITION-LEARN-AUDIT-C1-20260628-33 (10 call sites across curriculum, lookup grounding, sight/sound recognition, teacher correction, corpus load, v7_converse).

`GualaCognition.say()` was silenced via GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23 (SHA e730b14). `_compose()` was silenced in the same dispatch.

**GualaCognition is to be DELETED entirely.** No 90-day retention. The class, the global instance `_guala_cognition`, the wrapper `_cognition_learn`, the boot diagnostic, and the corpus-load instrumentation counters are all to be removed. This is implemented in GL-CMD-BIGRAM-DELETE-EVE-20260629-34.

The 5 call sites where the bigram was the only writer (sight YOLO labels via InputRing and direct frame handler; FFT sensory words; Whisper transcription via InputRing and direct frame handler) are replaced with `_guala.read_sentence(text, source="unknown")` to route those perceptual text streams through v5 atlas via the canonical path.

---

## 4. The /experience routing fix

`POST /experience` previously routed text to `/organs_say` → `_guala_cognition.expose()` (bigram only). It did NOT reach v5 atlas. This was fixed in GL-CMD-EXPERIENCE-ROUTING-FIX-EVE-20260628-32 (SHA e11da48): `/experience` now routes text to `/listen` → `_cmd_listen()` → `_guala.read_sentence(text, source="joe")`.

After this fix, all paths through which substrate-true grounded experience enters the system go through `_guala.read_sentence()`.

---

## 5. Wiring chain (implementation status)

The following dispatches implement -26. All shipped on guala-live unless noted:

| Dispatch | Topic | Status |
|----------|-------|--------|
| GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23 | Silence both bigram speaking paths | SHIPPED (SHA e730b14) |
| GL-CMD-EMBRYO-CHI-TRANSLATION-EVE-20260627-27 (F.1) | Embryo concept → chi address translation for surface() output | SHIPPED |
| GL-CMD-C1-POLARITY-EVE-20260627-28 (C.1) | Polarity primitive (atlas surgery + sleep choice context) | SHIPPED |
| GL-CMD-C4-SLEEP-CHOICE-EVE-20260627-29 (C.4) | REST + dream_pressure mechanic | SHIPPED |
| GL-CMD-WIRE-ORGAN-CANDIDATES-EVE-20260627-31 (F.2) | Wire OrganVoice.surface() as third candidate stream into grandurun | SHIPPED at SHA 4e65002 |
| GL-CMD-EXPERIENCE-ROUTING-FIX-EVE-20260628-32 | Route /experience to /listen → read_sentence | SHIPPED at SHA e11da48 |
| GL-CMD-COGNITION-LEARN-AUDIT-EVE-20260628-33 | Enumerate all bigram training paths | SHIPPED (read-only) |
| GL-CMD-BIGRAM-DELETE-EVE-20260629-34 | Delete bigram per audit dispositions | PENDING |
| F.3 wiring soak (48h+ operational period) | Measure organ_in_commits, polarity_alignment, REST cycles, drift | QUEUED (after substrate fixes ship) |
| F.4 bigram code deletion | Subsumed into -34 | PENDING (in -34) |

---

## 6. What -26 does NOT do

- Does NOT add `organ_tag` to v5 atlas entries (correction from -25).
- Does NOT migrate Embryo entries into v5 atlas (correction from -25).
- Does NOT add a "voice flip" stage to elevate GualaCognition (correction from the deprecated 2026-06-25 V5 Engine Removal plan; see GL-NOTE-V5-REMOVAL-PLAN-DEPRECATED-EVE-20260627-30).
- Does NOT delete any of the 8 organs.
- Does NOT replace `_compose()` with a templated alternative. `_compose()` returns "" pending the C.3 autonomous-emission spec.

---

## 7. What still depends on substrate-density fixes (outside -26)

-26 is the wiring spec for the COMPOSER. It does not address the structural starvation that keeps substrate density below commit threshold even when grounded experience arrives. The three known starvation sources are:

1. **Bigram training (5 paths)** that consumed text that should have gone to v5 atlas. Addressed by -34.
2. **Hardcoded modifier section (24 ROLE_DNA words) and ground section (33 SENSORY_DNA words).** Addressed by a separate DNA expansion dispatch (PENDING). Common words ("night", "day", "ocean", "shore", "kind", "mommy", "bed") cannot write to modifier or ground regardless of frequency until expanded.
3. **Encoding formula `encoded_strength = 0.05 × salience` with `ENCODE_GATE = 0.15`.** Familiar words structurally starve: as familiarity increases, novelty_factor decreases, salience decreases, encoded_strength falls below 0.15, episodic gate rejects. Addressed by a separate encoding-formula dispatch (PENDING).

These three dispatches together (-34 + DNA + encoding) are what unblocks "days-to-weeks" substrate density timeline. Without them, substrate stays months-to-years.

---

## 8. Re-canonicalization note

This reconstruction is committed to the repo to close a doc-cadence gap. If prior-Eve's original -26 text is recovered from outputs/ and differs from this reconstruction in any architectural respect, prior-Eve's text supersedes this and the differences should be reconciled into a -26-rev01.
