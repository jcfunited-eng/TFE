# Corpus Operating Rules

Generated: 2026-03-16 UTC
Status: active IDE corpus rule

## Purpose

This file defines how corpora must be treated in this IDE.

It is a permanent working rule for this session.

## Core Rule

Corpora are not just current-state summaries.

They must be treated as two different layers:

1. current-state control surface
2. append-only running history

Both are required.

## Current-State Control Surface

A current-state control corpus exists to answer:

- what is true now
- what is the active workstream now
- what is the exact next step now
- what authority rules are active now

This file may be superseded by a newer version.

It is allowed to be replaced by a newer current-state file.

## Append-Only Running History

A history corpus exists to answer:

- what failed
- what succeeded
- when it happened
- what artifact proved it
- what blocker was exact
- what fix closed it
- what rule should prevent recurrence

This layer must not be overwritten as if older events no longer matter.

New entries must be added as history, not erased by a new snapshot.

## Required Corpus Behavior

From this point forward:

- every major workstream must have a current-state control surface
- every major workstream must also have an append-only history ledger
- current-state files must point to the relevant history ledger
- history ledgers must record both failures and accepted successes
- blocker entries must record one exact blocker only
- success entries must record the exact accepted proof artifact
- residual debt entries must be marked as debt, not disguised as closure blockers

## Minimum History Entry Fields

Each history entry should record:

- timestamp
- workstream or phase
- status
- exact scope
- exact blocker or exact success
- artifact path
- root cause
- fix or closure action
- prevention rule

## Forbidden Corpus Drift

The following are not allowed:

- treating snapshot corpora as if they are the full historical record
- replacing running history with a rewritten summary
- using a new corpus version to hide an older failure chain
- recording only failures and omitting accepted successes
- recording only successes and omitting exact blocker history

## Current Weakness To Correct

The current corpus set is still too snapshot-heavy.

That means:

- current-state control files exist
- but the running chronology is incomplete and split across artifacts

This must be corrected over time by maintaining explicit history ledgers, not by pretending the snapshots are enough.

## IDE Rule

This is now a permanent IDE working rule:

- when corpora are updated, treat them as history plus control surface
- do not treat them as snapshot-only documentation
