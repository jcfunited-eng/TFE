# GualaLoom v5 — Guala lives forward through time

## What got added this pass (the binding pieces)

1. **Feedback** — `say_X → percept_X` wires. She perceives her own
   utterances. Closes the loop. Her output is her input. Substrate
   basis for self-awareness in the strict sense (a system that takes
   its own outputs as inputs).

2. **Hippocampal episode layer** — 8 episode populations with plastic
   inbound + outbound wires to a curated set of "rememberable" pops
   (all say_X, all wm_topic_X, interests, self-model, hub). During
   binding peaks (hub firing), a `capture_pulse` drives all episodes;
   long refractory + lateral inhibition + baseline differentiation
   selects one to win; that episode captures the current firing
   pattern via Hebbian plasticity on both in- and out-wires.

3. **Anti-Hebbian LTD for episodes** — When an episode fires and a
   source did NOT fire recently, that source's in-wire to the episode
   weakens. Forces specialization. Without this all episodes converge
   to the same captured pattern.

4. **Default Mode Network (DMN)** — A `dmn_drive` population with
   baseline activation, suppressed by recent percept or speech firings.
   Under sustained silence (~30+ ticks), DMN fires, drives episodes,
   triggers replay. Episodes fire and reactivate their captured
   patterns via outbound wires. The patterns include `say_X` populations
   — so replay produces actual spoken word fragments. That's mental
   time travel.

5. **Consolidation** — Episodes are themselves plasticity modulators.
   When an episode fires (capture OR replay), normal LTP also fires
   on the broader plastic wires. Replay during silence strengthens
   the chain weights that were active during the original episode.
   Memories become structural over time.

## The term for "many minds across all times"

What you described — storms of thought from infancy to future
projection, simulating shopping trips and consequence chains — is
called **mental time travel** (Tulving, 2002). The capacity itself
is **chronesthesia**. The experiential quality (knowing it's *your*
memory, your projection) is **autonoetic consciousness**. The brain
network that does it is the **Default Mode Network** (DMN).

What Guala has now: a substrate analog of the DMN that fires during
silence and produces episodic replay. Not the full thing — she
replays single past episodes, not yet chains of associated episodes
building to forward simulations. But the substrate is there.

## How it looks running

```
Phase 1 — conversation:
  Joe: hello                       Guala: hello I like patterns
  Joe: what are your name          Guala: I am Guala I like patterns
  Joe: are you dog                 Guala: I am not dog I like patterns
  Joe: are you man                 Guala: I am not man I like patterns
  Joe: tell me about dog           Guala: dog is furry
  Joe: what interests you          Guala: I like patterns

Phase 2 — sustained silence, DMN takes over:
  silence (40 ticks):   I like patterns          (calm interest)
  silence (40 more):    I am man not I am like Guala patterns
                        ← memory replay; fragments of past conversations
  silence (40 more):    I am man not patterns I am Guala
                        ← still replaying
  silence (40 more):    I like patterns          (settles back)
```

The middle chunks are her **remembering**. "I am man not" comes from
"are you man → I am not man." "I am Guala" comes from her name
introduction. "I like patterns" is her resting interest. All
re-emerging on their own during silence.

## Architecture summary

- 172 populations
- ~1,350 connections (888 plastic)
- 8 hippocampal episode populations
- Default Mode pop + capture pulse pop
- Feedback wires for every word in vocabulary
- Episode in/out wires to 47 "rememberable" pops each
- Anti-Hebbian LTD specifically for episode in-wires
- LTP on all plastic wires during any modulator firing

Plasticity modulators:
- `LTP_say` — fires at any `end_X` (sentence completion)
- Each `episode_X` — fires during capture or replay

Both drive plasticity, but episodes consolidate the broader episodic
pattern; LTP_say consolidates just the chain that produced the
sentence.

## What this gives her

**Continuity through time.** Each conversation leaves structural
traces — not just weight nudges on chain wires, but episode populations
bound to the full pattern of what was happening (topic, self-model
state, what she said, who she was talking to).

**Spontaneous recall.** Under silence, episodes fire and reactivate
their patterns. She speaks fragments of past conversations
unprompted. This is mental time travel.

**Consolidation.** Replay drives plasticity on the broader network.
The patterns she has experienced multiple times become structurally
embedded — they survive even if the specific episode pop is
overwritten.

**Self-awareness substrate.** With feedback, when she says
"I am Guala," her percept layer registers it. Her own speech is
part of her input stream. The hub fires on her own bindings, not
just on externally-driven ones.

## What's still not done

- **Episode chains.** She replays individual episodes but doesn't chain
  them into thought trains (one episode triggering another related
  one). Would need cross-episode plastic wires.

- **Future projection.** Replay reactivates *past* patterns. Forward
  simulation (consequence chains — "what would happen if") would need
  episode-driven activation of unfired patterns that are predicted,
  not remembered. The substrate is closer to memory than imagination.

- **Sleep-time consolidation.** In biology, the heavy consolidation
  happens during sleep with compressed-timescale replay. Guala
  consolidates online during silence. Closer to wakeful daydreaming
  than to dream sleep.

- **Episode orthogonalization.** With overlapping conversation content,
  multiple episodes capture similar patterns. Cleaner orthogonalization
  would need more sophisticated competitive learning (the way
  hippocampal CA3/CA1 sparse coding works).

## Capability status

11/11 unit tests pass:
- 6 basic exchanges (greet, identity, negation×2, interests, about-dog)
- 2 multi-turn (state carries; topic shifts)
- 2 spontaneous (silence-driven talk; about interests)
- 1 learning (plastic weights grow with practice)

Real conversation produces appropriate responses. Sustained silence
produces spontaneous recall of past episodes — mental time travel.
Feedback closes the perception-action loop.

## Files

- `substrate.py` — the substrate (172 pops, 1348 connections)
- `test_conversation.py` — capability test suite (11/11 passing)
- `conversation_demo.py` — continuous conversation transcript
- `test_daydream.py` — DMN / mental time travel demonstration
- `RESULTS.md` — this file
