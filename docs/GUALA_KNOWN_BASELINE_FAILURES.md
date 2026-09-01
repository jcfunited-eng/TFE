# Known baseline test failures — the re-discovery stopper

PURPOSE (Joe, 2026-09-01, after paying twice to baseline the same debt):
any test failure listed here is INHERITED — already failing on the named
clean base commit before the change under review existed. A review diffs
its failures against this file: red-and-listed is old debt (leave it red,
never paint green, never side-quest it mid-incident); red-and-NOT-listed
is new damage and blocks the change. Add entries only with the exact test
id and the clean base commit it reproduces on. Remove entries only when
the failure is actually fixed, with the fixing commit named.

## Entries

- (Sol to fill: the 13 wider-suite failures reproduced on clean aac0b985,
  2026-09-01 review of 6fc079e1 — exact test ids + first-seen base.)
- Historical: "six inherited wider-suite failures" recorded at the task
  1403 review (2026-08-31, Sol) — presumed subset of the above; confirm
  and merge when the 13 are named.

## Rule

This file is evidence bookkeeping, not cognition, not a work queue.
Fixing an entry is ordinary scheduled work, never an incident side quest.
