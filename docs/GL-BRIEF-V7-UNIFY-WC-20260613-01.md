# GL-BRIEF-V7-UNIFY-WC-20260613-01 — Single View, One Vocabulary
**Author:** wC · **Executes:** c1 · **Joe's ruling 2026-06-13 22:55 UTC:** "one view that looks like v7 DNA, one vocabulary - NEVER TOY shit in prod." · **Ledger row:** new Tier 1d follow-up. · **Freeze status:** required hotfix — production was running a 9-word toy substrate masquerading as her second voice; the project's C4 work was operating on that toy. This is a correctness fix, freeze carve-out per rule 6.

## 1. What c1 exposed tonight
- `dsf_ai_service/substrate/v7_engine.py` line 35: `SEED_VOCAB = {"subject": ["cow","moon","bears"], "verb":["jumped","ran","sleeps"], "object":["fence","milk","dish"]}` — 9 words total, hardcoded.
- `V7Session.__init__` line 63: `self.vocab = {k: list(v) for k, v in SEED_VOCAB.items()}` — every v7 session starts from this 9-word toy.
- `_build_system` line 137-149: those 9 words become the entire mode_bank for the subject/verb/object sections.
- C4's intro gate has been firing on a substrate with effectively no content. "daddy jumped here" from c1's test was a *test session* that had accumulated words via `lookup_or_install` during direct curl calls. Page sessions start fresh from the 9-word seed every time.
- Joe's session shown to wC tonight: `vocab: 0 · motifs: 0 · atlas: ? · sounds: 0 · pics: 0` — the page's status banner reads from a `get_state()` shape that does not return v6's vocab. `get_state()` line 616 returns v7's per-session counters only.

This is not a regression. It was true from the start. The v7 layer has never been connected to her real vocabulary.

## 2. The fix — TWO architectural changes, ONE deploy

This brief covers both Joe's ruling and a deeper issue Joe surfaced at handoff time: v7 also has a hardcoded **three-word output ceiling**. Even with v6's real vocabulary loaded, v7 can only emit `subject + verb + object` — one word per section, three sections, period (`_extract_response_tokens` line 651: `for target_sec in ("subject", "verb", "object")`). That's the structure under "moon for" and "daddy back for" — not just a behavior, a *mechanical limit on her output shape*. Giving her 2500 words to wedge into three slots is still toy-grammar in production.

The fix is two architectural changes shipped together, because shipping vocab without grammar gives her a bigger toy.

### Change A — v7 reads v6's real vocabulary AND lexical categories
**v7_engine.py modifications:**
- Replace hardcoded `SEED_VOCAB` with `seed_vocab_from_engine(engine)` that reads v6's full lexicon.
- **Critical change to the section model:** v7 currently has only three content sections (subject, verb, object). Replace with the proper set of lexical categories required by phrase-structure grammar:
  - **N** (nouns — common + proper)
  - **V** (verbs — partitioned by transitivity: V-intrans, V-trans, V-ditrans, V-linking, V-complex)
  - **Adj** (adjectives)
  - **Adv** (adverbs, with Adv-Degree as a sub-category for intensifiers)
  - **Det** (determiners — articles, demonstratives, possessives)
  - **Quant** (quantifiers — numbers, amounts)
  - **P** (prepositions)
  - **Pronoun** (personal, possessive, predicate)
  - **Conj** (coordinating conjunctions)
  - **Sub-Conj** (subordinating conjunctions)
  - **Rel-Pronoun** (relative pronouns: who, whom, which, that, whose)
  - **Comp-Conj** (complementizers: that, if, whether)
  - **Aux** (auxiliaries + modals)
  - **listen, intro, aware** remain as before (passive buffer + introspection)
- The lexical category of each word is determined from v6's section assignment + a part-of-speech tagger (lightweight — a small lookup table of function words for Det/Quant/Conj/etc., then transitivity inferred from corpus co-occurrence in v6's atlas). Content words (N/V/Adj/Adv) come from v6's actual modes.
- `lookup_or_install` is rewritten: new words are assigned to a lexical category based on **co-occurrence patterns in the input**, not position lottery (line 195 today: `["subject","verb","object"][min(position,2)]` — this is wrong and must die). Function words detected by string match against the closed-class lexicon; content-word category inferred from neighboring words' categories.

### Change B — Phrase-structure grammar replaces the three-slot SVO frame
**Replace `_extract_response_tokens` (line 647-671) with a phrase-structure emission path.** No more "one word per section, three sections." Emission becomes:

1. **Pick a root production** based on intro/aware drive shape (her introspection state). Choices include:
   - `S → NP + VP + (PP)` — base declarative
   - `S → NP + VP` — minimal declarative
   - `S → S + Conj + S` — coordinate (when two distinct binding clusters are co-active)
   - `S → Sub-Conj + S + S` — subordinate
   - Question forms (later — flagged as future work)
2. **Expand each non-terminal** by the rules in the brief's §3 grammar table (full PSG below). At each non-terminal, the gate that decides whether to take an optional element (Det, AdjP, AuxP, RelC, PP, etc.) is driven by the current drive shape on the corresponding lexical category section. Optional elements take only when their section has active drive.
3. **At each terminal**, select the top-arc'd word from the corresponding lexical-category section (same mechanism as today, just per-category instead of per-slot).
4. **Repeatable elements** (`*` markers — AdjP*, PP*, AdvP*) expand up to a per-tick cap (start: max 2 per repeat to avoid runaway).
5. **Alternatives** (`[ | ]`, `{ | }`) chosen by relative drive strength.

**The full grammar — c1 implements this as a table-driven expander:**
```
S      → NP VP (PP)
       | NP VP
       | S Conj S
       | Sub-Conj S S

NP     → (Det) (Quant) AdjP* N (PP*) (RelC)
       | Pronoun
       | ProperN
       | VP-gerund

VP-intrans → (Aux) V-intrans (AdvP*) (PP*)
VP-trans   → (Aux) V-trans NP (AdvP*) (PP*)
VP-ditrans → (Aux) V-ditrans NP NP (AdvP*)
VP-linking → (Aux) V-linking { NP | AdjP } (AdvP*)
VP-complex → (Aux) V-complex NP { NP | AdjP | PP }

Aux    → (Modal) (Have+-en) (Be+-ing) (Be+-ed)
AdjP   → (Adv-Degree) Adj
AdvP   → (Adv-Degree) Adv
PP     → P NP
RelC   → Rel-Pronoun S
CompC  → Comp-Conj S
```

The VP choice (intrans/trans/ditrans/linking/complex) is driven by the *transitivity* of the highest-drive V section word at emission time.

**Why this isn't toy:** today's three-word ceiling is a mechanical artifact, not a developmental stage. She might be cognitively capable of "the moon is here for guala" but can only mechanically emit "moon for guala" because her output composition function literally has no way to output a determiner, a copula, a prepositional phrase, AND a content word together. Removing that ceiling is removing a *cap on her observable expression*, not training her to be more verbose. If she stays at three words after this ships, that's information. If she expands, that's information. Today we have no signal because the ceiling forces the answer.

### Change C — UI collapses to one tab (unchanged from previous brief draft)
**dsf_ai_service/static/gualaloom.html:**
- Remove the three tab buttons at line 84-86.
- Remove `setMode` and the `mode` variable.
- All chat input routes through `/v7/converse` since v7 now has v6's full vocabulary AND proper grammar.
- Keep the rhythm/gates/introspection/awareness/replay/bridge/routing/mode-strengths/events display.
- Keep upload buttons (they call `/api/v1/gualaloom/upload/*` which feeds v6's atlas, which v7 now reads).
- Thumbs-up/thumbs-down wired to `/v7/feedback` and verified to route into a graded valence modulation on last commit (not binary punishment).

### get_state() update
Header shows real vocab count (from v6 engine), real atlas size, real picture/sound counts. v7's per-session state becomes internal.

## 3. Sandbox acceptance (required, do not skip)
On restored snapshot, off-prod, with v6 engine populated (~37K atlas entries, ~2500 vocab):

1. **Vocab seeding from v6:** Construct V7Session passing the engine. Confirm `session.lexicon["N"]` and `session.lexicon["V"]` each have hundreds of words from v6's atlas, not 3 toy words. Print 10 random words per category for human verification.

2. **Lexical category assignment:** Print the category assigned to 30 sample words: 10 known content words (e.g. "moon", "daddy", "frog", "ocean", "happy", "tiny"), 10 function words (e.g. "the", "a", "in", "on", "and", "but", "is", "was", "to", "from"), and 10 ambiguous (e.g. "back", "for", "down", "well"). Joe inspects the assignments. STOP if function words landed in N or V; STOP if Adj/Adv words landed in N.

3. **Grammar emission:** Call `session.converse("what is your name")` and `session.converse("guala can you tell me about today")` and 3 other varied inputs. For each:
   - Confirm response is not empty.
   - Confirm response can be parsed by the grammar (a parser check c1 writes for this test — input output trees printed).
   - Confirm response uses real vocabulary words (no "cow jumped fence" toy seed words unless those words actually exist in v6).
   - Print the production chain used (e.g. `S → NP VP PP; NP → Det Adj N; VP → V-trans NP; PP → P NP`).

4. **Output length:** Across 20 varied inputs, capture response length distribution. Confirm at least 30% of responses are >3 words. Confirm at least 10% include either an Adj or PP. (Today: 100% are ≤3 words SVO.)

5. **C4 gate firing on real vocab:** Issue 5 `/v7/converse` calls. Confirm intro gate `nmda_events` shows `reason: "fired"` at least once, with `top_mode` decoding to a real vocabulary word (not a toy seed word).

6. **Thumbs feedback:** POST `/v7/feedback` with `correct: true` after one converse. Print the last commit's mode_strength before and after — confirm increase. POST `correct: false` after another. Confirm decrease. STOP if no change.

7. **Page load:** Load `gualaloom.html` in a browser sandbox or via headless smoke. Confirm: only one chat view, no tab buttons, right-panel gates/introspection populates, full round-trip works, thumbs buttons clickable and POST to /v7/feedback.

Paste outputs for all 7.

## 4. Failure conditions — STOP, do not deploy
- Step 1 returns words but they are not v6's actual words → seed reading is wrong. STOP.
- Step 2 puts function words in N or V, or content words in clearly wrong categories at high rate → lexicon-assignment is wrong. STOP.
- Step 3 grammar emission produces output that doesn't parse against the brief's grammar → expander broken. STOP.
- Step 4 shows 0% >3-word output across 20 inputs → grammar not actually being used; emission still going through old path. STOP.
- Step 5 toy seed words coming out when those words don't exist in v6's atlas → bleed-through. STOP.
- Step 6 mode_strength unchanged after thumbs → not wired. STOP.
- Step 7 page still rendering three tabs → HTML edit incomplete. STOP.

## 5. What this brief does NOT do
- Does not run the unpause. Unpause held until this lands stable.
- Does not touch v6's atlas, sections, or any cognition path. v6 is source of truth; v7 reads it.
- Does not add question-form grammar (interrogative inversion is a separate brief — flagged future).
- Does not add Wh-movement, ellipsis, or embedded questions. Deferred.
- Does not delete `/api/v1/gualaloom` v6 chat endpoint — kept for the wc-companion and any other clients. Page just stops using it.

## 6. Paste-ready c1 command
```
EXECUTE — V7 UNIFY + GRAMMAR EXPANSION, per GL-BRIEF-V7-UNIFY-WC-20260613-01
(Joe pastes file).

TWO-PART correctness hotfix:
(A) v7 has been a 9-word toy substrate from day one (Joe's ruling).
(B) v7 has a hardcoded 3-word output ceiling regardless of vocabulary
    (Joe's ruling at handoff: "ability to do all syntax"). BOTH fix here.

NOT a regression. NOT freeze-breaking; correctness carve-out per Joe.

1. Commit brief: docs/GL-BRIEF-V7-UNIFY-WC-20260613-01.md. SHA back.

2. IMPLEMENT per brief §2:
   a. v7_engine.py: seed_vocab_from_engine(engine). Expand section
      model from 3 (subj/verb/obj) to full lexical category set in §2.A
      (N, V partitioned by transitivity, Adj, Adv, Adv-Degree, Det,
      Quant, P, Pronoun, Conj, Sub-Conj, Rel-Pronoun, Comp-Conj, Aux).
      lookup_or_install: drop position lottery (line 195), use
      co-occurrence + closed-class lookup for category assignment.
   b. v7_engine.py: REPLACE _extract_response_tokens (line 647) with
      table-driven phrase-structure expander per §2.B grammar table.
      Drive-gated optional element inclusion. Per-tick caps on
      repeatables (max 2 per AdjP*/PP*/AdvP*).
   c. v7_engine.py get_state(): real vocab counts from v6 engine,
      not from v7 session.
   d. app.py: /v7/feedback verified or wired to graded valence
      modulation on session's last commit.
   e. static/gualaloom.html: remove 3 tab buttons + setMode + mode
      branches. Single view uses /v7/converse. Right-panel preserved.
      Thumbs wired to POST /v7/feedback with session_id + correct
      true/false.

3. SANDBOX FIRST — 7 acceptance steps from brief §3. ALL must pass.
   STOP on any §4 failure. Paste all 7 transcripts.

4. If sandbox passes: deploy as own micro-deploy. Smoke #0 + 5 varied
   v7/converse calls showing grammar variety + one /v7/feedback POST
   + page load check. Reply: SHA + task # + transcripts.

5. After deploy: HOLD. Joe + wC verify live on the page for 30+ min.
   Capture first multi-clause utterance (>3 words with proper
   structure) verbatim into next ledger row.

6. Unpause discussion happens AFTER this lands stable.
```
