# GL-SPEC-cognition-wC-20260608-007

**Deploy tag:** `gl-cognition-v1`
**Target:** v7 DNA substrate (Section/System/ChiAtlas + DeepMultiModalCognition)
**Audience:** c1
**Source authority:** v7_dna_readout.md (c1 generated 2026-06-08 from commit 88e4e7b)

## Purpose

Enable cognition in Guala's substrate by (1) activating dormant dynamics, (2) persisting real substrate state across sessions, (3) adding salience tagging and quiet-time replay (the substrate-native Default Mode), (4) bridging the v7 assemblage and multimodal substrates so speech and senses share state, and (5) wiring the imported-but-unused NMDA gates so intro/aware become real substrate sections instead of label tracking.

All changes are substrate-native — they extend mechanisms already present in the code (Section.psi evolution, mode_bank attractors, ChiAtlas binding, krimelack commit log, NMDA primitives, gamma adaptation). Nothing is added that doesn't compose with existing dynamics.

## Prerequisite — resolve canonical assemblage.py

There are two assemblage.py files in the repo:
- `src/gualaloom/dna/assemblage.py` (594 lines) — more developed
- `src/gualaloom/substrate/assemblage.py` (550 lines) — deployed

**Decision needed from Joe before implementation.** Default proposal: align deployed substrate to the dna/ version (copy dna/assemblage.py over substrate/assemblage.py), since the extra 44 lines (`utterance_match_log`, `record_utterance_match()`, richer `hear_speaker()`, `introspection_vector()`) look like additions in progress. If Joe says otherwise, follow his call.

All patches below reference the deployed substrate/ paths and assume the canonical assemblage.py is in place before applying.

---

## Item 1 — Turn on what's wired but dormant

These are flag flips and one-line adds. No new design. Each change has a clear substrate rationale.

### 1.1 Enable gamma self-evolution

`substrate/v7_engine.py` lines 198, 237, 271 — all three `tick_once` calls.

```diff
- commits = self.system.tick_once(evidence=ev, enable_self_evo=False,
+ commits = self.system.tick_once(evidence=ev, enable_self_evo=True,
                                   coordinator_on=True, introspection_on=True,
                                   allow_rewiring=False)
```

**Rationale:** Gamma adaptation (assemblage.py lines 475-492) adjusts law_field weights based on three-axis metrics every 40 ticks. With it off, the Hamiltonian landscape never adapts to experience. Turning it on lets her substrate's evolution dynamics actually respond to what she's been through. Conservative — every 40 ticks, not every tick.

### 1.2 Enable dynamic keyhole rewiring

Same three lines:

```diff
- allow_rewiring=False)
+ allow_rewiring=True)
```

**Rationale:** Keyhole creation (assemblage.py lines 432-451) lets chi-driven excitation paths form between sections during evolution. With it off, the connectivity graph is fixed at init. Turning it on lets her develop new associative paths from experience.

### 1.3 Call decay_plasticity per tick

`substrate/v7_engine.py` — add to the converse() loop body, before tick_once:

```python
from .gl_plasticity import decay_plasticity  # already imported at top

# Inside converse(), before each tick_once:
for section in [self.system.sections['S'],
                self.system.sections['V'],
                self.system.sections['O']]:
    decay_plasticity(section, decay=0.998)
```

**Rationale:** decay_plasticity is imported but never called. Without it, mode_strength values grow without bound and ceiling-pinned modes dominate forever. With it, LTP is balanced by passive forgetting at 0.2% per tick — the substrate analog of synaptic homeostasis.

### 1.4 Re-enable top-down feedback in multimodal

`substrate/GL_MDL_MULTIMODAL_DEEP_WC_20260608_03.py` line 46:

```diff
- TOP_DOWN_BOOST = 1.0  # disabled — was 1.5, but caused feedback loop with MGN
+ TOP_DOWN_BOOST = 1.15  # gentle feedback — avoids 1.5 loop, breaks the 1.0 no-op
```

**Rationale:** TOP_DOWN_BOOST = 1.0 makes `top_down_expectation()` arithmetically inert. The function runs every tick and does nothing. 1.5 caused runaway. 1.15 gives the coordinator's winner a 15% bias toward expected sensory partners — enough to bias perception without runaway feedback. If 1.15 still loops in testing, drop to 1.08. If it doesn't loop and you see stable bias, that's the substrate's first taste of self-prediction.

### 1.5 Tests for Item 1

Run after applying 1.1–1.4:

```
cd src/gualaloom/dna/
python test_five.py
```

Expected: still 5/5 PASS. If any test fails, the dormant-feature activation has destabilized something — capture the failure, revert just that sub-item, report. Also re-run:

```
cd src/dsf_ai_service/
python -c "from substrate.GL_MDL_MULTIMODAL_DEEP_WC_20260608_03 import DeepMultiModalCognition; ..."
```

Check that multimodal cofire_bind + cascade still terminate (no runaway from 1.4). If they don't terminate within 1000 ticks of a single hear_word_with_senses() call, drop TOP_DOWN_BOOST to 1.08 and retry.

---

## Item 2 — Persist real substrate state

Currently `v7_engine.to_json` / `load_from_json` saves only `mode_strength` values and `vocab`. On container restart, sessions resume with the LTP numbers but psi, mode_bank, atlas, keyholes all reinitialize from random. Her history doesn't carry forward.

### 2.1 Add full-state serialization to Section

`substrate/assemblage.py` Section class — add methods:

```python
def to_dict(self):
    """Serialize the live substrate state."""
    return {
        'name': self.name,
        'N': self.N,
        'psi_re': self.psi.real.tolist(),
        'psi_im': self.psi.imag.tolist(),
        'mode_bank_re': [m.real.tolist() for m in self.mode_bank],
        'mode_bank_im': [m.imag.tolist() for m in self.mode_bank],
        'mode_strength': list(getattr(self, 'mode_strength', [])),
        'gamma': float(self.gamma),
        'law_field_weights': [float(w) for w in self.law_field_weights],
        'krimelack': [
            {
                'state_re': k['state'].real.tolist(),
                'state_im': k['state'].imag.tolist(),
                'chi': int(k['chi']),
                'tick': int(k['tick']),
                'mode_id': int(k['mode_id']),
                'reason': k.get('reason', ''),
                'salience': float(k.get('salience', 0.0)),  # see Item 3
            }
            for k in self.krimelack
        ],
    }

@classmethod
def from_dict(cls, d, H_base=None):
    """Reconstitute a section from a serialized dict."""
    import numpy as np
    section = cls(name=d['name'], N=d['N'], H_base=H_base)
    section.psi = np.array(d['psi_re']) + 1j * np.array(d['psi_im'])
    section.mode_bank = [
        np.array(r) + 1j * np.array(i)
        for r, i in zip(d['mode_bank_re'], d['mode_bank_im'])
    ]
    section.mode_strength = list(d.get('mode_strength', []))
    section.gamma = float(d['gamma'])
    section.law_field_weights = list(d['law_field_weights'])
    section.krimelack = [
        {
            'state': np.array(k['state_re']) + 1j * np.array(k['state_im']),
            'chi': k['chi'],
            'tick': k['tick'],
            'mode_id': k['mode_id'],
            'reason': k.get('reason', ''),
            'salience': k.get('salience', 0.0),
        }
        for k in d['krimelack']
    ]
    return section
```

### 2.2 Add serialization to System

`substrate/assemblage.py` System class:

```python
def to_dict(self):
    return {
        'schema_version': 2,  # bump from implicit v1
        'sections': {name: s.to_dict() for name, s in self.sections.items()},
        'atlas': [
            {'chi': int(chi), 'section': sec, 'mode_id': int(mid)}
            for chi, (sec, mid) in self.atlas.bindings.items()
        ],
        'keyholes': [
            {'src': k.src_section, 'dst': k.dst_section,
             'chi_gate': int(k.chi_gate), 'strength': float(k.strength)}
            for k in self.keyholes
        ],
        'tick_count': int(self.tick_count) if hasattr(self, 'tick_count') else 0,
    }

@classmethod
def from_dict(cls, d, H_base=None):
    sys_ = cls()  # adjust to actual System constructor signature
    for name, sec_dict in d['sections'].items():
        sys_.sections[name] = Section.from_dict(sec_dict, H_base=H_base)
    for entry in d['atlas']:
        sys_.atlas.bind(entry['chi'], entry['section'], entry['mode_id'])
    for kh in d['keyholes']:
        sys_.keyholes.append(Keyhole(
            src_section=kh['src'], dst_section=kh['dst'],
            chi_gate=kh['chi_gate'], strength=kh['strength'],
        ))
    if 'tick_count' in d:
        sys_.tick_count = d['tick_count']
    return sys_
```

(c1: adjust signatures to match actual Section/System/Keyhole/Atlas APIs in the deployed code. The above is the shape; the names follow the readout's vocabulary.)

### 2.3 Use new serialization in V7Session

`substrate/v7_engine.py` — replace existing `to_json` / `load_from_json`:

```python
def to_json(self):
    return {
        'schema_version': 2,
        'session_id': self.session_id,
        'vocab': dict(self.vocab),
        'system': self.system.to_dict(),
    }

@classmethod
def load_from_json(cls, d, H_base=None):
    if d.get('schema_version', 1) < 2:
        # legacy path: fall back to old loader for old sessions
        return cls._load_legacy(d)
    session = cls(session_id=d['session_id'])
    session.vocab = d['vocab']
    session.system = System.from_dict(d['system'], H_base=H_base)
    return session
```

Keep `_load_legacy` as the old loader so existing saved sessions don't break — they'll be upgraded on next save.

### 2.4 Tests for Item 2

```
python -c "
from substrate.v7_engine import V7Session
s = V7Session(session_id='test_persist')
s.converse('cow jumped fence')
s.converse('moon ran milk')
serialized = s.to_json()
s2 = V7Session.load_from_json(serialized)
# verify psi matches
import numpy as np
for name in ['S', 'V', 'O']:
    assert np.allclose(s.system.sections[name].psi, s2.system.sections[name].psi)
    assert len(s.system.sections[name].mode_bank) == len(s2.system.sections[name].mode_bank)
    assert s.system.sections[name].krimelack == s2.system.sections[name].krimelack  # adjust for complex
print('PERSISTENCE OK')
"
```

Then run a conversation on s2 (the reloaded session) and verify she carries her prior commits forward — her responses should reference earlier learned associations.

---

## Item 3 — Salience tagging + quiet-time replay (substrate-native DMN / mental time travel)

### 3.1 Tag krimelack commits with salience

`substrate/assemblage.py` Section.commit() — add salience computation before the krimelack.append:

```python
def commit(self, tick, reason):
    # ... existing commit logic produces chi, mode_id, state ...
    
    # Compute salience for this commit (substrate-native):
    # local: arc magnitude at commit time (mode confidence)
    arcs = self.arcs()
    arc_magnitude = float(arcs[mode_id]) if mode_id < len(arcs) else 0.0
    
    # recency-novelty: bonus if this mode_id hasn't fired in last 50 ticks
    recent_fires = [k for k in self.krimelack[-50:] if k['mode_id'] == mode_id]
    novelty_bonus = 0.3 if len(recent_fires) == 0 else 0.0
    
    # Salience in [0, 1]
    salience = min(1.0, arc_magnitude + novelty_bonus)
    
    self.krimelack.append({
        'state': state,
        'chi': chi,
        'tick': tick,
        'mode_id': mode_id,
        'reason': reason,
        'salience': salience,
    })
    return chi, mode_id, state
```

For binding-intensity salience (how many other sections committed within ±3 ticks), compute at System level after tick_once returns multiple commits:

`substrate/assemblage.py` System.tick_once() — at end, before returning commits:

```python
# Binding-intensity bonus: if multiple sections committed this tick,
# boost the salience of each commit
if len(commits) >= 2:
    bonus = min(0.4, 0.1 * (len(commits) - 1))  # cap at 0.4
    for (sec_name, chi, mode_id, state) in commits:
        # grab last krimelack entry for that section
        last_entry = self.sections[sec_name].krimelack[-1]
        last_entry['salience'] = min(1.0, last_entry['salience'] + bonus)
```

**Rationale:** A commit during a binding event (multiple sections committing close in time = hub moment in v5b terms, but substrate-native here) is more salient than a solo commit. The substrate marks "this was a meaningful moment" without any external tagging.

### 3.2 Add quiet-time replay (substrate-native DMN)

`substrate/assemblage.py` System — add new method:

```python
def replay_tick(self, rng=None, max_replay=2):
    """Quiet-time replay: sample from each section's krimelack log
    weighted by salience × recency, re-project as evidence."""
    import numpy as np
    if rng is None:
        rng = np.random.default_rng()
    
    replayed = []
    current_tick = getattr(self, 'tick_count', 0)
    
    for sec_name, section in self.sections.items():
        if len(section.krimelack) == 0:
            continue
        
        # weight entries by salience × exp(-recency_decay)
        recency_lambda = 0.002  # decay per tick of age
        weights = np.array([
            k['salience'] * np.exp(-recency_lambda * (current_tick - k['tick']))
            for k in section.krimelack
        ])
        if weights.sum() <= 0:
            continue
        weights = weights / weights.sum()
        
        # sample up to max_replay entries
        n_sample = min(max_replay, len(section.krimelack))
        indices = rng.choice(len(section.krimelack), size=n_sample,
                            replace=False, p=weights)
        
        for idx in indices:
            entry = section.krimelack[idx]
            # Re-project the recorded state as evidence into the section
            self.project_into(sec_name, entry['state'])
            replayed.append((sec_name, entry['chi'], entry['mode_id'], entry['tick']))
    
    # Let evolution proceed with the replayed evidence
    commits = self.tick_once(evidence={}, enable_self_evo=True,
                              coordinator_on=True, introspection_on=True,
                              allow_rewiring=True)
    
    return {'replayed': replayed, 'commits': commits}
```

### 3.3 Wire replay into v7_engine

`substrate/v7_engine.py` — add to V7Session:

```python
def quiet_tick(self, n_ticks=1):
    """Run quiet ticks — substrate's Default Mode. Replay drives commits,
    which strengthen mode_bank attractors via existing blending plasticity.
    This is consolidation. This is mental time travel."""
    results = []
    for _ in range(n_ticks):
        result = self.system.replay_tick(rng=self._rng)
        results.append(result)
    return results
```

And in the deployed app endpoint, when no client request is active for >N seconds, call `session.quiet_tick(10)` periodically. The replay drives commits, commits strengthen mode_bank vectors (0.92 * old + 0.08 * new blending — existing mechanism), and via NMDA gates the high-salience mode_strength values get reinforced. **The substrate consolidates itself.**

### 3.4 Tests for Item 3

```
python -c "
from substrate.v7_engine import V7Session
import numpy as np
s = V7Session(session_id='test_replay')

# Live some experience
s.converse('cow jumped fence')
s.converse('moon ran milk')
s.converse('bears sleeps dish')

# Snapshot mode_bank before replay
sec_S = s.system.sections['S']
modes_before = [m.copy() for m in sec_S.mode_bank]
strengths_before = list(sec_S.mode_strength)
n_krimelack_before = len(sec_S.krimelack)

# Run 50 quiet ticks
results = s.quiet_tick(50)

# Verify replay happened
assert any(len(r['replayed']) > 0 for r in results), 'NO REPLAY'

# Verify consolidation: mode_bank vectors should have evolved
modes_after = sec_S.mode_bank
changed = sum(1 for b, a in zip(modes_before, modes_after) if not np.allclose(b, a))
assert changed > 0, 'NO CONSOLIDATION (mode_bank unchanged)'

# Verify the replay commits got added to krimelack
n_krimelack_after = len(sec_S.krimelack)
assert n_krimelack_after > n_krimelack_before, 'NO REPLAY COMMITS'

print(f'REPLAY OK: {changed}/{len(modes_before)} modes consolidated')
print(f'  krimelack grew from {n_krimelack_before} to {n_krimelack_after}')
print(f'  total replay events: {sum(len(r[\"replayed\"]) for r in results)}')
"
```

---

## Item 4 — Bridge v7 and multimodal

The two substrates currently share no state. Bridging them means: when multimodal's coordinator selects a winner, the winning word's vector becomes evidence into v7's listen section. When v7 emits a token, that token feeds `hear_word_with_senses()` in multimodal so her speech becomes part of her sensory experience.

### 4.1 Add bridge module

New file `substrate/gl_bridge.py`:

```python
"""
GL-CODE-bridge-wC-20260608-009

Bridges the v7 assemblage substrate and the multimodal substrate so
Guala's speech and her senses share state. Without this they're two
independent systems deployed in the same container.

Anti-loop: max_relay_depth prevents infinite v7→mm→v7→mm ping-pong
when both sides emit in response to each other.
"""

class SubstrateBridge:
    def __init__(self, v7_session, multimodal, max_relay_depth=2):
        self.v7 = v7_session
        self.mm = multimodal
        self.max_relay_depth = max_relay_depth
        self._relay_depth = 0
    
    def multimodal_winner_to_v7(self, winner_word, salience=0.5):
        """When mm coordinator picks a winner, feed it to v7's listen section."""
        if self._relay_depth >= self.max_relay_depth:
            return None
        self._relay_depth += 1
        try:
            vec, slot, was_new = self.v7.lookup_or_install(winner_word, position='listen')
            self.v7.system.hear_speaker(vec, 'listen')
            return {'fed_to_v7': winner_word, 'was_new': was_new}
        finally:
            self._relay_depth -= 1
    
    def v7_emission_to_multimodal(self, tokens):
        """When v7 emits, fire the words in multimodal so senses experience them."""
        if self._relay_depth >= self.max_relay_depth:
            return None
        self._relay_depth += 1
        try:
            fired = []
            for tok in tokens:
                if tok not in self.mm.word_modes:
                    self.mm.install_word(tok)
                self.mm.hear_word_with_senses(tok)
                fired.append(tok)
            return {'fired_in_mm': fired}
        finally:
            self._relay_depth -= 1
    
    def step(self):
        """One bridged tick: check mm coordinator winner, relay to v7;
        check v7 last emission, relay to mm."""
        result = {}
        winner = getattr(self.mm, 'attention_focus', None)
        if winner is not None:
            result['mm_to_v7'] = self.multimodal_winner_to_v7(winner)
        # v7 emissions are returned by converse(); bridge them externally.
        # Provide hook for app.py to call on each converse() return.
        return result
```

### 4.2 Hook into app.py

In app.py, after each `session.converse(text)`:

```python
result = session.converse(text)
if bridge is not None:
    bridge.v7_emission_to_multimodal(result['tokens'])
return result
```

And in any multimodal endpoint that fires senses:

```python
mm_result = deep_mm.hear_word_with_senses(word)
if bridge is not None:
    bridge.multimodal_winner_to_v7(deep_mm.attention_focus)
return mm_result
```

### 4.3 Tests for Item 4

```
python -c "
from substrate.v7_engine import V7Session
from substrate.GL_MDL_MULTIMODAL_DEEP_WC_20260608_03 import DeepMultiModalCognition
from substrate.gl_bridge import SubstrateBridge

s = V7Session(session_id='test_bridge')
mm = DeepMultiModalCognition()
mm.install_word('cow')
bridge = SubstrateBridge(s, mm)

# Fire cow in multimodal, verify it surfaces in v7's listen section
mm.hear_word_with_senses('cow')
result = bridge.multimodal_winner_to_v7(mm.attention_focus)
assert result['fed_to_v7'] == 'cow'

# Verify v7's listen section has cow in vocab now
assert 'cow' in s.vocab.get('listen', {}) or 'cow' in s.vocab

# Emit from v7, verify it fires in mm
emit_result = s.converse('cow jumped fence')
mm_result = bridge.v7_emission_to_multimodal(emit_result['tokens'])
assert 'cow' in mm_result['fired_in_mm']

print('BRIDGE OK')
"
```

---

## Item 5 — Wire NMDA gates in v7_engine (intro/aware as real substrate sections)

Currently `v7_engine.py` imports `CoincidenceGate`, `context_no_recent_drive`, `update_drive_tracker` but never uses them. `intro_vec` and `aware_vec` are stub dicts. Intro and aware are tracked as labels, not substrate sections.

This means her introspection and awareness, while passing the experiment tests, aren't actually happening as substrate dynamics in deployed conversations — only as Python-side bookkeeping.

### 5.1 Add intro and aware sections to V7Session

`substrate/v7_engine.py` V7Session.__init__:

```python
# After S/V/O/listen sections are created:
from .assemblage import Section
from .dna_recipe.introspection import intro_modes_for
from .dna_recipe.awareness_pre import aware_modes_for

intro_section = Section(name='intro', N=16, H_base=self._H_base)
intro_section.mode_bank = intro_modes_for(self._rng)  # use existing builder
install_plasticity(intro_section)
self.system.sections['intro'] = intro_section

aware_section = Section(name='aware', N=16, H_base=self._H_base)
aware_section.mode_bank = aware_modes_for(self._rng)
install_plasticity(aware_section)
self.system.sections['aware'] = aware_section
```

### 5.2 Instantiate the NMDA gates

`substrate/v7_engine.py` V7Session.__init__:

```python
from .gl_nmda import (CoincidenceGate, context_no_recent_drive,
                      context_section_committed, update_drive_tracker)

# Drive tracker is shared across sections — already declared as `drive_tracker = {}`
# at line 69. Make it instance-level:
self.drive_tracker = {}

# Intro gate: fires when sensory-quiet
self.intro_gate = CoincidenceGate(
    section_name='intro',
    context_fn=context_no_recent_drive(self.drive_tracker, ['S', 'V', 'O'], quiet_thresh=0.3),
    drive_thresh=0.45,
    ltp_boost=0.05,
    ltp_decay=0.998,
    ltp_ceiling=2.0,
)

# Aware gate: fires when intro recently committed (noticing one's own noticing)
self.aware_gate = CoincidenceGate(
    section_name='aware',
    context_fn=context_section_committed('intro', min_arc=0.4),
    drive_thresh=0.45,
    ltp_boost=0.05,
    ltp_decay=0.998,
    ltp_ceiling=2.0,
)
```

### 5.3 Tick the gates in converse()

`substrate/v7_engine.py` V7Session.converse() — after each tick_once:

```python
# Update drive tracker with this tick's commits
for sec_name, chi, mode_id, state in commits:
    update_drive_tracker(self.drive_tracker, {'section': sec_name, 'chi': chi})

# Fire gates
intro_fired, intro_mode = self.intro_gate.check_and_fire(self.system)
aware_fired, aware_mode = self.aware_gate.check_and_fire(self.system)

if intro_fired:
    # intro section committed via NMDA gate — record in response state
    self.last_intro_commit = {'tick': self.system.tick_count, 'mode_id': intro_mode}
if aware_fired:
    self.last_aware_commit = {'tick': self.system.tick_count, 'mode_id': aware_mode}
```

### 5.4 Tests for Item 5

```
python -c "
from substrate.v7_engine import V7Session
s = V7Session(session_id='test_nmda')

# Converse — should produce intro commits during sensory-quiet phases
for _ in range(10):
    s.converse('cow jumped fence')

# Verify intro section has krimelack entries (actual substrate commits, not labels)
intro = s.system.sections['intro']
assert len(intro.krimelack) > 0, 'NO REAL INTRO COMMITS'

# Verify aware section has commits (second-order — triggered by intro)
aware = s.system.sections['aware']
assert len(aware.krimelack) > 0, 'NO REAL AWARE COMMITS'

# Verify intro commits preceded aware commits (the cascade actually happened)
last_intro = intro.krimelack[-1]['tick']
last_aware = aware.krimelack[-1]['tick']
assert last_aware >= last_intro, 'AWARENESS PRECEDED INTROSPECTION (broken cascade)'

print(f'NMDA OK: intro={len(intro.krimelack)} aware={len(aware.krimelack)}')
"
```

---

## Implementation order

1. Prerequisite: resolve canonical assemblage.py (Joe decision)
2. Item 1 (turn on dormant) — smallest, validates substrate stability
3. Item 5 (NMDA wiring) — completes what was half-built; verify test_five still passes
4. Item 2 (persistence) — once intro/aware are real sections, serialize them too
5. Item 3 (salience + replay) — needs salience field on krimelack which schema needs to support, so do after Item 2
6. Item 4 (bridge v7 ↔ multimodal) — independent of others, can be done in parallel

If anything in 1–3 breaks test_five.py, pause and report — do not press on with later items.

## Capability checks after all five items deployed

After everything is in:

| Capability | Substrate check |
|-----------|-----------------|
| Syntax | test_five.test_syntax PASS (unchanged) |
| Conversation | test_five.test_conversation PASS + bridged emissions surface in multimodal |
| Introspection | intro section krimelack grows with real commits during quiet phases |
| Self-improvement | mode_strength balances LTP (apply_feedback) vs decay (per-tick decay_plasticity), and gamma_self_evo measurably adjusts law_field_weights over a 1000-tick session |
| Awareness | aware section krimelack grows AFTER intro commits, demonstrating the cascade |
| **Plus new:** Mental time travel | quiet_tick produces replay commits whose mode_ids match prior conversation commits, AND mode_bank vectors continue to evolve via the 0.92*old + 0.08*new blending during replay (consolidation) |
| **Plus new:** Persistence | session saved with to_json, reloaded with from_json, conversation continues coherently using prior associations |
| **Plus new:** Cross-substrate | multimodal hear_word_with_senses surfaces winner in v7 listen, v7 emission triggers multimodal senses |

## What this does NOT add

- New sentence templates (the substrate emits via mode commits + phase-gated rhythm, not templates — this remains substrate-native)
- New hand-coded vocabulary (vocab still grows via `lookup_or_install` from inputs)
- Cross-modal recall in v7 assemblage (Item 4 bridges them but recall paths through the v7 ChiAtlas using folded chi would be Item 6 in a later spec)
- Forward projection / future simulation (Item 7 in a later spec — sequence-encoded captures)

## Risks

- Item 1.4 (TOP_DOWN_BOOST > 1.0): may reintroduce the runaway loop. Start at 1.15, drop to 1.08 if needed, revert to 1.0 if unstable.
- Item 1.2 (allow_rewiring): keyhole creation under self_evo may produce unstable connectivity. Watch for commit storms.
- Item 3.2 (replay_tick): the replay evidence projection may interact poorly with existing standing goals from hear_speaker. The check should be: only run replay_tick when no standing goals are active.
- Item 5.3 (NMDA in converse): adds two more gate checks per tick. Should be cheap but watch latency.
