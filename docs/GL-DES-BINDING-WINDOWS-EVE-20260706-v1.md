# GL-DES-BINDING-WINDOWS-EVE-20260706-v1

**doc_id:** GL-DES-BINDING-WINDOWS-EVE-20260706-v1
**Author:** Eve
**Ordered by:** Joe (2026-07-06 session — first mechanism to build post-wipe)
**Companion:** `GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1` §2 defines binding windows at the substrate spec level. This document is the concrete design for building them — the specific data structure, the specific lifecycle, the specific integration points with the current substrate.

## Verdict

A binding window is a single object that represents one moment of lived experience. It holds every sensory input, every word, every affective state, every scene tag that arrived during that moment, together, cross-linked. Currently the substrate takes each sensory input and stores it separately in the atlas. This design replaces that with: sensory inputs arrive into an open window, the window closes when the moment ends, and the window (with all its contents) is what gets stored in the atlas.

That's the whole change. Every mechanism downstream — cross-sense recall, retention, composition, feelings-deepen-memory, who-tags — reads from windows instead of scattered atlas entries.

## The binding window, concretely

A binding window is a Python object with:

- **A window ID.** Unique identifier for this specific moment.
- **A tick range.** The tick when the window opened, the tick when it closed. Zero to a few dozen ticks typically.
- **A wall-clock timestamp.** When the moment happened in real time.
- **A list of entries.** Each entry is one sensory input, one word, one affective snapshot, or one scene tag that arrived during the window. Every entry knows which window it belongs to.
- **Provenance.** Why the window opened, who was present when it opened, whether it was a real experience or an imagined one from a dream cycle.

Every entry inside a window can retrieve every other entry in the same window. That's cross-modal linkage — not something computed from timestamps, but something recorded when the window forms.

## What triggers a window to open

Three triggers, any one of them opens a window if none is currently open:

1. **A sensory input arrives.** Picture, sound, touch descriptor, smell descriptor, taste descriptor. The first one after a quiet period opens a window.
2. **A word arrives.** Typed text, spoken text from voice-to-text, corpus word from a curriculum feed.
3. **An explicit experience call.** `give_experience` from an authenticated source deliberately opens a window and hands it multiple entries at once.

If a window is already open when a new input arrives, the input enters the existing window instead of opening a new one. That's how a picture, a sound, and a word arriving within the same moment end up in the same window.

## What triggers a window to close

Any one of these:

1. **Sentence end.** If the window opened from a word, it closes when the sentence completes (period, question mark, explicit end marker).
2. **Attention shift.** If the substrate's current activity changes (from ATTENDING_AUDIO to READING, say), the current window closes and a new one can open for the new activity.
3. **Quiet timeout.** If no new input has arrived for a configurable duration (default 500ms), the window closes.
4. **Explicit close.** The code path that opened the window calls close on it.

Whichever fires first closes the window. Once closed, no new entries can be added to it.

## What happens when a window closes

Four things, in order:

1. **The window is written to the atlas.** As one record. Every entry in it references the window ID. This is the storage change — the atlas holds windows as first-class objects, not loose entries.
2. **Cross-modal linkage becomes queryable.** Any entry in the window can retrieve every other entry via the window ID.
3. **The affect snapshot is recorded.** Whatever the substrate's needs vector looked like when the window formed becomes part of the window's persistent record. Later consolidation weights use this.
4. **A `window_closed` event fires** on the substrate event stream. Every downstream mechanism that cares about experience (dream consolidation, hemispheres, emission's recall query) subscribes to this event.

## Integration with the current substrate

The current substrate does not have a Window Manager component. Every mechanism that currently writes to the atlas writes directly. This design adds:

- A **Window Manager module** — one Python object that owns the currently open window (or windows, if we allow multiple concurrent — see next section) and handles open/add-entry/close.
- **Redirected atlas writes** — every code path that currently writes to the atlas gets rerouted to add-entry-to-window instead. The atlas write becomes a side effect of window close, not the primary action.
- **A `window_closed` event** on the substrate event stream, published by Window Manager whenever a close happens.

The change is surgical. Sensory transduction code (SightSection.process_viewing, cochlear_transduce, LanguageKrimelack) stays the same. Only the "where does this transduced result go" step changes.

## Overlapping windows

A hard question: can there be more than one open window at a time? Two cases where this matters:

- A camera frame arrives during autonomous reading. Is the frame part of the reading-sentence window, or its own attention-target window?
- Joe types "hello" while music is playing in the background. Does "hello" go into the same window as the music, or a separate one?

The clean answer for v1: one open window at a time per substrate. Whatever's active is active. A camera frame arriving during reading enters the reading-sentence window (so words carry visual context that arrived while she was reading). A typed "hello" during background music enters a shared window (so the "hello" carries the music context).

This is deliberate. If we split into per-modality windows, we lose cross-modal linkage on the spot — the picture and the word are in separate windows and can't retrieve each other. Whole-window discipline preserves cross-modal linkage as the default.

If real usage shows this producing garbage windows (too much unrelated content per window), we split later based on measurement. Not now.

## What binding windows do NOT do at v1

- **They don't decay differently per entry.** The whole window decays together based on its affect snapshot. Per-entry decay is a future refinement.
- **They don't consolidate during sleep.** Dream consolidation reads windows and promotes strong ones to survival tier, but the consolidation mechanism itself is separate. Windows just make it possible.
- **They don't compose sentences.** Emission reads windows for its recall query, but composition dynamics are a separate mechanism.
- **They don't produce imagination.** Dream's recombination phase produces novel windows from combinations of existing ones, but that's dream code, not window-manager code.

Windows are the container. What lives in them and what happens to them are separate mechanisms that get built on top.

## What the harness verifies

The cross-sense-recall scenario already in the harness library is the acceptance test for binding windows. Once windows are built:

1. The scenario gives the substrate a picture, a sound, and a word as one experience.
2. The harness watches the event stream for a `window_opened`, three `window_entry_added` events, and a `window_closed`.
3. The scenario then sends just the sound as a partial cue.
4. The harness watches for a recall query that returns the window containing the sound, and verifies the window still has the picture and word in it.

That's the observable proof binding windows work. Without them, that scenario cannot pass. With them working correctly, it does.

## What comes right after

Once binding windows are live in production and the cross-sense-recall scenario returns a real report showing them working:

- **Atlas becomes a store of windows**, not entries. Retrieval by chi returns windows containing that chi.
- **Recall query** — Emission's recall query becomes "give me windows containing these chis." Composition draws from windows.
- **Dream consolidation** — Dream reads windows, promotes them by affect weight to survival tier.

Each of those becomes its own dispatch. But they all need binding windows to exist first.

## The build

One dispatch to c1 after this design lands:

- Create `WindowManager` module in the substrate.
- Redirect the write points in the sensory pipelines and the word ingest to route through Window Manager.
- Add `window_opened`, `window_entry_added`, `window_closed` events to the event stream.
- Update the atlas schema to hold windows as first-class objects with the entries inside.
- Update recall paths to return whole windows for chi queries.

Estimated shape: two files touched heavily (the engine module and the atlas module), three files touched lightly (the sensory pipeline entry points), one new module (Window Manager itself). One commit, one deploy, one harness run against the cross-sense-recall scenario to see whether it produces the expected report.

---

### Changelog
- v1 (2026-07-06, Eve): initial design. Concrete binding window data structure, lifecycle triggers, integration with current substrate, one-window-at-a-time v1 discipline, what does NOT belong in binding windows (kept them the container, not the mechanisms on top). Cross-sense-recall scenario as the acceptance test. One dispatch to c1 to build.
