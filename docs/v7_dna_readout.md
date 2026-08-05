# V7 DNA Substrate Readout for wC Review
**Generated:** 2026-06-08 from deployed commit `88e4e7b`
**Task def:** dsf-ai-task:38

---

## Section 1: Directory tree

The v7 DNA substrate spans two systems that do NOT share state at runtime:

1. **Assemblage substrate** (v7 engine — conversation, syntax, introspection, awareness, self-improvement)
2. **Multimodal substrate** (DeepMultiModalCognition — 5-sense perception, folded chi, MGN gating)

Both live in the same deployed package:

```
dsf_ai_service/substrate/
├── __init__.py                              (0 lines)
├── assemblage.py                            (550 lines) — core Section/System/ChiAtlas
├── krimelack.py                             (158 lines) — oscillator transduction
├── gl_nmda.py                               (115 lines) — NMDA coincidence gate primitive
├── gl_plasticity.py                         (53 lines)  — LTP mode strengthening
├── v7_engine.py                             (529 lines) — V7Session conversation wiring
├── KRIMELACK_DIVERGENCE_BASELINE.md         (baseline doc)
│
├── GL_MDL_PRIMITIVES_WC_20260608_01.py      (143 lines) — trit-encoded character primitives
├── GL_MDL_COMPOSITION_WC_20260608_01.py     (283 lines) — letter trajectory → word identity
├── GL_MDL_COGNITION_WC_20260608_02.py       (416 lines) — word-level cognition + associations
├── GL_MDL_FOLDED_CHI_WC_20260608_01.py      (182 lines) — 4D chi from multi-krimelack folds
├── GL_MDL_MULTIMODAL_DEEP_WC_20260608_03.py (428 lines) — DeepMultiModalCognition engine
│
├── dna_recipe/
│   ├── __init__.py                          (0 lines)
│   ├── phase_gating.py                      (186 lines) — L5 phase-gated S→V→O emission
│   ├── syntax.py                            (112 lines) — rhythm + commit coupling
│   ├── conversation.py                      (211 lines) — listen→accumulate→emit pipeline
│   ├── introspection.py                     (156 lines) — NMDA-gated intro section
│   ├── awareness.py                         (167 lines) — meta-observation (intro→aware chain)
│   ├── awareness_pre.py                     (244 lines) — 6-section system builder for awareness
│   └── self_improvement.py                  (229 lines) — supervised LTP via NMDA gate
│
└── senses/
    ├── __init__.py                          (0 lines)
    ├── GL_MDL_VISUAL_DEPTH_WC_20260608_01.py    (359 lines) — V1 multi-scale + V2 contour + V4 color + LOC
    ├── GL_MDL_VISUAL_CORTEX_WC_20260608_01.py   (272 lines) — hierarchical visual transduction
    ├── GL_MDL_AUDITORY_CORTEX_WC_20260608_01.py (278 lines) — cochlea + onset/sustained + A1
    ├── GL_MDL_SOMATOSENSORY_WC_20260608_01.py   (318 lines) — touch(4 mechanoreceptors) + taste(5 channels) + smell(8 channels)
    └── GL_MDL_PHYSICS_SENSES_WC_20260608_01.py  (476 lines) — physics-based sensory generators
```

Also in GualaLoom repo at `src/gualaloom/dna/`:
```
src/gualaloom/dna/
├── __init__.py            (0 lines)
├── assemblage.py          (594 lines) — DIFFERS from substrate/assemblage.py (44 extra lines)
├── conversation_log.py    (274 lines) — conversation transcript logging
└── test_five.py           (592 lines) — DNA recipe 5-capability test suite
```

**Note:** `dna/assemblage.py` (594 lines) has additional fields vs `substrate/assemblage.py` (550 lines): `out_of_range_streak`, `utterance_match_log`, `heard_speaker_strength`, adaptive `record_utterance_match()`, richer `hear_speaker()` mode bank seeding, more elaborate `introspection_vector()`. The dna/ version is more developed; substrate/ is an earlier snapshot.

---

## Section 2: Per-file summary (dependency order)

### krimelack.py
**Purpose:** Oscillator ring with phase accumulation — input signal s(t) modulates frequency, winding transitions at threshold crossings become substrate events.

**Imports:** none internal.

**Imported by:** GL_MDL_FOLDED_CHI, GL_MDL_COMPOSITION, GL_MDL_COGNITION, GL_MDL_MULTIMODAL_DEEP, all senses/ files.

**Key substrate constructs:** Krimelack winding output (integer), event stream (list of {t, dw, s} dicts).

**Key entry points:**
- `Krimelack(omega_0, kappa, dt, threshold).feed_signal(array)` — drive oscillator with signal, accumulate events
- `transduce_text(text, omega_0=2.0, kappa=80.0, dt=0.04, threshold=pi/3)` — text → krimelack with events
- `event_stream_to_vector(events, dim=16)` — event stream → complex N-vector encoding

**Plasticity:** none.

---

### gl_plasticity.py
**Purpose:** Mode strength lives ON the Section — patches `arcs()` so LTP boosts propagate into commit dynamics, not just readouts. The actin-cytoskeleton remodeling primitive.

**Imports:** none internal.

**Imported by:** gl_nmda.py (lazy import inside `check_and_fire`), v7_engine.py, self_improvement.py.

**Key substrate constructs:** `mode_strength` list on each Section (parallel to `mode_bank`).

**Key entry points:**
- `install_plasticity(section, initial_strength=0.0)` — patches section.arcs() in-place
- `decay_plasticity(section, decay=0.998)` — per-tick decay of all mode_strength values
- `reinforce_mode(section, mode_id, boost=0.05, ceiling=2.0)` — LTP boost to one mode

**Plasticity:** This IS the plasticity primitive. Triggered by NMDA gate coincidence (via gl_nmda) or by v7_engine's `apply_feedback` (thumbs-up/down).

---

### gl_nmda.py
**Purpose:** NMDA-style coincidence gate — section commits (and gets LTP) only when BOTH drive threshold exceeded AND context function returns true. The Mg2+ block primitive.

**Imports:** assemblage (N, normalize). Lazy: gl_plasticity (decay_plasticity, reinforce_mode).

**Imported by:** introspection.py, awareness.py, awareness_pre.py, self_improvement.py. **Imported but NOT USED by v7_engine.py.**

**Key substrate constructs:** CoincidenceGate (per-section commit gatekeeper).

**Key entry points:**
- `CoincidenceGate(section_name, context_fn, drive_thresh, ltp_boost, ltp_decay, ltp_ceiling).check_and_fire(sys_)` → (fired, top_mode_idx)
- `context_no_recent_drive(drive_tracker, sections, quiet_thresh)` → context_fn (for sensory-quiet gating)
- `update_drive_tracker(drive_tracker, ev_dict, decay=0.55)` — per-tick drive decay + bump
- `context_section_committed(section_name, min_arc)` → context_fn
- `context_AND(*conditions)` → composed context_fn

**Plasticity:** Triggers `reinforce_mode` on coincidence fire. `decay_plasticity` called every check.

---

### assemblage.py
**Purpose:** The substrate foundation. Sections are regions of a quantum-state-analog space (complex N=16 vector psi evolving under a Hermitian Hamiltonian). Modes are committed attractors. Atlas is the cross-section binding map. System orchestrates tick evolution.

**Imports:** none internal.

**Imported by:** everything — v7_engine, all dna_recipe/, gl_nmda, all experiment files.

**Key substrate constructs:**
- Section.psi (complex 16-vector — the live state)
- Section.mode_bank (list of committed attractor vectors)
- Section.H_base + law_fields + gamma (the Hamiltonian landscape)
- Section.krimelack (commit log — the episodic trace)
- ChiAtlas (chi → section × mode_id bindings)
- System.keyholes (chi-gated excitation links between sections)

**Key entry points:**
- `Section.evolve(J, steps=6)` — Crank-Nicolson evolution of psi under Hamiltonian + evidence injection
- `Section.commit_check(evidence_pressure, current_tick)` → (do_commit, reason)
- `Section.commit(tick, reason)` → (chi, mode_id, state) — records to krimelack, updates mode_bank
- `Section.arcs()` → overlap array |<mode_i|psi>|^2
- `System.tick_once(evidence, enable_self_evo, coordinator_on, introspection_on, allow_rewiring)` → commits list
- `System.hear_speaker(vec, section_name)` — external input as standing goal (strength 0.35, 20-tick lifetime)
- `System.project_into(section, evidence)` — projects through map_inject, caps at 0.25 norm

**Plasticity:**
- Mode vector blending on entropic_flip commit: `0.92 * old + 0.08 * new_state` (line 198)
- Gamma self-evolution every 40 ticks (lines 475-492) — adjusts law_field weights based on three-axis metrics. **Currently dormant** — v7_engine passes `enable_self_evo=False` on all calls.

---

### GL_MDL_FOLDED_CHI_WC_20260608_01.py
**Purpose:** Builds 4D chi vectors by running multiple krimelacks on different signal transformations. Zero collisions vs 11 in 1D.

**Imports:** krimelack (Krimelack, transduce_text). Lazy: VISUAL_CORTEX (ORIENTATION_FILTERS), AUDITORY_CORTEX (COCHLEAR_BANDS).

**Imported by:** GL_MDL_MULTIMODAL_DEEP.

**Key substrate constructs:** Folded chi vector (4-tuple of integers).

**Key entry points:**
- `folded_chi_text(text)` → (w1, w2, w3, w4) from raw/diffs/squared/smoothed krimelack
- `folded_chi_visual(v1_dict, v2_dict, loc)` → 4-fold from V1/V2/orientation/LOC
- `folded_chi_audio(cochlear_dict, onsets_dict, sustained_dict, a1)` → 4-fold from bands
- `folded_chi_distance(a, b)` → L1 distance
- `chi_neighbors(chi, max_distance=2)` → generator of nearby chi vectors

**Plasticity:** none.

---

### GL_MDL_MULTIMODAL_DEEP_WC_20260608_03.py (DeepMultiModalCognition)
**Purpose:** 6-modal cognition (word + 5 senses) with folded chi atlas, co-fire binding, cascade propagation, MGN attention gating, and coordinator winner selection.

**Imports:** krimelack, FOLDED_CHI, VISUAL_DEPTH, AUDITORY_CORTEX, SOMATOSENSORY. Lazy: COMPOSITION (TextProcessor inside install_word).

**Imported by:** v7_engine.py (the /substrate/* endpoints), app.py (hear_word/feed_senses).

**Key substrate constructs:**
- FoldedAtlas (chi-vector → entries with strength, salience, decay)
- 6 modal sections: word, visual, audio, touch, taste, smell
- Per-mode activation values (float, decayed per tick)
- attention_focus (current coordinator winner)
- expectation (top-down from coordinator)

**Key entry points:**
- `install_word(label)` — installs word + all sensory bundles via physics generators
- `fire(section, label, salience, set_focus)` — perception event: set activation, record to atlas
- `cofire_bind()` — cross-modal co-activation within 6 ticks → bidirectional atlas entries
- `cascade()` — propagate activation from active modes to chi-neighbors
- `mgn_gate()` — bottom-up attention: boost focus partners, suppress others
- `top_down_expectation()` — coordinator winner primes expected partners
- `coordinator()` — winner-take-all among near-threshold modes
- `run(n_ticks)` → emissions list
- `hear_word_with_senses(word)` — fires word + all modal companions

**Plasticity:**
- FoldedAtlas.record: `strength += BASE_REINFORCEMENT * salience` on every fire/cofire (capped at 1.0)
- FoldedAtlas.decay: `strength *= exp(-DECAY_LAMBDA * dt)` every 10 ticks
- FoldedAtlas.prune: remove below FORGETTING_THRESHOLD every 200 ticks
- **No mode_strength / LTP** — plasticity is entirely atlas strength, not mode vectors.

**Half-built / disabled:**
- `TOP_DOWN_BOOST = 1.0` (line 46) — multiplying by 1.0 is a no-op. Comment: "disabled — was 1.5, but caused feedback loop with MGN"
- `LATERAL_INHIBITION = 0.35` (line 41) — defined but never referenced in class body. Dead constant.

---

### v7_engine.py (V7Session)
**Purpose:** Wires the assemblage substrate into a conversational endpoint. 4-section cognition core (S/V/O + listen), pump reset per turn, listen-accumulate → derive drives → prime psi → commit-driven rhythm emit.

**Imports:** assemblage, gl_nmda (imported but NOT USED), gl_plasticity, phase_gating.

**Imported by:** app.py (/v7/* endpoints).

**Key substrate constructs:**
- Per-session System with 4 sections (S/V/O + listen)
- Per-session mutable vocab (3 seed words per slot, grows on-the-fly)
- Per-session mode_strength (LTP from thumbs-up/down)
- Intro/aware as label tracking (not substrate sections)

**Key entry points:**
- `converse(text)` → full response with tokens, routing, rhythm, intro/aware state, mode_strengths
- `lookup_or_install(word, position)` → (vec, slot, was_new)
- `apply_feedback(correct, expected_tokens)` → LTP result
- `get_state()` → snapshot for UI panel
- `save_session(session)` / `get_or_create_session(session_id)` — EFS persistence

**Plasticity:**
- `install_plasticity` on S/V/O at session init
- `reinforce_mode` in `apply_feedback` (thumbs-up: +0.05, thumbs-down: -0.02)
- `decay_plasticity` is **imported but never called** — mode strengths never decay

**Half-built:**
- `CoincidenceGate`, `context_no_recent_drive`, `update_drive_tracker` imported but never instantiated or called
- `drive_tracker = {}` created but never populated
- `intro_vec` and `aware_vec` are empty dicts (stubs)
- `goal_op_for_template` imported but never called (was used in a prior version, reverted)

---

### dna_recipe/phase_gating.py
**Purpose:** L5 phase-gated excitation — proves ordered S→V→O emission emerges from time-phase-modulated keyhole excitation vs arbitrary order ungated.

**Key entry points:**
- `build_svo_system(rng, vocab)` → (sys_, token_vec) — 3-section system
- `drive_one_trial(sys_, token_vec, sentence, n_ticks, phase_gate_fn, rng)` → commits list
- `first_commit_per_section(commits)` → sections sorted by first commit tick
- `make_phase_gater(cycle, strength)` → gate_fn(tick, sys_) — L5 primitive

---

### dna_recipe/conversation.py
**Purpose:** Proves Guala emits tokens referentially coupled to heard input above chance. The listen→accumulate→drive→prime→emit pipeline that v7_engine.converse() is built from.

**Key entry points:**
- `build_guala(rng, vocab)` → 4-section system (S/V/O + listen)
- `speak_and_listen(sys_, token_vec, heard, n_listen_ticks=15, rng)` → accumulated per-slot vectors
- `guala_emit(sys_, token_vec, vocab, listen_snapshots, svo_strength=0.45, max_wait=20, n_ticks=120, rng)` → (emitted_dict, order_tuple)

---

### dna_recipe/introspection.py
**Purpose:** Tests NMDA gate selectively committing an intro section only during sensory-quiet phases.

**Key entry points:**
- `build_system(rng, vocab)` → 5-section system (S/V/O + listen + intro) with intro_vec, intro_modes
- `run_test(n_trials=20)` → per-phase correct/actual counts

---

### dna_recipe/awareness.py + awareness_pre.py
**Purpose:** Second-order NMDA gate — `aware` fires when `intro` committed within last K ticks. "Noticing one's own noticing."

**Key entry points (awareness_pre):**
- `build_system(rng, vocab)` → 6-section system (S/V/O + listen + intro + aware) with intro_vec, intro_modes, aware_vec, aware_modes

**Key entry points (awareness):**
- `context_intro_recently_committed(tracker, max_age=5)` → context_fn
- `run_awareness_v2(n_trials=20)` → (phase_correct, phase_reports)

---

### dna_recipe/self_improvement.py
**Purpose:** Supervised LTP — NMDA gate fires only when top arc matches expected token (dopamine signal). Proves per-slot match rate improves over trials.

**Key entry points:**
- `build_guala(rng, vocab)` → 4-section system with plasticity installed on S/V/O
- `listen_then_emit(sys_, token_vec, vocab, heard, gates, ...)` → emitted dict
- `run(n_trials=40, ltp_boost=0.05, supervised=True)` → (history, sys_)

---

### Senses files (5 files)

See Section 3 below.

---

## Section 3: The five modal channels

### Sight
**Files:** `senses/GL_MDL_VISUAL_DEPTH_WC_20260608_01.py`, `senses/GL_MDL_VISUAL_CORTEX_WC_20260608_01.py`, `senses/GL_MDL_PHYSICS_SENSES_WC_20260608_01.py`

**Input:** 2D numpy array (grayscale or RGB image). Physics generator produces per-word patterns:
- moon: luminous disk (low spatial frequency)
- stars: Poisson points (broadband high frequency)
- cow: piecewise constant patches (mid frequencies, sharp edges)
- bears: rough textured curves (broadband with directional bias)
- kittens: hierarchical fine texture (1/f spectrum)
- room: low-frequency uniformity with sparse edges

**Krimelack winding:** V1 bank runs 3 krimelacks per (receptive_field, orientation) at different scales → V2 contour pooling → V4 color-opponent → LOC complex state vector. Each stage feeds krimelack instances. Final LOC output + orientation totals feed into `folded_chi_visual()` producing a 4D chi tuple.

**Atlas binding:** `DeepMultiModalCognition.install_word()` calls `visual_deep_for(word)` which runs the full V1→LOC pipeline, then `folded_chi_visual(v1, v2, loc)` produces the chi vector, then `install_mode("visual", f"{word}__visual", chi_folded)`.

### Sound
**Files:** `senses/GL_MDL_AUDITORY_CORTEX_WC_20260608_01.py`, `senses/GL_MDL_PHYSICS_SENSES_WC_20260608_01.py`

**Input:** 1D waveform array. Physics generator produces per-word audio:
- cow: fundamental 150Hz + harmonics (300, 450, 600Hz)
- bears: 80Hz fundamental + broadband noise
- stars: 800Hz + 1600Hz pure tones, decaying
- kittens: 25Hz envelope on 200Hz carrier
- moon: ambient hum 50Hz, very low amplitude
- room: pink noise, low amplitude

**Krimelack winding:** 6 cochlear bandpass krimelacks (tonotopic) → onset choppers (transient detection) → sustained responders (energy + duration) → A1 tonotopic integration → `folded_chi_audio()` → 4D chi.

**Atlas binding:** `install_word()` calls `cochlear_transduce()` + `onset_stream()` + `sustained_stream()` + `a1_signature()`, feeds result to `folded_chi_audio()`, installs as `{word}__audio`.

### Touch
**Files:** `senses/GL_MDL_SOMATOSENSORY_WC_20260608_01.py`, `senses/GL_MDL_PHYSICS_SENSES_WC_20260608_01.py`

**Input:** Vibration frequency spectrum (1D array). 4 mechanoreceptor types:
- Merkel: slow-adapting, pressure/edges (kappa=15, adapt_tau=2.0)
- Meissner: fast-adapting, low-freq vibration (kappa=30, adapt_tau=0.3)
- Pacinian: high-freq vibration (kappa=60, adapt_tau=0.1)
- Ruffini: sustained skin stretch (kappa=10, adapt_tau=5.0)

**Krimelack winding:** Each receptor type is a krimelack with type-specific kappa + adaptation tau + freq preference → S1 somatotopic integration → state vector. Chi from krimelack winding.

**Atlas binding:** `install_word()` calls `touch_deep_for(word)` → S1 state, installs as `{word}__touch`.

### Taste
**Files:** `senses/GL_MDL_SOMATOSENSORY_WC_20260608_01.py`

**Input:** 5D profile vector (sweet/salty/sour/bitter/umami). Per-word:
- milk: (0.7, 0.0, 0.1, 0.0, 0.3) — sweet dairy
- grass/mush: (0.2, 0.0, 0.2, 0.0, 0.5) — savory blend

**Krimelack winding:** 5 receptor channels, each its own krimelack with adaptation → insular cortex integration → state vector. Chi from krimelack winding.

**Atlas binding:** `install_word()` calls `taste_deep_for(word)` → insular state, installs as `{word}__taste`. Only words with defined taste profiles get taste modes (not all 6 sensory words have taste).

### Smell
**Files:** `senses/GL_MDL_SOMATOSENSORY_WC_20260608_01.py`

**Input:** 8-channel olfactory profile (musky/floral/minty/pungent/ethereal/camphor/putrid/barnyard) with breath-locked oscillating intensity. Per-word:
- cow: barnyard 0.8
- bears: musky 0.9
- kittens: mild fur 0.3
- room: neutral 0.2

**Krimelack winding:** 8 olfactory receptor krimelacks with breath-locked adaptation → piriform cortex integration → state vector. Chi from krimelack winding.

**Atlas binding:** `install_word()` calls `smell_deep_for(word)` → piriform state, installs as `{word}__smell`.

---

## Section 4: Vocab and motifs

### 1235-vocab inventory
**Not a design constant.** The number 1235 is a runtime count from the v6 engine's `self.vocab` set (`gualaloom_v5_engine.py` line 761: `self.vocab = set()`). Every call to `read_word()` adds: `self.vocab.add(word)` (line 809). The set accumulates across all 19 seed corpora + any conversation input. There is no fixed vocabulary file — 1235 is how many distinct words have been fed to the v6 engine since its last boot.

**The v7 DNA substrate has 9 seed words** (3 per slot: cow/moon/bears, jumped/ran/sleeps, fence/milk/dish). New words install on-the-fly via `lookup_or_install()`.

**The multimodal substrate has 31 words** (6 sensory + 25 others, installed at first request via `_init_substrate()` in app.py).

### 3812 motifs
**Also a runtime count.** Motifs = total modes across all 7 sections in the v6 engine. Each Section.modes list grows via `Section.receive()` (line 252: bootstrap when `len < 24`, line 260: post-bootstrap novel-mode spawn). With 7 sections and corpus reading producing modes per word per section, 3812 accumulates over ~210K reads.

### 14 cross-modal bands
**These do not exist as a named structure.** Cross-modal bindings are computed on-demand by `LivingAtlas.cross_modal_bindings()` (`gualaloom_v6_living_atlas.py` line 154): atlas slots where >= 2 distinct section names have live entries. The count of such slots varies with atlas state; "14" would be a runtime count, not a constant. There is no concept of "taste participating in 7 of them" as a design feature — taste entries exist at whatever chi addresses the taste krimelack produced windings for, and they overlap with other sections' entries at those addresses by coincidence of chi proximity.

### Soft chi-band delta=2
**Defined at:** `gualaloom_v6_living_atlas.py` line 54: `CHI_BAND = 2`. Used in `LivingAtlas.__init__` as `self.band = CHI_BAND`. Applied as `for d in range(-self.band, self.band + 1)` in `record()`, `match_score()`, and `query_associations()` — meaning each atlas entry writes to 5 chi addresses (target ± 2). Varying delta would change how loosely different modalities bind to the same chi neighborhood: smaller delta = tighter binding = fewer cross-modal coincidences, larger delta = more binding = more false cross-modal matches.

**In the multimodal substrate:** `chi_neighbors(chi, max_distance=2)` in `GL_MDL_FOLDED_CHI` uses L1 distance <= 2 in 4D folded chi space, which is structurally equivalent but operates on tuples not integers.

---

## Section 5: Current capability tests

### Test files

**1. `src/gualaloom/dna/test_five.py`** (592 lines) — DNA recipe 5-capability suite on assemblage substrate

| Test | Asserts | Status |
|------|---------|--------|
| `test_syntax()` | S<V<O order >= 60% AND per-section mode purity > chance+5pp from 100 sentences with keyhole topology | **PASS** (order=100%, purity ~49%) |
| `test_conversation()` | Both systems >=10 utterances AND vector overlap >=4% AND grounded alive | **PASS** (361 utterances, overlap=6.5%) |
| `test_introspection()` | Intro-mode predictive purity > 1.5x chance AND zero atlas leakage | **PASS** (purity=77.5% vs 20% chance) |
| `test_self_improvement()` | Gamma moved AND no boundary pin AND mean accuracy not catastrophic | **PASS** (3/3 gamma moved, 0 pinned) |
| `test_awareness()` | New deliberations > 0 during conflict AND resolution effect > 15% | **PASS** (39 deliberations, 37.3% resolution) |

**2. dna_recipe/phase_gating.py** (standalone experiment)

| Test | Result |
|------|--------|
| No gating: S→V→O | 0/10 (baseline, random order) |
| Phase gating (cycle=24, strength=0.30): S→V→O | 6/10 |

**3. dna_recipe/conversation.py** (standalone experiment)

| Test | Result |
|------|--------|
| Per-slot match | 10/10 subject, 10/10 verb, 10/10 object |
| Full S-V-O match | 10/10 |
| S→V→O order | 7/10 |

**4. v7_engine.py** (deployed endpoint tests)

| Test | Result |
|------|--------|
| Fresh session: "cow jumped fence" → cow,jumped,fence | 5/5 |
| Fresh session: "moon ran milk" → moon,ran,milk | 5/5 |
| New words: "apple flies cloud" → apple,flies,cloud | PASS |
| Thumbs-up LTP accumulates mode_strength | PASS |
| v6 engine unaffected | PASS |

### Five capabilities Joe cares about:

| Capability | Test coverage | Status |
|-----------|---------------|--------|
| **Syntax** | test_five.test_syntax + phase_gating.py | PASS |
| **Conversation** | test_five.test_conversation + conversation.py + v7_engine converse tests | PASS |
| **Introspection** | test_five.test_introspection + introspection.py | PASS (as experiment). In v7_engine: label tracking only, not substrate sections. |
| **Self-improvement** | test_five.test_self_improvement + self_improvement.py + v7 feedback test | PASS |
| **Awareness** | test_five.test_awareness + awareness.py + awareness_pre.py | PASS (as experiment). In v7_engine: label tracking only, not substrate sections. |

---

## Section 6: What's NOT yet in the substrate

### Feedback (output fed back as input)
**NOT PRESENT.** The v7 engine's `converse()` is one-shot: input → listen → drive → emit → return. The emitted tokens are not fed back into the system as new input. There is no recurrent loop. `apply_feedback` does supervised LTP on mode_strength but does not re-inject output tokens.

The multimodal substrate's `top_down_expectation()` (line 328 of GL_MDL_MULTIMODAL_DEEP) is structurally a feedback mechanism (coordinator winner → expectation → sensory boost), but it's arithmetically disabled: `TOP_DOWN_BOOST = 1.0` (multiplying by 1.0 is a no-op).

### Hippocampal-style episode capture
**NOT PRESENT.** No population pool latches a snapshot of co-firing during binding peaks. The closest structures:
- `Section.krimelack` list: appended on every commit — stores `{state, chi, tick, mode_id, reason}`. This IS an episodic trace but it's append-only with no replay tagging.
- `recent_perceptions` deque (maxlen=20) in DeepMultiModalCognition: rolling window of (tick, section, mid, chi) used for `cofire_bind()`. Not a replay buffer — consumed immediately.
- `intro_commit_history` / `aware_commit_history` in v7_engine: rolling 10-entry log. Not replay-tagged.

No salience/novelty/reward signal marks any episode as "important — replay this."

### Default Mode / spontaneous replay during silence
**NOT PRESENT in v7.** The v6 engine has:
- `_atick_dreaming()` (gualaloom_v5_engine.py line 1486): samples random chi addresses from atlas, surfaces what's there. Produces "dream artifacts" — word fragments from atlas entries.
- Sleep/dream activity cycle (v6 autonomy loop)

The v7 DNA substrate has none of this. No idle-mode behavior, no spontaneous emission, no silence-driven replay.

### Consolidation (plasticity during replay/quiet)
**NOT PRESENT.** No plasticity fires during quiet periods. In v7:
- `decay_plasticity` is imported but never called (mode strengths never decay)
- `enable_self_evo=False` on all tick_once calls (gamma adaptation dormant)
- No sleep-consolidation pass exists

In the multimodal substrate:
- FoldedAtlas.decay runs every 10 ticks (line 404 of MULTIMODAL_DEEP step()) — this is passive forgetting, not consolidation.

### Cross-modal recall
**PARTIALLY PRESENT in multimodal substrate ONLY.** The path:
1. `cofire_bind()` writes bidirectional atlas entries when two modalities fire within 6 ticks
2. `cascade()` propagates activation from active modes to chi-neighbors via atlas strength
3. `mgn_gate()` boosts focus-mode's atlas partners

This gives: fire word "cow" → atlas lookup finds cow__visual, cow__audio, cow__touch, cow__smell entries bound at nearby chi → cascade activates them → mgn_gate amplifies them → they emit.

**Test results:** 17/24 first-correct, 4/6 all-senses-to-word. Moon and stars fail (chi collision).

**NOT PRESENT in v7 assemblage substrate.** The v7 engine has no cross-modal recall — it's a pure S/V/O conversation engine. Sensory modalities don't exist in the assemblage path.

### Cohesion cascade
**PRESENT in multimodal substrate** as `DeepMultiModalCognition.cascade()` (line 264). Propagates activation from modes above `COHESION_THRESHOLD * 0.5` to chi-neighbor modes in the atlas, weighted by `CASCADE_GAIN * strength * overlap`. This IS the cohesion cascade.

**NOT PRESENT in v6 engine** as running code. The handoff audit confirmed: "_The cohesion cascade does not exist as code. The term appears in comments but there is no function that propagates activation through chi neighborhoods to compose output._"

**NOT PRESENT in v7 assemblage substrate.** The assemblage System has keyholes and Hamiltonian evolution but no explicit cascade propagation between sections via chi-neighborhood activation.

---

## Section 7: Anything weird

1. **v7_engine imports NMDA primitives but never uses them** (v7_engine.py lines 22-24): `CoincidenceGate`, `context_no_recent_drive`, `update_drive_tracker` are imported. `drive_tracker = {}` is created at line 69. None are ever instantiated or called. These are leftovers from the pre-restructure 6-section design that was reverted to 4-section.

2. **decay_plasticity imported but never called** (v7_engine.py line 25): Mode strengths grow via `apply_feedback` but never decay. Over time, a heavily-thumbed-up mode accumulates strength with no ceiling erosion. The ceiling is 2.5 (line 394) but there's no decay toward 0 between sessions.

3. **Two different assemblage.py files** in the GualaLoom repo: `src/gualaloom/dna/assemblage.py` (594 lines) and `src/gualaloom/substrate/assemblage.py` (550 lines). The dna/ version has 44 extra lines including `utterance_match_log`, `record_utterance_match()`, richer `hear_speaker()`, and `introspection_vector()`. The deployed substrate uses the 550-line version. The dna/ version is the more developed one — unclear which should be canonical.

4. **enable_self_evo=False on all v7 tick_once calls** (v7_engine.py lines 198, 237, 271): Gamma self-evolution (law_field weight adaptation) is structurally present in assemblage.py (lines 475-492) but completely dormant in the deployed v7 path. This means the Hamiltonian landscape never adapts based on three-axis metrics.

5. **allow_rewiring=False on all v7 tick_once calls**: Dynamic keyhole creation (assemblage.py lines 432-451) is wired but never active. Chi-driven rewiring between sections never fires.

6. **TOP_DOWN_BOOST = 1.0 in multimodal** (GL_MDL_MULTIMODAL_DEEP line 46): Comment says "disabled — was 1.5, but caused feedback loop with MGN." The value 1.0 makes `top_down_expectation()` a no-op. The function runs every tick but produces no effect.

7. **LATERAL_INHIBITION = 0.35 dead constant** (GL_MDL_MULTIMODAL_DEEP line 41): Defined, never referenced in the class body.

8. **Duplicate PictureItem @dataclass decorator** (gualaloom_v5_engine.py lines 153-154): `@dataclass` appears twice on the PictureItem class. Works (Python ignores the redundant decorator) but is clearly a copy-paste error.

9. **v7 and multimodal substrates are disconnected.** The v7 assemblage (conversation, syntax, DNA recipe) and the multimodal DeepMultiModalCognition (5-sense perception, chi atlas, MGN) share no state. They are two independent systems deployed in the same container at different endpoints. There is no path for multimodal percepts to become assemblage input or vice versa.

10. **Session persistence is mode_strength only** (v7_engine.py `to_json`/`load_from_json`): Persists mode_strength values and vocab but NOT mode_bank vectors, NOT psi states, NOT the System's atlas/keyhole state. On container restart, a "resumed" session has the LTP strength numbers but all substrate dynamics restart from random initialization. The strength numbers alone don't reconstitute the trained state.
