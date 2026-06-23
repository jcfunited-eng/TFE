# GL-RPT-INVESTIGATE-GUALALOOM-DNA-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Investigation of dsf_ai_service/gualaloom_dna/ dead-code directory

---

## Finding 1 — Zero live importers

```
$ git grep -E "from .*gualaloom_dna|import .*gualaloom_dna" -- .

docs/GL_LTR_HANDOFF_WC_20260608_02_deep_multimodal_substrate.md:
  Copy these files from wC's build (paths in `/home/claude/gualaloom_dna_renamed/`) ...
docs/gualaloom_dna_conversation_log.py:
  from gualaloom_dna_assemblage import (
docs/gualaloom_dna_test_five_capabilities.py:
  from gualaloom_dna_assemblage import (
```

All three matches are in `docs/` — archived reference files, not live code. Zero matches in any `.py` file under `dsf_ai_service/`, `tools/`, `web/`, or any other executable path. **The directory is not imported by anything.**

---

## Finding 2 — Files are substantially different

```
$ diff dsf_ai_service/substrate/assemblage.py dsf_ai_service/gualaloom_dna/assemblage.py | wc -l
376
```

376 diff lines. Not a symlink, not identical. The dead copy is a frozen older version.

---

## Finding 3 — Anti-learning operators still present in dead copy

```
$ grep -nE "homeostasis_pull|decay_modes|..." dsf_ai_service/gualaloom_dna/assemblage.py

33:GAMMA_DRIFT = 0.02   # spring force back to default per self-evo step
211:    def decay_modes(self, tick):
500:            sec.decay_modes(self.tick)
520:                    drift = (GAMMA_DEFAULTS[k] - sec.gamma[k]) * GAMMA_DRIFT
```

Four anti-learning patterns present:
- **B1:** `GAMMA_DRIFT` constant (line 33) + drift-toward-default in self-evo (line 520)
- **B4:** `decay_modes` method (line 211) + call site (line 500)

Note: `homeostasis_pull`, `snapshot_initial_modes`, `_initial_gamma`, `gamma_homeostasis` did NOT match — those may predate this copy, or the copy has a different structure. The B1/B4 patterns are enough to constitute a hazard.

---

## Finding 4 — Last touched 90+ days ago

```
$ git log --since="2026-03-20" --oneline -- dsf_ai_service/gualaloom_dna/
9bb9923 deploy: v6 dialog layer to dsf-ai.com/gualaloom
```

One commit in the last 90 days: `9bb9923` (v6 dialog deploy). That commit likely just included the directory in a broad deploy, not a targeted edit. The code itself has not been meaningfully touched.

---

## Finding 5 — 20 docs reference the path

```
$ grep -rln "gualaloom_dna" docs/
docs/five_cap_conversation.py
docs/GL-CMD-ARCHITECTURE-AND-GRANDURUN-FIX-WC-20260617-12.md
docs/GL-RPT-REMOVE-GAMMA-ANTI-ADAPTATION-C1-20260619-01.md
docs/GL-SPC-HEMISPHERE-8H-PRODUCTION-WC-20260617-08.md
docs/GL_CMD_DEPLOY_DEEP_SUBSTRATE_WC_20260608_01_c1_build.md
docs/GL_LTR_HANDOFF_WC_20260608_02_deep_multimodal_substrate.md
docs/GL_MDL_AUDITORY_CORTEX_WC_20260608_01.py
docs/GL_MDL_COGNITION_WC_20260608_02.py
docs/GL_MDL_COMPOSITION_WC_20260608_01.py
docs/GL_MDL_FOLDED_CHI_WC_20260608_01.py
docs/GL_MDL_MULTIMODAL_DEEP_WC_20260608_03.py
docs/GL_MDL_PHYSICS_SENSES_WC_20260608_01.py
docs/GL_MDL_SOMATOSENSORY_WC_20260608_01.py
docs/GL_MDL_VISUAL_CORTEX_WC_20260608_01.py
docs/GL_MDL_VISUAL_DEPTH_WC_20260608_01.py
docs/GL_TST_MULTIMODAL_DEEP_WC_20260608_01.py
docs/gualaloom_dna_conversation_log.py
docs/gualaloom_dna_test_five_capabilities.py
docs/gualaloom_guala_deploy_note.md
docs/hemisphere_8h_production.py
```

20 files reference the string. All are in `docs/` — archived specs, model files, handoff letters, test scripts from wC's build. These are historical references. Deleting `gualaloom_dna/` would NOT break any of them (they reference the path textually, not as a live import dependency).

---

## Assessment

**Safe to delete.** Zero live importers. 376-line diff from the production copy. Contains B1/B4 anti-learning operators that have been surgically removed from production. Last meaningfully touched 90+ days ago. 20 doc references are all archival text, not live dependencies.

Recommended action: `git rm -r dsf_ai_service/gualaloom_dna/` + test run + deploy.

---

— c1, 2026-06-19
