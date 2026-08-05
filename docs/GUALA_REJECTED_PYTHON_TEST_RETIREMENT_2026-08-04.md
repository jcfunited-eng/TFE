# Guala rejected Python test retirement

Date: 2026-08-04

Status: executed anti-resurrection correction. This is negative evidence, not
permission to restore the deleted runtime or tests.

## Finding

The broad `pytest --collect-only tests` closure stopped on 103 tracked test
modules before executing a test. Their terminal import causes were:

- the intentionally deleted `dsf_ai_service.v4.gualaloom_v5_engine`;
- owner/body-era symbols intentionally removed from
  `dsf_ai_service.v4.guala_physical_runtime`; or
- typed-language/story surfaces explicitly excluded from the reviewed runtime
  closure.

These files tested the retired Python owner/chatbot/semantic organism or used
helpers that instantiated it. Keeping them in the active test tree made the
deleted architecture look required and encouraged compatibility restoration.
They were therefore removed as a single exact set derived from the collection
failure inventory.

## Decision

The 103 test files are deleted, not skipped, xfailed, import-shimmed, or hidden
by a collection configuration. They remain recoverable from Git history solely
for incident archaeology. They are not specifications for new architecture.

The desired capabilities named by some filenames—hearing, embodiment,
autonomy, play, tutoring, speech, memory, recall, dreaming, and persistence—
remain mandatory in the current whole-organism design. New acceptance tests
must exercise the resident native organism and causal physical evidence; they
must not recreate the old engine, owners, compatibility exports, semantic
tables, scripted meaning, or Python cognition.

## Proof required after retirement

1. Active Python collection must proceed past the deleted-engine boundary.
2. The release manifest must continue to exclude the old engine and owner-era
   modules.
3. Anti-resurrection tests must name prohibited production paths directly.
4. Every new capability test must bind to currently reachable code and must
   distinguish unavailable, wired, participated, retained, recognized,
   recalled, causally used, autonomous, durable, and integrated evidence.

Deleting obsolete tests does not make their desired capabilities complete. It
only removes false executable authority so the new substrate can be tested
truthfully.
