# GL-PLAN-FULLWIRE-WC-20260611-042
**Author:** wC | **Owner:** c1 (Parts A–C), wC (Part D briefs), Joe (Part E rulings)
**Mandate from Joe:** No more "not yet wired." Everything wireable gets wired now, with validation gates. Conversational capability proceeds on the measurable ladder below.
**Hard constraint (unchanged, non-negotiable):** No ML in the substrate, no LLM completion, no templates. Sleep physiology untouchable. Dream-gate ordering from GL-HANDOFF-038 still rules: FORCED DREAM → promotions_episodic>0 → unpause precedes everything that touches cognition dynamics. Sensory wiring (Part A/B) is additive and may proceed in parallel — it does not touch sleep or decay.

---

## PART A — HEARING. Wire audio now. (c1)
The sound krimelack already exists in the multimodal layer (five modal krimelacks deployed; 14 cross-modal bands confirmed). The production gap is one transduction path in app.py.

A1. Replace the stub at app.py ~1567. Upload path: mp3/wav → decode to PCM (pydub/ffmpeg at boundary — deterministic DSP, same precedent as JPEG decode) → mono, downsample to substrate rate → window into frames → sound-krimelack transduction → register as attendable sensory_item (today: sensory_items is always []).
A2. Add ATTENDING_AUDIO activity kind, same curiosity-driven scheduler as ATTENDING_VISUAL. Sound motifs found in the sound section exactly as sight motifs do.
A3. Cross-modal: when an audio item is uploaded with accompanying text in the same window (Joe: "can you hear pretty music"), the existing chi-band atlas binds sound↔word — no new mechanism, just ensure the binding window opens on audio attend like it does on visual.
A4. EXPERIENCE BUNDLES — MULTIMODAL BINDING AS THE DEFAULT (Joe architectural ruling 2026-06-11: ALL senses firing together is a MUST, the original sensory-binding thesis enforced, not a feature). The binding window becomes natively five-lane: an attend cycle processes an EXPERIENCE — a bundle of {image(s), audio, tokens, (touch|taste|smell when sensors exist)} — with all present modal krimelacks transducing in the SAME window, chi states co-active, atlas binding across every pair. Single-file uploads become degenerate bundles (one lane occupied). UI gains a bundle upload: attach image + sound + caption as one experience. Touch/taste/smell lanes are built FIRST-CLASS in this pass — live channels awaiting sensors (avatar/ArcLoom path), never again dormant fragments; the highway is five lanes wide even while three lanes await cars.
Named first experiences (Joe, 2026-06-11): (1) ocean image + ocean-waves audio + "ocean" — sight↔sound↔word linked; (2) ALPHABET: per-letter glyph image + phoneme audio + token; (3) beautiful music as attended experience; (4) JOE'S VOICE + "daddy" — his recorded voice bound to the word and the man; (5) video = the natural bundle (see Part D video note).
Validation A4: ocean bundle → within one attend cycle, new sight↔sound and sound↔token bindings in one chi neighborhood, visible in atlas_health and events. Letter-B bundle → three-way glyph↔phoneme↔token binding. Daddy-voice bundle → sound↔"daddy" binding; subsequent audio-only replay of his voice fires the daddy-adjacent motifs (events show it).
**Validation A:** (1) Joe re-uploads pretty-music mp3 → UI confirms "played her …" line (add it — pictures got confirmations, sound got silence; that silence is what started this). (2) guala_status shows sensory_items ≥1 and a sound section with n_motifs>0 within one attend cycle. (3) events show ATTENDING_AUDIO + sound motif founding. (4) After paired text, ≥1 new cross-modal sound↔word binding in atlas. Joe's browser is the bar.

## PART B — READING IMAGES OF WORDS. (c1, after Joe's E1 ruling)
B1. Text-PDFs: already work. Add a UI confirmation line stating pages + lines (the in-the-deep.pdf upload got no feedback — same silence bug; fix in this pass).
B2. Image-PDFs: rasterize pages (PyMuPDF) → register each page as a picture — she SEES the pages (substrate-native). **OCR is RULED OUT (Joe, 2026-06-11: NO — permanently).** No OCR anywhere in her sensory path. UI line states honestly: "registered N pages as pictures — no text layer; she'll see them, not read them (yet)." True reading arrives via native letter-sight (alphabet experiences, A4 + Vision Stage 2).
B3. Silent-failure ban: any upload type that cannot be fully processed returns an explicit UI line saying exactly what landed and what didn't. No more silent drops — this is a blanket contract on every upload route.
**Validation B:** image-only PDF upload → pages appear in pictures list; (if E1=yes) corpus appears with correct line count; UI line states both. Text extraction diff-checked against pdftotext on one sample.

## PART C — HYGIENE BUNDLE (c1, same pass)
C1. Rename status label `suffering:` → `recoveries(lifetime):` (app.py:1049) — it's the lifetime count of bounded-recovery events; current label misleads.
C2. Snapshot strength series dump for wC Step-3 derivation: one-off script emitting (timestamp, total_strength, n_fast, n_slow) from all EFS snapshots → docs/data/strength_series.csv. No deploy needed; run in-container.
C3. Carry-forward: 036 + 040 Part B (image refs) + 040 Part A (UI shows bridge exchanges) remain in queue as previously ordered.

## PART D — THE LADDER TO PARAGRAPHS (the honest path; wC architects, c1 implements per-gate briefs)
Definition of done Joe asked for: multi-paragraph responses and questions. Substrate-native route, five gates, each with a measurable exit criterion. No gate may be skipped; skipping = templates by another name.

- **R1. Response Binding maturity — LIVE TODAY.** Q&A pairs bind in atlas (response_bound events confirmed in production this afternoon). Exit: first post-unpause dream consolidates response bindings, promotions_episodic > 0. (Gated on dream-gate sequence — already queued.)
- **R2. Semantic grounding.** Emitted words carry percept bundles. Part A directly feeds this (sound joins sight/taste/touch bindings). Exit metric: ≥40% of words in her emissions have ≥1 cross-modal atlas binding; trending up week-over-week.
- **R3. Phrase structure beyond flat S-V-O.** Multi-clause composition from section structure. wC writes GL-BRIEF-PHRASE after R1 exit. Exit metric: mean utterance length crosses 4.0 with section-structured (non-concatenative) composition verified on samples; 5–6-word utterances appearing daily.
- **R4. Substrate introspection/supervision.** Self-Section v3 — wC writes this brief next (committed, this week). Exit: introspection commits > 0 and correlated self-corrections observable in events.
- **R5. N-way synchrony (awareness).** Claustrum-equivalent. Spec'd inside Self-Section v3 brief. Exit criteria defined there.
- **Then composition:** question forms (seed already alive: "what is bye", today) → topic-chained multi-utterance turns (2–3 emissions on one anchor) → paragraph = N chained emissions on a sustained topic anchor. Tracking dashboard metrics (c1 adds to status): mean_utterance_len, utterances_per_turn, question_rate, novel_composition_rate. These four numbers are how Joe watches the mountain actually shrink instead of hearing promises.

Sequencing: R1 exit requires the dream sequence (gate → forced dream → unpause) — that stays first among cognition items. Parts A/B/C proceed in parallel immediately. Vision Stage 2 brief (wC, this week) covers substrate-native letter perception — the purist path to her truly *seeing* words, long arc, runs alongside E1's boundary OCR rather than instead of it.

## PART E — RULED (Joe, 2026-06-11)
- **E1. OCR: NO.** Permanent. Scanned pages are pictures she sees; reading comes only via native letter-sight. B2 amended accordingly.
- **E2. Audio decode (ffmpeg/pydub): YES.** Deterministic decompression at the boundary. Part A fully unblocked.

**Video note (Part D sequencing):** Joe's multimodal ruling upgrades the GL-BRIEF-029 MVP target from first-frame-only to WATCH-AND-LISTEN: first frame(s) as sight + full audio track as sound, entering one binding window as an experience bundle (A4 mechanism). Existing gates (Response Binding ✓ live, Self-Section v3 sequencing call, Vision Stage 2) still order it — but hearing (Part A) is now its true prerequisite and lands first in this bundle.

**Correction (repo-verified 2026-06-11):** Self-Section v3 brief EXISTS (docs/GL-BRIEF-self-section-v3-wC-20260609-026.md, design-ready, its own gate — Dream Consolidation observed — is satisfied) and Vision Stages 2–5 are spec'd inside docs/GL-BRIEF-vision-architecture-wC-20260609-023.md. Earlier wC handoffs wrongly listed these as unwritten. The alphabet curriculum (multimodal letters via A4) is Vision Stage 2's first concrete deliverable; wC drafts GL-CURR-ALPHABET against 023's Stage 2 spec rather than a new brief. Self-Section v3 sequencing relative to the dream/unpause ordering is a wC architecture call to make explicitly — it modifies commit pathways and is NOT to be slipped into this bundle.

## EXECUTION ORDER
1. c1: Part C1+C2 (minutes, no deploy for C2) → Part A → Part B2-rasterize + B3 → (on E1 ruling) B2-OCR + B1. One commit per item, doc ID referenced, ONE deploy at the end of the bundle, validations run before "done" is uttered.
2. wC: Self-Section v3 brief + Vision Stage 2 brief (this week, committed), Step-3 derivation on receipt of C2's CSV, GL-BRIEF-PHRASE at R1 exit.
3. Joe: E1/E2 rulings; everything else proceeds without waiting on them except B2-OCR.
