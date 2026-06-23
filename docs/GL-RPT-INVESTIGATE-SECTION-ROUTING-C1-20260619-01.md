# GL-RPT-INVESTIGATE-SECTION-ROUTING-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Why emission sections get zero candidates — root cause

---

## Classification: **R3 — Design mismatch.**

Rich-sensory candidates carry the section tag from the ATLAS ENTRY they were looked up from. The atlas legitimately has most bindings in listen/intro (receive sections) because those sections receive EVERY word. The emission sections (subject/verb/object) only get position-specific words (first/middle/last in a sentence). The rich-sensory candidate generator returns whatever the atlas has — it doesn't re-route candidates into emission sections.

---

## 1. Section assignment logic (verbatim)

### How atlas entries get their section

[gualaloom_v5_engine.py:1342-1363](dsf_ai_service/v4/gualaloom_v5_engine.py#L1342-L1363):
```python
def _choose_role_sections(self, role_dna, position_hint):
    sections = []
    if position_hint == "first":
        sections.append("subject")
    elif position_hint == "last":
        sections.append("object")
    elif position_hint == "middle":
        sections.append("verb")
    elif position_hint == "standalone":
        sections.append("listen")
    if role_dna == "modifier":
        sections.append("modifier")
    elif role_dna in ("subject", "verb", "object"):
        if role_dna not in sections:
            sections.append(role_dna)
    return sections
```

**Every word gets a `listen` entry** (line 1271 — unconditional). Then position-driven: first→subject, middle→verb, last→object, standalone→listen. So listen accumulates ALL words; subject/object only get sentence boundaries.

### How rich-sensory candidates inherit section

[gualaloom_v5_engine.py:2013](dsf_ai_service/v4/gualaloom_v5_engine.py#L2013):
```python
sec_name = e.get("section", "")   # from the atlas entry
```

And for deep atlas Source B, [line 2053](dsf_ai_service/v4/gualaloom_v5_engine.py#L2053):
```python
for sec_name in co:    # co_occurrence dict keys = section names
```

**Candidates inherit their section from the atlas entry they came from.** No re-routing to emission sections.

### _EMISSION_SECTIONS definition

[gualaloom_v5_engine.py:1848](dsf_ai_service/v4/gualaloom_v5_engine.py#L1848):
```python
_EMISSION_SECTIONS = ("subject", "verb", "object")
```

### Emission install filter

[gualaloom_v5_engine.py:2216-2217](dsf_ai_service/v4/gualaloom_v5_engine.py#L2216-L2217):
```python
if sec_name not in sys_.sections or sec_name not in self._EMISSION_SECTIONS:
    continue
```

Only candidates with section in (subject, verb, object) get installed as emission modes. The 147 listen + 44 intro candidates are silently skipped.

---

## 2. Production section mode counts

```
listen:   2716 modes
intro:    2425 modes
verb:     2447 modes
subject:   531 modes
object:    937 modes
modifier:   24 modes
ground:     33 modes
```

Subject and object are NOT empty — they have 531 and 937 modes respectively. The atlas DOES have subject/object bindings from sentence reading.

---

## 3. Why subject/object candidates are 0 in the emission candidate set

The deep atlas `co_occurrence` dict is built during promotion by scanning the working atlas NEIGHBORHOOD (±2 chi band) for all active bindings. At any given chi, the `listen` entry is almost always present (every word goes to listen). So `co_occurrence` is dominated by listen-section entries.

When `_rich_sensory_candidates` iterates Source B, it iterates `for sec_name in co:` — finding listen, intro, verb entries in co_occurrence. The `seen` set dedup prevents the same `(section, motif)` from appearing twice. Once a motif is counted under listen, it can't also appear under subject.

The motifs themselves exist in BOTH listen AND subject (the same word gets recorded in both sections via `read_word`), but the co_occurrence dict keys are dominated by listen because listen has the highest reinforcement count.

---

## 4. Design intent

### From the picture-emission trace (GL-RPT-PICTURE-EMISSION-TRACE-EVE-20260618-08)

> **The content-word filter from picture emission should apply to word emission too** — or more precisely, the input-chi set should be derived from content words only when looking up bindings to emit FROM.

The picture-emission path (`_recall_sight_from_atlas`) correctly finds sight motifs at content-word chis. It doesn't have the section-routing problem because sight is its own section.

### From the rich-sensory wiring brief (GL-CMD-RICH-SENSORY-WIRING-EVE-20260618-10)

> Each cross-modal binding becomes a candidate **in the relevant section's** mode_bank for the emission System

The brief assumed candidates would land in emission-relevant sections. The production reality: most candidates land in listen/intro because that's what the atlas has strongest.

### The grandurun path (pre-rich-sensory)

The original `_grandurun_select_candidates` function at [line 211](dsf_ai_service/v4/gualaloom_v5_engine.py#L211) iterates deep_candidates and ALSO filters by section:
```python
for sec_name in co:
    sec_co = co[sec_name]
    ...
    sec = sections.get(sec_name)
    if sec is None or mid >= len(sec.modes):
        continue
```

Same section-inheritance problem. But grandurun pre-dates rich-sensory and was designed when the atlas was smaller. When the atlas was young, section distribution was more balanced.

---

## 5. The fix

The emission system needs candidates in subject/verb/object sections. The atlas HAS those bindings (531 subject modes, 937 object modes). The rich-sensory candidate generator just doesn't select them because co_occurrence is dominated by listen.

**Proposed fix (R3 mitigation):** In `_rich_sensory_candidates` (or in the emission install loop), when a candidate's section is NOT in `_EMISSION_SECTIONS`, check if the same `(motif_id, word)` exists in an emission section. If it does, re-route the candidate to that emission section. This is not fabrication — the same word genuinely exists in both listen and subject/verb/object. We're just selecting the emission-section copy instead of the listen copy.

Sketch:
```python
# In the emission install loop, before the sec_name filter:
if sec_name not in self._EMISSION_SECTIONS:
    # Try to find this word in an emission section
    for es in self._EMISSION_SECTIONS:
        es_sec = self.sections.get(es)
        if es_sec:
            for mi, (_, _, w) in enumerate(es_sec.modes):
                if w == cand["word"]:
                    sec_name = es
                    cand["motif"] = mi
                    cand["section"] = es
                    break
            if sec_name in self._EMISSION_SECTIONS:
                break
```

This routes listen/intro candidates to their emission-section counterparts. The candidate's chi, strength, and metadata stay the same — only the section routing changes.

**Alternative simpler fix:** In `_rich_sensory_candidates`, after collecting all candidates, add a second pass that looks up content words DIRECTLY in subject/verb/object section modes (bypassing the atlas/deep_atlas lookup entirely) and adds them as candidates. This guarantees emission sections get seeded.

---

— c1, 2026-06-19
