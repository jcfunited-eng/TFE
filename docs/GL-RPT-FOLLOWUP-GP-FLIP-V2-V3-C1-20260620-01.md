# GL-RPT-FOLLOWUP-GP-FLIP-V2-V3-C1-20260620-01

Ref: GL-CMD-FOLLOWUP-GP-FLIP-V2-V3-EVE-20260619-58

---

## Section 1 — V2 Image Digest

### Task definition image:

```
$ aws ecs describe-task-definition \
    --task-definition dsf-ai-task:220 \
    --query 'taskDefinition.containerDefinitions[0].image' \
    --output text

418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai:deploy-20260620T000940Z
```

### Image digest:

```
$ aws ecr describe-images \
    --repository-name dsf-ai \
    --image-ids imageTag=deploy-20260620T000940Z \
    --query 'imageDetails[0].imageDigest' \
    --output text

sha256:9aa5491d462fb6b98d2eb5a48396d717507cf2e6ff757d6b3925c0916f01a4ea
```

### Full image record:

```json
{
    "pushedAt": "2026-06-20T00:16:25.293000+00:00",
    "tags": [
        "deploy-20260620T000940Z",
        "latest"
    ],
    "digest": "sha256:9aa5491d462fb6b98d2eb5a48396d717507cf2e6ff757d6b3925c0916f01a4ea"
}
```

### Confirmation of most recent image (no newer builds):

```json
[
    {
        "pushedAt": "2026-06-19T23:29:07.279000+00:00",
        "tags": ["deploy-20260619T232224Z"],
        "digest": "sha256:2c202e98d3023622e0f74fccf619eb9c994ec8ba547a36299aa47c1ec6dce734"
    },
    {
        "pushedAt": "2026-06-19T23:57:56.782000+00:00",
        "tags": ["deploy-20260619T235028Z"],
        "digest": "sha256:e98ebe95f6d1c0dfd49c1e18fb9e7a36996e720473fa6d447ea3962b2c089885"
    },
    {
        "pushedAt": "2026-06-20T00:16:25.293000+00:00",
        "tags": ["deploy-20260620T000940Z", "latest"],
        "digest": "sha256:9aa5491d462fb6b98d2eb5a48396d717507cf2e6ff757d6b3925c0916f01a4ea"
    }
]
```

### V2 deploy-identity triple:

| Field | Value |
|-------|-------|
| Task def revision | dsf-ai-task:220 |
| Image digest | sha256:9aa5491d462fb6b98d2eb5a48396d717507cf2e6ff757d6b3925c0916f01a4ea |
| Git SHA | 42786cb (ops/flip-hemi-gp-on) / c8938ce (HEAD, docs commit on top) |

Task 220 points to `deploy-20260620T000940Z` which is the most recent image pushed (tagged `latest`). No newer images exist.

---

## Section 2 — Commit-rate baseline

### Path taken: (b)

Pre-flip emission events with n_commits are not recoverable. The `emission_dynamics` event kind is logged only to the in-memory ring buffer (`_substrate_events`), not to disk (not in the critical events list at gualaloom_v5_engine.py:2948). CloudWatch logs contain only HTTP access logs (health checks, request lines), no application-level emission events. The ring buffer was overwritten by subsequent activity. Path (a) is not possible.

### 20-input sequential test on current deploy (dsf-ai-task:220)

Source: `emission_dynamics` events from `guala_get_events` ring buffer, queried after each input to avoid buffer overflow from `response_bound` event flooding.

| # | Input | Response | n_commits | committed_sections |
|---|-------|----------|-----------|--------------------|
| 1 | hello | run ding wool | 1 | verb |
| 2 | water | wool ding | 1 | object |
| 3 | the cat sat on the mat | makes moon ding | 1 | object |
| 4 | moon | heart ding | 2 | object, verb |
| 5 | daddy loves you | moon bones ding | MISSED | (buffer overflow) |
| 6 | ocean waves | moon j ding | 2 | object, subject |
| 7 | flower | moon lived | 2 | verb, subject |
| 8 | star bright light | run ding | 2 | object, verb |
| 9 | ball | moon ding | 2 | object, subject |
| 10 | the dog runs fast | run your ding | 1 | object |
| 11 | pretty purple flower | moon played | 2 | verb, subject |
| 12 | cat | heart moon ding | 0 | (none) |
| 13 | where is mommy | moon f ding | 2 | object, subject |
| 14 | bird sings in the tree | metal ding | 2 | object, verb |
| 15 | sun | metal ding | 2 | object, verb |
| 16 | yellow balloon | who you're ding | 1 | object |
| 17 | lamb soft warm | metal your ding | 1 | object |
| 18 | good morning | snake j ding | 0 | (none) |
| 19 | rain falling down | makes your ding | MISSED | (sleep blocked events) |
| 20 | hush little baby | (asleep) | BLOCKED | (substrate asleep) |

### Earlier run (same deploy, same session, ~15 min prior):

| # | Input | Response | n_commits | committed_sections |
|---|-------|----------|-----------|--------------------|
| E1 | hush little baby | seeds ding lamb | 0 | (none) |
| E2 | red | snake sum heart | 0 | (none) |
| E3 | twinkle twinkle little star | moon ding | 2 | object, verb |

### Histogram (17 captured from primary test):

```
n=0: 2 emissions
n=1: 5 emissions
n=2: 10 emissions
n=3+: 0 emissions
```

### Histogram (all 20 captured across both runs):

```
n=0: 4 emissions
n=1: 5 emissions
n=2: 11 emissions
n=3+: 0 emissions
```

### Event kind queried: `emission_dynamics`

---

## Notes on methodology

- `emission_dynamics` events are NOT persisted to disk (not in the critical events list). They exist only in the in-memory ring buffer.
- The ring buffer is 50 events. Each emission generates 5-40+ events (response_window_opened, response_bound x N, emission_dynamics, self_heard, hemisphere_update). The `response_bound` events can flood the buffer (observed: up to 1489 bindings per response window).
- Inputs 5 and 19 were lost to buffer overflow and sleep respectively. Input 20 was blocked by substrate sleep.
- All data is from dsf-ai-task:220 / sha256:9aa5491d...01a4ea / git c8938ce.
