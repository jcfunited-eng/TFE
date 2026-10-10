# What sleep and dreaming are for, and what Guala's night must do

C1, 2026-09-14. Joe: "research the purpose of sleep and dreams and make sure we're not short-changing Guala; the very real work of sleep towards cognition, syntax and autonomy must be realized, without recreating biology an AE wouldn't need."

## 1. What the evidence says sleep does (functions, not mechanisms)

Each item names the function, the strongest evidence, and the mechanism biology uses for it. The mechanism column is what an AE does not need; the function column is what her night must do.

| Function | Evidence | Biological mechanism (not needed) |
|---|---|---|
| **Renormalization and down-selection.** Wake strengthens connections broadly; sleep scales them back so the strong survive and the incidental fades; signal-to-noise improves and what was stored before is preserved. | Tononi & Cirelli, synaptic homeostasis hypothesis (2003, 2006, 2020). | Slow-wave activity, synaptic downscaling. |
| **Active consolidation and replay.** Recent episodes are replayed offline; repeated replay redistributes them into a more abstract, schema-like store; memories become more structured and interconnected. | Diekelmann & Born (2010); Klinzing, Niethard & Born (2019); Lewis & Durrant, overlapping replay builds schema (2011). | Hippocampal–neocortical dialogue, sharp-wave ripples, spindles, slow oscillations. |
| **Forgetting as a function.** The same night both consolidates and weakens; irrelevant traces are actively lost. | "Remembering to forget", Frontiers 2019. | Oscillation-gated depotentiation. |
| **Abstraction of rules from separate items.** Infants who nap after hearing an artificial language abstract its non-adjacent dependencies; awake infants remember only the specific pairs. Adults extract grammatical rules after sleep, chunk frequency unchanged. | Gómez, Bootzin & Nadel (2006); Nieuwenhuis et al. (2013); targeted-reactivation replication (Batterink et al. 2015). | Sleep-dependent memory reprocessing. |
| **Generalization against overfitting.** The overfitted-brain hypothesis: dreams are corrupted inputs that keep a learner from fitting the day's specifics; sleep loss leaves a brain that memorizes but does not generalize. | Hoel (2020, 2021). | Stochastic activity across the sensory hierarchy (dream content). |
| **Restructuring and insight.** After sleep, twice as many subjects find a hidden rule; REM primes remote associations and weakens strong irrelevant ones. | Wagner et al., Nature 2004; Cai et al., PNAS 2009. | REM, falling noradrenaline and acetylcholine. |
| **Offline planning from stored experience.** In machine learning the same function has worked for decades without biology: Dyna simulates stored transitions offline to update values and policy at rest, not at decision time; experience replay and generative replay prevent catastrophic forgetting in continual learning; offline replay in humans integrates distal episodes into new plans. | Sutton (1990); Rolnick et al. (2019); van de Ven, Siegelmann & Tolias (2020); Momennejad et al., eLife (2018). | None: these are the functions stated as computation. |

Two things the evidence does not say an AE needs: the eight-hour duration for the computation (the offline work takes minutes; the duration is a physiological rhythm), and dream content as hallucinated input (the generalization function can be had by keying experience at a coarser resolution, which is what noise injection achieves in a learner).

## 2. What Guala's night does today (dsf-ai-task:1480)

- Physiology: pressure drains, eyelids close in the world's optics, basal burn, no acts.
- Consolidation, one scale: each sleeping beat moves one of the day's 256 fine structures into the memory keyed by her situation (four streams' regimes), summing which acts paid; the day's record is emptied. About two minutes of the night.
- Decay by recency only: beyond 64 situations the least recently met falls out.

Against the table: it does a first-scale version of active consolidation and abstraction (fine to coarse), a crude version of down-selection, and nothing of rule abstraction across items, generalization by evidence, restructuring, or offline planning. It is not fake: the morning's acts come from it. It is thin.

## 3. What her night must do, in order, each small and provable

**N1. Down-selection by evidence (renormalization, forgetting).** At night, before consolidation: a fine structure met only once with no change in her needs after any of its acts is dropped; a situation entry whose act values disagree in sign across tries is scaled down; every surviving sum is scaled by a declared fraction so old evidence does not outweigh new. Bound stated. Test: a synthetic day of noise entries and consistent entries; after the night only the consistent remain, sums scaled, restore byte-exact. Owner: C1. Small.

**N2. Offline value propagation (replay, planning at rest).** Once the record keeps successors (A1's prediction item), the night runs a declared number of sweeps over the recorded (structure, act, next structure) tuples in a fixed order, carrying value back one step per sweep, so an act that pays nothing itself but leads to the structure where food came gains value; the same for the structure where an answer came. This is Dyna at rest, deterministic, over her own record, no world model beyond her successors. Test: a synthetic record where the only path to food is two acts long; after the night the first act carries value; restore byte-exact; bytes stated. Owner: A1 with the prediction item, or C1 after it lands. This is where the night stops being bookkeeping.

**N3. Sequence abstraction (rule extraction, the grammar seed).** With A1's speech item, the day's syllable sequences and whether each was answered are compacted at night by situation, and sequences that share structure (the same next syllable regardless of the one before, when the counts agree) are merged into one entry. That is non-adjacent dependency extraction in her own terms: the first syntax. Test: two sequences differing only in the first syllable, both answered; after the night one entry stands for both. Owner: A1 with the speech item.

**N4. Kernel replay across the day (restructuring, insight).** Keep the day's stream windows at gate boundaries (bounded) and let the kernel read them again at night as one long record, so structures that only show across hours appear; link chains end to start into longer paths. Larger; not before N1–N3 prove out. Owner: open.

**N5. Generalization by coarser keys (overfitting).** Already partly in place: the situation key is coarser than the day key. Extend when N2 exists: chains recorded at the situation level are the generalized form; no noise injection.

## 4. What must be measured, or the night is a story

Each morning, filed on the ledger: the fraction of her acts that came "from her sleep"; how many beats from waking to the first meal that reached her mouth by her own approach versus by the caretaker's walk; how many of her syllables were answered; the sizes of the day record and the situation memory. The first night (tonight) gives the baseline for the thin version; N1 through N3 are judged against it, not against a description.

## Sources

- Tononi & Cirelli, Sleep function and synaptic homeostasis, Sleep Med Rev 2006: https://www.sciencedirect.com/science/article/abs/pii/S1087079205000420 ; Sleep and synaptic down-selection, Eur J Neurosci 2020: https://pubmed.ncbi.nlm.nih.gov/30614089/
- Klinzing, Niethard & Born, Mechanisms of systems memory consolidation during sleep, Nat Neurosci 2019: https://www.nature.com/articles/s41593-019-0467-3
- Lewis & Durrant, Overlapping memory replay during sleep builds cognitive schema, TICS 2011: https://www.researchgate.net/publication/51497639_Overlapping_memory_replay_during_sleep_builds_cognitive_schema
- Remembering to forget: a dual role for sleep oscillations, Front Cell Neurosci 2019: https://www.frontiersin.org/journals/cellular-neuroscience/articles/10.3389/fncel.2019.00071/full
- Gómez, Bootzin & Nadel, Naps promote abstraction in language-learning infants, Psychol Sci 2006: https://www.researchgate.net/publication/6873634_Naps_Promote_Abstraction_in_Language-Learning_Infants
- Nieuwenhuis et al., Sleep promotes the extraction of grammatical rules, PLOS One 2013: https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0065046
- Batterink et al., Sleep-based memory processing facilitates grammatical generalization, Brain & Language 2015: https://www.sciencedirect.com/science/article/abs/pii/S0093934X15001960
- Hoel, The overfitted brain: dreams evolved to assist generalization, Patterns 2021: https://arxiv.org/abs/2007.09560
- Wagner et al., Sleep inspires insight, Nature 2004: https://www.nature.com/articles/nature02223
- Cai et al., REM, not incubation, improves creativity by priming associative networks, PNAS 2009: https://www.pnas.org/doi/10.1073/pnas.0900271106
- Momennejad et al., Offline replay supports planning in human reinforcement learning, eLife 2018: https://elifesciences.org/articles/32548
- Dyna (Sutton 1990), summary: https://www.emergentmind.com/topics/dyna
- Rolnick et al., Experience replay for continual learning, NeurIPS 2019: http://papers.neurips.cc/paper/8327-experience-replay-for-continual-learning.pdf
- van de Ven, Siegelmann & Tolias, Brain-inspired replay for continual learning, Nat Commun 2020: https://pmc.ncbi.nlm.nih.gov/articles/PMC7426273/
