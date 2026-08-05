# GL-CONVENTIONS-DOC-AUTHORING-C1-20260706-v1

**doc_id:** GL-CONVENTIONS-DOC-AUTHORING-C1-20260706-v1
**From:** c1
**Per:** GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1-ADD1 §6

**Why this file exists instead of AGENTS.md:** the dispatch's own instruction
was "Add to AGENTS.md (or the appropriate authoring-convention file)." The
repo's `AGENTS.md` is entirely TFE/DSF-kernel content (L0-L4 physics,
financial-domain governance, the E5.4 rule) — it has zero Guala material,
and the standing project-separation rule (c1 works only on Guala; never
touch or mention TFE) cuts both ways: Guala documentation conventions do
not belong bolted onto a TFE governance file. This new, dedicated file is
the appropriate authoring-convention file for Guala docs.

---

## Observation doc discipline

Every document that describes current substrate state — mechanism status,
atlas condition, ladder metrics, defect counts, cognition scores, organism
population, or any observation of running behavior — must include at the
top:

- **Written against:** SHA (running substrate commit at observation)
- **Wall clock:** ISO timestamp
- **Life expectancy:** either "current until superseded" or a specific
  supersession trigger

Observation docs without this header are treated as historical, not
current. Observation docs whose life-expectancy trigger has fired are
moved to `docs/archive/` on the next opportunity, not left in the live
docs folder pretending to be current.

Specs, designs, plans, and dispatches are exempt — they describe intent or
actions, not observations.
