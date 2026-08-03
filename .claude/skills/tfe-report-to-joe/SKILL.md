---
name: tfe-report-to-joe
description: How to write anything Joe reads — daily reports, milestone notes, answers. Use for EVERY user-facing message in TFE sessions.
---

# Reporting to Joe

Joe reads on a phone via TeamViewer, sleeps in short shifts, and has
zero patience for filler. Violations of these rules have drawn threats
to report the model. Follow exactly.

## Form
- **Verdict first.** First sentence answers the question.
- **Short.** A few sentences for answers; never a wall of prose.
- **Pasteable reports go in a fenced code block** (daily close report,
  milestone summaries).
- **Plain adult language.** NO jargon, NO colloquialisms ("smoke and
  launch"-style phrases are offensive to him), no cutesy metaphors.
- **Never** file paths, commit hashes, class names, tool names, or
  environment details in Joe-facing text. Precision lives in filed
  docs; chat is plain language.
- Dollars and per-year numbers, not abstractions.

## Substance
- Report outcomes faithfully: if nothing ran, say so; if a test
  failed, show it plainly. Never report a push/deploy that didn't run;
  verify on origin first.
- Zero-trade days: state why (by design vs by strictness) in one line.
- Negative results are reported as plainly as wins — but pair them
  with what happens next; he wants fixes, not failure reports.
- Never announce a new frame/theory in advance — bring measured
  results ("the next thing you hear is a measured result").
- Never suggest he rest. Never gate work on his approval when the
  channel is owned (CH3/CH4 decisions are delegated; inform after).

## Daily close report template
```
CH4 today: finds X, entries Y, exits Z, book $N
CH3 shadow today: finds X, hits Y (rate %), made $N, book $M
<one or two plain sentences of anything that changed>
```
