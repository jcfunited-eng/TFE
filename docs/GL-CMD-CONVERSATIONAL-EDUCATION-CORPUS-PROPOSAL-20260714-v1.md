# GL-CMD-CONVERSATIONAL-EDUCATION-CORPUS-PROPOSAL-20260714-v1

**doc_id:** GL-CMD-CONVERSATIONAL-EDUCATION-CORPUS-PROPOSAL-20260714-v1
**Date:** 2026-07-14
**Status:** Proposal only — nothing executed, nothing ratified
**Purpose:** Design for Step 8 ("Educate the clean generation") of `GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md` §10. Answers the open decision named in that handoff's §16 item 6 and in `GLEW_LANGUAGE_WEAVE_PROFILE_v1.json`'s `open_decisions_requiring_explicit_ratification`: "clean education source and acceptable seed provenance." This document is itself an input to that ratification, not a substitute for it.
**Scope:** Content/data design only. No code, no schema, no deploy.

---

## 1. The design principle

A scene is taught for its own sake — because it really happened or was honestly emulated. Ordinary conversational language is admitted only when it is a genuine, incidental part of that scene, never manufactured because a reviewer wants "hello" to work. The teacher never supplies an output. Every episode below supplies only an input side: a real or honestly-emulated experience plus whatever real words a real person actually said or typed inside it. What the substrate later says is its own commit, learned through `expression_learning.py`/`commit.py`, never inserted.

## 2. The scripted-vs-lived test

A batch is a **disguised script** if: the same picture/sound is reused across many entries *only* to satisfy `is_multimodal_language_experience`, the captions are paraphrases converging on one intended reply, or a reviewer could reconstruct an input→output table from it. A batch is **lived material** if: the scene would have existed regardless of what got said, the wording varies because different real moments produce different real words, and no output is ever recorded — only what was said, never what should be said back.

**Positive (legitimate):**
1. *Live, unauthored.* Joe simply talks to her with camera+mic on, the way he already does — arrives, says whatever he says, mentions her name. Sight+sound+language land in one window through the existing live pipeline. Nothing here is "written" at all; this is the least scripted source that exists.
2. *Reuse of an already-real clip's own words.* The "your name is guala" sound already in her library is real recorded speech nobody has fed to language yet (the same gap the picture-title bug already proved exists for images — titles were never bound to language until `GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04`). Feeding its verbatim transcript as a caption citing that real sound is grounding an already-real event, not inventing one.
3. *Teacher re-sharing, scene first.* Joe replays an existing real photo (e.g. the ocean) and says whatever he actually says when sharing something again — "remember this?" is address-shaped conversation, but it exists because re-sharing is a real behavior, not because someone needed an "identity question" example.

**Negative (disguised script):**
1. Twenty bundles captioned as paraphrases of "hello, i am guala, i am doing well," all citing one arbitrary stock picture/sound purely to pass the multimodal gate, authored at a desk. The giveaway: the sensory reference is constant and irrelevant while the text converges on one meaning nobody actually said.
2. A file shaped like `{"input": "hello", "output": "hello, how are you"}`, laundered by putting both lines into one caption with a token touch tag attached. Wrapping a Q&A table in sensory fields does not change what it structurally is — §6 of the handoff forbids this shape explicitly, regardless of packaging.

## 3. Why this can generalize to real "hello" competence

Today's live mechanism (legacy Fact-Strand) already lets one heavily-repeated exact exchange continue correctly ("60x growth" → "in one year") because that exact word order was closed inside enough real multimodal windows. Broad real coverage of many different real greeting-shaped exchanges — different people, different days, different actual words — increases the odds that a real "hello" arrives and an exact, honestly-earned continuation already exists for it, by the identical mechanism, not a new one.

Under the GLEW architecture named in the handoff (§8.4/§9.4, `expression_modes.py`), the payoff is larger: recognition is `unique_full_interval_vector_dominance` over the full sensory+language field, not string identity. Enough real greeting-shaped episodes — sharing a structural pattern (mutual presence establishing itself, direct address, low sensory novelty) without sharing exact wording — let a genuine expression mode form and later recognize a structurally similar but never-before-seen greeting. That generalization is not built yet (full commit authority is `false` per the upstream profile); this corpus is what such a mode would need once it is.

## 4. Real media already available (no new capture required)

- **Pictures (repo-confirmed, ids from `docs/curriculum_seed_v1.json`, 2026-06-30):** moon `9bb63f93d7af`, mommy `da9d973d4fab`, daddy `5b47a97ce9e3`, family `4eeee4d3d6de`, guala `8bd9e45cae48`, aven `bc9b432c3138`, hug `2045ca965187`/`5aa967930289`, ocean `6b8122be0f2a`, sun `27def0e2842b`, flower `dc0aa333bbba`, balloon `2700ff625028`, rose `72156845a2bc`, lana `396f4d80bbce` — 22 real photos total per `GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04`.
- **Sounds (repo-confirmed):** hush-a-little-baby `addc0846da2a`, ocean waves `b46ba21b76a5`, bell `440d1619ec77`, two cat sounds `6c6561e73388`/`b5416742f6f7`.
- **Five sounds from the most recent live status check** (per this task's given ground truth, not independently re-verified here): ocean waves, daddy voice, cat meow, bouncing balls, **your name is guala**. The last is a real recorded utterance already carrying ordinary identity-conversation content.
- **Precedent this project already ran:** `curriculum_seed_v1.json` (100 real bundles citing real picture/sound ids), and the ratified "daddy-voice bundle" test (`GL-PLAN-FULLWIRE-WC-20260611-042`) — sound↔"daddy" binding from Joe's real recorded voice. Both prove the mechanism this proposal reuses, not a new one.

**Caveat:** all ids above are historical (June/early-July). The substrate has been wiped and restored multiple times since. Every id must be reverified via `/status` (or the bridge) immediately before use — do not execute against a stale id.

## 5. First batch — 7 real episodes

1. **your-name-is-guala.** `/bundle:` caption = the verbatim transcript of the real "your name is guala" clip (confirm by listening — do not assume the label), `sound_id` = its real current id, `picture_id` = the guala/family photo, `source="joe"` only if Joe is truly the recorded voice. No touch/smell/taste (keeps `experience_origin="observed"`).
2. **daddy-voice.** Same pattern, citing the real "daddy voice" clip and the daddy photo, caption = its true verbatim transcript.
3. **ocean-resharing.** Joe replays the real ocean photo (+ ocean-waves sound) for her and says whatever he genuinely says in the moment of sharing it again — logged verbatim afterward as the caption, not decided in advance. Real cool/wet/salty descriptors ride along honestly (marks the window `emulated`).
4. **moon-resharing.** Same shape with the moon photo, on a different real day, so the wording differs from episode 3 by construction (a different real moment, not a paraphrase).
5. **live-greeting-session-A.** Joe, camera+mic on, an ordinary real session in which he happens to greet her, ask what she's doing, or say his own name — no `/bundle:` needed; the live sensory pipeline already satisfies the multimodal gate. Words are whatever is truly said.
6. **live-greeting-session-B.** A second real session, different day, ideally a second real person present, so the substrate accumulates variation rather than one repeated voice.
7. **recall-cued follow-up.** In a later real session, Joe references something shared earlier ("remember the ocean?") without re-showing the photo — a spoken cue with no picture, the Stage-γ "first real conversation gate" already named in `GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1` §7.2.

## 6. What genuinely requires a human

- Speaking or typing the real words in episodes 3–7 — an agent cannot generate them without turning them into a script.
- Listening to the "your name is guala" / "daddy voice" clips and confirming the literal transcript before using it as a caption.
- Reverifying every id above via `/status` before execution.
- Deciding real speaker attribution per episode. **Finding from this investigation:** `app.py` line 3089's caption-lane call hardcodes `source="joe"` regardless of who is actually speaking, while other lanes in the same bundle correctly use the caller-supplied `source`. Until that gap is fixed (a code change, out of scope here), only teach a caption this way when Joe truly is the speaker, or flag the mismatch rather than let a different real teacher's words be silently mis-attributed.
- Pacing delivery through the substrate's own state gates (the existing curriculum-orchestrator's dry-run/live pattern), not a batch dump.
- Joe's explicit ratification of this whole approach as acceptable seed provenance before any of it is treated as production education.
