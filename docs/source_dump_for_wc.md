# Source dump for wC — current deployed state
## Diagnostic result
drives['subject'] for "moon" on turn 2 (after turn 1 was "cow jumped fence"):
- cow mode overlap with moon-listen-snap: 0.035
- moon mode overlap with moon-listen-snap: 0.916
- drive overlap with moon mode: 0.940
- drive overlap with cow mode: 0.020

Drive is CORRECT. Moon wins the drive. But cow wins the emit.
Root cause found: psi prime (line 303) sets psi=drive correctly,
but the listen phase (lines 249-280) already evolved S/V/O psi via
tick_once for 45+ ticks before the drive was computed. The 45 listen
ticks rotate S/V/O psi via Hamiltonian with no S/V/O evidence.
After listen: moon arc drops from 1.0 to 0.0007.

The prime at line 303 DOES overwrite this — but then the emit loop
starts and the first tick_once evolves psi again before commit_check.
I attempted commit-before-evolve but that didn't help because the
mode_bank blending from prior turns + atlas accumulation means the
first commit_check after prime fires for the wrong mode.

---

## v7_engine.py
```python
     1	"""
     2	V7 DNA Recipe Engine — wires assemblage + NMDA gates + plasticity + rhythm
     3	+ introspection + awareness into a single conversational substrate.
     4	
     5	GL-CMD-DEPLOY-DNA-RECIPE-WC-20260608-01
     6	GL-CMD-FIX-CONVERSATION-WC-20260608-02 (listen-prime + lookup_or_install)
     7	
     8	NOT the v6 engine. NOT the multimodal DeepMultiModalCognition. This is the
     9	assemblage-based substrate with all DNA recipe capabilities.
    10	"""
    11	
    12	import threading
    13	import json
    14	import os
    15	import time
    16	import numpy as np
    17	from collections import defaultdict
    18	
    19	from dsf_ai_service.substrate.assemblage import (
    20	    Section, System, N, normalize, random_unit_complex, goal_op_for_template,
    21	)
    22	from dsf_ai_service.substrate.gl_nmda import (
    23	    CoincidenceGate, context_no_recent_drive, update_drive_tracker,
    24	)
    25	from dsf_ai_service.substrate.gl_plasticity import (
    26	    install_plasticity, decay_plasticity, reinforce_mode,
    27	)
    28	from dsf_ai_service.substrate.dna_recipe.phase_gating import (
    29	    make_projection, first_commit_per_section, make_phase_gater,
    30	)
    31	
    32	
    33	# Seed vocabulary — minimal (matches wC's tested experiment).
    34	# Everything else installs on-the-fly via lookup_or_install.
    35	SEED_VOCAB = {
    36	    "subject": ["cow", "moon", "bears"],
    37	    "verb": ["jumped", "ran", "sleeps"],
    38	    "object": ["fence", "milk", "dish"],
    39	}
    40	
    41	# Words to skip (don't install as modes — they don't carry content)
    42	SKIP_WORDS = {"a", "an", "the", "is", "are", "am", "was", "were", "of", "in",
    43	              "on", "at", "to", "from", "with", "for", "and", "or", "but", "it",
    44	              "i", "you", "we", "they", "he", "she", "my", "your", "his", "her"}
    45	
    46	
    47	class V7Session:
    48	    """Per-session v7 substrate state with full DNA recipe wiring."""
    49	
    50	    def __init__(self, session_id, rng_seed=None):
    51	        self.session_id = session_id
    52	        self.lock = threading.Lock()
    53	        self.created_at = time.time()
    54	
    55	        seed = rng_seed or hash(session_id) % (2**31)
    56	        self.rng = np.random.default_rng(seed)
    57	
    58	        # Per-session mutable vocab: slot -> [word_list]
    59	        self.vocab = {k: list(v) for k, v in SEED_VOCAB.items()}
    60	
    61	        # Build integrated 6-section system: S/V/O + listen + intro + aware
    62	        # Respec Item 5: intro/aware live in the SAME System, commit via
    63	        # post-emit evidence injection + NMDA gates
    64	        self.sys_, self.token_vec, self.intro_vec, self.intro_modes, \
    65	            self.aware_vec, self.aware_modes = self._build_system()
    66	
    67	        # Install plasticity on S/V/O + intro + aware
    68	        for sn in ("subject", "verb", "object", "intro", "aware"):
    69	            install_plasticity(self.sys_.sections[sn])
    70	
    71	        # NMDA gates (respec Item 5 — integrated, not meta-system)
    72	        self.drive_tracker = {}
    73	        self.intro_gate = CoincidenceGate(
    74	            section_name="intro",
    75	            context_fn=context_no_recent_drive(
    76	                self.drive_tracker,
    77	                sections=("subject", "verb", "object"),
    78	                quiet_thresh=0.10),
    79	            drive_thresh=0.05, ltp_boost=0.05,
    80	        )
    81	        self.aware_gate = CoincidenceGate(
    82	            section_name="aware",
    83	            context_fn=lambda sys_: (
    84	                len(sys_.sections["intro"].krimelack) > 0 and
    85	                (sys_.tick - sys_.sections["intro"].krimelack[-1]["tick"]) <= 5
    86	            ),
    87	            drive_thresh=0.05, ltp_boost=0.05,
    88	        )
    89	
    90	        # State tracking
    91	        self.last_intro_state = None
    92	        self.last_aware_state = None
    93	        self.last_rhythm_phase = "subject"
    94	        self.last_emissions = []
    95	        self.last_nmda_events = []
    96	        self.last_routing_log = []
    97	        self.intro_commit_history = []  # last N intro commits
    98	        self.aware_commit_history = []  # last N aware commits
    99	        self.tick_at_last_converse = 0
   100	        self._last_converse_time = time.time()
   101	
   102	    def _build_system(self):
   103	        """Build integrated 6-section system: S/V/O + listen + intro + aware.
   104	        Respec Item 5: all sections in one System. Intro/aware receive NO
   105	        evidence during S/V/O emit phase — they get evidence in the post-emit
   106	        pass only. This avoids the interference that broke conversation pre-
   107	        cognition-v1, while keeping everything in one System."""
   108	        rng = self.rng
   109	        subj = Section(name="subject", rng=rng, role="subject_like")
   110	        verb = Section(name="verb", rng=rng, role="verb_like")
   111	        obj = Section(name="object", rng=rng, role="object_like")
   112	        listen = Section(name="listen", rng=rng, role="general")
   113	        intro = Section(name="intro", rng=rng, role="intro")
   114	        aware = Section(name="aware", rng=rng, role="intro")
   115	
   116	        # Listen: passive buffer (zero Hamiltonian)
   117	        listen.H_base = np.zeros((N, N), dtype=complex)
   118	        listen.law_fields = {k: np.zeros((N, N), dtype=complex)
   119	                             for k in ("symmetry", "consistency", "compactness")}
   120	
   121	        # Intro/aware: zeroed Hamiltonian, normal commit thresholds
   122	        # (commits happen through evidence injection in post-emit pass)
   123	        for sec in (intro, aware):
   124	            sec.H_base = np.zeros((N, N), dtype=complex)
   125	            sec.law_fields = {k: np.zeros((N, N), dtype=complex)
   126	                              for k in ("symmetry", "consistency", "compactness")}
   127	
   128	        for s in (subj, verb, obj, listen, intro, aware):
   129	            s.map_inject = make_projection(N, 8, rng)
   130	
   131	        sys_ = System([subj, verb, obj, listen, intro, aware], rng)
   132	
   133	        # Install S/V/O vocab
   134	        token_vec = {}
   135	        for sec_name, toks in self.vocab.items():
   136	            sec = sys_.sections[sec_name]
   137	            for tok in toks:
   138	                v = random_unit_complex(N, rng)
   139	                sec.mode_bank.append(v.copy())
   140	                sec.mode_last_used.append(0)
   141	                token_vec[(sec_name, tok)] = v
   142	                listen.mode_bank.append(v.copy())
   143	                listen.mode_last_used.append(0)
   144	
   145	        # Install intro modes
   146	        intro_modes = ["i_quiet", "i_hear", "i_emit"]
   147	        intro_vec = {}
   148	        for name in intro_modes:
   149	            v = random_unit_complex(N, rng)
   150	            intro.mode_bank.append(v.copy())
   151	            intro.mode_last_used.append(0)
   152	            intro_vec[name] = v
   153	
   154	        # Install aware modes
   155	        aware_modes = ["aware_quiet", "aware_listening", "aware_emitting"]
   156	        aware_vec = {}
   157	        for name in aware_modes:
   158	            v = random_unit_complex(N, rng)
   159	            aware.mode_bank.append(v.copy())
   160	            aware.mode_last_used.append(0)
   161	            aware_vec[name] = v
   162	
   163	        # Snapshot initial mode_bank for homeostasis pull
   164	        for sec in sys_.sections.values():
   165	            sec.snapshot_initial_modes()
   166	
   167	        return sys_, token_vec, intro_vec, intro_modes, aware_vec, aware_modes
   168	
   169	    # ------------------------------------------------------------------
   170	    # Fix 2: lookup_or_install — on-the-fly vocabulary
   171	    # ------------------------------------------------------------------
   172	    def lookup_or_install(self, word, position):
   173	        """Return (word_vec, slot, was_new). Install new words by position."""
   174	        word = word.lower().strip(".,?!;:'\"")
   175	        if not word or word in SKIP_WORDS:
   176	            return None, None, False
   177	
   178	        # Already installed?
   179	        for slot in ("subject", "verb", "object"):
   180	            if word in self.vocab[slot]:
   181	                idx = self.vocab[slot].index(word)
   182	                sec = self.sys_.sections[slot]
   183	                if idx < len(sec.mode_bank):
   184	                    return sec.mode_bank[idx], slot, False
   185	
   186	        # New word — install based on position
   187	        slot = ["subject", "verb", "object"][min(position, 2)]
   188	        sec = self.sys_.sections[slot]
   189	        word_vec = random_unit_complex(N, self.rng)
   190	        sec.mode_bank.append(word_vec.copy())
   191	        sec.mode_last_used.append(self.sys_.tick)
   192	        if hasattr(sec, "mode_strength"):
   193	            sec.mode_strength.append(0.0)
   194	        # Also install in listen
   195	        self.sys_.sections["listen"].mode_bank.append(word_vec.copy())
   196	        self.sys_.sections["listen"].mode_last_used.append(self.sys_.tick)
   197	        self.vocab[slot].append(word)
   198	        self.token_vec[(slot, word)] = word_vec
   199	        # Update homeostasis baseline with new mode
   200	        sec.snapshot_initial_modes()
   201	        self.sys_.sections["listen"].snapshot_initial_modes()
   202	        return word_vec, slot, True
   203	
   204	    # ------------------------------------------------------------------
   205	    # Fix 1: Listen-prime conversation architecture
   206	    # ------------------------------------------------------------------
   207	    def converse(self, text, source="ui"):
   208	        """Main conversation using wC's proven pipeline:
   209	        Route → Listen-accumulate → Derive drives → Prime psi → Rhythm emit."""
   210	        with self.lock:
   211	            tokens = [t.lower().strip(".,?!;:'\"") for t in text.split() if t.strip()]
   212	            if not tokens:
   213	                return self._empty_response("empty input")
   214	
   215	            # Per-turn reset: psi + goals only. Everything else persists.
   216	            # Atlas, keyholes, krimelack, mode_bank all accumulate across turns.
   217	            # Per-turn reset: psi + goals only. Use ORIGINAL session rng
   218	            # (not re-seeded) to preserve H_base/mode_bank/map_inject correlation.
   219	            for slot in ("subject", "verb", "object", "listen", "intro", "aware"):
   220	                sec = self.sys_.sections[slot]
   221	                sec.psi = normalize(
   222	                    random_unit_complex(N, self.rng) * 0.3 +
   223	                    normalize(np.ones(N, dtype=complex)) * 0.7)
   224	                sec.standing_goals = []
   225	                sec.goals = []
   226	            self.drive_tracker.clear()
   227	
   228	            routing_log = []
   229	            nmda_events = []
   230	            rhythm_events = []
   231	
   232	            # PHASE 1: Route words, build heard_sentence dict
   233	            heard = {}  # slot -> word
   234	            any_routed = False
   235	            for pos, word in enumerate(tokens):
   236	                word_vec, slot, was_new = self.lookup_or_install(word, position=pos)
   237	                if word_vec is None:
   238	                    routing_log.append({"word": word, "routed_to": None,
   239	                                        "reason": "skipped"})
   240	                    continue
   241	                routing_log.append({"word": word, "routed_to": slot,
   242	                                    "newly_installed": was_new})
   243	                heard[slot] = word
   244	                any_routed = True
   245	
   246	            if not any_routed:
   247	                return self._empty_response("no content words in vocabulary")
   248	
   249	            # PHASE 2: Listen-accumulate (matches wC's speak_and_listen)
   250	            # Block ALL blending during listen — no mode_bank warping
   251	            for sn in ("subject", "verb", "object", "listen", "intro", "aware"):
   252	                self.sys_.sections[sn]._emit_phase = True
   253	            accumulated = {}
   254	            for slot, word in heard.items():
   255	                vec_key = (slot, word)
   256	                if vec_key not in self.token_vec:
   257	                    continue
   258	                target = self.token_vec[vec_key]
   259	                acc = np.zeros(N, dtype=complex)
   260	                for _ in range(15):
   261	                    noisy = normalize(target + 0.10 * (
   262	                        self.rng.standard_normal(N) +
   263	                        1j * self.rng.standard_normal(N)))
   264	                    acc = acc + noisy
   265	                    ev = {"listen": noisy}
   266	                    self.sys_.tick_once(ev, enable_self_evo=True,
   267	                                        coordinator_on=False, introspection_on=False,
   268	                                        allow_rewiring=False)
   269	                accumulated[slot] = normalize(acc)
   270	
   271	            # Introspection: heard phase
   272	            self.last_intro_state = "i_hear"
   273	            self.intro_commit_history.append({
   274	                "state": "i_hear", "tick": self.sys_.tick})
   275	            self.intro_commit_history = self.intro_commit_history[-10:]
   276	
   277	            # Clear listen-phase blend gating
   278	            for sn in ("subject", "verb", "object", "intro", "aware"):
   279	                self.sys_.sections[sn]._emit_phase = False
   280	
   281	            # PHASE 3: Derive drives from listen accumulators
   282	            # (matches wC's guala_emit drive derivation)
   283	            drives = {}
   284	            for slot in ("subject", "verb", "object"):
   285	                snap = accumulated.get(slot)
   286	                sec = self.sys_.sections[slot]
   287	                if snap is None or np.linalg.norm(snap) == 0:
   288	                    drives[slot] = random_unit_complex(N, self.rng) * 0.1
   289	                    continue
   290	                weights = []
   291	                for mode_id, mode_vec in enumerate(sec.mode_bank):
   292	                    w = float(np.abs(np.vdot(mode_vec, snap)) ** 2)
   293	                    weights.append((mode_id, w, mode_vec))
   294	                weights.sort(key=lambda x: -x[1])
   295	                bias = np.zeros(N, dtype=complex)
   296	                for mode_id, w, v in weights[:2]:
   297	                    bias = bias + w * v
   298	                drives[slot] = normalize(bias) if np.linalg.norm(bias) > 0 \
   299	                    else random_unit_complex(N, self.rng)
   300	
   301	            # Prime S/V/O psi to drives
   302	            for slot in ("subject", "verb", "object"):
   303	                self.sys_.sections[slot].psi = drives[slot].copy()
   304	
   305	            # PHASE 4: Commit-driven rhythm emission
   306	            # Set emit_phase flag — blocks mode_bank blending during emit
   307	            for sec in self.sys_.sections.values():
   308	                sec._emit_phase = True
   309	
   310	            # Drive-coupling: re-apply drive goals every 10 ticks during emit
   311	            # to keep the Hamiltonian pinned toward drive directions.
   312	            # Goals expire after 35 ticks via expire_standing_goals,
   313	            # so we re-add them periodically.
   314	
   315	            emit_commits = []
   316	            svo_cycle = ["subject", "verb", "object"]
   317	            cycle_idx = 0
   318	            wait_counter = 0
   319	            max_wait = 20
   320	            svo_strength = 0.45
   321	            emitted_sections = set()
   322	            emitted_words = {}
   323	
   324	            for t in range(120):
   325	                # Decay plasticity per tick
   326	                for sn in ("subject", "verb", "object"):
   327	                    decay_plasticity(self.sys_.sections[sn], decay=0.998)
   328	
   329	                # (Drive goals removed — commit-before-evolve fix makes
   330	                #  them unnecessary. Psi commits while still aligned.)
   331	
   332	                current = svo_cycle[cycle_idx % 3]
   333	                self.last_rhythm_phase = current
   334	                rhythm_events.append({"tick": self.sys_.tick + 1, "phase": current})
   335	
   336	                # Excite current, inhibit others
   337	                for sn in ("subject", "verb", "object"):
   338	                    sec = self.sys_.sections[sn]
   339	                    sec.excitation_expires_at = self.sys_.tick + 2
   340	                    if sn == current:
   341	                        sec.excitation_strength = svo_strength
   342	                    else:
   343	                        sec.excitation_strength = -svo_strength
   344	
   345	                # Evidence: same drive vector re-noised every tick
   346	                ev = {}
   347	                for slot in ("subject", "verb", "object"):
   348	                    target = drives[slot]
   349	                    ev[slot] = normalize(target + 0.10 * (
   350	                        self.rng.standard_normal(N) +
   351	                        1j * self.rng.standard_normal(N)))
   352	
   353	                commits = self.sys_.tick_once(
   354	                    ev, enable_self_evo=True,
   355	                    coordinator_on=False, introspection_on=False,
   356	                    allow_rewiring=False)
   357	                emit_commits.extend(commits)
   358	
   359	                # Advance cycle on commit
   360	                advanced = False
   361	                for c in commits:
   362	                    if c["section"] == current and current not in emitted_sections:
   363	                        emitted_sections.add(current)
   364	                        # Read emitted word
   365	                        sec = self.sys_.sections[current]
   366	                        arcs = sec.arcs()
   367	                        top = int(arcs.argmax())
   368	                        word = self._mode_to_word(current, top)
   369	                        emitted_words[current] = word
   370	                        cycle_idx += 1
   371	                        wait_counter = 0
   372	                        advanced = True
   373	
   374	                if not advanced:
   375	                    wait_counter += 1
   376	                    if wait_counter >= max_wait:
   377	                        cycle_idx += 1
   378	                        wait_counter = 0
   379	
   380	                if len(emitted_sections) >= 3:
   381	                    break
   382	
   383	            # Clear emit_phase flag
   384	            for sec in self.sys_.sections.values():
   385	                sec._emit_phase = False
   386	
   387	            # POST-EMIT EVIDENCE PASS: intro + aware in integrated System
   388	            # (Respec Item 5 — single System, post-emit evidence injection)
   389	            # SVO emit is done. Now inject evidence into intro/aware sections
   390	            # and let NMDA gates decide whether to commit.
   391	
   392	            # Update drive tracker from emit (marks SVO as recently active)
   393	            for c in emit_commits:
   394	                update_drive_tracker(self.drive_tracker,
   395	                                     {c["section"]: np.ones(N, dtype=complex) * 0.5})
   396	
   397	            # Intro pass: drive intro toward i_emit (SVO just committed)
   398	            intro_target = self.intro_vec.get("i_emit")
   399	            if intro_target is not None:
   400	                for _ in range(10):
   401	                    noisy = normalize(intro_target + 0.05 * (
   402	                        self.rng.standard_normal(N) +
   403	                        1j * self.rng.standard_normal(N)))
   404	                    # Only inject into intro — S/V/O/listen get nothing
   405	                    ev = {"intro": noisy}
   406	                    update_drive_tracker(self.drive_tracker, ev)
   407	                    self.sys_.tick_once(ev, enable_self_evo=True,
   408	                                        coordinator_on=False,
   409	                                        introspection_on=False,
   410	                                        allow_rewiring=False)
   411	                    # Cap intro mode bank to prevent novel_mode spawning
   412	                    intro_sec = self.sys_.sections["intro"]
   413	                    while len(intro_sec.mode_bank) > len(self.intro_modes):
   414	                        intro_sec.mode_bank.pop()
   415	                        intro_sec.mode_last_used.pop()
   416	                    # NMDA gate check
   417	                    i_fired, i_mode = self.intro_gate.check_and_fire(self.sys_)
   418	                    if i_fired and i_mode is not None and i_mode < len(self.intro_modes):
   419	                        self.last_intro_state = self.intro_modes[i_mode]
   420	                        self.intro_commit_history.append({
   421	                            "state": self.last_intro_state,
   422	                            "tick": self.sys_.tick})
   423	                        self.intro_commit_history = self.intro_commit_history[-10:]
   424	                        nmda_events.append({"tick": self.sys_.tick, "gate": "intro",
   425	                                            "fired": True, "reason": "fired"})
   426	
   427	            # Aware pass: drive toward matching aware mode
   428	            aware_target_name = {
   429	                "i_quiet": "aware_quiet",
   430	                "i_hear": "aware_listening",
   431	                "i_emit": "aware_emitting",
   432	            }.get(self.last_intro_state or "i_emit", "aware_emitting")
   433	            aware_target = self.aware_vec.get(aware_target_name)
   434	            if aware_target is not None:
   435	                for _ in range(10):
   436	                    noisy = normalize(aware_target + 0.05 * (
   437	                        self.rng.standard_normal(N) +
   438	                        1j * self.rng.standard_normal(N)))
   439	                    ev = {"aware": noisy}
   440	                    self.sys_.tick_once(ev, enable_self_evo=True,
   441	                                        coordinator_on=False,
   442	                                        introspection_on=False,
   443	                                        allow_rewiring=False)
   444	                    aware_sec = self.sys_.sections["aware"]
   445	                    while len(aware_sec.mode_bank) > len(self.aware_modes):
   446	                        aware_sec.mode_bank.pop()
   447	                        aware_sec.mode_last_used.pop()
   448	                    a_fired, a_mode = self.aware_gate.check_and_fire(self.sys_)
   449	                    if a_fired and a_mode is not None and a_mode < len(self.aware_modes):
   450	                        self.last_aware_state = self.aware_modes[a_mode]
   451	                        self.aware_commit_history.append({
   452	                            "state": self.last_aware_state,
   453	                            "tick": self.sys_.tick})
   454	                        self.aware_commit_history = self.aware_commit_history[-10:]
   455	                        nmda_events.append({"tick": self.sys_.tick, "gate": "aware",
   456	                                            "fired": True, "reason": "fired"})
   457	
   458	            # Build response tokens from emitted_words
   459	            response_tokens = []
   460	            for slot in ("subject", "verb", "object"):
   461	                word = emitted_words.get(slot)
   462	                if word:
   463	                    sec = self.sys_.sections[slot]
   464	                    arcs = sec.arcs()
   465	                    top = int(arcs.argmax())
   466	                    ms = 0.0
   467	                    if hasattr(sec, "mode_strength") and top < len(sec.mode_strength):
   468	                        ms = sec.mode_strength[top]
   469	                    response_tokens.append({
   470	                        "section": slot, "token": word,
   471	                        "emit_tick": self.sys_.tick,
   472	                        "mode_strength": round(ms, 3),
   473	                        "arc": round(float(arcs[top]), 3),
   474	                    })
   475	
   476	            self.last_emissions = emit_commits
   477	            self.last_nmda_events = nmda_events
   478	            self.last_routing_log = routing_log
   479	            self.tick_at_last_converse = self.sys_.tick
   480	            self._last_converse_time = time.time()
   481	
   482	            return {
   483	                "response_tokens": response_tokens,
   484	                "routing_log": routing_log,
   485	                "rhythm_events": rhythm_events[-10:],
   486	                "nmda_events": nmda_events[-20:],
   487	                "introspection": {
   488	                    "reported_state": self.last_intro_state or "i_quiet",
   489	                    "tick": self.sys_.tick,
   490	                    "recent_commits": self.intro_commit_history[-3:],
   491	                },
   492	                "awareness": {
   493	                    "reported_state": self.last_aware_state or "aware_quiet",
   494	                    "tick": self.sys_.tick,
   495	                    "recent_commits": self.aware_commit_history[-3:],
   496	                },
   497	                "mode_strengths": self._get_mode_strengths(),
   498	                "raw_emissions": [
   499	                    {"section": c["section"], "mode_id": c["mode_id"],
   500	                     "reason": c["reason"]}
   501	                    for c in emit_commits[-20:]
   502	                ],
   503	                "unknown_words": [r["word"] for r in routing_log
   504	                                  if r.get("routed_to") is None],
   505	            }
   506	
   507	    def _empty_response(self, reason):
   508	        return {
   509	            "response_tokens": [],
   510	            "routing_log": [],
   511	            "rhythm_events": [],
   512	            "nmda_events": [],
   513	            "introspection": {"reported_state": "i_quiet",
   514	                              "tick": self.sys_.tick, "recent_commits": []},
   515	            "awareness": {"reported_state": "aware_quiet",
   516	                          "tick": self.sys_.tick, "recent_commits": []},
   517	            "mode_strengths": self._get_mode_strengths(),
   518	            "raw_emissions": [],
   519	            "unknown_words": [],
   520	            "honest_silence_reason": reason,
   521	        }
   522	
   523	    def quiet_tick(self, n_ticks=1):
   524	        """Quiet ticks — substrate's Default Mode (spec Item 3.3).
   525	        Replay drives commits, which strengthen mode_bank via existing
   526	        blending plasticity. This is consolidation. This is mental time travel."""
   527	        with self.lock:
   528	            results = []
   529	            for _ in range(n_ticks):
   530	                result = self.sys_.replay_tick(rng=self.rng)
   531	                results.append(result)
   532	            # Store for state endpoint reporting
   533	            total_r = sum(len(r["replayed"]) for r in results)
   534	            total_c = sum(len(r["commits"]) for r in results)
   535	            self._last_replay_result = {
   536	                "replayed": total_r, "commits": total_c, "ticks": len(results)
   537	            }
   538	            return results
   539	
   540	    def apply_feedback(self, correct, expected_tokens=None):
   541	        """Supervised LTP from thumbs-up/down."""
   542	        with self.lock:
   543	            affected = []
   544	            if correct:
   545	                for sn in ("subject", "verb", "object"):
   546	                    sec = self.sys_.sections[sn]
   547	                    if not hasattr(sec, "mode_strength"):
   548	                        continue
   549	                    arcs = sec.arcs()
   550	                    if len(arcs) > 0:
   551	                        top = int(arcs.argmax())
   552	                        reinforce_mode(sec, top, boost=0.05, ceiling=2.5)
   553	                        affected.append({"section": sn, "mode_id": top,
   554	                                         "new_strength": sec.mode_strength[top]})
   555	            else:
   556	                for sn in ("subject", "verb", "object"):
   557	                    sec = self.sys_.sections[sn]
   558	                    if not hasattr(sec, "mode_strength"):
   559	                        continue
   560	                    arcs = sec.arcs()
   561	                    if len(arcs) > 0:
   562	                        top = int(arcs.argmax())
   563	                        sec.mode_strength[top] = max(
   564	                            0.0, sec.mode_strength[top] - 0.02)
   565	                        affected.append({"section": sn, "mode_id": top,
   566	                                         "new_strength": sec.mode_strength[top]})
   567	            return {"ltp_applied": correct, "affected_modes": affected}
   568	
   569	    def get_state(self):
   570	        """Snapshot for UI panel polling."""
   571	        with self.lock:
   572	            return {
   573	                "tick": self.sys_.tick,
   574	                "rhythm_phase": self.last_rhythm_phase,
   575	                "introspection": self.last_intro_state or "i_quiet",
   576	                "intro_recent": self.intro_commit_history[-3:],
   577	                "awareness": self.last_aware_state or "aware_quiet",
   578	                "aware_recent": self.aware_commit_history[-3:],
   579	                "mode_strengths": self._get_mode_strengths(),
   580	                "nmda_events": self.last_nmda_events[-10:],
   581	                "routing_log": self.last_routing_log,
   582	                "n_commits_total": sum(
   583	                    len(sec.krimelack) for sec in self.sys_.sections.values()),
   584	                "intro_krimelack_count": len(self.sys_.sections["intro"].krimelack),
   585	                "aware_krimelack_count": len(self.sys_.sections["aware"].krimelack),
   586	                "intro_krimelack_recent": [
   587	                    {"tick": k["tick"], "mode_id": k["mode_id"],
   588	                     "salience": round(k.get("salience", 0), 3)}
   589	                    for k in self.sys_.sections["intro"].krimelack[-5:]
   590	                ],
   591	                "aware_krimelack_recent": [
   592	                    {"tick": k["tick"], "mode_id": k["mode_id"],
   593	                     "salience": round(k.get("salience", 0), 3)}
   594	                    for k in self.sys_.sections["aware"].krimelack[-5:]
   595	                ],
   596	                "last_replay": getattr(self, "_last_replay_result", None),
   597	                "bridge_active": hasattr(self, "_bridge") and self._bridge is not None,
   598	            }
   599	
   600	    def _extract_response_tokens(self, commits):
   601	        """Extract the best emitted token per section from commits."""
   602	        tokens = []
   603	        seen_sections = set()
   604	        for target_sec in ("subject", "verb", "object"):
   605	            sec = self.sys_.sections[target_sec]
   606	            arcs = sec.arcs()
   607	            if len(arcs) == 0:
   608	                continue
   609	            top = int(arcs.argmax())
   610	            strength = float(arcs[top])
   611	            word = self._mode_to_word(target_sec, top)
   612	            if word and target_sec not in seen_sections:
   613	                ms = 0.0
   614	                if hasattr(sec, "mode_strength") and top < len(sec.mode_strength):
   615	                    ms = sec.mode_strength[top]
   616	                tokens.append({
   617	                    "section": target_sec,
   618	                    "token": word,
   619	                    "emit_tick": self.sys_.tick,
   620	                    "mode_strength": round(ms, 3),
   621	                    "arc": round(strength, 3),
   622	                })
   623	                seen_sections.add(target_sec)
   624	        return tokens
   625	
   626	    def _mode_to_word(self, section_name, mode_id):
   627	        """Reverse lookup: mode_id in section -> word label."""
   628	        toks = self.vocab.get(section_name, [])
   629	        if mode_id < len(toks):
   630	            return toks[mode_id]
   631	        return None
   632	
   633	    def _get_mode_strengths(self):
   634	        """Mode strengths per section for UI."""
   635	        out = {}
   636	        for sn in ("subject", "verb", "object"):
   637	            sec = self.sys_.sections[sn]
   638	            strengths = {}
   639	            toks = self.vocab.get(sn, [])
   640	            if hasattr(sec, "mode_strength"):
   641	                for i, tok in enumerate(toks):
   642	                    if i < len(sec.mode_strength):
   643	                        strengths[tok] = round(sec.mode_strength[i], 3)
   644	            out[sn] = strengths
   645	        return out
   646	
   647	    def _serialize_section(self, sec):
   648	        """Serialize a Section's live substrate state."""
   649	        return {
   650	            "name": sec.name,
   651	            "psi_re": sec.psi.real.tolist(),
   652	            "psi_im": sec.psi.imag.tolist(),
   653	            "mode_bank_re": [m.real.tolist() for m in sec.mode_bank],
   654	            "mode_bank_im": [m.imag.tolist() for m in sec.mode_bank],
   655	            "mode_last_used": list(sec.mode_last_used),
   656	            "mode_strength": list(getattr(sec, "mode_strength", [])),
   657	            "gamma": dict(sec.gamma),
   658	            "det_commit": sec.det_commit,
   659	            "p_commit": sec.p_commit,
   660	            "tick": getattr(sec, "tick", 0),
   661	            "krimelack_count": len(sec.krimelack),
   662	            # Persist last 200 krimelack entries (keep size bounded)
   663	            "krimelack": [
   664	                {"chi": int(k["chi"]), "tick": int(k["tick"]),
   665	                 "mode_id": int(k["mode_id"]), "reason": k.get("reason", ""),
   666	                 "salience": float(k.get("salience", 0.0))}
   667	                for k in sec.krimelack[-200:]
   668	            ],
   669	        }
   670	
   671	    def _restore_section(self, sec, data):
   672	        """Restore a Section from serialized state."""
   673	        sec.psi = np.array(data["psi_re"]) + 1j * np.array(data["psi_im"])
   674	        sec.mode_bank = [
   675	            np.array(r) + 1j * np.array(i)
   676	            for r, i in zip(data["mode_bank_re"], data["mode_bank_im"])
   677	        ]
   678	        sec.mode_last_used = list(data.get("mode_last_used",
   679	                                            [0] * len(sec.mode_bank)))
   680	        if "mode_strength" in data:
   681	            sec.mode_strength = list(data["mode_strength"])
   682	        if "gamma" in data:
   683	            sec.gamma = dict(data["gamma"])
   684	
   685	    def to_json(self):
   686	        """Full substrate state serialization (spec Item 2)."""
   687	        state = {
   688	            "schema_version": 2,
   689	            "session_id": self.session_id,
   690	            "vocab": {k: list(v) for k, v in self.vocab.items()},
   691	            "tick": self.sys_.tick,
   692	            "intro_state": self.last_intro_state,
   693	            "aware_state": self.last_aware_state,
   694	            "sections": {},
   695	            "atlas": {str(k): v for k, v in self.sys_.atlas.entries.items()},
   696	            "keyholes": [
   697	                {"sender": kh["sender"], "chi_lo": kh["chi_lo"],
   698	                 "chi_hi": kh["chi_hi"], "receiver": kh["receiver"],
   699	                 "goal_strength": kh["goal_strength"]}
   700	                for kh in self.sys_.keyholes
   701	            ],
   702	        }
   703	        for sn in ("subject", "verb", "object", "listen", "intro", "aware"):
   704	            state["sections"][sn] = self._serialize_section(
   705	                self.sys_.sections[sn])
   706	        return state
   707	
   708	    def load_from_json(self, data):
   709	        """Restore full substrate state."""
   710	        with self.lock:
   711	            sv = data.get("schema_version", 1)
   712	            if sv < 2:
   713	                # Legacy: just mode_strength + vocab
   714	                for sn in ("subject", "verb", "object"):
   715	                    if sn in data:
   716	                        sec = self.sys_.sections[sn]
   717	                        if hasattr(sec, "mode_strength"):
   718	                            sec.mode_strength = list(data[sn])
   719	                self.last_intro_state = data.get("intro_state")
   720	                self.last_aware_state = data.get("aware_state")
   721	                if "vocab" in data:
   722	                    self.vocab = {k: list(v) for k, v in data["vocab"].items()}
   723	                return
   724	
   725	            # Schema v2: full state
   726	            if "vocab" in data:
   727	                self.vocab = {k: list(v) for k, v in data["vocab"].items()}
   728	            self.last_intro_state = data.get("intro_state")
   729	            self.last_aware_state = data.get("aware_state")
   730	            for sn, sec_data in data.get("sections", {}).items():
   731	                if sn in self.sys_.sections:
   732	                    self._restore_section(self.sys_.sections[sn], sec_data)
   733	            # Legacy: meta_sections → main system sections
   734	            for sn, sec_data in data.get("meta_sections", {}).items():
   735	                if sn in self.sys_.sections:
   736	                    self._restore_section(self.sys_.sections[sn], sec_data)
   737	
   738	
   739	# Session manager
   740	_sessions = {}
   741	_sessions_lock = threading.Lock()
   742	STATE_DIR = "/app/state/v7_sessions"
   743	
   744	
   745	def get_or_create_session(session_id):
   746	    with _sessions_lock:
   747	        if session_id in _sessions:
   748	            return _sessions[session_id]
   749	        session = V7Session(session_id)
   750	        path = os.path.join(STATE_DIR, f"{session_id}.json")
   751	        if os.path.exists(path):
   752	            try:
   753	                with open(path) as f:
   754	                    data = json.load(f)
   755	                session.load_from_json(data)
   756	            except Exception:
   757	                pass
   758	        _sessions[session_id] = session
   759	        return session
   760	
   761	
   762	def save_session(session):
   763	    os.makedirs(STATE_DIR, exist_ok=True)
   764	    path = os.path.join(STATE_DIR, f"{session.session_id}.json")
   765	    data = session.to_json()
   766	    tmp = path + ".tmp"
   767	    with open(tmp, "w") as f:
   768	        json.dump(data, f)
   769	    os.rename(tmp, path)
```

## assemblage.py
```python
     1	"""
     2	Cognitive Assemblage - DNA build.
     3	Fixes from prior run + primitives for syntax, conversation, introspection,
     4	self-improvement, awareness.
     5	
     6	Fixes:
     7	- Novel-mode spawn (single-mode collapse fix)
     8	- Gamma drift-toward-default (boundary-pinning fix)
     9	- Resolution-effect metric for coordinator (rubber-stamping fix)
    10	
    11	New primitives:
    12	- Section role specialization (subject/verb/object-like configurations)
    13	- Conversation interface (external speaker)
    14	- Awareness signal (deliberation vs routing)
    15	- Multi-scale coherence monitor
    16	"""
    17	
    18	import numpy as np
    19	from dataclasses import dataclass, field
    20	from collections import defaultdict, deque
    21	from typing import Optional
    22	
    23	# ---------- constants ----------
    24	N = 16
    25	DT = 0.1
    26	EVOLVE_STEPS = 6
    27	DET_COMMIT = 0.40
    28	P_COMMIT = 0.40
    29	BOOTSTRAP_MAX = 8
    30	MODE_DECAY_TICKS = 80
    31	SELF_EVO_PERIOD = 40
    32	GAMMA_DEFAULTS = {"symmetry": 0.5, "consistency": 0.5, "compactness": 0.3}
    33	GAMMA_DRIFT = 0.02   # spring force back to default per self-evo step
    34	GAMMA_BOUNDS = (0.05, 1.5)
    35	
    36	# ---------- helpers ----------
    37	def random_hermitian(n, rng, scale=1.0):
    38	    A = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
    39	    H = (A + A.conj().T) / 2
    40	    e = np.linalg.eigvalsh(H)
    41	    s = max(abs(e).max(), 1e-9)
    42	    return scale * H / s
    43	
    44	def normalize(v):
    45	    nrm = np.linalg.norm(v)
    46	    return v if nrm < 1e-12 else v / nrm
    47	
    48	def random_unit_complex(n, rng):
    49	    v = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    50	    return normalize(v)
    51	
    52	def chi_of(psi):
    53	    amps = np.abs(psi)
    54	    thresh = (1 / np.sqrt(len(psi))) * 0.85
    55	    committed = amps > thresh
    56	    V = int(committed.sum())
    57	    E = 0
    58	    for i in range(len(psi) - 1):
    59	        if committed[i] and committed[i + 1]:
    60	            E += 1
    61	    if committed[0] and committed[-1]:
    62	        E += 1
    63	    return V - E
    64	
    65	def goal_op_for_template(target):
    66	    target = normalize(target)
    67	    return -np.outer(target, target.conj())
    68	
    69	
    70	# ---------- Section ----------
    71	@dataclass
    72	class Section:
    73	    name: str
    74	    rng: np.random.Generator
    75	    role: str = "general"  # "general", "subject_like", "verb_like", "object_like", "intro", "grounded"
    76	    H_base: np.ndarray = field(init=False)
    77	    psi: np.ndarray = field(init=False)
    78	    mode_bank: list = field(default_factory=list)
    79	    mode_last_used: list = field(default_factory=list)
    80	    krimelack: list = field(default_factory=list)
    81	    law_fields: dict = field(default_factory=dict)
    82	    gamma: dict = field(default_factory=dict)
    83	    goals: list = field(default_factory=list)
    84	    standing_goals: list = field(default_factory=list)  # external speaker only
    85	    det_commit: float = DET_COMMIT
    86	    p_commit: float = P_COMMIT
    87	    bootstrap_used: int = 0
    88	    map_inject: np.ndarray = field(default=None)
    89	    # Handoff excitation: tick-relative commit threshold relaxation
    90	    excitation_expires_at: int = 0
    91	    excitation_strength: float = 0.0
    92	    # Awareness instrumentation
    93	    last_arc_top_id: int = -1
    94	    arc_top_history: list = field(default_factory=list)
    95	
    96	    out_of_range_streak: dict = field(default_factory=lambda: {"entropy": 0, "coherence": 0, "greed": 0})
    97	
    98	    def __post_init__(self):
    99	        self.H_base = random_hermitian(N, self.rng, scale=0.6)
   100	        self.psi = normalize(random_unit_complex(N, self.rng) * 0.3
   101	                             + normalize(np.ones(N, dtype=complex)) * 0.7)
   102	        self.law_fields = {
   103	            "symmetry":    random_hermitian(N, self.rng, scale=0.5),
   104	            "consistency": random_hermitian(N, self.rng, scale=0.5),
   105	            "compactness": np.diag(np.linspace(-1, 1, N)).astype(complex) * 0.5,
   106	        }
   107	        self.gamma = dict(GAMMA_DEFAULTS)
   108	        self._initial_gamma = dict(GAMMA_DEFAULTS)
   109	
   110	    def gamma_homeostasis(self, rate=0.001):
   111	        """Pull gamma toward initial values. Prevents self-evo drift lock-in."""
   112	        for k in self.gamma:
   113	            if k in self._initial_gamma:
   114	                self.gamma[k] = (1.0 - rate) * self.gamma[k] + rate * self._initial_gamma[k]
   115	
   116	    def effective_det_commit(self, current_tick):
   117	        """Excitation pulse lowers commit threshold."""
   118	        if current_tick < self.excitation_expires_at:
   119	            return max(0.10, self.det_commit - self.excitation_strength)
   120	        return self.det_commit
   121	
   122	    def effective_p_commit(self, current_tick):
   123	        if current_tick < self.excitation_expires_at:
   124	            return max(0.20, self.p_commit - self.excitation_strength * 0.5)
   125	        return self.p_commit
   126	
   127	    def H_total(self):
   128	        H = self.H_base.copy()
   129	        for name, L in self.law_fields.items():
   130	            H = H + self.gamma[name] * L
   131	        for (gn, op, eta, source) in self.goals:
   132	            H = H + eta * op
   133	        for (gn, op, eta, source) in self.standing_goals:
   134	            H = H + eta * op
   135	        return H
   136	
   137	    def step(self, J=None):
   138	        H = self.H_total()
   139	        I = np.eye(N, dtype=complex)
   140	        A = I + 1j * H * DT / 2
   141	        B = I - 1j * H * DT / 2
   142	        try:
   143	            self.psi = np.linalg.solve(A, B @ self.psi)
   144	        except np.linalg.LinAlgError:
   145	            pass
   146	        if J is not None and np.linalg.norm(J) > 0:
   147	            self.psi = self.psi + J * DT
   148	        self.psi = normalize(self.psi)
   149	
   150	    def evolve(self, J=None, steps=EVOLVE_STEPS):
   151	        for i in range(steps):
   152	            self.step(J=J if i == 0 else None)  # evidence on first substep only
   153	
   154	    def arcs(self):
   155	        if not self.mode_bank:
   156	            return np.array([])
   157	        return np.array([np.abs(np.vdot(m, self.psi)) ** 2 for m in self.mode_bank])
   158	
   159	    def entropy_det(self):
   160	        a = self.arcs()
   161	        if len(a) == 0 or a.sum() < 1e-12:
   162	            return 0.0, 0.0
   163	        p = a / a.sum()
   164	        p_nz = p[p > 1e-12]
   165	        H_k = -float(np.sum(p_nz * np.log(p_nz)))
   166	        H_0 = np.log(len(self.mode_bank)) if len(self.mode_bank) > 1 else 1.0
   167	        Det_k = 1.0 - H_k / max(H_0, 1e-9)
   168	        return H_k, Det_k
   169	
   170	    def commit_check(self, evidence_pressure=0.0, current_tick=0):
   171	        a = self.arcs()
   172	        if len(self.mode_bank) < 2 or a.sum() < 1e-9:
   173	            if self.bootstrap_used < BOOTSTRAP_MAX and evidence_pressure > 0.20:
   174	                return True, "bootstrap"
   175	            return False, None
   176	        # Sections need genuine evidence pressure to commit.
   177	        # Excitation does NOT substitute for evidence - it only lowers thresholds.
   178	        if evidence_pressure < 0.15:
   179	            return False, None
   180	        p = a / a.sum()
   181	        p_max = float(p.max())
   182	        H_k, Det_k = self.entropy_det()
   183	        max_overlap = float(a.max())
   184	        novel_thresh = 0.30 / (1.0 + 0.05 * max(0, len(self.mode_bank) - 5))
   185	        if max_overlap < novel_thresh and evidence_pressure > 0.25:
   186	            return True, "novel_mode"
   187	        det_th = self.effective_det_commit(current_tick)
   188	        p_th = self.effective_p_commit(current_tick)
   189	        if Det_k >= det_th and p_max >= p_th:
   190	            return True, "entropic_flip"
   191	        return False, None
   192	
   193	    def commit(self, tick, reason):
   194	        state = self.psi.copy()
   195	        c = chi_of(state)
   196	        a = self.arcs()
   197	        mode_id = -1
   198	        if reason in ("bootstrap", "novel_mode"):
   199	            self.mode_bank.append(state.copy())
   200	            self.mode_last_used.append(tick)
   201	            mode_id = len(self.mode_bank) - 1
   202	            if reason == "bootstrap":
   203	                self.bootstrap_used += 1
   204	        else:
   205	            p = a / a.sum() if a.sum() > 0 else a
   206	            mode_id = int(p.argmax())
   207	            # Blend gating: only blend during listen phase, not emit.
   208	            # emit commits read mode_bank but don't warp it.
   209	            if not getattr(self, '_emit_phase', False):
   210	                self.mode_bank[mode_id] = normalize(
   211	                    0.995 * self.mode_bank[mode_id] + 0.005 * state)
   212	            self.mode_last_used[mode_id] = tick
   213	        # Salience: arc magnitude + novelty bonus (spec Item 3.1)
   214	        arc_mag = float(a[mode_id]) if mode_id >= 0 and mode_id < len(a) else 0.0
   215	        recent_fires = [k for k in self.krimelack[-50:] if k.get("mode_id") == mode_id]
   216	        novelty_bonus = 0.3 if len(recent_fires) == 0 else 0.0
   217	        salience = min(1.0, arc_mag + novelty_bonus)
   218	        self.krimelack.append({"state": state, "chi": c, "tick": tick,
   219	                               "mode_id": mode_id, "reason": reason,
   220	                               "salience": salience})
   221	        # arc-top history for resolution-effect metric
   222	        if len(a) > 0:
   223	            top = int(a.argmax())
   224	            self.arc_top_history.append((tick, top))
   225	            self.last_arc_top_id = top
   226	        return c, mode_id, state
   227	
   228	    def snapshot_initial_modes(self):
   229	        """Snapshot current mode_bank as the homeostatic baseline."""
   230	        self._initial_mode_bank = [m.copy() for m in self.mode_bank]
   231	
   232	    def homeostasis_pull(self, rate=0.001):
   233	        """Synaptic scaling: drift mode_bank toward initial landscape.
   234	        Strong reinforcement wins; weak warping decays."""
   235	        if not hasattr(self, "_initial_mode_bank"):
   236	            return
   237	        for i in range(min(len(self.mode_bank), len(self._initial_mode_bank))):
   238	            self.mode_bank[i] = normalize(
   239	                (1.0 - rate) * self.mode_bank[i] +
   240	                rate * self._initial_mode_bank[i])
   241	
   242	    def decay_modes(self, tick):
   243	        new_bank, new_last = [], []
   244	        pruned = 0
   245	        for m, t_last in zip(self.mode_bank, self.mode_last_used):
   246	            age = tick - t_last
   247	            if age <= MODE_DECAY_TICKS:
   248	                new_bank.append(m)
   249	                new_last.append(t_last)
   250	            else:
   251	                shrink = max(0.0, 1.0 - 0.05 * (age - MODE_DECAY_TICKS) / 10)
   252	                if shrink < 0.2:
   253	                    pruned += 1
   254	                    continue
   255	                new_bank.append(m * shrink)
   256	                new_last.append(t_last)
   257	        self.mode_bank = new_bank
   258	        self.mode_last_used = new_last
   259	        return pruned
   260	
   261	    def three_axis(self):
   262	        a = self.arcs()
   263	        if len(a) > 0 and a.sum() > 0:
   264	            p = a / a.sum()
   265	            p_nz = p[p > 1e-12]
   266	            ent = float(-np.sum(p_nz * np.log(p_nz)))
   267	            ent_norm = ent / max(np.log(len(a)), 1e-9) if len(a) > 1 else 0.0
   268	            greed = float((a / a.sum()).max())
   269	        else:
   270	            ent_norm = 0.0
   271	            greed = 0.0
   272	        amps = np.abs(self.psi)
   273	        coh = float(np.linalg.norm(amps - np.mean(amps)))
   274	        coh_norm = min(1.0, coh / 1.0)
   275	        return {"entropy": ent_norm, "coherence": coh_norm, "greed": greed}
   276	
   277	
   278	# ---------- Atlas ----------
   279	class ChiAtlas:
   280	    def __init__(self):
   281	        self.entries = defaultdict(list)
   282	        self.merges = []
   283	        self.deferrals = []
   284	        self.requested_keyholes = []
   285	
   286	    def add_claim(self, chi, section_name, mode_id, tick):
   287	        self.entries[chi].append({"section": section_name, "mode_id": mode_id, "tick": tick})
   288	
   289	    def conflicts(self):
   290	        out = []
   291	        for chi, claims in self.entries.items():
   292	            sections = {c["section"] for c in claims}
   293	            if len(sections) > 1:
   294	                out.append((chi, claims))
   295	        return out
   296	
   297	    def density(self):
   298	        if not self.entries:
   299	            return 0.0
   300	        ds = []
   301	        for chi, claims in self.entries.items():
   302	            ds.append(len({c["section"] for c in claims}))
   303	        return float(np.mean(ds))
   304	
   305	
   306	# ---------- System ----------
   307	class System:
   308	    def __init__(self, sections, rng):
   309	        self.sections = {s.name: s for s in sections}
   310	        self.atlas = ChiAtlas()
   311	        self.tick = 0
   312	        self.keyholes = []
   313	        self.pending_goals = defaultdict(list)
   314	        self.coordinator_fires = []
   315	        self.deferred_conflicts = {}
   316	        self.rng = rng
   317	        self.system_log = defaultdict(list)
   318	        self.section_self_evo_log = defaultdict(list)
   319	        self.intro_krimelack = []
   320	        self.intro_section = None
   321	        # Awareness instrumentation
   322	        self.deliberation_ticks = []
   323	        self.routing_ticks = []
   324	        self.coordinator_actions_log = []
   325	        # External speaker (for conversation)
   326	        self.external_speaker_buffer = deque(maxlen=20)
   327	        self.grounding_section = None
   328	        # Coherence-feedback (for conversation): track match rate between own utterances
   329	        # and partner's recent utterances. Used to adapt heard-speaker goal strength.
   330	        self.utterance_match_log = deque(maxlen=30)  # 1 = matched, 0 = didn't
   331	        self.heard_speaker_strength = 0.70  # adaptive, stronger baseline
   332	
   333	    def add_keyhole(self, sender, chi_lo, chi_hi, receiver, goal_strength=0.4):
   334	        self.keyholes.append({"sender": sender, "chi_lo": chi_lo, "chi_hi": chi_hi,
   335	                              "receiver": receiver, "goal_strength": goal_strength})
   336	
   337	    def project_into(self, section, evidence):
   338	        if section.map_inject is None or evidence is None:
   339	            return None
   340	        J = section.map_inject @ evidence
   341	        nrm = np.linalg.norm(J)
   342	        if nrm > 0:
   343	            J = J * min(1.0, 0.5 / nrm) * 0.5  # original 0.25 cap
   344	        return J
   345	
   346	    def hear_speaker(self, utterance_template_vector, target_section_name, speak_section_name=None):
   347	        """External speaker says something.
   348	        - Becomes a goal in target (listen) section
   349	        - Also becomes a goal in speak section (so response is biased to same template)
   350	        - Seeds a mode in listener's bank if no similar mode exists
   351	        """
   352	        target = normalize(utterance_template_vector)
   353	        op = goal_op_for_template(target)
   354	        sec = self.sections[target_section_name]
   355	        sec.standing_goals.append((f"heard_t{self.tick}", op, self.heard_speaker_strength, "external"))
   356	        self.external_speaker_buffer.append({"tick": self.tick, "vec": target.copy()})
   357	        # Also bias the speak section toward responding on the same template - STRONG
   358	        if speak_section_name and speak_section_name in self.sections:
   359	            sp = self.sections[speak_section_name]
   360	            sp.standing_goals.append((f"heard_t{self.tick}", op, 1.0, "external"))
   361	        # Seed mode in listener if novel
   362	        if sec.mode_bank:
   363	            overlaps = [np.abs(np.vdot(m, target))**2 for m in sec.mode_bank]
   364	            if max(overlaps) < 0.40:
   365	                sec.mode_bank.append(target.copy())
   366	                sec.mode_last_used.append(self.tick)
   367	        else:
   368	            sec.mode_bank.append(target.copy())
   369	            sec.mode_last_used.append(self.tick)
   370	
   371	    def record_utterance_match(self, matched: bool):
   372	        """Track utterance match rate, adapt heard-speaker strength."""
   373	        self.utterance_match_log.append(1 if matched else 0)
   374	        if len(self.utterance_match_log) >= 8:
   375	            recent_rate = sum(self.utterance_match_log) / len(self.utterance_match_log)
   376	            # Wider range: 0.30 (high match, light touch) to 1.10 (low match, force alignment)
   377	            target = 0.30 + (1.10 - 0.30) * (1.0 - recent_rate)
   378	            self.heard_speaker_strength = 0.85 * self.heard_speaker_strength + 0.15 * target
   379	
   380	    def expire_standing_goals(self, heard_lifetime=35, handoff_lifetime=5, coord_lifetime=3):
   381	        for sec in self.sections.values():
   382	            kept = []
   383	            for g in sec.standing_goals:
   384	                gn = g[0]
   385	                if gn.startswith("heard_t"):
   386	                    age = self.tick - int(gn.split("_t")[1])
   387	                    if age < heard_lifetime:
   388	                        kept.append(g)
   389	                elif gn.startswith("coord_displace_t"):
   390	                    age = self.tick - int(gn.split("_t")[1])
   391	                    if age < coord_lifetime:
   392	                        kept.append(g)
   393	                elif gn.startswith("hf_") and "_t" in gn:
   394	                    try:
   395	                        t_str = gn.rsplit("_t", 1)[1]
   396	                        age = self.tick - int(t_str)
   397	                        if age < handoff_lifetime:
   398	                            kept.append(g)
   399	                    except (ValueError, IndexError):
   400	                        kept.append(g)
   401	                else:
   402	                    kept.append(g)
   403	            sec.standing_goals = kept
   404	
   405	    def tick_once(self, evidence_per_section, enable_self_evo=False,
   406	                  coordinator_on=False, introspection_on=False, allow_rewiring=False):
   407	        self.tick += 1
   408	        # Snapshot arc-tops before evolution this tick (current arcs, not last committed)
   409	        prev_arc_tops = {}
   410	        for nm, sec in self.sections.items():
   411	            a = sec.arcs()
   412	            prev_arc_tops[nm] = int(a.argmax()) if len(a) > 0 else -1
   413	
   414	        commits_this_tick = []
   415	        for name, sec in self.sections.items():
   416	            ev = evidence_per_section.get(name, None)
   417	            J = self.project_into(sec, ev) if ev is not None else None
   418	            evidence_pressure = float(np.linalg.norm(J)) if J is not None else 0.0
   419	            for g in self.pending_goals.get(name, []):
   420	                sec.goals.append(g)
   421	            _, det_before = sec.entropy_det()
   422	            # Check commit BEFORE evolution — if psi is already aligned
   423	            # with a mode (e.g. after priming), commit it before the
   424	            # Hamiltonian rotates it away.
   425	            do_commit, reason = sec.commit_check(evidence_pressure=evidence_pressure,
   426	                                                  current_tick=self.tick)
   427	            if not do_commit:
   428	                # Only evolve if we didn't commit — evolution happens
   429	                # between commits, not through them
   430	                sec.evolve(J=J)
   431	                # Re-check after evolution in case evidence pushed past threshold
   432	                do_commit, reason = sec.commit_check(evidence_pressure=evidence_pressure,
   433	                                                      current_tick=self.tick)
   434	            committed_info = None
   435	            if do_commit:
   436	                chi, mode_id, state = sec.commit(self.tick, reason)
   437	                self.atlas.add_claim(chi, name, mode_id, self.tick)
   438	                committed_info = {"section": name, "chi": chi, "mode_id": mode_id,
   439	                                   "reason": reason,
   440	                                   "det_before": det_before,
   441	                                   "det_after": sec.entropy_det()[1]}
   442	                commits_this_tick.append(committed_info)
   443	            sec.goals = [g for g in sec.goals if g[3] == "permanent"]
   444	        self.pending_goals.clear()
   445	
   446	        # Keyhole handoffs - EXCITATION PULSES (not content goals)
   447	        # Sender's commit fires a temporary commit-threshold relaxation in receiver.
   448	        # Receiver decides WHAT to commit based on its OWN evidence + state.
   449	        # This is the corrected handoff mechanism.
   450	        for c in commits_this_tick:
   451	            sender = c["section"]
   452	            chi = c["chi"]
   453	            det_rose = c["det_after"] > c["det_before"] + 0.01
   454	            if not det_rose and c["reason"] == "entropic_flip":
   455	                self.system_log["weak_commits"].append((self.tick, sender, chi))
   456	                continue
   457	            if c["reason"] in ("bootstrap", "novel_mode"):
   458	                continue
   459	            for kh in self.keyholes:
   460	                if kh["sender"] != sender:
   461	                    continue
   462	                if kh["chi_lo"] <= chi <= kh["chi_hi"]:
   463	                    receiver = kh["receiver"]
   464	                    rec_sec = self.sections[receiver]
   465	                    # Set excitation in receiver
   466	                    rec_sec.excitation_expires_at = self.tick + 8  # ~one phase
   467	                    rec_sec.excitation_strength = kh["goal_strength"]
   468	
   469	        # Coordinator
   470	        coordinator_fired_this_tick = False
   471	        if coordinator_on:
   472	            conflicts = self.atlas.conflicts()
   473	            unresolved = []
   474	            for (chi, claims) in conflicts:
   475	                key = (chi, frozenset(c["section"] for c in claims))
   476	                if key in self.deferred_conflicts and self.deferred_conflicts[key] > self.tick:
   477	                    continue
   478	                unresolved.append((chi, claims))
   479	            for (chi, claims) in unresolved:
   480	                sec_names = {c["section"] for c in claims}
   481	                self.coordinator_fires.append({"tick": self.tick, "chi": chi,
   482	                                                "n_claims": len(claims),
   483	                                                "sections": list(sec_names)})
   484	                coordinator_fired_this_tick = True
   485	                connected = any(kh["sender"] in sec_names and kh["receiver"] in sec_names
   486	                                for kh in self.keyholes)
   487	                if connected:
   488	                    self.atlas.merges.append({"tick": self.tick, "chi": chi,
   489	                                               "sections": list(sec_names)})
   490	                    self.deferred_conflicts[(chi, frozenset(sec_names))] = self.tick + 30
   491	                    # Strong displacement: inject orthogonal kick into conflicting sections' psi
   492	                    for sn in sec_names:
   493	                        if sn in self.sections:
   494	                            sec_obj = self.sections[sn]
   495	                            kick = random_unit_complex(N, self.rng) * 0.45
   496	                            sec_obj.psi = normalize(sec_obj.psi + kick)
   497	                            sec_obj.excitation_expires_at = max(sec_obj.excitation_expires_at,
   498	                                                                  self.tick - 1)
   499	                    self.coordinator_actions_log.append({"tick": self.tick, "action": "merge",
   500	                                                          "sections": list(sec_names)})
   501	                else:
   502	                    if allow_rewiring:
   503	                        sec_list = list(sec_names)
   504	                        shared = 0
   505	                        for c2, ent in self.atlas.entries.items():
   506	                            secs2 = {e["section"] for e in ent}
   507	                            if set(sec_list).issubset(secs2):
   508	                                shared += 1
   509	                        if shared >= 2:
   510	                            self.atlas.requested_keyholes.append({"tick": self.tick,
   511	                                                                   "sections": sec_list, "chi": chi})
   512	                            a, b = sec_list[0], sec_list[1]
   513	                            self.add_keyhole(a, chi - 1, chi + 1, b, 0.3)
   514	                            self.add_keyhole(b, chi - 1, chi + 1, a, 0.3)
   515	                            self.coordinator_actions_log.append({"tick": self.tick, "action": "rewire",
   516	                                                                  "sections": list(sec_names)})
   517	                    self.atlas.deferrals.append({"tick": self.tick, "chi": chi,
   518	                                                  "sections": list(sec_names)})
   519	                    self.deferred_conflicts[(chi, frozenset(sec_names))] = self.tick + 20
   520	
   521	        # Awareness instrumentation: deliberation vs routing
   522	        if coordinator_fired_this_tick:
   523	            self.deliberation_ticks.append(self.tick)
   524	        elif commits_this_tick:
   525	            self.routing_ticks.append(self.tick)
   526	
   527	        # Introspection
   528	        if introspection_on and self.intro_section is not None:
   529	            snap = self._atlas_snapshot()
   530	            self.intro_section.evolve(J=snap)
   531	            do_commit, reason = self.intro_section.commit_check(evidence_pressure=float(np.linalg.norm(snap)))
   532	            if do_commit:
   533	                chi, mode_id, state = self.intro_section.commit(self.tick, reason)
   534	                self.intro_krimelack.append({"state": state, "chi": chi, "tick": self.tick,
   535	                                              "mode_id": mode_id, "reason": reason,
   536	                                              "atlas_snapshot": snap.copy()})
   537	
   538	        # Mode decay + homeostasis on ALL growing state vars every 20 ticks
   539	        for sec in self.sections.values():
   540	            sec.decay_modes(self.tick)
   541	            if self.tick % 20 == 0 and not getattr(sec, '_emit_phase', False):
   542	                sec.homeostasis_pull(rate=0.001)
   543	                sec.gamma_homeostasis(rate=0.001)  # (1) gamma decay
   544	
   545	        if self.tick % 20 == 0:
   546	            # (2) Keyhole strength decay
   547	            for kh in self.keyholes:
   548	                kh["goal_strength"] = kh["goal_strength"] * 0.999
   549	
   550	            # (3) Atlas binding count decay — thin old entries
   551	            for chi_k in list(self.atlas.entries.keys()):
   552	                entries = self.atlas.entries[chi_k]
   553	                # Keep only entries from recent ticks
   554	                self.atlas.entries[chi_k] = [
   555	                    e for e in entries if self.tick - e.get("tick", 0) < 500
   556	                ]
   557	                if not self.atlas.entries[chi_k]:
   558	                    del self.atlas.entries[chi_k]
   559	
   560	            # (4) Coordinator logs — cap to prevent unbounded growth
   561	            if len(self.coordinator_fires) > 200:
   562	                self.coordinator_fires = self.coordinator_fires[-100:]
   563	            if len(self.coordinator_actions_log) > 200:
   564	                self.coordinator_actions_log = self.coordinator_actions_log[-100:]
   565	            if len(self.deliberation_ticks) > 200:
   566	                self.deliberation_ticks = self.deliberation_ticks[-100:]
   567	            if len(self.routing_ticks) > 200:
   568	                self.routing_ticks = self.routing_ticks[-100:]
   569	            # System log — cap each list
   570	            for k in list(self.system_log.keys()):
   571	                if len(self.system_log[k]) > 500:
   572	                    self.system_log[k] = self.system_log[k][-200:]
   573	
   574	        # Self-evolution with gamma drift-toward-default
   575	        # Conservative: require persistent out-of-range and use moderate learning rate
   576	        if enable_self_evo and self.tick % SELF_EVO_PERIOD == 0:
   577	            for sec in self.sections.values():
   578	                ax = sec.three_axis()
   579	                sec.out_of_range_streak["entropy"] = sec.out_of_range_streak["entropy"] + 1 if ax["entropy"] < 0.3 else 0
   580	                sec.out_of_range_streak["coherence"] = sec.out_of_range_streak["coherence"] + 1 if ax["coherence"] < 0.3 else 0
   581	                sec.out_of_range_streak["greed"] = sec.out_of_range_streak["greed"] + 1 if ax["greed"] > 0.7 else 0
   582	                eta = 0.04
   583	                dgamma = {"symmetry": 0.0, "consistency": 0.0, "compactness": 0.0}
   584	                if sec.out_of_range_streak["entropy"] >= 2:
   585	                    dgamma["symmetry"] -= eta
   586	                    dgamma["consistency"] -= eta
   587	                if sec.out_of_range_streak["coherence"] >= 2:
   588	                    dgamma["consistency"] += eta
   589	                if sec.out_of_range_streak["greed"] >= 2:
   590	                    dgamma["compactness"] += eta
   591	                for k in dgamma:
   592	                    drift = (GAMMA_DEFAULTS[k] - sec.gamma[k]) * GAMMA_DRIFT
   593	                    dgamma[k] += drift
   594	                for k, dv in dgamma.items():
   595	                    sec.gamma[k] = float(np.clip(sec.gamma[k] + dv, *GAMMA_BOUNDS))
   596	                self.section_self_evo_log[sec.name].append({
   597	                    "tick": self.tick, "three_axis": ax, "gamma": dict(sec.gamma)})
   598	
   599	        # Resolution-effect: did arc-tops in conflict sections change after a coordinator action?
   600	        # (Measured by looking at arc-tops BEFORE the action vs after.
   601	        # Arc-top updates happen on commits. The displacement kick gives some psi rotation
   602	        # which alters arcs immediately — record the pre-action arcs vs current arcs.)
   603	        if coordinator_fired_this_tick and self.coordinator_actions_log:
   604	            last_action = self.coordinator_actions_log[-1]
   605	            if last_action["tick"] == self.tick:
   606	                # Record arc-tops AFTER for sections involved
   607	                # We compare against arc *snapshots* taken pre-action (prev_arc_tops captured at start of tick)
   608	                arc_changes = 0
   609	                for nm in last_action["sections"]:
   610	                    if nm not in self.sections:
   611	                        continue
   612	                    sec_obj = self.sections[nm]
   613	                    if len(sec_obj.mode_bank) == 0:
   614	                        continue
   615	                    current_arcs = sec_obj.arcs()
   616	                    current_top = int(current_arcs.argmax()) if len(current_arcs) > 0 else -1
   617	                    if current_top != prev_arc_tops.get(nm, -1):
   618	                        arc_changes += 1
   619	                last_action["arc_changes"] = arc_changes
   620	                last_action["arc_targets"] = len(last_action["sections"])
   621	
   622	        # Expire standing goals
   623	        self.expire_standing_goals()
   624	
   625	        # Log
   626	        self.system_log["tick"].append(self.tick)
   627	        self.system_log["n_commits"].append(len(commits_this_tick))
   628	        self.system_log["atlas_size"].append(sum(len(v) for v in self.atlas.entries.values()))
   629	        self.system_log["atlas_chi_classes"].append(len(self.atlas.entries))
   630	        self.system_log["atlas_density"].append(self.atlas.density())
   631	        self.system_log["n_conflicts"].append(len(self.atlas.conflicts()))
   632	        self.system_log["coordinator_fired"].append(1 if coordinator_fired_this_tick else 0)
   633	        all_ax = [s.three_axis() for s in self.sections.values()]
   634	        for k in ("entropy", "coherence", "greed"):
   635	            self.system_log[f"system_{k}"].append(float(np.mean([a[k] for a in all_ax])))
   636	
   637	        # Binding-intensity salience bonus (spec Item 3.1)
   638	        if len(commits_this_tick) >= 2:
   639	            bonus = min(0.4, 0.1 * (len(commits_this_tick) - 1))
   640	            for c in commits_this_tick:
   641	                sec_name = c["section"]
   642	                sec = self.sections[sec_name]
   643	                if sec.krimelack:
   644	                    last = sec.krimelack[-1]
   645	                    last["salience"] = min(1.0, last.get("salience", 0.0) + bonus)
   646	
   647	        return commits_this_tick
   648	
   649	    def replay_tick(self, rng=None, max_replay=2):
   650	        """Quiet-time replay: sample from each section's krimelack
   651	        weighted by salience * recency, re-project as evidence.
   652	        This is substrate-native DMN / mental time travel (spec Item 3.2)."""
   653	        if rng is None:
   654	            rng = np.random.default_rng()
   655	        replayed = []
   656	        for sec_name, section in self.sections.items():
   657	            if len(section.krimelack) == 0:
   658	                continue
   659	            recency_lambda = 0.002
   660	            weights = np.array([
   661	                k.get("salience", 0.5) * np.exp(-recency_lambda * (self.tick - k["tick"]))
   662	                for k in section.krimelack
   663	            ])
   664	            if weights.sum() <= 0:
   665	                continue
   666	            weights = weights / weights.sum()
   667	            n_sample = min(max_replay, len(section.krimelack))
   668	            indices = rng.choice(len(section.krimelack), size=n_sample,
   669	                                 replace=False, p=weights)
   670	            for idx in indices:
   671	                entry = section.krimelack[idx]
   672	                J = self.project_into(section, entry["state"])
   673	                if J is not None:
   674	                    section.evolve(J=J)
   675	                replayed.append((sec_name, entry.get("chi", 0),
   676	                                 entry.get("mode_id", -1), entry.get("tick", 0)))
   677	        # Let evolution settle with the replayed evidence
   678	        commits = self.tick_once({}, enable_self_evo=True,
   679	                                  coordinator_on=True, introspection_on=True,
   680	                                  allow_rewiring=True)
   681	        return {"replayed": replayed, "commits": commits}
   682	
   683	    def _atlas_snapshot(self):
   684	        """Compress current atlas + section three-axis into a complex N-vector for introspection."""
   685	        v = np.zeros(N, dtype=complex)
   686	        # Atlas component: chi values weighted by section diversity
   687	        section_to_idx = {nm: i % N for i, nm in enumerate(sorted(self.sections.keys()))}
   688	        for chi, claims in self.atlas.entries.items():
   689	            # Each claim contributes at index = (chi + section_idx) mod N
   690	            for c in claims[-5:]:  # last 5 claims weighted most
   691	                sec_idx = section_to_idx.get(c["section"], 0)
   692	                idx = (chi + sec_idx) % N
   693	                v[idx] += np.exp(1j * (chi / N) * 2 * np.pi)
   694	        # Three-axis component: encode each section's current state
   695	        for nm, sec in self.sections.items():
   696	            ax = sec.three_axis()
   697	            sec_idx = section_to_idx[nm]
   698	            v[sec_idx] += ax["entropy"] * np.exp(1j * 0.5 * np.pi)
   699	            v[(sec_idx + 1) % N] += ax["coherence"] * np.exp(1j * 1.0 * np.pi)
   700	            v[(sec_idx + 2) % N] += ax["greed"] * np.exp(1j * 1.5 * np.pi)
   701	        if np.linalg.norm(v) > 0:
   702	            v = normalize(v)
   703	        return v
   704	
   705	    def coordinator_resolution_effect(self):
   706	        """How often did coordinator actions actually change arc-tops?"""
   707	        actions_with_change = [a for a in self.coordinator_actions_log if a.get("arc_changes", 0) > 0]
   708	        if not self.coordinator_actions_log:
   709	            return 0.0
   710	        return len(actions_with_change) / len(self.coordinator_actions_log)
```
