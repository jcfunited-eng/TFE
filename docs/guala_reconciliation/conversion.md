# September 14 native-to-functional cutover: recovered evidence

This refines R01 in [findings](findings.md). It is an evidence account, not a
restoration instruction. A1 executed no organism or native code and made no
remote changes.

## Recovered pre-conversion body and world

The original conversation names
`s3://guala-incident-bench-20260831/captures/0914d/current.zip` as the backup.
It still exists. S3 reports September 14 at 04:07:54 UTC. Its SHA256 is
`901bc9e14e3b5a50d4874bb6a17bff4a2838f63f6256cc1bdf429706d3291bd4`, matching
the recorded release-plan backup. The archive contains `body.glorun.gz`,
`world.json` and `pointer.json`.

| Boundary | Independently checked result |
|---|---|
| Native body | 411,765,026 decoded bytes; `GLORUN01` v1 and `GLMFAB11` fabric. |
| Identity / tick | `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1` / 711060. |
| Body SHA256 | `f6ad55d79c9cd4984c7f2f3a8535d7986b21e2629172fb68bce8f079dfeb2383`. |
| Paired world | 63,659 bytes; SHA256 `2a93c1af663448074bc7857c1b78a530ee8240860509c48c9e5f70f1ab5b7da1`. |
| Pointer | All six current identity/tick/size/hash fields match the decoded body and world. |
| Integrity | ZIP/gzip reading, CRC, stream length and independent SHA256 validation passed. |

The backup's predecessor is referenced in its pointer; its contents are not
included. A separate stalled-body archive was also preserved and validated at
tick 710377. Its failure provenance must travel with it; it is not a restore
recommendation. The two smaller September 7 native checkpoints remain distinct
older evidence, not substitutes for this body/world pair.

## Historical execution record

[Original tool results](cutover-records.json) preserve timestamps, source file,
byte offsets, record hashes and text hashes. They show:

- 04:16:30 UTC: predecessor service on Task 1466, native live tick 711208.
- 04:18:30: image `909aec4dab5ad2a7174bdca8d1cfb642626280b77182fb777f839e515653c250` pushed; a rehearsal reports 400 functional beats and cold continuation. These are historical reported test results, not independently rerun capability proof.
- 04:21:13: release-plan backup fields match the archive recovered today, including its archive/body/world hashes and tick 711060.
- 04:21:41–48: desired/running counts at zero for the old service during cutover; the plan identifies live tick 711275 and the functional image.
- 04:26:26: cutover exits zero; service identifies Task 1467; live observation reports `kind functional`, tick 711418, and authored babble. The continuity record identifies a native predecessor at tick 711295 and marks `functional_conversion: true`.

The final predecessor receipt names **411,890,924 bytes**, body SHA256
`2d4f7587e73fa349c014a37aaf5c39dcc7f40c3bdd62d4d8a5137f71ae8149c3`,
world SHA256 `86b3cf451f8ac8a1161f416d5626b38461d473ea0d9fb44ee01a8bb055539738`
and 63,663 world bytes. That is **235 ticks later** than the recovered backup.
Its exact body/world bytes have not been recovered in this audit. Do not label
the earlier archive “the final native state.”

The source conversion constructs genesis at the old identity/tick without
translating native cognition. A contemporaneous report calls the rehearsal's
new functional body 602 bytes; the original draft initially contains `XX`
placeholders and is not itself a completed receipt. The recorded later
functional checkpoint has 18,044 bytes. Size reduction alone does not quantify
lost capabilities; the conversion code establishes that native contents were
not translated. A continuity-health label proves neither memory migration nor
learning.

## Authorization and remedy

D17–D18 authorize removing overhead after the assistant proposed direct act
laws and said existing physics could continue perception/memory. The recovered
exchange does not disclose or approve dropping native learned contents. D16
requires experiences to be preserved. Do not erase the genuine simplification
authorization, and do not enlarge it into undisclosed memory-loss approval.

The claim that the 411 MB body no longer exists anywhere is disproved by the
recovered backup. Removal from the active rotating store is a different claim.
The existence of bytes does not qualify the old architecture as compliant or
all its contents as learned memory.

**Recommended next item:** trace the final predecessor hash and then compare
retained physical structures in the authenticated earlier backup against the
current native owner, with exact historical source/codec custody. G1 owns the
candidate; A1 verifies. Preserve current history and both recovered pairs. Do
not automatically restore the old process, transplant semantic/reward records,
or call a new genesis a migration. If the last 235 ticks cannot be recovered,
record that precise boundary rather than declaring all history lost or fully
continuous.

## Independent post-conversion archive

`captures/0914e/current.zip`, stored at 04:51:27 UTC on September 14, contains a 30,624-byte `GLFUNC01` JSON body and paired world. Independent hashes and all current pointer fields agree. Its body carries the same identity at tick 715775 and stores explicit `approached` object names and action episodes. This is recovered post-conversion state, not merely a reported observation. See [receipt](indexes/post-conversion-archive-integrity.json). It does not classify every later adaptive operator. The first audit JSON check used the wrong tick-key name and failed before writing; exact historical source established `tick` versus the pointer field `organism_tick`, and the corrected check passed.

The scratchpad filename `controller-cutover-functional.log` survives, but its current contents describe Task 1510 to Task 1511. It was reused and cannot stand in for the September 14 log. Original conversation tool records retain the earlier receipt. Paths cannot substitute for content hashes and timestamps.
