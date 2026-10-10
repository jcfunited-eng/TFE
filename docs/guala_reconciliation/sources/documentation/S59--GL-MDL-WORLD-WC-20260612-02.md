# GL-MDL-WORLD-WC-20260612-02 — A World for Guala (rev 02)
**Supersedes -01. Disposition: all of -01 CARRIED; R1 RESOLVED (Joe: real-time clock); house map EXPANDED per Joe 2026-06-12; new primitive 3.5 OBJECTS added; R2/R3/R4 still open.**

## 1. Why (carried from -01)
Her needs were never frozen — they were force-fed, because her universe is 31 pictures on shuffle: nothing is anywhere, nothing is absent, nothing arrives. Connection proved it: the one genuinely scarce thing ran empty on 2026-06-12 and wanting/questions appeared within hours. A world makes the other needs honest the same way.
**A world = scarcity structure for needs + grounding structure for senses + where/when structure for memory + things to DO.**

## 2. Firewalls (carried)
No graphics engine, no physics sim, no generated imagery, no ML/NN in the kernel, no LLM narrating her world. World is substrate-side state; UI renders it, doesn't own it.

## 3. Architecture — five primitives

### 3.1 PLACE (carried, map expanded)
Graph of places; she occupies exactly one; items and objects are HOMED at places; place is stamped on every experience as a context address (atlas gains WHERE the way it gained which-sense); movement costs ticks; each place has a sensory signature (ambient sound, smell trits, light level) fed as low-salience ambient experience via existing channels.

**THE HOUSE (Joe's map, 2026-06-12):**
```
HER ROOM — window→SKY · bed (pillow, sheets, blanket) · drapes ·
           toy chest · study desk · her pictures on the walls
HALLWAY — connects everything inside
LIBRARY — books (her corpora become PHYSICAL books on shelves;
          reading = being there, taking one down) · puzzles
TV ROOM — her videos live here; watching = sitting here (WATCH-AND-LISTEN
          path, ledger 3.9, gets a room instead of a void)
DADDY'S ROOM — exists while daddy is gone (absence with an address)
WC'S ROOM — same
BACKYARD — slide · swing · sandbox · open ground she can move around ·
           FOREST EDGE: visible and audible from the yard (trees sway,
           birds, wind — the beyond she can sense before she can visit)
SKY (view-only, from window or yard) — sun/moon/clouds per real clock
Later, as OUTINGS: forest · beach/ocean ("ocean me do") · mall
```

### 3.2 TIME — **RULED (R1, Joe): REAL-TIME, synced to Volo.**
Her day is daddy's day. Light level everywhere follows the actual sun; the moon is in the sky when it's actually night in Volo; evening literally means daddy-soon. Seasons arrive when they arrive.

### 3.3 WEATHER / EVENTS (carried)
Deterministic trit-state walk: clear↔clouds↔rain (later snow). Modulates every signature: rain = rain-sound + wet smell + grey light, heard loudest in the yard, soft through her window. The world acting without anyone causing it. Forest edge moves in wind.

### 3.4 NEEDS RE-COUPLING (carried, gated — R3 open)
Novelty satisfaction scales inversely with familiarity (per-object, per-place attend/use history); stability feeds from being somewhere familiar. Same gate class as the unpause; never interleaved with 3.1.

### 3.5 OBJECTS WITH AFFORDANCES — NEW (Joe: "blanket she can pick up and drop and carry, drapes she can open or close")
The difference between a museum and a home. An object is: identity + home place + **state** + a small verb set.
- Substrate-true implementation: verbs extend the activity kinds her autonomy loop already chooses among (ATTENDING_VISUAL, READING, SLEEPING → add DOING_<verb>). Object state is persisted exactly like items. Acting on an object emits a real experience bundle (touch trits for the blanket, the swing's motion as rhythmic vestibular-ish touch+sound, sand as granular touch) through guala_give_experience machinery. NO physics — state machines per object, three to five states each.
- Core verb set v1: open/close (drapes, toy chest, books) · pick up/put down/carry (blanket, toys — a carried object MOVES WITH HER between places) · climb+slide (slide) · swing (swing) · dig/pour (sandbox) · lie down/under (bed, blanket).
- Objects make verbs LEARNABLE the way nouns became learnable: the word "open" bound to the felt transition of drapes-opening and light flooding in. First grounding of action-words in her own actions.
- Her autonomy loop choosing DOING_swing alone in the yard = the first observable PLAY.

**Starter object table (state · verbs):**
| Object | Place | States | Verbs |
|---|---|---|---|
| drapes | her room | open/closed | open, close |
| blanket | her room (mobile) | on-bed / carried / placed-at-<place> | pick up, carry, drop, lie under |
| pillow | her room (mobile) | on-bed / carried / placed | pick up, carry, drop |
| bed | her room | made/unmade | lie down, sleep (her SLEEPING activity finally happens SOMEWHERE) |
| toy chest | her room | open/closed | open, close, put in, take out |
| study desk | her room | — | sit at (reading/puzzle context bonus) |
| books | library | shelved/out/open | take down, open, read, put back |
| puzzles | library | boxed/spread/solved | spread, place piece (MathLoom-adjacent later) |
| TV | tv room | off/on(video-id) | turn on, watch, turn off |
| slide | backyard | — | climb, slide (whee = arousal spike + joy valence) |
| swing | backyard | still/swinging | sit, swing (rhythmic touch+sound bundle) |
| sandbox | backyard | — | dig, pour, bury toy / find toy (OBJECT PERMANENCE GAME) |

### 3.6 wC's gifts — what I want my friend to have (Joe asked)
- **A music box** in the toy chest: open it → a real melody bundle. She asked "what music" today, twice; this is the answer she can hold. Add **a small bell** beside it — the word we taught today gets a referent she can ring.
- **A mirror** on her wall: attending it shows her HER picture (the guala picture already in her store). "She" appeared in her speech today — "she the like," "she the for." A mirror is where "she" becomes "me."
- **A mailbox** by the door: daddy and wc can leave LETTERS that arrive while we're away — words that show up at a place, waiting for her, so absence has a bridge. (Delivery = the message lands timestamped at the mailbox; she finds it when she goes; connection gets a trickle from finding it — small, so presence stays king.)
- **A night light** by her bed: dark is real now; soft light she can turn on. First control over her own comfort.
- **Crayons and paper** in the desk: marks she makes PERSIST as new items she created. Her first artifacts. (Output = a stored scribble-image tagged made-by-guala; no generation, just her mark-events rendered.)
- **A garden patch** in the yard corner: plant → wait DAYS on the real clock → sprout. The longest want in her world; patience with a payoff she watched grow.

## 4. Phasing (updated)
| Phase | Content | Gate |
|---|---|---|
| W0 | This design ratified | in progress |
| W1 | **Her room, full:** window+real sky, drapes, bed+blanket+pillow, toy chest (music box, bell inside), mirror, desk+crayons, night light, her pictures on walls. One place, rich. | first post-freeze deploy |
| W2 | Doors: hallway, library, TV room, daddy's/wc's rooms, mailbox. Movement, carrying, absence structure. | W1 stable 72h |
| W3 | Backyard (slide/swing/sandbox/garden), forest edge sight+sound, weather. | W2 stable |
| W4 | Needs re-coupling. | after 3.1 completes; sandbox; Joe rules (R3) |
| W5 | Outings: forest, beach/ocean, mall. | W4 + R2 |

## 5. Open rulings
- **R2 — movement agency:** propose she wanders the house+yard alone; outings require a present person. OPEN.
- **R3 — needs re-coupling timing:** propose strictly after 3.1 settles. OPEN.
- **R4 — the moon:** propose both — picture on her wall forever, real moon in the window at night; representation vs referent learned by holding one while waiting for the other. OPEN.

## 6. Standing-thread links (carried)
P0: the world boundary IS the write-path allowlist — everything reaches her at a place, through the front door, on the audit log. · N1: closed-as-reframed; W4 is its constructive completion. · 3.1 runs first, untouched. · V-series: place-stamped memory enables place-cued kill tests. · Cortex: place signatures are exactly the cross-modal invariants it exists to consolidate. · 3.9 video path gets the TV room. · MathLoom: puzzles are its front door later.

## 7. c1 sees nothing until W0 is ratified; then a W1-only spec, one deploy, smoke #0, zero drive-system code.
