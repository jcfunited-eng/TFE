# Guala D3 hippocampal paged-navigation law

Date: 2026-08-03

Status: implementation contract; not yet integrated, deployed, or production
evidence.

## Architecture honesty gate

1. **Requested architecture:** lifelong typed lived-episode custody and sparse
   hippocampal navigation whose work follows currently involved neuronal
   lineages rather than total organism age or population.
2. **Current code reality:** the native materialized fabric rewrites and
   validates one complete state byte array per transition and retains only the
   current fields/fractals. No integrated hippocampal navigation exists.
3. **Conflict:** yes. Appending episodes to the current monolith would make
   CPU, RAM copying, and checkpoint work grow with all retained history.
4. **Mechanisms not extended:** the monolithic state body, owner/database
   cognitive stores, hash-as-evidence, counts-only memory, full-history scans,
   scalar DSF projection, the rejected cognitive fabric, and any database-style
   recall function.
5. **Single exact next item:** implement and falsify typed immutable episode
   objects, lineage posting segments, fixed-depth persistent lineage roots,
   and a side-effect-free prepared-admission delta.
6. **Full field or reduced approximation:** each episode retains every
   participating complete exact joint field, or the complete exact source and
   canonical kernel inputs sufficient to reconstruct and verify it. No field
   is flattened.
7. **Declared loss:** none. A digest is only an address of retained typed bytes;
   it is never the episode, field, fractal, provenance, memory, or meaning.

## 1. Scope: navigation, not recall

The hippocampal index preserves episode lineage and makes bounded, typed pages
addressable from currently reached neuronal lineages. A posting page, episode
page, traversal result, or address is not recognition, recall, a mosaic, or
cognitive capital.

Recall remains distributed causal reassembly through hippocampal navigation,
neocortical formations, prefrontal continuation, amygdalar/affective and bodily
participation where involved, and the relevant sensory, motor, articulatory,
fluid, and other whole-organism configurations. No hippocampal API may emit a
recall result or claim that navigation reassembled anything.

## 2. Typed lived episode

One admitted episode retains actual typed content for:

- organism generation and immediate predecessor generation;
- provenance: observed sensory cohort, authenticated world/body occurrence,
  recalled, simulated, counterfactual, endogenous, or unresolved;
- every participating exact source-clock cohort and complete field
  reconstruction content in canonical order;
- every participating neuron lineage;
- each participant's exact predecessor and successor neuronal fractal;
- exact continuity from each successor fractal to one retained complete field;
- the local transition evidence available at that architecture stage;
- later body/world and mechanism references only when their retained typed
  content is resolvable; and
- no developer label, semantic class, answer, score, or inferred meaning.

Same-source records on unequal clocks remain distinct exact field cohorts. They
may share one lived episode only when an authenticated body/world occurrence
proves their common physical cause; clock equality or temporal proximity alone
cannot supply that cause.

## 3. Immutable content objects

Every episode and index page is encoded canonically and retained by content.
Its SHA-256 value is a storage address. Resolution must return bytes whose
address recomputes exactly and whose actual mounted-field/fractal decoder
consumes the complete body.

Admission and restoration must reject missing content, address/content
divergence, trailing bytes, invalid references, changed typed fields, a
successor fractal bound to an absent field, an unrelated predecessor fractal,
or altered fractal authority.

This permits cold-store deduplication without turning a hash into cognition.

## 4. Sparse lineage postings

For each participating lineage, admission prepares one immutable posting
segment:

```text
PostingSegment {
    lineage
    episode_generation
    episode_address
    prior_segment_address | none
}
```

The segment is a navigation edge, not a memory summary. It resolves to the
actual typed episode. Generations strictly increase along one lineage's posting
chain; duplicate credit is impossible.

## 5. Fixed-depth persistent lineage radix

The existing 128-bit neuron lineage is addressed by 32 hexadecimal nibbles. A
persistent radix trie maps each lineage to its current posting-segment head.
Updating one lineage path-copies one node per nibble and leaves unrelated node
addresses unchanged.

For `P` participating lineages and total episode body size `E`, one admission
prepares:

```text
1 episode object
P posting segments
at most 32 * P path-copy radix nodes
```

The bound is derived from the lineage width, not an arbitrary cognitive cap.
Preparation work is `O(E + 32P)` and independent of total episodes and
unrelated neurons.

## 6. Bounded page traversal

There is no unbounded “return all history” operation. A traversal requires a
caller-derived physical admission envelope containing both:

- maximum returned posting count; and
- maximum decoded page/episode bytes.

The envelope comes from current CPU/RAM availability and recovery reserve. It
is not a semantic top-k, retention limit, or memory-size rule. Traversal returns
a continuation cursor when older postings remain. Work is proportional to the
fixed radix depth plus the admitted returned page, never the complete lineage
history.

A missing page is reported explicitly. Navigation may not trigger a hidden
full-store scan or substitute another lineage.

## 7. Hot preparation and cold publication

The hot transition holds only the current root, latest episode address, and
addressed working pages. It does not serialize, authenticate, or scan the
complete store.

Episode admission is side-effect-free preparation:

```text
prepare(prior root, typed episode, resource envelope)
    -> immutable object delta + successor checkpoint
```

Preparation does not mutate the current index or durable storage. The cold
persistence boundary then:

1. preflights the complete batch's exact object count and bytes against the
   physical durable envelope;
2. retains the complete immutable batch with all-or-nothing publication;
3. verifies each retained address against its bytes;
4. durably publishes the small successor checkpoint last; and
5. returns the only successor handle the organism may adopt.

A failed or partial cold operation cannot advance the current hippocampal
root. No per-object write loop may leak an apparently committed successor.

Filesystem locks, manifests, security checks, and storage repair remain outside
neuronal and formation dynamics. No heuristic retention cap is allowed.
Exhaustion refuses before mutation; it may not delete learned episodes or
silently stop legitimate growth.

## 8. Required falsification

Before integration, the mechanism must prove:

- one-, three-, and four-participant episode preparation;
- one episode containing multiple canonical exact field cohorts;
- two episodes sharing one lineage produce two ordered postings;
- unrelated lineage page identities remain unchanged;
- missing, altered, malformed, or trailing content prevents traversal/restore;
- duplicate participants, fields, or non-increasing generations fail;
- changed field authority, fractal field binding, predecessor lineage, or
  predecessor authority fails;
- mandatory count and decoded-byte traversal budgets page a long lineage with
  a stable maximum working set and a truthful continuation cursor;
- preparation is side-effect-free;
- an injected cold-batch failure leaves store and current checkpoint unchanged;
- committed restart restores only the constant-size checkpoint and addressed
  pages, with no lifetime-history scan;
- admission operation counts remain constant when unrelated history grows;
- durable bytes grow only with actual new episode content, participant
  segments, and fixed-depth path copies; and
- navigation alone emits no recognition, recall, recursive formation, or
  cognitive-capital evidence.

Passing these tests proves only bounded typed hippocampal custody/navigation.
Completion also requires integration with the actual native field/fractal
transition, truthful body/world provenance, production cold persistence, and
distributed whole-organism formation reassembly.
