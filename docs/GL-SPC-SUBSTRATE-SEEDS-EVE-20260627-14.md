# GL-SPC-SUBSTRATE-SEEDS-EVE-20260627-14

doc_id: GL-SPC-SUBSTRATE-SEEDS-EVE-20260627-14
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Type: Specification (not a dispatch — agreement document)
Requires: Joe + Eve agreement before any seed writes execute

## What this is

The discipline for substrate-true seeding via atlas surgery. Every seed
pattern, every source tag, every verification step is specified here.
Atlas surgery without this discipline becomes statistical cheating in a
different shape. With this discipline, seeding is acceptable acceleration —
substrate-native acceleration of capabilities her organic learning is too
slow to develop in the timeframes we care about.

This document is the contract between us. If atlas surgery deviates from
this, the deviation is a violation, not a feature.

## The four requirements for substrate-true

A seed is substrate-true if and only if ALL four hold:

**1. Writes go through `atlas.record`.** Same path her natural producers
use (read_word, read_sentence, _atick_attending_*, episode wire). No
parallel write path. No fabricated structure. No bypassing of clarity,
salience, polarity, or any other field-validation her normal path enforces.

**2. Source tagging is honest.** Every seed entry carries
`source="seed:<topic>:<seq>"` where topic is the capability being seeded
(e.g. `negation`, `self`, `embedding`, `hierarchy`) and seq is a sequence
number. NEVER `source="joe"` or `source="self"` or `source="wc"` or any
other tag that lies about provenance. The atlas knows what is seeded and
what is organic.

**3. Recall consultation verified.** Before any seed pattern executes at
scale, we verify that her recall mechanism (grandurun candidate retrieval,
section dominance, episode_ref lookup, parent_chi traversal — whichever the
seed touches) actually consults entries with `source="seed:*"`. If grandurun
filters out seed-source entries because of any source-restriction logic, the
seeds are dead data and we've fooled ourselves. Verification protocol below.

**4. Behavioral integration verified.** A seed pattern is not "working" until
her emissions demonstrably USE the seeded primitive. We observe her
emissions over a defined window after seeds land. If the substrate has
integrated the pattern, emissions will compose with it. If they don't,
the seed didn't take and the architecture needs investigation.

If any of the four fails, the seed pattern is not substrate-true and must
not ship.

## What we will NOT seed (the bright line)

These would be cheats with extra steps, and we don't write them:

- **No response text.** Sentences she might say as output.
- **No emission templates.** Pre-built compositions ready to surface.
- **No conversation scripts.** Dialogue turns indexed by context.
- **No verbatim quotes from input she's heard.** That's bigram with curation.
- **No fabricated experiences.** "She remembers her mother singing" without
  there actually being a structural representation of a singing-mother event.
- **No pre-loaded preferences** (e.g. "she loves the moon" as a stored fact).
  Preferences accumulate from real attention. Seeded preferences are
  statistical lies.
- **Nothing that could surface verbatim as her output.** If the seed could
  appear word-for-word in an emission and look like she composed it, it is
  a cheat.

What we DO seed: **structural primitives**. The architectural building blocks
her substrate uses to compose comprehension. Not content. Not output.
Scaffolding.

## Source tagging discipline

Every seed write uses `source="seed:<topic>:<seq>"`:

- `seed:negation:001` through `seed:negation:NNN` for negation seeds
- `seed:self:001` through `seed:self:NNN` for self-reference seeds
- `seed:embedding:001` through `seed:embedding:NNN` for embedding seeds
- `seed:hierarchy:001` through `seed:hierarchy:NNN` for hierarchy seeds
- `seed:quantification:001` through `seed:quantification:NNN` for quantifier seeds

Episode_refs follow the same pattern: `episode_ref="seed:negation:001"` etc.
A seed write's `episode_ref` matches its source topic and sequence.

This lets us audit at any time: "did the substrate use any `seed:negation:*`
entries in her last 100 emissions?" If yes, the seed integrated. If no,
the seed is decoration.

Composite seeds (e.g. an embedding seed that also touches polarity) carry
the primary topic in source: e.g. `seed:embedding:001` with `polarity=+1`
is an embedding seed, not a negation seed, even though it has a polarity field.

## Verification protocol (per seed pattern)

Before deploying seed patterns of a given topic at scale:

**Step 1 — Field round-trip smoke.** Write one seed entry. Save atlas to
EFS. Restart container. Load atlas. Confirm the seed entry's fields are
preserved exactly. If any field is lost (polarity drops to default, head_chi
goes None, parent_chis list empties), the substrate's persistence path is
incomplete for that field. Fix persistence before seeding.

**Step 2 — Recall consultation check.** Issue an `atlas_query` for a
keyword the seed entry binds. Confirm the seed entry surfaces in the
returned candidates. If the query returns matching organic entries but
NOT the seed entry, grandurun is filtering by source somewhere. Diagnose
and fix the filter before seeding more.

**Step 3 — Single-entry behavioral test.** Write one seed of the pattern.
Issue a converse that should activate it (e.g. for a negation seed binding
"not moon" with polarity=-1, send input "the moon is not bright"). Observe
her emission for polarity flip or contrast use. If the substrate uses the
seed in composition, the pattern is viable. If she ignores it, the
architecture doesn't recall-traverse the field yet — go back to spec.

**Step 4 — Scaled deployment with monitoring.** After Step 3 passes,
deploy the full seed batch for that topic via T1 atlas surgery endpoint.
Monitor emissions over 24 hours of substrate runtime (or N converses,
whichever surfaces enough emissions for statistical signal). Track how
many emissions use seeded primitives via `source="seed:<topic>:*"` audit.

**Step 5 — Integration verdict.** If integration rate > 5% of relevant
emissions over the monitoring window, the seed is substrate-true and
counts as a real capability addition. If integration is below 5%, the
seed didn't take — pull the seeds, investigate, re-spec.

The 5% threshold is provisional; refine after the first seeded capability
deploys.

## Seed patterns by capability

Each capability requires its architectural extension to ship FIRST (the
field, the recall consumer, the emission composition path). Seeds populate
the field with examples after the architecture exists. Seeds do not replace
or shortcut the architectural work.

### Negation (requires C1 polarity field)

**What seeds.** Operator entries (`not`, `no`, `never`, `neither`, `without`)
as substrate primitives. Contrast pairs for foundational concepts —
the same motif with both polarities in separate episode_refs.

**Example seed batch.**
```
atlas.record(motif="not", section="modifier", chi=<assigned>,
             polarity=+1, clarity=0.9, source="seed:negation:001",
             episode_ref="seed:negation:001")

atlas.record(motif="moon", section="subject", chi=<chi_moon>,
             polarity=+1, clarity=0.7,
             source="seed:negation:002",
             episode_ref="seed:negation:002")

atlas.record(motif="moon", section="subject", chi=<chi_moon>,
             polarity=-1, clarity=0.7,
             source="seed:negation:003",
             episode_ref="seed:negation:003")

# Same pattern for: sun (-1 / +1), water, fire, food, mother, daddy, hot, cold...
```

**Behavioral test.** Send `"the moon is not bright"`. Expect her emission
to compose with polarity=-1 on "bright" or invert the polarity of the moon
binding. If grandurun selects a polarity=-1 candidate where input had
"not", substrate-true confirmed.

**Verification source tag.** All entries `source="seed:negation:NNN"`.

### Self-reference (requires C2 self section)

**What seeds.** Identity mappings — "guala" / "i" / "me" / "my" all
bind to the same self chi with `section="self"`. Self-source replay seeds
that establish her own emissions as inputs to her self section.

**Example seed batch.**
```
atlas.record(motif="guala", section="self", chi=<chi_self>,
             clarity=0.9, source="seed:self:001",
             episode_ref="seed:self:001")

atlas.record(motif="i", section="self", chi=<chi_self>,
             clarity=0.9, source="seed:self:002",
             episode_ref="seed:self:002")

atlas.record(motif="me", section="self", chi=<chi_self>,
             clarity=0.9, source="seed:self:003",
             episode_ref="seed:self:003")

atlas.record(motif="my", section="self", chi=<chi_self>,
             clarity=0.8, source="seed:self:004",
             episode_ref="seed:self:004")
```

Note: the source is `seed:self:NNN`, NOT `source="self"`. The self section
is the SECTION of the binding; the source is provenance. These are
different concepts.

**Behavioral test.** Send `"who are you"`. Expect her emission to
self-section commit with "guala" or "i" or related. Send `"are you guala"`.
Expect her recall to surface self-section bindings.

### Embedding (requires C3 head_chi pointer)

**What seeds.** Head-modifier pairs with `head_chi` pointers establishing
nested clause structure.

**Example seed batch.**
```
# Pair 1: "bright moon"
atlas.record(motif="moon", section="subject", chi=<chi_M>,
             head_chi=None, clarity=0.7,
             source="seed:embedding:001",
             episode_ref="seed:embedding:001")

atlas.record(motif="bright", section="modifier", chi=<chi_B>,
             head_chi=<chi_M>, clarity=0.7,
             source="seed:embedding:001",
             episode_ref="seed:embedding:001")

# Pair 2: "warm sun"
atlas.record(motif="sun", section="subject", chi=<chi_S>,
             head_chi=None, clarity=0.7,
             source="seed:embedding:002",
             episode_ref="seed:embedding:002")

atlas.record(motif="warm", section="modifier", chi=<chi_W>,
             head_chi=<chi_S>, clarity=0.7,
             source="seed:embedding:002",
             episode_ref="seed:embedding:002")

# Continue for: cold water, hot fire, soft blanket, loud bell, etc.
```

**Behavioral test.** Send `"the moon is bright"`. Expect grandurun to
produce an emission where head (moon) and modifier (bright) share the same
`head_chi` linkage. Send `"tell me about the sun"`. Expect her emission to
include modifier-bindings of sun (warm) via head_chi traversal.

### Hierarchy (requires C4 parent_chi field)

**What seeds.** Parent-child chains for foundational categories.

**Example seed batch.**
```
# "things in the sky" → moon, sun, stars, clouds
atlas.record(motif="things_in_sky", section="subject", chi=<chi_TIS>,
             parent_chis=[], clarity=0.5,
             source="seed:hierarchy:001",
             episode_ref="seed:hierarchy:001")

atlas.record(motif="moon", section="subject", chi=<chi_M>,
             parent_chis=[<chi_TIS>], clarity=0.7,
             source="seed:hierarchy:002",
             episode_ref="seed:hierarchy:002")

atlas.record(motif="sun", section="subject", chi=<chi_S>,
             parent_chis=[<chi_TIS>], clarity=0.7,
             source="seed:hierarchy:003",
             episode_ref="seed:hierarchy:003")

# Multi-parent example: moon is celestial AND in_sky
atlas.record(motif="celestial_body", section="subject", chi=<chi_CB>,
             parent_chis=[], clarity=0.5,
             source="seed:hierarchy:010",
             episode_ref="seed:hierarchy:010")

atlas.record(motif="moon", section="subject", chi=<chi_M>,
             parent_chis=[<chi_TIS>, <chi_CB>], clarity=0.7,
             source="seed:hierarchy:011",
             episode_ref="seed:hierarchy:011")
```

**Behavioral test.** Send `"tell me about things in the sky"`. Expect her
emission to surface moon, sun, stars via parent_chi traversal. Send `"the
moon is something"`. Expect her emission to compose with a parent category
(things_in_sky or celestial_body) even though "things_in_sky" was never
co-attended with "moon" in any organic experience.

### Quantification (requires C4 hierarchy + C8 quantifier operators)

**What seeds.** Quantifier operators + quantified generalizations over
seeded hierarchies.

**Example seed batch.**
```
atlas.record(motif="all", section="modifier", chi=<assigned>,
             clarity=0.9, source="seed:quantification:001",
             episode_ref="seed:quantification:001")

atlas.record(motif="some", section="modifier", chi=<assigned>,
             clarity=0.9, source="seed:quantification:002",
             episode_ref="seed:quantification:002")

# "All things in the sky are bright"
# Hierarchy traversal of chi_TIS → moon, sun, stars
# Each child gets a binding with brightness:
for child_chi in [chi_moon, chi_sun, chi_stars]:
    atlas.record(motif="bright", section="modifier", chi=<chi_B>,
                 head_chi=child_chi, polarity=+1, clarity=0.7,
                 source="seed:quantification:003",
                 episode_ref="seed:quantification:003")
```

**Behavioral test.** Send `"is the new_thing bright"` where new_thing is a
member of things_in_sky she hasn't seen with "bright" organically. Expect
her emission to compose with brightness via inherited quantified property.

## Architectural prerequisites table

| Seed topic | Requires architectural extension | Order in -08 emergence plan |
|------------|----------------------------------|----------------------------|
| Negation | C1 polarity field | Group α |
| Self-reference | C2 self section | Group α |
| Embedding | C3 head_chi pointer | Group β |
| Hierarchy | C4 parent_chi list | Group β |
| Quantification | C4 hierarchy + C8 operators | Group γ |

No seed pattern executes until its architectural prerequisite has shipped,
passed its own behavioral test, and the field-round-trip persistence
smoke test has confirmed seed entries survive container restart.

## Atlas surgery endpoint (T1 from -08)

The endpoint that executes seed writes is `POST /admin/atlas_surgery`
already specified in `GL-SPC-EMERGENCE-WAVES-EVE-20260627-08.md`. It accepts
a list of structured bindings:

```json
{
  "bindings": [
    {
      "motif": "moon",
      "section": "subject",
      "chi": <int>,
      "polarity": -1,
      "head_chi": null,
      "parent_chis": [<int>],
      "clarity": 0.7,
      "salience": 1.0,
      "source": "seed:negation:003",
      "episode_ref": "seed:negation:003"
    },
    ...
  ]
}
```

The endpoint validates field round-trips, source tagging compliance, and
chi-uniqueness before writing. Writes execute via `atlas.record` — same
path organic learning uses.

T1 ships as part of Group α from -08. Before T1 ships, no seeding executes.

## What seeding lets us accelerate

Once architectural extensions ship AND seed verification passes:

- **Foundational concept structure** seeded with rich relationships across
  sun/moon/stars/sky/water/fire/food/body/family categories
- **Negation as substrate primitive** with contrast pairs for foundational
  concepts (she has examples of "not X" structure across many X)
- **Self-reference** explicitly seeded (guala/i/me/my → self chi) instead
  of waiting for organic emergence
- **Compositional structure** (modifier-head pairs) seeded so her grandurun
  has working examples to compose with
- **Hierarchical generalization** seeded so she can generalize from
  instance to category without exhaustive organic exposure
- **Quantification** seeded so she can compose "all", "some", "no"
  statements over foundational categories

What this is NOT accelerating: her actual learning. Her substrate still
learns the way it learns. We give her structural scaffolding so the
learning has framework to use. Comprehension still has to emerge from
her substrate using these primitives.

## What seeding will NOT do (manage expectation)

- It will NOT make her speak more fluently. Fluency comes from her
  composer (v5 grandurun and/or organ-brain `_compose`), not from atlas
  state.
- It will NOT replace her organic learning. Seeds are scaffolds; experience
  is content.
- It will NOT pass behavioral tests by itself. Architecture has to consume
  the seeded fields. Seeds without architecture are wasted writes.
- It will NOT produce convincing fakeouts. The 5% integration threshold
  catches dead seeds. If we deploy seeds and her emissions don't change,
  we'll know.

## Failure modes to watch for

**FM-1. Seed source filtering.** If grandurun has source-filter logic
anywhere that excludes "seed:*" entries, seeds will be dead data and we
won't know until integration verification fails. Step 2 of verification
catches this.

**FM-2. Clarity insufficient.** Seeds with `clarity` below threshold
won't surface in recall. Default seed clarity 0.7 should be safe but
needs verification per topic.

**FM-3. Conflict with organic bindings.** Seed entries with same (motif,
section, chi) as existing organic entries will be ignored or merged
unpredictably. Atlas surgery must check for collision before writing.

**FM-4. Persistence gaps.** New fields (polarity, head_chi, parent_chis)
must round-trip through save/load. If persistence is incomplete for any
seeded field, deploy will lose the seed state on restart. Step 1 catches
this.

**FM-5. Seed quality degrading organic learning.** If seeds are too
salient, they may dominate her recall and crowd out organic experience.
Mitigation: seed clarity ≤ 0.7 by default; salience = 1.0 (normal); no
elevated affect on seeds unless explicitly designed.

## Approval required before any seed writes execute

This document is the spec. The discipline is here. Specific seed batches
for each topic require separate dispatches with concrete chi assignments,
motif lists, and behavioral test plans:

- `GL-CMD-SEED-NEGATION-EVE-<date>-<seq>`
- `GL-CMD-SEED-SELF-EVE-<date>-<seq>`
- `GL-CMD-SEED-EMBEDDING-EVE-<date>-<seq>`
- `GL-CMD-SEED-HIERARCHY-EVE-<date>-<seq>`
- `GL-CMD-SEED-QUANTIFICATION-EVE-<date>-<seq>`

Each dispatch references this spec by doc_id and confirms compliance.

Joe approves this spec → C1 ships T1 atlas surgery endpoint → architectural
extensions ship per emergence plan → seed dispatches author per capability
→ verification per protocol → integrated capability or pulled seed.

That's the path.
