# Guala D3 sparse cognitive-capital ledger law

Date: 2026-08-03

Status: ratified storage law and focused falsification proof. Native runtime
admission, atomic production publication, Loom observation, and live tutoring
proof remain separate delivery work.

## Architecture honesty gate

1. **Requested architecture:** observe whole-organism cognitive capital as
   capability × participating physical mechanism/path × evidence dimension.
2. **Current code reality before this correction:** the ledger exposed only the
   forty-mechanism axis and allocated a fixed forty-slot checkpoint plus ten
   heads in every mechanism page. It could not represent the thirty-nine
   ratified capabilities.
3. **Conflict:** yes. A mechanism is not a capability.
4. **Mechanism not extended:** the old one-axis ledger, dense Cartesian storage,
   scores, weights, static capability/mechanism mappings, caller-authored axes,
   duplicated evidence, and v2 compatibility shims.
5. **Single exact item delivered here:** replace the ledger with sparse,
   addressed v3 storage that preserves all three axes and proves separate
   sensory queries plus zero-object no-capital events.
6. **DSF scope:** this ledger does not evaluate DSF and does not reduce DSF.
   Causal evidence may reference neuronal authorities, but no `D_k`, `M_k`,
   `R_rev_k`, `U_star_k`, `C_k`, `P_k`, or `B_k` value is interpreted here.
7. **Field loss:** none caused by this ledger. It stores the complete sealed
   evidence body once and retains only its content address in capital entries.

## Three orthogonal axes

### Capability — exact canonical 39-row catalog

1. Vision
2. Hearing
3. Touch
4. Temperature
5. Smell
6. Taste
7. Proprioception and body position
8. Vestibular balance
9. Interoception and visceral state
10. Multisensory integration
11. Recognition and familiarity
12. Attention and orienting
13. Immediate causal state
14. Episodic memory
15. Procedural and physical memory
16. Recall
17. Relational thought
18. Prediction
19. Deliberation and choice
20. Imagination and simulation
21. Language comprehension
22. Speech and articulation
23. Ordered thinking
24. Social cognition and other-perspective
25. Empathy
26. Emotion and affect
27. Emotional balance and regulation
28. Motivation, needs, and curiosity
29. Self and body continuity
30. Motor and actuator control
31. Navigation and avoidance
32. Play and exploration
33. Sleep and rest
34. Dreaming
35. Consolidation
36. Autonomous cognition and action
37. Learning and developmental growth
38. Creativity and self-expression
39. Integrated practiced capability

These are observation identities, not labels injected into cognition. Vision,
hearing, touch, temperature, smell, and taste remain separately queryable.

### Participating mechanism/path — exact orthogonal 40-row catalog

The existing forty rows are retained only as physical-observation paths. They
answer *what participated*, not *what capability exists*. A mechanism cannot be
used to derive a capability through a lookup table. Both axes must be present in
the sealed causal evidence and must match the private staging carrier.

### Evidence dimension — exact 10-row catalog

1. availability
2. participation
3. retention
4. recognition
5. recall
6. causal use
7. transfer
8. autonomous use
9. durability
10. integration depth

The dimensions remain independent. No total, average, rank, scalar capital
level, or decision authority is produced.

## Sparse addressed storage law

The checkpoint contains only sorted capability roots that have evidence. Each
capability root addresses a page containing only participating mechanism roots.
Each mechanism page contains only dimensions that have evidence. There is no
preallocated 39 × 40 × 10 object or slot matrix.

Each credited evidence entry preserves:

- exact capability;
- exact participating mechanism/path;
- exact dimension;
- organism generation;
- evidence lineage;
- content address of the complete evidence body; and
- address of the prior entry for bounded reverse paging.

The evidence body is stored once by content address even when multiple entries
refer to it. Exact lineage membership uses immutable path-compressed Patricia
nodes. Only the reached path is read and path-copied. A generation with no
capital evidence returns the unchanged checkpoint and creates zero objects,
including when all preparation budgets are zero.

## Admission authority

Production callers cannot construct a credit's axes directly. The staging
carrier fields are private. A typed causal-evidence decoder derives capability,
mechanism/path, dimension, generation, and lineage from the complete sealed
body. Any mismatch refuses the batch before publication.

This storage layer does not decide that a mosaic, recall, transfer, autonomous
use, or durability occurred. The corresponding native physical operation must
produce that evidence. Capital observes it after the fact.

## Codec and migration law

This is an intentionally incompatible v3 cutover:

- entry magic: `GCCENT03`;
- capability-page magic: `GCCCAP03`;
- mechanism-page magic: `GCCMEC03`;
- Patricia-node magic: `GCCPAT03`; and
- object codec version: `3`.

The organism-generation checkpoint encoding is now:

1. optional latest credited organism generation;
2. unsigned 16-bit count of observed capability roots; and
3. sorted repeated `(capability code, 32-byte capability-page address)`.

The prior fixed forty optional mechanism addresses are removed. v2 dense pages
are rejected by typed magic; there is no runtime compatibility shim or inferred
axis migration. A real persisted v2 capital inventory would require an offline,
explicitly authorized migration whose source evidence can truthfully recover a
capability. If that capability is absent from the evidence, it cannot be
invented and the old record cannot become v3 capital.

## Focused falsification proof

The focused Rust suite proves:

- the exact thirty-nine capability rows, forty mechanism/path rows, and ten
  dimensions remain distinct;
- six external senses are independently stored and queried;
- only observed axis combinations allocate pages;
- complete evidence bodies are stored exactly once;
- caller axes must match typed evidence axes;
- duplicate/replayed lineage and noncanonical batches fail before publication;
- false recall, transfer, and autonomous-use claims fail;
- cold paging re-resolves and revalidates exact evidence bodies;
- missing or altered addressed bodies fail closed;
- v2 page bodies are rejected, not silently adapted;
- Patricia work is path-compressed rather than fixed-depth per credit; and
- a no-capital generation creates zero objects and advances no capital clock.

Passing these tests proves the ledger law, not live cognitive growth. D3 becomes
production-complete only when native physical evidence is atomically published,
cold-restored, and truthfully observed in production.
