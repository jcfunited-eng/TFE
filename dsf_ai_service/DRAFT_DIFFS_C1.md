# C1 Cleanup — Complete Diffs for Review
## Status: DRAFT — NOT pushed to prod

---

## P1: Homepage restructure (index.html)

### DIFF 1A: Hero section

**OLD:**
```html
<h2>Upload your measurement data.<br>Get structural analysis in 60 seconds.</h2>
<p class="hero-sub">Phase transitions. Polymorph screening. Regime detection. Battery degradation. From any measurement type — physics, pharma, materials, medical. No domain expertise required.</p>
```

**NEW:**
```html
<h2>Structural analysis tools<br>for measurement data and material properties.</h2>
<p class="hero-sub">A family of tools: detect phase transitions in any CSV data, predict nanoparticle properties from geometry, find optimal thermocouple pairs. Different computations, one service.</p>
```

**Rationale:** Stops implying one engine does everything. "Family of tools" is honest.

### DIFF 1B: Domain tags — remove Battery

**OLD:**
```html
<span class="domain-tag">Battery Materials</span>
```

**NEW:** (removed)

**Rationale:** Battery page was pulled for lack of evidence.

### DIFF 1C: CSV Analysis section header

**OLD:**
```html
<h2>Structural Analysis</h2>
<p>Upload a two-column CSV (stimulus, measurement). Temperature vs resistance, pressure vs volume, time vs voltage — anything.</p>
```

**NEW:**
```html
<h2>DSF Structural Analyzer</h2>
<p>Upload a two-column CSV (stimulus, measurement) and get transition detection, precursor onset, and stability classification. Temperature vs resistance, pressure vs volume, time vs voltage — any positive scalar field. Deterministic. No training. Same pipeline for all domains.</p>
```

**Rationale:** Named tool, honest scope description. "Any positive scalar field" is technically accurate without overselling.

### DIFF 1D: Cluster Screener section header

**OLD:**
```html
<h2>Nanoparticle Cluster Screener</h2>
<p>Predict magnetic moment, electron affinity, Seebeck coefficient, and HOMO-LUMO gap for any d-metal cluster. No DFT. Milliseconds per prediction.</p>
```

**NEW:**
```html
<h2>Icosahedral Cluster Predictor</h2>
<p>Predict nanoparticle properties from element, cluster size, and lattice type. Geometric model based on icosahedral frustration angle — not the same computation as the CSV analyzer. 4 property types, 23 d-metals, 5 magic sizes. No DFT. Milliseconds per prediction.</p>
```

**Rationale:** Explicitly says "not the same computation." Names the geometric basis without revealing the full framework. 

**FLAG:** Does "icosahedral frustration angle" reveal too much? Alternative: "Geometric Cluster Predictor" with no method hint. Joseph/wC to decide.

### DIFF 1E: Thermocouple section header

**OLD:**
```html
<h2>Thermocouple Pair Finder</h2>
<p>Find optimal nanoparticle thermocouple pairs. Maximizes the Seebeck difference between two cluster materials for highest voltage output.</p>
```

**NEW:**
```html
<h2>Thermocouple Pair Finder</h2>
<p>Utility built on the Cluster Predictor's Seebeck output. Finds the nanoparticle pair with maximum Seebeck difference for highest voltage output.</p>
```

**Rationale:** Makes the dependency explicit — this is a utility on top of the cluster predictor, not a separate engine.

### DIFF 1F: Example section — tool badges

In the "What DSF-AI Finds" section, add tool badges to each example card:

- Physics R(T) card: add `<span class="tool-badge tool-kernel">Structural Analyzer</span>`
- Pharma DSC card: add `<span class="tool-badge tool-kernel">Structural Analyzer</span>`
- Materials table card: add `<span class="tool-badge tool-kernel">Structural Analyzer</span>`
- Sample downloads card: no badge needed

**Rationale:** Visually reinforces which tool produced which result.

---

## P2: Validation page rewrite

Full rewrite at `validation-draft.html` (already created). Key structural changes:

### Section A: Cluster Predictor Validation

**Calibration data** (Fe13, Co13):
- Labeled explicitly: "The (d−1)/(d+2) exchange form was extracted from Fe and Co observations."
- Error shown but context given: these INFORMED the formula

**Out-of-sample predictions** (everything else):
- Ni13 pair correction: genuinely predicted
- Size-dependent (Fe55, Co55, Ni55, Fe147, Co147, Ni147, Fe700): extrapolated from calibrated formula
- Electron affinities: Perdew model applied to cluster sizes
- Au13 Seebeck: computed before comparison
- Au13 HOMO-LUMO: needs confirmation from Joseph
- Seebeck signs: labeled "Textbook" — encodes known d-band physics

**No numerical claims change.** The numbers are the same. Only the framing changes.

### Section B: Structural Analyzer Validation

- Phase transition table: unchanged (all detected, all correctly matched)
- Added note: "All transition values were known beforehand — this tests detection, not discovery"
- Precursor detection: added note "claims are author-validated only; third-party confirmation needed"
- Changed "zero domain configuration" → "Same pipeline, same parameters across all domains tested"

### Section C: What is NOT validated

New section:
- "No third-party reproduction yet"
- "Cluster predictor: icosahedral assumption fails at non-magic sizes (Ag8 outlier documented)"
- "Structural analyzer: precursor detection claims are author-validated only"
- "240 Seebeck predictions for non-Au clusters are untested"

---

## P3: Feedback capture

### DIFF 3A: Add to footer of index.html, pharma.html, all case study pages

**OLD footer:**
```html
<p>DSF-AI © 2026. Universal structural analysis service. <a href="mailto:support@dsf-ai.com">support@dsf-ai.com</a></p>
```

**NEW footer:**
```html
<p>DSF-AI © 2026. <a href="/static/legal.html">Terms & Privacy</a> | <a href="mailto:support@dsf-ai.com">support@dsf-ai.com</a></p>
<p style="font-size:0.8rem;color:#999;">Tried DSF-AI on your own data? Tell us what happened — what worked, what didn't, what surprised you. <a href="mailto:support@dsf-ai.com?subject=DSF-AI%20Feedback">Send feedback</a></p>
```

**Rationale:** Simple email-based feedback. No form, no database, no GDPR issues. Just a mailto link with a pre-filled subject.

---

## P4: UFCP/private research reference audit

**Result: CLEAN.** Only one match found:
- `validation.html:193` — "Kagome superconductor" describing CsV₃Sb₅ — this is standard physics terminology, NOT a reference to the RTSC project. **No change needed.**

No references to: UFCP, coherence fields, fusion, superconductor design, room temperature superconductor, Cu3O2, RTSC, diamond quantum, antigravity, pulsar, geometric coupling law, frustration cascade.

---

## Review checklist for wC and Joseph:

- [ ] P1: Is "Icosahedral Cluster Predictor" acceptable or does "icosahedral" reveal too much?
- [ ] P1: Is "any positive scalar field" accurate for the kernel's input requirements?
- [ ] P2: Was Au13 HOMO-LUMO gap computed before or after seeing 0.650 eV?
- [ ] P2: Are size-dependent moments (Fe55, etc.) fairly labeled as "out-of-sample"?
- [ ] P2: Is the "What is NOT validated" section appropriate for a commercial site?
- [ ] P2: Should we add the Ag8 outlier data to the validation table?
- [ ] P3: Is email-only feedback capture sufficient, or do we need a form?
- [ ] P4: Confirmed clean — any other terms to check?
- [ ] General: Do any of these changes affect numerical claims? (Answer: No)
