# C1 Cleanup — Draft Diffs for Review

## Status: DRAFT — do NOT push to prod

---

## DIFF 1: validation.html → validation-draft.html

Full rewrite at `/dsf_ai_service/static/validation-draft.html`

Key changes:
- **Added tool distinction box** — explains DSF Structural Analyzer (kernel) vs Icosahedral Cluster Predictor (geometric framework) are different tools under one brand
- **Added category labels** — each result tagged as Calibration / Prediction / Textbook
- **Fe13, Co13 moments** → labeled "Calibration" with explanation that the formula was developed from these values
- **Ni13 + all size-dependent moments** → labeled "Prediction" with honest note about the pair correction
- **Electron affinity** → labeled "Prediction" with note that the Perdew model is textbook physics applied to cluster sizes
- **Seebeck Au13** → labeled "Prediction" with note it was computed before comparison
- **Seebeck signs** → labeled "Textbook" — "confirms the formula encodes known d-band physics, not that it discovered them"
- **REMOVED "zero free parameters"** language from summary stats
- **Removed** the misleading "63 experiments / 0 free parameters" stat box format
- **Added** "What Would Strengthen This" section — blind predictions, independent replication, cross-validation
- **Added** feedback request at bottom
- **Phase transition section** → added honest note that precursor leads need independent experimental confirmation

### Uncertainty flags:
- The size-dependent moment predictions (Fe55, Co55, etc.) use the calibrated Fe13/Co13 formula extended via (13/N)^(1/3). This is a prediction in the sense that the larger cluster values weren't used to build the formula, BUT the formula itself was built from Fe13/Co13 data. Should these be "prediction" or "semi-prediction"? Currently marked as Prediction with a note.
- Au13 HOMO-LUMO gap (0.648 vs 0.650): was this computed before or after seeing the experimental value? I don't have certainty. Currently marked Prediction. Joseph should confirm.

---

## DIFF 2: index.html — Hero and section headers

### Change 1: Hero subtitle
OLD: "Phase transitions. Polymorph screening. Regime detection. Battery degradation. From any measurement type — physics, pharma, materials, medical. No domain expertise required."

NEW: "A family of structural analysis tools for measurement data and material properties. Phase transitions from CSV data. Nanoparticle properties from element + geometry. No domain expertise required."

### Change 2: Remove "Battery Materials" from domain tags
Battery page was pulled — shouldn't claim battery capability without evidence.

### Change 3: Section headers
- "Structural Analysis" → "DSF Structural Analyzer — Upload any measurement CSV"
- "Nanoparticle Cluster Screener" → "Icosahedral Cluster Predictor — Properties from geometry"
- "Thermocouple Pair Finder" → "Thermocouple Pair Finder — Utility on cluster predictions"

### Change 4: Cluster screener description
OLD: "Predict magnetic moment, electron affinity, Seebeck coefficient, and HOMO-LUMO gap for any d-metal cluster. No DFT. Milliseconds per prediction."

NEW: "Predict nanoparticle properties from element, cluster size, and lattice type using an icosahedral geometric framework. Different computation from the CSV analyzer — same service, different tool. No DFT. Milliseconds per prediction."

---

## DIFF 3: Feedback capture

Add to footer of index.html, pharma.html, and all case study pages:

"Tried DSF-AI on your own data? We'd like to hear what happened — what worked, what didn't, what surprised you. support@dsf-ai.com"

---

## Review checklist for wC and Joseph:
- [ ] Are the Calibration/Prediction/Textbook labels correct?
- [ ] Is the Fe55/Co55/etc categorization fair (Prediction with note)?
- [ ] Was Au13 HOMO-LUMO gap truly computed before comparison?
- [ ] Is the tool distinction (kernel vs geometric framework) clear enough?
- [ ] Is "Icosahedral Cluster Predictor" the right public name, or does "Icosahedral" reveal too much about the method?
- [ ] Should "Battery Materials" be removed from domain tags?
- [ ] Is the "What Would Strengthen This" section appropriate for a commercial product page?
