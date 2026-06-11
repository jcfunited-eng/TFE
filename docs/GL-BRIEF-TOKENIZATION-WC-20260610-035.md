# GL-BRIEF-TOKENIZATION-WC-20260610-035
## Input Tokenization — Punctuation Stripping in converse() and read_sentence()

**Author:** wC | **Date:** 2026-06-10 | **Status:** AUTHORIZED FOR PROD (Joe, 2026-06-10)
**Input:** GL-FIND-INPUT-TOKENIZATION-C1-20260610

## Problem
`converse()` strips only `, . ?`; `read_sentence()` strips only `, .`. All other
punctuation stays glued to words: "body (e.g. the arm)" tokenizes as
["body", "(e", "g", "the", "arm)"]. Junk tokens like "(e" install as vocabulary,
create atlas entries, and surface in emissions ("what is (e").

## Fix
Single normalization function used by BOTH converse() and read_sentence():
1. Strip/separate punctuation: ( ) [ ] { } : ; ! ? " ' , . — - … and unicode
   quote/dash variants. Apostrophes INSIDE words preserved (don't, it's).
2. Lowercase (existing behavior), collapse whitespace.
3. Drop resulting empty tokens and bare single-character punctuation remnants.
4. NO other behavior change: no stemming, no stop-word removal, no vocabulary
   filtering. She keeps every real word, including weird ones — only
   typographic junk is removed.

## Existing junk vocabulary
Do NOT mass-purge installed junk tokens in this deploy (entries like "(e",
"arm)", "body)"). They are low-dwell, unreinforced; metadecay (033) fast channel
will wash them out naturally within hours of deploy. Mass deletion risks
touching adjacent chi entries. Exception: if any junk token appears in deep
atlas, report it (should be impossible — dwell gate — but verify).

## Safety
Small, pure-function change. Unit test the tokenizer with the FIND's exact
failure inputs before deploy. No env var needed; rollback = revert commit.

## Acceptance
The FIND's input "body (e.g. the arm)" produces ["body", "e", "g", "the", "arm"]
or ["body", "eg", "the", "arm"] (implementer's call, stated in report); no new
punctuation-glued vocabulary after deploy; Joe's browser.
