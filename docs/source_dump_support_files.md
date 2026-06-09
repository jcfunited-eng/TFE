# Support file source dump for wC
## Diagnostic finding
PRE_TICK trace shows drives['subject'] points at COW (0.9998) not MOON (0.00002).
The drive derivation itself is wrong. The listen accumulator for "moon" ends up
overlapping with cow's mode_bank entry. The emit cycle, Hamiltonian, and commit
order are all red herrings — the bug is upstream in Phase 2/3.

---
## gl_plasticity.py
```python
     1	"""
     2	GL-PRM-PLASTICITY-WC-20260608-01
     3	
     4	Gate-to-section feedback: mode_strength lives ON the section, not the gate.
     5	Section.arcs() returns effective arcs (raw * (1 + strength)). This means
     6	LTP from the NMDA gate propagates into Section.commit_check / commit /
     7	cascade dynamics — not just into post-hoc reads.
     8	
     9	This is the actin-cytoskeleton remodeling primitive from the spec: when
    10	the NMDA gate opens and calcium floods, the spine swells. In substrate
    11	terms, mode_strength permanently changes the mode's apparent magnitude.
    12	"""
    13	
    14	import numpy as np
    15	import types
    16	
    17	
    18	def install_plasticity(section, initial_strength=0.0):
    19	    """Add mode_strength list and patch arcs() to use it."""
    20	    section.mode_strength = [initial_strength] * len(section.mode_bank)
    21	
    22	    def plastic_arcs(self):
    23	        if not self.mode_bank:
    24	            return np.array([])
    25	        # Keep strength array sized to mode bank
    26	        while len(self.mode_strength) < len(self.mode_bank):
    27	            self.mode_strength.append(0.0)
    28	        raw = np.array([np.abs(np.vdot(m, self.psi)) ** 2 for m in self.mode_bank])
    29	        multiplier = np.array([1.0 + self.mode_strength[i] for i in range(len(raw))])
    30	        return raw * multiplier
    31	
    32	    section.arcs = types.MethodType(plastic_arcs, section)
    33	    return section
    34	
    35	
    36	def decay_plasticity(section, decay=0.998):
    37	    """Per-tick decay of mode strength (fast-LTP decay; without
    38	       reinforcement, the spine shrinks back)."""
    39	    if not hasattr(section, "mode_strength"):
    40	        return
    41	    for i in range(len(section.mode_strength)):
    42	        section.mode_strength[i] *= decay
    43	
    44	
    45	def reinforce_mode(section, mode_id, boost=0.05, ceiling=2.0):
    46	    """Apply LTP boost to a specific mode. Called by the NMDA gate when
    47	       coincidence fires."""
    48	    if not hasattr(section, "mode_strength"):
    49	        return
    50	    while len(section.mode_strength) <= mode_id:
    51	        section.mode_strength.append(0.0)
    52	    section.mode_strength[mode_id] = min(ceiling,
    53	                                          section.mode_strength[mode_id] + boost)
```

## gl_nmda.py
```python
     1	"""
     2	GL-PRM-NMDA-COINCIDENCE-WC-20260608-01
     3	
     4	NMDA-style coincidence-gated commit primitive.
     5	
     6	Biological mechanism: NMDA receptors require BOTH
     7	  (a) glutamate binding (drive signal arrives), AND
     8	  (b) postsynaptic depolarization (Mg2+ block removed by context)
     9	before the channel opens, calcium floods, and LTP / commit happens.
    10	
    11	Substrate translation: a section's commit is blocked by default. The block
    12	is removed only when a context-condition is true. When BOTH drive arc is
    13	high AND context permits, the section commits. The same coincidence event
    14	triggers LTP: the mode that fired gets strengthened (raised arc weight for
    15	future ticks).
    16	
    17	Three substrate problems this fixes:
    18	  1. Introspection state transitions — intro fires only when sensory-quiet,
    19	     so transitions are decisive instead of fighting accumulated psi.
    20	  2. Self-improvement via LTP — only coincidence commits strengthen modes,
    21	     so mistakes (which fire without proper context) don't reinforce.
    22	  3. Awareness sync — a meta section fires only when two specific other
    23	     sections are in committed states simultaneously.
    24	
    25	This module:
    26	  - CoincidenceGate class
    27	  - apply_gate(sys_, section_name, gate) to install the gate
    28	  - process_gated_commits(sys_) called each tick to fire gated commits
    29	  - mode strength dict tracking LTP-strengthened modes
    30	"""
    31	
    32	import numpy as np
    33	from dsf_ai_service.substrate.assemblage import N, normalize
    34	
    35	
    36	class CoincidenceGate:
    37	    """An NMDA-style gate: commit only when drive AND context both hold.
    38	       When the gate fires, LTP is applied to the section's mode_strength
    39	       (which must be installed via install_plasticity first)."""
    40	
    41	    def __init__(self, section_name, context_fn, drive_thresh=0.15,
    42	                 ltp_boost=0.05, ltp_decay=0.998, ltp_ceiling=2.0):
    43	        self.section_name = section_name
    44	        self.context_fn = context_fn
    45	        self.drive_thresh = drive_thresh
    46	        self.ltp_boost = ltp_boost
    47	        self.ltp_decay = ltp_decay
    48	        self.ltp_ceiling = ltp_ceiling
    49	
    50	    def check_and_fire(self, sys_):
    51	        """Each tick: decay strengths, check coincidence. If both drive AND
    52	           context hold, fire LTP on the section's top mode."""
    53	        from dsf_ai_service.substrate.gl_plasticity import decay_plasticity, reinforce_mode
    54	
    55	        sec = sys_.sections[self.section_name]
    56	        decay_plasticity(sec, decay=self.ltp_decay)
    57	
    58	        arcs = sec.arcs()  # this is now effective arcs (with mode_strength)
    59	        if len(arcs) == 0:
    60	            return False, None
    61	
    62	        top_idx = int(arcs.argmax())
    63	        top_val = float(arcs[top_idx])
    64	        drive_ok = top_val > self.drive_thresh
    65	
    66	        if not drive_ok:
    67	            return False, None
    68	
    69	        context_ok = self.context_fn(sys_)
    70	        if not context_ok:
    71	            return False, None
    72	
    73	        reinforce_mode(sec, top_idx, boost=self.ltp_boost,
    74	                       ceiling=self.ltp_ceiling)
    75	        return True, top_idx
    76	
    77	
    78	def context_no_recent_drive(drive_tracker, sections=("listen", "subject", "verb", "object"),
    79	                              quiet_thresh=0.10):
    80	    """Context condition: none of the named sections received drive recently.
    81	       drive_tracker is a dict {section_name: float} updated externally per tick."""
    82	    def check(sys_):
    83	        for sn in sections:
    84	            if drive_tracker.get(sn, 0.0) > quiet_thresh:
    85	                return False
    86	        return True
    87	    return check
    88	
    89	
    90	def update_drive_tracker(drive_tracker, ev_dict, decay=0.55):
    91	    """Bump tracker for each section that got driven this tick; decay all."""
    92	    for sn in list(drive_tracker.keys()):
    93	        drive_tracker[sn] *= decay
    94	    for sn, vec in ev_dict.items():
    95	        norm = float(np.linalg.norm(vec))
    96	        drive_tracker[sn] = drive_tracker.get(sn, 0.0) * decay + norm
    97	
    98	
    99	def context_section_committed(section_name, min_arc=0.30):
   100	    """Context condition: another section has a committed-level arc."""
   101	    def check(sys_):
   102	        if section_name not in sys_.sections:
   103	            return False
   104	        arcs = sys_.sections[section_name].arcs()
   105	        if len(arcs) == 0:
   106	            return False
   107	        return float(arcs.max()) > min_arc
   108	    return check
   109	
   110	
   111	def context_AND(*conditions):
   112	    """Compose multiple conditions with AND."""
   113	    def check(sys_):
   114	        return all(c(sys_) for c in conditions)
   115	    return check
```

## phase_gating.py
```python
     1	"""
     2	GL-EXP-L5-PHASE-GATING-WC-20260608-01
     3	
     4	Q: Does ordered SUBJECT -> VERB -> OBJECT emission emerge from substrate
     5	   dynamics when keyhole excitation is time-phase-modulated (L5 primitive),
     6	   vs arbitrary order when ungated?
     7	
     8	Setup: Three sections (subject, verb, object), each with a mode bank.
     9	Drive all three with evidence for tokens simultaneously.
    10	
    11	Experiment A: NO PHASE GATING. Record commit order across trials.
    12	Experiment B: PHASE-GATED EXCITATION. Subject excitable in phase 0..C/3,
    13	verb in phase C/3..2C/3, object in phase 2C/3..C. Record commit order.
    14	
    15	If A is arbitrary and B is consistently S->V->O, L5 carries syntax.
    16	If B doesn't sort, named failure: which primitive refuses to compose.
    17	"""
    18	
    19	import numpy as np
    20	from collections import Counter
    21	from dsf_ai_service.substrate.assemblage import Section, System, N, normalize, random_unit_complex
    22	
    23	# ---- shared rig ----
    24	
    25	def make_projection(n, dim, rng):
    26	    M = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
    27	    Q, _ = np.linalg.qr(M)
    28	    P = np.zeros((n, n), dtype=complex)
    29	    P[:dim, :dim] = np.eye(dim)
    30	    return Q @ P @ Q.conj().T
    31	
    32	def build_svo_system(rng, vocab):
    33	    """Three-section S-V-O system. vocab = {'subject': [...], 'verb': [...], 'object': [...]}."""
    34	    subj = Section(name="subject", rng=rng, role="subject_like")
    35	    verb = Section(name="verb",    rng=rng, role="verb_like")
    36	    obj  = Section(name="object",  rng=rng, role="object_like")
    37	    for s in (subj, verb, obj):
    38	        s.map_inject = make_projection(N, 8, rng)
    39	    sys_ = System([subj, verb, obj], rng)
    40	    # Install modes (one per token per section)
    41	    token_vec = {}
    42	    for sec_name, toks in vocab.items():
    43	        sec = sys_.sections[sec_name]
    44	        for tok in toks:
    45	            v = random_unit_complex(N, rng)
    46	            sec.mode_bank.append(v.copy())
    47	            sec.mode_last_used.append(0)
    48	            token_vec[(sec_name, tok)] = v
    49	    return sys_, token_vec
    50	
    51	def drive_one_trial(sys_, token_vec, sentence_dict, n_ticks, phase_gate_fn=None, rng=None):
    52	    """Drive subject, verb, object simultaneously with evidence for the target tokens.
    53	       sentence_dict = {'subject': 'cow', 'verb': 'jumped', 'object': 'fence'}
    54	       phase_gate_fn(tick, sys_) called at start of each tick to set excitation if desired.
    55	       Returns list of commits with (tick, section, mode_id).
    56	    """
    57	    if rng is None:
    58	        rng = np.random.default_rng(0)
    59	    commits = []
    60	    # Evidence vectors: noisy versions of the target token's mode vector
    61	    targets = {sec: token_vec[(sec, tok)] for sec, tok in sentence_dict.items()}
    62	    for t in range(n_ticks):
    63	        if phase_gate_fn is not None:
    64	            phase_gate_fn(sys_.tick + 1, sys_)
    65	        # Build evidence dict — drive each section with noisy target
    66	        ev = {}
    67	        for sec_name, target in targets.items():
    68	            noisy = normalize(target + 0.10 * (rng.standard_normal(N) + 1j * rng.standard_normal(N)))
    69	            ev[sec_name] = noisy
    70	        these_commits = sys_.tick_once(ev,
    71	                                       enable_self_evo=False,
    72	                                       coordinator_on=False,
    73	                                       introspection_on=False)
    74	        for c in these_commits:
    75	            commits.append({"tick": sys_.tick, "section": c["section"], "mode_id": c["mode_id"]})
    76	    return commits
    77	
    78	def first_commit_per_section(commits):
    79	    """Return order of sections by first-commit-tick."""
    80	    first = {}
    81	    for c in commits:
    82	        if c["section"] not in first:
    83	            first[c["section"]] = c["tick"]
    84	    # Sort by tick
    85	    return sorted(first.items(), key=lambda kv: kv[1])
    86	
    87	# ---- Experiment A: no gating ----
    88	
    89	def run_no_gating(n_trials=20, n_ticks=60):
    90	    rng_master = np.random.default_rng(42)
    91	    orders = []
    92	    no_emission = 0
    93	    for trial in range(n_trials):
    94	        seed = int(rng_master.integers(0, 10_000_000))
    95	        rng = np.random.default_rng(seed)
    96	        vocab = {"subject": ["cow", "moon", "bears"],
    97	                 "verb":    ["jumped", "ran", "sleeps"],
    98	                 "object":  ["fence", "milk", "dish"]}
    99	        sys_, token_vec = build_svo_system(rng, vocab)
   100	        sentence = {"subject": "cow", "verb": "jumped", "object": "fence"}
   101	        commits = drive_one_trial(sys_, token_vec, sentence, n_ticks,
   102	                                  phase_gate_fn=None, rng=rng)
   103	        order = [sec for sec, _ in first_commit_per_section(commits)]
   104	        if len(order) < 3:
   105	            no_emission += 1
   106	            orders.append(tuple(order))
   107	        else:
   108	            orders.append(tuple(order))
   109	    return orders, no_emission
   110	
   111	# ---- Experiment B: phase-gated excitation ----
   112	
   113	def make_phase_gater(cycle, strength):
   114	    """L5 primitive: at tick t in [0..cycle/3) excite subject,
   115	       [cycle/3..2cycle/3) excite verb, [2cycle/3..cycle) excite object.
   116	       Excitation pulse expires after one phase-width."""
   117	    phase_width = cycle // 3
   118	    def gate(tick, sys_):
   119	        phase = tick % cycle
   120	        if phase < phase_width:
   121	            target = "subject"
   122	        elif phase < 2 * phase_width:
   123	            target = "verb"
   124	        else:
   125	            target = "object"
   126	        # Excite target, INHIBIT non-targets (negative strength raises threshold)
   127	        for sec_name in ("subject", "verb", "object"):
   128	            sec = sys_.sections[sec_name]
   129	            sec.excitation_expires_at = tick + 2
   130	            if sec_name == target:
   131	                sec.excitation_strength = strength
   132	            else:
   133	                sec.excitation_strength = -strength  # inhibition
   134	    return gate
   135	
   136	def run_phase_gating(n_trials=20, n_ticks=60, cycle=24, strength=0.20):
   137	    rng_master = np.random.default_rng(42)
   138	    orders = []
   139	    no_emission = 0
   140	    gater = make_phase_gater(cycle, strength)
   141	    for trial in range(n_trials):
   142	        seed = int(rng_master.integers(0, 10_000_000))
   143	        rng = np.random.default_rng(seed)
   144	        vocab = {"subject": ["cow", "moon", "bears"],
   145	                 "verb":    ["jumped", "ran", "sleeps"],
   146	                 "object":  ["fence", "milk", "dish"]}
   147	        sys_, token_vec = build_svo_system(rng, vocab)
   148	        sentence = {"subject": "cow", "verb": "jumped", "object": "fence"}
   149	        commits = drive_one_trial(sys_, token_vec, sentence, n_ticks,
   150	                                  phase_gate_fn=gater, rng=rng)
   151	        order = [sec for sec, _ in first_commit_per_section(commits)]
   152	        if len(order) < 3:
   153	            no_emission += 1
   154	            orders.append(tuple(order))
   155	        else:
   156	            orders.append(tuple(order))
   157	    return orders, no_emission
   158	
   159	# ---- Report ----
   160	
   161	def summarize(label, orders, no_emission):
   162	    print(f"\n=== {label} ===")
   163	    print(f"Trials with <3 commits: {no_emission}/{len(orders)}")
   164	    full = [o for o in orders if len(o) == 3]
   165	    counts = Counter(full)
   166	    target = ("subject", "verb", "object")
   167	    n_target = counts.get(target, 0)
   168	    print(f"S->V->O order: {n_target}/{len(full)} of full-commit trials")
   169	    print("Top 5 orders:")
   170	    for o, n in counts.most_common(5):
   171	        flag = "  <- target" if o == target else ""
   172	        print(f"  {o}: {n}{flag}")
   173	
   174	if __name__ == "__main__":
   175	    print("Experiment A — NO GATING (baseline)")
   176	    a_orders, a_none = run_no_gating(n_trials=20, n_ticks=60)
   177	    summarize("A: no gating", a_orders, a_none)
   178	
   179	    print("\nExperiment B — PHASE GATING sweep")
   180	    for strength in [0.20, 0.30, 0.45, 0.60]:
   181	        for cycle in [18, 24, 36]:
   182	            b_orders, b_none = run_phase_gating(n_trials=20, n_ticks=60,
   183	                                                cycle=cycle, strength=strength)
   184	            target = Counter(b_orders).get(("subject", "verb", "object"), 0)
   185	            subj_first = sum(1 for o in b_orders if len(o) >= 1 and o[0] == "subject")
   186	            print(f"  strength={strength}, cycle={cycle}: S->V->O={target}/20, subject_first={subj_first}/20")
```

## ChiAtlas (from assemblage.py lines 279-310)
```python
     1	class ChiAtlas:
     2	    def __init__(self):
     3	        self.entries = defaultdict(list)
     4	        self.merges = []
     5	        self.deferrals = []
     6	        self.requested_keyholes = []
     7	
     8	    def add_claim(self, chi, section_name, mode_id, tick):
     9	        self.entries[chi].append({"section": section_name, "mode_id": mode_id, "tick": tick})
    10	
    11	    def conflicts(self):
    12	        out = []
    13	        for chi, claims in self.entries.items():
    14	            sections = {c["section"] for c in claims}
    15	            if len(sections) > 1:
    16	                out.append((chi, claims))
    17	        return out
    18	
    19	    def density(self):
    20	        if not self.entries:
    21	            return 0.0
    22	        ds = []
    23	        for chi, claims in self.entries.items():
    24	            ds.append(len({c["section"] for c in claims}))
    25	        return float(np.mean(ds))
    26	
    27	
    28	# ---------- System ----------
    29	class System:
    30	    def __init__(self, sections, rng):
    31	        self.sections = {s.name: s for s in sections}
    32	        self.atlas = ChiAtlas()
```
