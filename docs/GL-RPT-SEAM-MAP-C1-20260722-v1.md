# GL-RPT-SEAM-MAP-C1-20260722-v1 — Guala Substrate Connectivity Seam Map

**Trigger:** Joe's 2026-07-22 hypothesis: "the connectivity between all the elements has been neglected and maybe that has been causing challenges for this project's success goals."
**Verdict: CONFIRMED.** The elements are individually well-built; the joints between them are the dominant failure class. Every major recent failure maps to a seam defect, and every recent win (auditory causal boundary, cogmeter real-or-gone, chi-index consolidation) was a joint repair.

Method: 3 read-only audit agents over the live-deployed code (SHA c573bea6 at survey time, task :723) + live GET evidence. Classification: CONNECTED-LIVE / HALF-CONNECTED (one direction) / LABEL-BRIDGE (joined by a token/label/cache instead of shared causal identity) / SEVERED (consumer or producer removed, counterpart still active) / NEVER-BUILT.

## Headline finding

**Only heard microphone speech carries true causal identity end-to-end** (`causal-experience:<event_id>` + receipt chain — Sol's fix). Everything else that enters as text — curriculum books, corpus loads, world feeds, tutor teach-backs, uploaded captions, typed conversation — enters the same `read_sentence` door but lands as `language:<source>:<turn>` with label-only provenance. Vision keeps its pixel content but binds it with an id-hash address and string refs (the pre-fix auditory pattern one level up). The label-bridge is the substrate's endemic disease; the auditory fix is the template cure.

## Seam table (condensed; agent transcripts hold full anchors)

| Seam | Class |
|---|---|
| Auditory capture → causal experience | CONNECTED-LIVE (fixed 07-22, task :723) |
| Auditory → organism sound lane | SEVERED — `_last_sound_signal` permanently None (retired cache, consumer still reads); root cause of every `has_sound:false` |
| Visual capture (live camera / audiovisual / local video) | CONNECTED-LIVE (real pixel receipts) |
| Stored-picture attend + captions → language | LABEL-BRIDGE (chi = motif_id % 100, "pic:" string refs, captions read with no causal intake) |
| Vision → emission/grounding | NEVER-BUILT ("no vision tap exists yet" — engine's own comment); pictures surface titles only |
| Curriculum/corpus/worldfeed/tutor text → causal stream | SAME stream, LABEL-BRIDGE provenance; intake was throttled to 1/30 (fixed tonight, bounded backpressure) |
| Tutor gap loop (engine misses → ledger → tutor items) | CONNECTED-LIVE (bidirectional) but emission-starved |
| Organism ← senses | HALF-CONNECTED: 3s wall-clock cache join; in practice text-only (sound severed, sight cache camera-only) |
| Organism → emission | LABEL-BRIDGE via word-string index; population vote echo-dominated at current age |
| Emission: 6 sections + 4 candidate sources | Merged only at vote time in a per-turn scratch assemblage whose mode banks are wiped each call — no single coherence field (spec divergence #1) |
| Working ↔ deep atlas (dream promotion) | CONNECTED-LIVE |
| Wave atlas read side | HALF-CONNECTED (write+decay live; `read_near` has zero callers) |
| Drives/dream/familiarity/affect | CONNECTED-LIVE |
| Virtual world percepts | HALF-CONNECTED (sky/location stamps only) |
| Virtual world ACTIONS | SEVERED twice: actuator lives only in the never-launched :8090 sidecar; live `/action` route posts to the dead port AND has a NameError |
| Organ-brain sidecar | SEVERED; 3 live pollers still poll it; `/organ_brain_status` serves a FABRICATED `{warming:true}` fallback (real-or-gone violation) |
| GLEW runtime | Flag-off dormant as conversation engine; its exact-math primitives ARE live imports (auditory L5, exact causal experience) |
| Voice out + self-hear | CONNECTED-LIVE |
| Dashboards/events | CONNECTED-LIVE (except the fabricated organ-brain fallback; LOOM Scan route 404 — one-liner) |

## Failure→seam attribution (the proof of Joe's hypothesis)

1. Three-week single-word saga → NEVER-BUILT single coherence field (scratch-assemblage vote merge).
2. `has_sound:false` on every experience → SEVERED organism sound lane.
3. Silent replies → compound label-bridge: ungrounded heard words + chi-less candidates + echo-dominated organism vote (all three addressed tonight).
4. Intake collapse 1/30 → over-strict backpressure joint (fixed tonight, bounded).
5. World actions dead → SEVERED sidecar actuator.

## Ranked reconnection queue (post-tonight)

1. ~~Heard-word grounding + candidate chi + intake valve~~ — **done tonight (deploy `7bcffcd4`)**.
2. **Auditory → organism sound lane**: route a bounded reduction of the settled L5 field into `experience_word`'s sound snapshot instead of permanent None. Restores `has_sound`, cross-sense recall. Small, well-scoped, high value.
3. **World actions in-process**: port `WorldState.apply_verb`/`ambient_words` into the live activity loop; delete the three dead pollers and the fabricated status fallback (lean + honesty win). Gives visible autonomy: it acts on its own room.
4. **Vision gets the auditory treatment**: verified visual terminal events (content-derived identity + receipts) for attended pictures; captions read with causal intake. Direct sequel to Sol's pattern; the boundary test suite is the template.
5. **Attention-window co-binding**: while attending a picture/sound, concurrent reads bind into the open attending window — real co-attention grounding without any new store.
6. Wave-atlas read side: either wire `read_near` to a real consumer or retire the store (lean doctrine: no write-only stores).

*(Bridge MCP connector unverifiable from non-interactive sessions — needs OAuth re-auth in claude.ai connector settings; only seam not probed.)*
