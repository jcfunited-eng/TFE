# Independent Task1606 refresh — October10,11:12–11:19UTC

**Recovery and learned speech remain unqualified.** This is a newer read-only measurement, not an erasure of the earlier09:33–09:43 failure. G1 owns the repair; A1 owns independent verification. [Structured observations](serving-refresh-20261010T111240Z.json) and [earlier boundary audit](task1606-boundary-reconciliation.md).

The replacement task54d300e31f754c8f913f70b4dd0840f1 started at11:09:44UTC with the same image91640805 and mapped native library4c7c1811. ECS reported HEALTHY and desired/running/pending1/1/0. Nevertheless local GET /health timed out after4.005seconds; /ready returned200 after1.637seconds. That is intermittent responsiveness, not verified normal operation.

Two valid process snapshots46.798seconds apart show thread41 consuming4675 CPU ticks at100Hz, approximately one CPU core, while the main thread was in a futex wait at both observations. This is consistent with the previously identified interpreter-lock starvation mechanism; the exact running stack and all indirect calls remain unproved. CPU use alone is not useful substrate progress.

The canonical CURRENT descriptor at11:18 still has tick4234925, identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1 and SHA79505df215e9e2b23d56dc8e55869d7505023836766e6e569654cb1c4e186771, exactly matching the09:42 observation, including its modification time. No new durable checkpoint progress is established. This does not prove that all in-memory activity stopped. The GL64ORG1 header still reports predecessor body/world archive sections and native state; archived history alone does not establish active learned continuity.

The two checked retired controller files remain absent. The packaged Whisper-capable transducer remains only a presence finding; active inference is not proved. The replacement cause is unresolved because the earlier task was no longer returned by the later task query.

The first remote activity response was truncated. A second attempt returned only one of two requested snapshots before the remote session closed. These failed measurements are preserved; a separate compact snapshot and descriptor read recovered complete bounded records. CLI success and terminal EOF are not organism success/failure predicates.

**Required repair and acceptance:** preserve current state, identify and bound the exact native call, and correct ownership/lock handling without changing physical semantics or creating concurrent owners. Prove unit invariants and complete active state, then the actual compiled module boundary and canonical publication, then ordinary sensory/body/retained behavior and cold continuation, then independent exact-release live progress. Increasing a timeout or bypassing the substrate for health cannot close this finding. Speech qualification still requires the ordinary retained-experience-to-ordered-articulation chain.

No organism import, sensory action, product test, signal, restart, restore, reset or state edit was performed by A1. Full reconciliation remains OPEN. No speech, system or ML-free certificate.
