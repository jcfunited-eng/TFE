# Guala Production Deployment Protocol

Status: authoritative production procedure  
Effective: 2026-07-30  
Scope: Guala physical runtime, authenticated persistent state, and live observation pages

## Purpose

Deploy one reviewed Guala build without losing, duplicating, time-travelling,
flattening, or silently replacing the living substrate state.

This protocol preserves unchanged canonical L0-L4, explicit DSF fields, neurons,
learned sensory state, and one physical state owner. It does not authorize
Chi/Atlas cognition, scripted meaning, named sensory profiles, TTS-as-cognition,
ML, heuristic identity, or legacy compatibility state.

## Release authority

`tools/deploy_dsf_ai.sh` is the production release controller.
`tools/ecs_seal_transport.py` is the authenticated management transport for the
exact running owner. `tools/run_guala_candidate_rehearsal_task.py` is the
mandatory discarded-state rehearsal controller. Manual ECS actions are recovery
actions, not the normal release path, and must preserve the same zero-owner and
identity contracts.

## Required evidence before turnover

The candidate must have one reviewed commit, one immutable image digest, one
registered task definition, and passing tests proportional to the changed
surface. The running service must have exactly one owner:

- desired tasks: 1
- running tasks: 1
- pending tasks: 0
- one task in both the ECS service and task family
- task definition and resolved image digest equal the captured values

The exact owner must return authenticated deep readiness and identify:

- its organism identity
- deployment baseline generation, manifest, and tick
- active recovery generation, manifest, and tick
- active recovery as a distinct overlay

Any mismatch stops the deployment before state turnover.

Before the live owner is sealed, the exact candidate commit and image digest
must also pass one isolated production rehearsal. A one-off task mounts the
current sealed source read-only, materializes it into task-local storage,
performs one genuine physical sight-and-sound lesson through unchanged L0-L4
and the complete DSF fields, commits the affected owners, and cold-restores the
result exactly. The rehearsal must retain zero PCM bytes and is discarded when
the task exits. The task may observe a newer authenticated overlay than the
preflight observation; that exact overlay is named in its proof. A second
authenticated owner observation must prove that the production causal tick has
not changed during rehearsal. An equal-tick overlay publication refreshes the
exact generation and manifest used by the seal; a different tick aborts.

## Production turnover

1. Build and test the candidate. Push the immutable image and register its task
   definition. Re-read the image digest and task-definition storage contract.

2. Re-prove the original sole owner immediately before handoff. Do not rely on a
   census captured before the build.

3. Run the exact candidate image in the mandatory discarded-state rehearsal.
   Require its commit, image digest, source generations, identity, starting
   tick, full-field roots, changed owner roots, zero retained PCM, persistence,
   and cold-restore receipt to match. Re-prove the live owner state afterward;
   any causal tick change aborts without sealing production, while an
   authenticated equal-tick overlay refreshes the seal identity exactly.

4. Ask that exact owner to quiesce and seal through the authenticated local
   management route. The response must be nonce-bound and identify the sealed
   generation, identity, manifest, and tick.

5. Re-census the active recovery state after quiescence. Quiescence can publish
   a fresh equal-tick recovery overlay, so a pre-quiescence recovery UUID is
   evidence of history, not authority for the next step.

6. If the candidate owner schema differs, perform only the reviewed one-way
   authenticated migration while no application owner is running. The migration
   must preserve every historical owner byte except the exact declared schema
   changes, seal a distinct current-schema generation, cold-restore it, and
   produce an authenticated migration receipt.

7. Scale the service to zero and prove:

   - desired tasks: 0
   - running tasks: 0
   - pending tasks: 0
   - the prior task is stopped
   - no service or family task remains a state owner

8. While ownership is still zero, install the new task definition as the sole
   ECS scheduling authority. Prove there is exactly one PRIMARY deployment and
   that no older deployment retains any desired, running, or pending task.

9. Re-read the candidate image tag and require the same immutable digest. Then
   raise desired count from zero to one.

10. Admit exactly one new owner. Its task definition, image digest, mounted
   persistent volume, storage ceilings, and startup state must match the release
   evidence.

11. Require authenticated deep readiness from the new task. The response must
    match the deployed task definition and image digest and must expose the exact
    active generation, manifest, identity, and tick.

12. Read the sealed generation manifest and count its authenticated owner-state
    records. Cold restoration must succeed without migration authority after a
    migration has been published.

13. Verify the public observation API and both live human pages. A page returning
    HTTP 200 is necessary but not sufficient: its observation must come from the
    deployed task and truthfully show mounted, active, quiescent, or unavailable
    mechanisms without invented activity.

14. Record the release evidence and send the checked Slack completion notice.
    A release is not complete before that notice succeeds.

## Failure and recovery rule

Before a new generation is sealed, the original owner may continue unchanged.
After a successor generation is sealed, an older image must never be restarted
against the successor schema. Recovery must keep ownership at zero, build or
select a compatible immutable image, install that task definition at zero, and
then admit exactly one owner. No recovery may move `CURRENT` to an older lived
tick or restore a disconnected legacy brain.

An ambiguous response after the irreversible seal boundary is treated as a
possible successful seal. The controller must fail closed to zero owners and
inspect authenticated state before any task is allowed to start.

## Schema-extension rule

An owner-schema extension is accepted only when its exact migration set is named
in code, authenticated by the migration proof, admitted by startup, and proven
by a cold round trip. An arbitrary extra file remains a startup failure.

The 2026-07-30 extension consists exactly of:

- `whole_organism_internal_reentry_genesis`
- `autonomous_experience_driver_genesis`
- `passive_whole_organism_thing_learning_v1_to_v2`
- `embodied_vocal_body_world_to_anatomy_edge`

The exact retired legacy purge-proof path is admitted only to bounded
materializer retirement; it is not restored as cognition.

## First protocol evidence

The first completed deployment under this corrected sequence is:

- task definition: `dsf-ai-task:809`
- deployed code commit: `991d3dedbabe4542fc9683e13570a793b3846811`
- image digest:
  `sha256:e74ddd17b6b8bf544fd5980ccaadf3663204b0c973830fc117f6387b4b80d19f`
- active generation: `e62ef452-fa72-42ad-a89d-88e9156bb652`
- generation manifest:
  `25503c7f7009da1454f464406b30bd69a3e94de8f693a2d7ea7d10cd81ce2d50`
- lived tick: `23723727`
- authenticated owner-state records: 50
- ECS service: desired 1, running 1, pending 0, rollout completed
- public pages:
  `https://dsf-ai.com/gualaloom.html` and
  `https://dsf-ai.com/loomscan.html`

This evidence proves deployment, ownership, persistence, and observation
integrity. It does not claim that a curriculum lesson has already occurred or
that learned speech has already emerged.
