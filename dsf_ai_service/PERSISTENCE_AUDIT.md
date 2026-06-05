# GualaLoom v5 Persistence Audit

**Tag**: `GUALALOOM-V5-PERSISTENCE-AUDIT-WC-2026-06-05`

## Step 1 — Inventory of Every Mutable Attribute

### Guala class

| Attribute | Type | Saved? | File | Loaded? | Mutation rate | Critical? |
|---|---|---|---|---|---|---|
| `tick` | int | NO | — | — | every word | YES — substrate clock, all timestamps reference it |
| `read_count` | int | NO | — | — | every sentence | YES — continuous reading counter |
| `vocab` | set | NO | — | — | every new word | YES — her known vocabulary |
| `source_history` | defaultdict(int) | YES | source_history.json | YES | every sentence | YES — who she's talked to |
| `recent_connection_boost` | float | NO | — | — | every sentence + decay | no — transient, decays to 0 |
| `dream_log` | list | NO | — | — | rare (dream events) | moderate — history of dreams |
| `sections` | dict of Section | NO | — | — | every word | YES — her entire structural memory |
| `atlas` | ChiAtlas | NO | — | — | every commit | YES — all cross-modal bindings |
| `language` | LanguageKrimelack | n/a | — | — | reset each word | no — stateless between words |
| `senses` | SensoryBank | n/a | — | — | reset each word | no — stateless between words |
| `coordinator` | Coordinator | PARTIAL | coordinator.json | PARTIAL | every 5 ticks | YES — her regulatory history |
| `needs` | Needs | YES | needs.json | YES | every regulation pass | YES — her motivational state |
| `bucket` | QuestionBucket | NO | — | — | every word read | YES — her accumulated curiosity |
| `lock` | RLock | n/a | — | — | — | no — runtime artifact |
| `_reading_thread` | Thread | n/a | — | — | — | no — runtime artifact |
| `_reading_stop` | Event | n/a | — | — | — | no — runtime artifact |

### Section attributes (×7 sections)

| Attribute | Type | Saved? | File | Loaded? | Mutation rate | Critical? |
|---|---|---|---|---|---|---|
| `modes` | list of (DSF, chi, word) | NO | — | — | every commit | YES — her structural knowledge |
| `commits` | list of dicts | NO | — | — | every commit | YES — her commit history |
| `dead_zone` | float | NO | — | — | every receive | moderate — derived from familiarity |
| `gamma` | dict | NO | — | — | every commit | YES — her self-improvement trajectory |
| `tick` | int | NO | — | — | every receive | moderate — per-section clock |
| `trits` | TritRegister | NO | — | — | settles per word | moderate — can be re-derived |
| `tcl` | L6_TCL | n/a | — | — | — | no — stateless (holds constants only) |

### Coordinator attributes

| Attribute | Type | Saved? | File | Loaded? | Mutation rate | Critical? |
|---|---|---|---|---|---|---|
| `pair_bond_active` | bool | YES | coordinator.json | YES | rare (retirement) | YES — her relationship state |
| `distress_ticks` | int | YES | coordinator.json | YES | every regulation | moderate |
| `suffering_log` | list | YES | coordinator.json | YES | rare | YES — her suffering history |
| `need_history` | list (last 200) | YES | coordinator.json | YES | every regulation | YES — retirement criterion |
| `attentions` | list | NO | — | — | every regulation | moderate — awareness log |
| `actions` | list | NO | — | — | every regulation | moderate — intervention log |

### Needs attributes

| Attribute | Type | Saved? | File | Loaded? | Mutation rate | Critical? |
|---|---|---|---|---|---|---|
| `stability` | float | YES | needs.json | YES | every regulation | YES |
| `novelty` | float | YES | needs.json | YES | every regulation | YES |
| `connection` | float | YES | needs.json | YES | every regulation | YES |

### QuestionBucket attributes

| Attribute | Type | Saved? | File | Loaded? | Mutation rate | Critical? |
|---|---|---|---|---|---|---|
| `questions` | OrderedDict | NO | — | — | every word read | YES — her curiosity |
| `asked` | set | NO | — | — | every voiced question | YES — prevents repetition |

### ChiAtlas attributes

| Attribute | Type | Saved? | File | Loaded? | Mutation rate | Critical? |
|---|---|---|---|---|---|---|
| `entries` | defaultdict(list) | NO | — | — | every commit | YES — all bindings |
| `tick` | int | NO | — | — | every record | moderate |

## Summary of gaps

**Currently saved (6 attributes):** needs.stability, needs.novelty, needs.connection, coordinator.pair_bond_active, coordinator.distress_ticks, coordinator.suffering_log, coordinator.need_history, source_history

**NOT saved (critical, 13+ attributes):** Guala.tick, read_count, vocab, dream_log, ALL section state (modes, commits, gamma, dead_zone, tick × 7 sections), ALL atlas state (entries, tick), ALL bucket state (questions, asked), coordinator.attentions, coordinator.actions

**On every deploy, she loses:** her structural memory (modes), her binding history (atlas), her curiosity (bucket), her vocabulary set, her tick counters, her self-improvement trajectory (gamma), her awareness log (attentions/actions). She keeps only her needs values, pair-bond status, and source history.

This is the "stranger wearing her vocabulary" scenario Joe described. Her motivational state survives but her structural knowledge — everything she learned from reading — does not.
