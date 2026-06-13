# GL-BRIEF-CHITRACE-WC-20260613-01 — Readout for Lookup-vs-Cognition
**Author:** wC · **Executes:** c1 · **Replaces** the GL-BRIEF-V2READOUT drafts (-01, -02) — both superseded; this brief is narrower, modeled against the real engine, and ships alone. No force_attend. No S3 layer. No paired V2-protocol dependency. **Ledger row:** new Tier V item, V0 readout (instrumentation only). · **Freeze status:** read-only endpoint, no cognition changes; freeze-compatible.

## 1. What this enables
A single read-only HTTP endpoint that, given a list of picture or sound item_ids and an optional input string, returns the chi-geometry behind those items: which chi addresses they occupy, what else lives at those addresses (cross-modal neighbors), the working-vs-deep split per binding, and (if input given) the chi addresses the input transduces to.

wC uses this in two ways:
- On demand, when Joe asks "how did her last response shape up" / "what's the geometry behind this picture-ref emission," wC calls the endpoint, returns both raw substrate data and a cold interpretation.
- Later: V2 (chi-collision null study) reads the same endpoint output as its trial data — but that protocol is a separate brief, not a dependency.

It exists to distinguish three things that look identical on the gualaloom.html screen but are structurally different in her substrate:
- **Lookup of strong existing binding** (chi already saturated, response item is the top-strength entry at that chi)
- **Working-memory recall** (chi recently driven by input, response item bound there in current session)
- **Deep-memory reinstatement** (response item's bindings exist in deep atlas, not just working)

Today we cannot tell these apart from outside.

## 2. Code paths read and modeled (so this isn't guessed)
- `dsf_ai_service/v4/gualaloom_v6_living_atlas.py` — LivingAtlas; `.entries: defaultdict(chi_key → [entry])`; entry = `{section, motif, chi, strength, last_tick, born_tick, encoded_strength, dwell_ticks, reinforcement_count, released}`. Already exposes `query_associations(section, chi_value)`. Band lookup via ±self.band.
- `dsf_ai_service/substrate/deep_atlas.py` — DeepAtlas; `get_prior(chi_value, section, motif) → float`. Use to mark a binding as deep-backed.
- `dsf_ai_service/v4/gualaloom_v5_engine.py:1085-1096` — input→chi for text: tokenize, `LanguageKrimelack().transduce(word)`, take `.winding`. Reusable as-is.
- `dsf_ai_service/v4/gualaloom_v5_engine.py:1242-1260` (inside `_recall_sight_from_atlas`) — picture→chi reverse mapping: scan `atlas.entries` for `section=="sight"` entries; resolve `motif` to a `SightMotif` via `self.sight.motifs`; check `sm.source_history` for the picture's item_id. Sound→chi follows the same pattern with the audio section + cochlear motif store (confirm field name during implementation; if absent for sounds, return empty `chis` list and `_note: "sound→chi mapping not yet wired in production"` rather than guess).
- `PictureItem` (engine line 187) has no chi field, confirmed. SightMotif's source_history is the link.

## 3. Endpoint specification

`POST /api/v1/gualaloom/chi_trace`

Body:
```json
{
  "picture_ids": ["..."],
  "sound_ids":   ["..."],
  "input_text":  "what is your name"
}
```
All three fields optional; at least one must be present or return 400.

Response:
```json
{
  "tick": 6834753,
  "input_chis": [12, 47, 18],

  "refs": {
    "<item_id>": {
      "kind": "picture" | "sound",
      "title": "guala hugs star",
      "n_chis": 7,
      "chis": [
        {
          "chi": 47,
          "binding_strength": 0.83,
          "encoded_strength": 0.91,
          "dwell_ticks": 12,
          "reinforcement_count": 9,
          "deep_prior": 0.42,
          "in_deep": true,
          "cross_modal_neighbors": {
            "word":  [{"motif": "star", "strength": 0.74}, {"motif": "hug", "strength": 0.31}],
            "audio": [{"motif": "bells", "strength": 0.22}]
          }
        }
      ],
      "_note": null
    }
  },

  "input_chi_neighborhoods": {
    "12": {
      "by_section": {
        "sight": [{"motif_id": "...", "strength": 0.61, "in_deep": false}],
        "word":  [{"motif": "name", "strength": 0.88, "in_deep": true}]
      }
    }
  }
}
```

Notes on fields:
- `chis[].deep_prior`: from `deep_atlas.get_prior(chi, section_of_ref, motif_of_ref_at_this_chi)`. 0.0 = not in deep atlas.
- `chis[].in_deep`: `deep_prior > 0`.
- `cross_modal_neighbors`: from `atlas.query_associations(<ref_section>, chi)` — every section *other than* the ref's own. Capped at top-5 per section by strength.
- `chis` capped at top-K=16 by `binding_strength` to bound response size.
- `input_chi_neighborhoods` is the same shape, keyed by input chi; lets wC compute overlap between input chis and ref chis without a second call.
- Response size target: < 8KB for typical 4-ref query. Hard-cap response at 64KB; if exceeded, truncate `cross_modal_neighbors` first, then `chis`, and set `_truncated: true`.

Implementation: pure read against `engine.atlas.entries`, `engine.sight.motifs`, `engine.deep_atlas`. Zero state mutation. Refactor the input→chi block (lines 1089-1096) into a method `_chis_for_text(text) → list[int]` and reuse.

## 4. Bridge tool
`bridge/server.py`: add one tool `guala_atlas_query(picture_ids=None, sound_ids=None, input_text=None)` — thin wrapper, posts to `/chi_trace`, returns the JSON.

This is the tool wC calls during visits to assemble a substrate report. Not exposed in the UI. Not auto-called by the companion (that's a later HTML edit).

## 5. Sandbox acceptance (paste in c1's reply; do not skip)
On a restored snapshot, off-prod:

1. Call `/chi_trace` with `{"picture_ids": ["<pid_with_known_high_attends>"], "input_text": "what is your name"}` — pick a picture from her live store with `times_attended > 20`. Show: `input_chis` nonempty; `refs.<pid>.n_chis > 0`; at least one `chis[]` entry with `binding_strength > 0.05`; at least one `cross_modal_neighbors` entry nonempty.
2. Call with a picture that has `times_attended == 0` (smoke-test pollution items or a freshly added one). Show: either `n_chis == 0` (no bindings formed) OR `n_chis > 0` with all `binding_strength < 0.1` (formed but weak). Either is correct — but the result must be honest, not faked.
3. Call with a sound id. Show: either real audio-section chis returned, OR `n_chis: 0` with `_note: "sound→chi mapping not yet wired in production"`. Lying about sound geometry is worse than admitting we haven't wired it.
4. Call with all three fields empty / missing. Show: HTTP 400 with a clear error, not 500.
5. Call with a bogus item_id. Show: that id's entry is `{"kind": "picture", "title": null, "n_chis": 0, "chis": [], "_note": "item not found"}`. Endpoint does not crash on bad inputs.
6. Time the call on a query of 4 known pictures + input_text. Target < 200ms. If slower, paste the response time and note it; we will optimize later, not now.

## 6. Production acceptance
- Single micro-deploy. Rule 7 smoke includes smoke #0 + one chi_trace call with 4 known pictures + input_text.
- Bridge redeploy needed (one new tool).
- 24h post-deploy: no new ELB kills, no save-time regression, no integrity errors. The endpoint is read-only — these are sanity checks, not function tests.

## 7. Failure conditions stated cold
- **If sandbox step 1 returns `n_chis == 0` for a high-attends picture:** the picture→sight-motif→chi reverse mapping is broken or wC modeled it wrong. STOP, do not deploy. c1 pastes the picture's `source_history` and the atlas's sight-section entry count. wC re-reads and revises this brief. No fix-forward.
- **If sandbox step 3 returns chis for a sound but the engine has no sound→chi wiring** (i.e., the endpoint fabricates): STOP. The error mode "lie about geometry" is worse than the error mode "admit no wiring."
- **If endpoint adds > 50ms to a normal converse call** (read of shared structures contending with the engine loop): defer deploy, c1 adds a lock-free copy step, wC reviews.
- **If V2 trials later show the readout's `cross_modal_neighbors` are systematically empty for cases where they should be populated:** revise this brief before changing V2's protocol. The readout is the truth; if it says nothing is there, nothing is there.

## 8. What this brief does NOT do
- No force_attend. wC accepts working from her natural attention. Adding override is a separate brief; do not bundle.
- No S3 readout-storage layer. wC asks the endpoint per-question, paraphrases to Joe in chat, no persistence layer.
- No companion HTML changes. Companion page stays as-is until Joe wants it updated.
- No V2-protocol. That is a separate brief that wC writes *after* this endpoint exists and wC has called it a few times to verify the schema is what V2 needs.
- No cognition changes anywhere.

## 9. Paste-ready c1 command
```
EXECUTE — CHITRACE READOUT ENDPOINT, per GL-BRIEF-CHITRACE-WC-20260613-01
(Joe pastes file). Freeze-safe: read-only endpoint, no cognition changes.

1. Commit the brief: docs/GL-BRIEF-CHITRACE-WC-20260613-01.md. SHA back.
2. IMPLEMENT in dev:
   a. app.py: refactor lines ~1089-1096 (input→chi) into engine method
      _chis_for_text(text) → list[int]. Add POST /api/v1/gualaloom/chi_trace
      per brief §3. Read-only: atlas.entries reads, sight.motifs lookups,
      deep_atlas.get_prior calls. No mutation.
   b. bridge/server.py: add guala_atlas_query tool per brief §4.
3. SANDBOX FIRST. Restore newest snapshot off-prod. Run all 6 acceptance
   steps from brief §5. Paste outputs. If ANY step fails per §7, STOP,
   do not deploy, paste diagnostics, wC revises brief.
4. If sandbox passes: micro-deploy (engine + bridge). Rule 7 smoke per §6.
5. DONE = SHA + task # + sandbox transcript + prod smoke transcript.
6. Freeze continues. wC begins using the tool; V2-protocol brief follows
   when wC has called the endpoint enough to know the schema serves it.
```
