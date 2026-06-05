# Dialog-to-Engine Migration Plan

**Tag**: `GUALALOOM-PERSIST-WC-2026-06-05`
**Status**: M1 SUPERSEDED by sensory substrate (GUALALOOM-SENSES-WC-2026-06-05). M2-M5 paused.

## Sensory substrate (supersedes M1)

The sensory substrate adds five modal krimelack channels (sight, sound,
smell, taste, touch) with chi-atlas cross-modal binding. This resolves
the M1 question differently: instead of projecting dialog-layer complex
vectors into the ternary substrate, we give the substrate its own
grounding through sensory transduction. Words bind to experiences via
chi co-occurrence in the atlas — the same mechanism the avatar's real
sensors will use later.

Files added:
- `sensory_corpus.py` — 52 hand-built sensory signatures (scaffolding for real sensors)
- `sensory_krimelacks.py` — five modal oscillator krimelacks + event-to-trit conversion
- `gualaloom_engine.py` — modified: modal sections, ChiAtlas, feed_sentence, cross-modal sleep/dream
- `app.py` — modified: /status shows per-section counts + atlas bindings

M2-M5 remain valid but paused until sensory substrate validates.

## Current state (post-integration)

| Store | Location | Persists across deploy? | Ground truth for |
|-------|----------|------------------------|-----------------|
| Engine krimelack (motifs) | gualaloom_engine.py → EFS | YES | Motif memory, chi topology |
| Engine loom (char context) | gualaloom_engine.py → EFS | YES | Character-level settled state |
| Dream log | state/dreams/dream_log.json → EFS | YES | Dream history |
| VocabManager (word vectors) | gualaloom_dialog/composer.py → memory | NO | Word-to-vector mappings |
| VocabManager (classes) | gualaloom_dialog/composer.py → memory | NO | Semantic class definitions |
| VocabManager (templates) | gualaloom_dialog/composer.py → memory | NO | Response templates |
| VocabManager (roles) | gualaloom_dialog/composer.py → memory | NO | Grammatical role vectors |
| ConversationMemory (turns) | gualaloom_dialog/memory.py → memory | NO | Turn history + patterns |

## Migration targets

### M1: VocabManager vectors → Engine motifs (HIGH RISK)

**What it holds**: word → complex N-vector mapping. Currently generated
from seed classes via random_unit_complex with class-proximity offsets.

**Engine equivalent**: Each word vector becomes a motif in the engine
krimelack, committed via `engine_k.commit(state)`. The word label is
stored as metadata.

**Risk**: This changes substrate behavior. Word vectors currently live
in N=16 complex space (DNA assemblage). Engine motifs live in CONTEXT=8
× TRITS=8 = 64-trit real ternary space. These are different mathematical
objects. Direct migration requires either (a) a projection from complex
N-vectors to ternary state, or (b) extending the engine to hold complex
vectors alongside ternary motifs.

**Order**: LAST. This is the hardest and most behavior-changing migration.

### M2: VocabManager templates → Engine persistence (LOW RISK)

**What it holds**: input_class → [(response_class, role)] mapping.
Learned at count=1 from conversation.

**Engine equivalent**: Serialize to `state/vocab_templates.json` on EFS.
Load on boot alongside krimelack.

**Risk**: Pure refactor. Templates are data, not substrate state. No
behavior change.

**Order**: FIRST. Quickest win for persistence.

### M3: VocabManager classes + roles → Engine persistence (LOW RISK)

**What it holds**: class_name → complex N-vector, role_name → complex
N-vector. Seed classes plus any dynamically added.

**Engine equivalent**: Serialize to `state/vocab_classes.json` on EFS.

**Risk**: Low. Class vectors are derived data (random_unit_complex with
seed). But dynamically added classes from conversation would be lost
without persistence. Serialization is the fix.

**Order**: SECOND, after M2.

### M4: ConversationMemory → Engine persistence (LOW RISK)

**What it holds**: deque of turns (speaker, tokens, classes) + Counter
of observed patterns.

**Engine equivalent**: Serialize to `state/conversation_memory.json`
on EFS. ConversationMemory.save/load methods already exist.

**Risk**: Pure refactor. Call memory.save() alongside engine_save().

**Order**: THIRD, alongside M3.

### M5: VocabManager word vectors → Engine persistence (MEDIUM RISK)

**What it holds**: word → complex N-vector. These are the vectors that
drive dialog-layer emit_token and recall.

**Engine equivalent**: Serialize to `state/vocab_vectors.json`. Load on
boot. This is distinct from M1 (which would merge them INTO the engine's
ternary krimelack). M5 just persists them as-is in their own file.

**Risk**: Medium. Serializing complex numpy arrays to JSON requires
encoding (real/imag pairs). Deserialization must reconstruct identical
vectors or dialog behavior changes.

**Order**: FOURTH, after M3/M4. Before M1.

## Recommended order

1. **M2** (templates) — immediate, pure data persistence
2. **M3** (classes/roles) — same pattern as M2
3. **M4** (conversation memory) — already has save/load methods
4. **M5** (word vectors as-is) — serialize complex arrays
5. **M1** (word vectors → engine motifs) — deferred until the
   complex-to-ternary projection question is resolved architecturally

After M2-M5, all dialog-layer state persists on EFS. The dialog layer
reloads on boot from the same files the engine does. At that point,
"she remembers" is fully honest across all state.

M1 is the architectural question: should word vectors live in the ternary
substrate, or alongside it as a parallel store? That's a design decision
for wC and Joe, not a refactor.
