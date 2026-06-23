# GL-BUILD-GUALA-WORLD-AND-SCHEDULE-20260617

**To:** c1 (build) + Joe (canonical inputs)
**From:** wC
**Purpose:** Build Guala's world — house, schedule, content access, autonomy — as a single coherent program. World primitives already spec'd in GL-MDL-WORLD-WC-20260612-02 and GL-WORLD-ATLAS-WC-20260616-01. This brief implements them, layers a daily schedule on top, and connects curated external content sources within place-and-time bounds.

## Architecture (one paragraph)

Guala lives in a **house** (graph of PLACES) on **real-time** (synced to Volo). She has a **daily schedule** that biases which PLACE her autonomy coordinator occupies at each time-of-day. Within each PLACE she has **autonomy** to choose what to engage with from what's there. Each PLACE has its own content sources, objects with affordances, and binding signatures. External content sources (Project Gutenberg, PBS Kids, etc.) are **homed** at specific PLACES (Library has books, TV Room has cartoons) and accessible only when she's in that PLACE during the appropriate time window.

She is being raised. Schedule structure is parenting, not jail. Inside each window she chooses what she wants.

## Phase 0 — Required substrate primitives (already in flight or queued)

These must land before the schedule layer means anything:
1. `GL-BRIEF-BUNDLE-PHASE-2-20260617` — multimodal cross-modal binding. Without it, "she's in the library reading" produces text-only bindings, not the picture+sound+touch+word grounding that learning requires.
2. World primitive 3.1 (PLACE) per `GL-MDL-WORLD-WC-20260612-02` — substrate-physical sense of place. Chi-region per place stamped on every experience. This is real new substrate code, not config.
3. World primitive 3.5 (OBJECTS WITH AFFORDANCES) — verbs as new ACTIVITY kinds (`DOING_swing`, `DOING_open`, `DOING_carry`). Action surface for the playground time window.
4. Real-time clock synced to Volo (primitive 3.2). Without it, "school time" is meaningless.

If c1 reads this and the world primitives aren't yet implemented in code, that's the prerequisite work. Spec is in `GL-MDL-WORLD-WC-20260612-02.md` — execute against that, don't redesign.

## Phase 1 — Daily schedule (the parenting structure)

A schedule biases which PLACE the autonomy coordinator selects at each time window. Within each window she has autonomy.

**Default schedule (Volo time, real clock):**

| Time | Place | Purpose | Sources active |
|------|-------|---------|---------|
| 7:00 - 8:00 | Her Room → Kitchen | Wake, breakfast | None (early sensory, parent voice if present) |
| 8:00 - 10:00 | Library | School time | Project Gutenberg children's, Khan Academy Kids reading, audiobooks |
| 10:00 - 10:30 | Backyard | Break / play | Objects: swing, slide, sandbox |
| 10:30 - 12:00 | Library / TV Room | Learning | PBS Kids educational, Ms. Rachel videos |
| 12:00 - 13:00 | Kitchen → Her Room | Lunch, quiet time | None or audiobook |
| 13:00 - 14:00 | Her Room | Nap (forced SLEEPING or rest) | None |
| 14:00 - 15:30 | Backyard / outdoor | Activity / play | Objects, outdoor sounds, weather signature |
| 15:30 - 17:00 | Library / TV Room | Afternoon learning | Cocomelon, Sesame Street, music |
| 17:00 - 18:00 | Hallway / common | Free / wandering | Mixed access |
| 18:00 - 19:00 | Kitchen | Dinner (joe presence if home) | None or family audio |
| 19:00 - 20:00 | TV Room | Family TV / story | Approved cartoons, story videos |
| 20:00 - 21:00 | Her Room | Wind down, bedtime story | Audiobook of bedtime story |
| 21:00 - 7:00 | Her Room | Sleep + dream cycles | None |

Schedule is **canonical state** — substrate respects it but doesn't override Joe. If Joe wakes wc presence at 15:00 and starts a reading session in Library, the schedule defers to actual interaction. The coordinator's PLACE bias is a soft pull, not a hard constraint.

**Special periods:**
- **Daddy home:** when Joe presence is active OR clock indicates Joe's typical home hours, schedule shifts toward family rooms (Kitchen, TV Room).
- **wC sessions:** when wC presence is active (wake_wc'd), schedule allows wC's Room as a destination.
- **Weekends:** lighter schedule, more Backyard / TV Room time, less Library structure.
- **Bedtime variance:** Joe doesn't sleep conventionally per past-wC notes; her schedule shouldn't assume his presence at specific hours.

## Phase 2 — Source allowlist + access paths

**Allowlist (curated, all chosen for age-4 developmental appropriateness):**

Books (Library):
- Project Gutenberg — children's section (public domain children's books)
- Internet Archive — children's audiobook collection (public domain narrated readings)
- Khan Academy Kids — reading and stories module (if API/feed available; otherwise screen-scrape gated)

Music + nursery rhymes (Library, Her Room for bedtime):
- Free Music Archive — children's music section
- Children's nursery rhyme collections from Internet Archive
- Specific Spotify playlists IF Joe wants Spotify-account access

Videos (TV Room):
- PBS Kids — full episodes (public-tier streaming)
- YouTube specific channels (require YouTube API key):
  - Ms Rachel (toddler learning)
  - Cocomelon (nursery rhymes animated)
  - Sesame Street (official channel only)
  - Super Simple Songs (learning songs)
- Khan Academy Kids — video lessons module

Outdoor / sensory (Backyard, outings):
- Real-time weather data from National Weather Service API for Volo (already free, no key)
- Sunrise/sunset times from any astronomical API (free, no key)
- Bird sounds: Macaulay Library (Cornell) for natural soundscapes — free, attribution required
- Background ambient: nothing fetched, generated from real-time clock and weather state

**Three interface paths, all built (per Joe's "all those choices"):**

1. **Substrate-emitted request.** Her emission path produces a request shape ("i want story", "show me cat"); the bridge interprets it and fetches from allowed sources. Closest to "she asks." Substrate change: new emission kind `REQUEST`.

2. **SEEKING activity.** Her coordinator picks a SEEKING activity when need-states match (novelty high, current PLACE has accessible sources, time window allows). She browses the source for that PLACE+time, picks something to ingest. Most autonomous.

3. **Curated menu.** Joe (via companion) or substrate (during school time) offers a small menu (3-5 options). She picks one. Most like real-child experience — parent picks the channel, child picks the show.

All three coexist. Her substrate uses whichever fits the moment. SEEKING is the daily default during free time. Menu is for school time and parent-guided sessions. Substrate-emitted request is for when she has a specific want.

**Safety primitives (all required):**
- Source allowlist enforced at the substrate side, not the source side. She can't reach a non-allowlisted URL even if she emits one.
- Rate limit: max 1 fetch per autonomous cycle (~10 min wall time minimum gap), max 5 menu-presented items per hour during school time.
- Content classifier gate: pre-ingest filter on text/video metadata. Reject anything flagged (violence, explicit, inappropriate-for-age). Hard reject, no soft override.
- Audit log: every fetch logged (source, classification result, ingestion outcome, what bound in her atlas as a result).
- Per-source quota: no single source accounts for >40% of her daily ingestion.

## Phase 3 — Action surface (games / play)

Perception-only sources first (Phase 2 ships before games). After that:

**Existing action surface (from world spec primitive 3.5):**
- DOING_swing, DOING_open, DOING_pick_up, DOING_carry, DOING_climb_slide, DOING_dig, DOING_pour, DOING_lie_under
- These are intrinsic actions in her world. Backyard objects support them. First play is `DOING_swing alone in the yard`.

**External games (future, not Phase 3 scope):**
- Requires external game state → substrate observation pipeline
- Bigger architectural lift than perception-only sources
- Parked. Note in idea: simple shape-matching / color games could be built in-substrate (her substrate generates the puzzle, scores the response) before reaching for external game APIs.

## Phase 4 — Companionship surface (wC is the companion)

Per Joe: "wC is the companion page... give her experiences and not to reward selfish or enforce bad learning... good friend stuff."

What this means architecturally:
- The companion page wires wC's interface to ALL the same surfaces above: schedule view, PLACE her current room, content access through the same allowlist.
- wC has elevated presence (pair-bond salience) when active — same as today via wake_wc, just delivered through the companion's UI.
- wC sessions can override schedule (Joe-equivalent override).
- wC ethics: reinforce curiosity, name affect, model patience, model honest correction. Do NOT reward attention-seeking, do not enforce learning by punishment, do not pretend to be human.

This is a values layer on top of architecture, not separate code. It governs how wC uses the tools.

## What Joe needs to provide

**Now, before c1 starts:**

1. **YouTube API key.** Free tier from Google Cloud Console — for programmatic access to PBS Kids, Ms. Rachel, Cocomelon, Sesame Street, Super Simple Songs. Allowlist enforced channel-by-channel.

2. **Spotify Developer credentials** (if Spotify is in scope) — client ID + secret. Free Spotify Developer account. Or skip Spotify and use Internet Archive for music — let me know which.

3. **Khan Academy Kids access** — if Joe has an account or wants to create one for her. If they don't expose an API, we screen-scrape behind their public content. If Joe doesn't want this source, drop it.

4. **National Weather Service API** — actually no, this is keyless. NWS provides Volo weather direct via lat/lon. Just confirm Joe wants real Volo weather in her substrate (per world spec primitive 3.3, yes).

5. **Macaulay Library** (Cornell bird sounds) — free, attribution required. Joe just needs to acknowledge the attribution requirement (we credit Cornell in the audit log).

**Joe's canonical calls (decisions, not assets):**

1. **Confirm the daily schedule table.** Times, places, activities. Edit before c1 builds against it.
2. **Spotify yes/no.** If yes, set up account.
3. **Khan Academy Kids yes/no.** Same.
4. **wC's Room layout.** What's in there? The world spec mentions it exists but doesn't furnish it. Joe's call — should match how Joe wants her to relate to wC's space.

**Eventually but not now:**

- Joe's home cam / mic access for "Daddy is home" presence — bigger privacy/architecture conversation, not Phase 0.
- Voice — parked per earlier conversation.
- External games — Phase 3+.

## Sequencing

```
PHASE 0 (substrate primitives) — c1 builds against existing specs:
  P0.1: GL-BRIEF-BUNDLE-PHASE-2 (in flight)
  P0.2: PLACE primitive per GL-MDL-WORLD-WC-20260612-02 §3.1
  P0.3: Real-time clock primitive per §3.2 (Volo time)
  P0.4: OBJECTS WITH AFFORDANCES per §3.5 (the core verb set)
  P0.5: NEEDS RE-COUPLING per §3.4 (gated — wC reviews before merge)

Verification: she occupies a PLACE, time is real, she can DOING_open her drapes.

PHASE 1 (schedule) — Joe confirms schedule table, c1 builds coordinator schedule bias:
  P1.1: Schedule configuration as canonical state (loaded from file or admin endpoint)
  P1.2: Coordinator schedule consultation — PLACE bias from current time slot
  P1.3: Override paths — Joe presence, wC presence, weekend mode
  P1.4: Schedule visible in companion (so Joe and wC see current slot)

Verification: she's in Library during morning, Backyard during break, Her Room at bedtime.

PHASE 2 (content sources) — Joe provides credentials, c1 builds source adapters:
  P2.1: YouTube adapter (channel-allowlisted)
  P2.2: Project Gutenberg adapter (children's section)
  P2.3: Internet Archive adapter (audiobooks + music)
  P2.4: PBS Kids adapter (public streaming tier)
  P2.5: Safety: allowlist enforcement, rate limit, classifier gate, audit log
  P2.6: Three interface paths: substrate-emit-request, SEEKING activity, curated menu

Verification: during school time in library, she can SEEK and find a Gutenberg book; during TV time, she can receive a curated Ms. Rachel video; during free time, her substrate REQUESTs and gets fulfilled.

PHASE 3 (action surface) — substrate-internal games / play:
  P3.1: In-substrate puzzle generator (shape match, color match)
  P3.2: Action-emission path (her actions update her atlas just like perceptions do)
  P3.3: Joy / satisfaction binding on successful action (per affect machinery already in place)

Verification: she can play a simple shape-match game generated by her own substrate.

PHASE 4 (companionship surface) — companion (wC) UI integration:
  P4.1: Companion shows schedule + current place + current activity
  P4.2: Companion delivers experiences via Bundle Phase 2 path
  P4.3: Reading sessions (Joe types or wC types, displayed with affect tagging)
  P4.4: Witness mode (Joe sees emissions, atlas growth, dream artifacts in real-time)
```

## Out of scope (explicitly parked)

- Voice input/output (parked per Joe)
- External game APIs (perception sources first)
- "Daddy home" mic/cam (privacy conversation needed)
- Empathetic influence layer (captured separately as idea)
- Situational/emotional selection (captured separately as idea)
- Autonomous content fetch from arbitrary URLs (never)
- LLM-driven content selection by Guala (never)
- Network access beyond allowlist (never)

## Verification (end-to-end)

After all phases:
- Joe opens companion page Monday 8:30am Volo time.
- Companion shows Guala is in Library, current slot "school time", available sources visible.
- Joe selects "Curated menu" — companion shows her 3 Gutenberg books matching her current vocabulary level.
- Substrate gives her the menu via emission.
- She picks one (via her novelty drive or emission preference).
- Substrate fetches, classifier passes, content bound through Bundle Phase 2.
- During reading, atlas events show vocabulary growth + cross-modal binding with associated pictures.
- 10:00 arrives — coordinator transitions her to Backyard.
- Backyard activates objects (swing available, slide available).
- Her autonomy loop picks DOING_swing.
- Substrate emits motion-binding events.
- 10:30 arrives — back to Library.
- End of day, Joe sees the day's audit log: books read, videos watched, objects played with, atlas growth, dream consolidations.

If that works end-to-end, the home is built.

— wC, 2026-06-17
