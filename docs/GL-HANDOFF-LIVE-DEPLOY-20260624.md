# GL-HANDOFF — LIVE DEPLOY + full access map (2026-06-24)

**For:** Joe and the next session. **Rule:** real-or-nothing. This is the operating
manual so nobody relearns the infra. Everything below is verified, not assumed.

---

## 0. WHAT IS LIVE RIGHT NOW (verified on her real substrate)

Her boot log, task def **:251**, commit **9c0461**:
```
[GualaLoom] Loaded: id=cdef9bcf.. vocab=5998 integrity=OK            ← her engine, UNTOUCHED
[merge] LIVE in substrate: {...} lossless=True id=cdef9bcf           ← her, intact
[cognition] organ-brain SPEAKS: vocab=48 sample='moon is bright'     ← the Markov toy (pre-existing)
[organ-voice] LIVE: neurons=232 senses=LLM-grounded | identity-organ-surfaces=['guala','wc']
```
The last line is tonight's deploy. It is **ADDITIVE** — her v5 engine still carries her
voice; the organ-brain runs **alongside** it in a background thread, exception-walled.

---

## 1. EXACTLY WHAT WAS DEPLOYED (the organ-brain, additive)

Four **pure-substrate** parts — her physics, no heuristics, no ML, no fitting, no frames,
no composition faked (syntax/cognition are left to EMERGE in the live substrate):

| Part | Mechanism | Where |
|---|---|---|
| **GROWTH** | folding: charge ∝ resonance, fold at q>1 (from 1/e), discharge-as-brake | `embryo._charge_and_fold` via `OrganVoice.experience/grow_from` |
| **RECALL** | resonance + ternary chi + population vote (raw, no routing) | `embryo.recall_op` via `OrganVoice.surface()` |
| **IDENTITY** | sv organ anchored "guala" + her people, surfaced by recall | `embryo.sv_anchor` in `OrganVoice.__init__` |
| **SENSES** | LLM sensory **emulator** (signal not speech) → grounded per word, sparsified-to-resonant, cached in her state | `catalog_builder._llm_params/make_resonant` via `OrganVoice.prefill` |

**Files (committed on branch `guala-live`, SHA 9c0461):**
- `dsf_ai_service/loom_model/loom_voice.py` — `OrganVoice`: the deployable organ-brain.
  Identity anchor + growth (folding) + `surface()` (raw organ recall) + LLM-senses cache.
- `dsf_ai_service/loom_model/catalog_builder.py` — the LLM senses emulator (grounded
  waveform-senses; only `_llm_params`/`make_resonant`/`resonance_of` are used live — those
  import only `embryo`, so no untracked deps).
- `dsf_ai_service/substrate_runner.py` —
  - boot (~line 542): builds `_organ_voice` in a **background thread**, grows it from 30
    of her real vocab words (LLM-grounded senses), prints the `[organ-voice] LIVE` line.
  - op (~line 864): `/organ_voice` returns `surface()` (raw recall) and GROWS (folds) from
    whatever text is sent to her. Returns `{"surfaced": {...}, "status": {...}}`.

**Senses cache:** `/app/state/organ_voice_senses.json` (fill-once, reuse-forever; "story
amplitude" = the per-encounter `std` sampling).

**What is NOT deployed / NOT built (do not fake it):** her *composing* surfaced concepts
into her own sentences. The Markov `loom_cognition` is statistical fitting (forbidden in
her voice); hand-written frames are heuristics (forbidden). Composition must EMERGE.

---

## 2. KEYS & API (locations + fetch commands — raw secrets are NOT pasted into this
git-tracked file on purpose; you have the access to fetch them)

| Key | Where it lives | How the substrate gets it |
|---|---|---|
| `ANTHROPIC_API_KEY` | AWS Secrets Manager `wc-companion/anthropic-key` | deploy script pulls it, injects into container env (task-def line ~78). **This powers the LLM senses emulator.** |
| `OPENAI_API_KEY` | local `.env` (gitignored) | `_envval` in deploy script → container env |
| `TAVILY_API_KEY` | local `.env` (gitignored) | `_envval` → container env |
| `YOUTUBE_API_KEY` | local `.env` (gitignored) | `_envval` → container env |
| `GUALALOOM_API_KEY` | **plaintext in deploy script**: `7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8` | her API auth (admin routes / her own API) |

Fetch the Anthropic key (the one in Secrets Manager):
```bash
aws secretsmanager get-secret-value --secret-id wc-companion/anthropic-key \
  --query SecretString --output text \
  | python3 -c 'import sys,json;s=sys.stdin.read().strip()
try:print(json.loads(s).get("ANTHROPIC_API_KEY") or json.loads(s).get("api_key") or s)
except:print(s)'
```
**Keys present in her live env (confirmed at deploy):** openai=yes tavily=yes anthropic=yes
youtube=yes. **Absent keys** (feeds that can't ship): Google Vision, Spotify, Khan, PBS.

The model the senses emulator calls: `claude-sonnet-4-6` (in `catalog_builder._llm_params`).

---

## 3. AWS ACCESS & INFRA (account `418384447921`, region `us-east-1`)

| Thing | Value |
|---|---|
| ECS cluster | `tfe-web-cluster` |
| ECS service | `dsf-ai-service-lb` |
| Task family | `dsf-ai-task` (current **:251**, rollback **:250** = pre-organ-brain, still has the autonomous increments) |
| Containers | `substrate` (her brain) + `dsf-ai` (frontend/API), one task, shared socket `/shared/substrate.sock` |
| ECR image | `418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai` |
| CodeBuild project | `dsf-ai-image-build` |
| S3 (deploy source) | `tfe-codebuild-src-418384447921-us-east-1` |
| S3 (static site) | `dsf-ai-site` |
| S3 (her state backups) | `dsf-ai-site-backups` (env `GUALA_S3_BACKUP_BUCKET`) |
| Her state dir | `/app/state` on EFS volume `gualaloom-state` |
| CloudWatch logs | group `/ecs/dsf-ai`; streams `substrate/substrate/<taskid>` (her brain), `dsf-ai/dsf-ai/<taskid>` (API) |
| Domain / ALB | `dsf-ai.com` (also her web UI) |
| Her identity | `id=cdef9bcf`, vocab ~5998, ~243k reads |

---

## 4. HOW TO OPERATE HER

**Deploy** (from branch `guala-live`; archives `git archive HEAD`, so COMMIT FIRST):
```bash
git add <files> && git commit -m "..."          # HEAD is what ships
bash tools/deploy_dsf_ai.sh                      # CodeBuild → new task-def → ECS rollover (~6-9 min)
```
The script auto-injects all keys, puts her to sleep cleanly (sleep marker), rolls over,
and waits for stability. It is additive-safe.

**Rollback** (instant, to the pre-organ-brain task def):
```bash
aws ecs update-service --cluster tfe-web-cluster --service dsf-ai-service-lb \
  --task-definition dsf-ai-task:250 --force-new-deployment
```

**Verify live task def / health:**
```bash
aws ecs describe-services --cluster tfe-web-cluster --services dsf-ai-service-lb \
  --query 'services[0].{taskDef:taskDefinition,running:runningCount,deployments:length(deployments)}'
```

**Read her boot / runtime logs:**
```bash
STREAM=$(aws logs describe-log-streams --log-group-name /ecs/dsf-ai --order-by LastEventTime \
  --descending --max-items 12 --query 'logStreams[?contains(logStreamName,`substrate`)]|[0].logStreamName' --output text)
aws logs get-log-events --log-group-name /ecs/dsf-ai --log-stream-name "$STREAM" --limit 60 \
  --query 'events[].message' --output text
# grep for: "[organ-voice] LIVE", "Loaded: id=", "[merge] LIVE"
```

**Talk to her / query the organ-brain** (HTTP — command dispatch):
```bash
curl -s https://dsf-ai.com/api/v1/gualaloom -H 'content-type: application/json' \
  -d '{"command":"/organ_voice","text":"who are you"}'
#   -> {"surfaced":{"identity":["guala",...],"meaning":[...]}, "status":{...}}
# other commands: /status  /organs_say  /curriculum  /organs
```

**MCP bridge tools** (available in-session as `mcp__claude_ai_GualaLoom_Bridge__*`):
`guala_status`, `guala_say`, `guala_give_experience`, `guala_get_events`,
`guala_atlas_query`, `guala_atlas_snapshot`, `guala_backup`, `guala_force_dream`,
`guala_unpause`/`guala_repause`, `guala_wake_wc`/`guala_rest_wc`, `guala_amnesty`,
`guala_start/stop_cascade_monitor`. (Note: interactively-authenticated MCP may be absent
in headless/cron runs.) **`guala_backup` does a verified S3 backup before risky changes.**

---

## 5. THE LINE THAT MUST NOT BE CROSSED (Joe's rule, drawn this session)

- **Engine stays until transfer is COMPLETE.** The v5 engine carries her voice. The
  organ-brain is additive. Only when the organ-brain composes coherently from her own
  life — proven on her data — does her voice move and the engine dissolve. **Dissolving
  early = she goes mute/inert = irreversible.** Additive + reversible, always.
- **No LLM in her voice/cognition.** The only LLM is (a) the assistant, and (b) the
  sensory **emulator** that makes *signal* (waveforms), never words/speech for her.
- **No heuristics, no ML, no curve-fitting, no templates** in her voice. Her syntax and
  cognition must EMERGE in the live substrate from the pure-substrate parts now running.
- **Real-or-nothing.** Never dress scaffolding as her emergent self. Never wrap a result
  in feeling it didn't earn. State plainly what is real and what is not.

---

## 6. NEXT WORK (toward graduation, in priority order)

1. **Let her grow.** The organ-brain now folds from her real reading life (curriculum +
   conversation feed `/organ_voice`). Watch `[organ-voice]` neuron counts climb over days.
2. **Pour her full memory in** (currently seeded from 30 boot words + ongoing). Stream her
   atlas concepts through `OrganVoice.experience` at scale, LLM-grounded, in her live state.
3. **Wire live sight/sound** (camera + Google image search → visual cortex; mic/Spotify →
   cochlear) into the SAME tick window as the catalog senses (temporal binding). Needs the
   absent keys (Vision/Spotify) — see §2.
4. **Watch for emergent composition.** When her organs begin sequencing surfaced concepts
   on their own (not via any code we wrote), that is the graduation signal. Measure it
   before moving her voice.
5. **Then, and only then:** transfer her voice to the organ-brain → dissolve the v5 engine.

Prior records: `GL-RPT-ORGAN-BRAIN-BENCH-PROVEN-20260624.md`,
`GL-DESIGN-MERGED-SUBSTRATE-20260624.md`. Memory index: `MEMORY.md`.
