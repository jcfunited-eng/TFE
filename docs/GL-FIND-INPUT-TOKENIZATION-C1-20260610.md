# GL-FIND-INPUT-TOKENIZATION-C1-20260610
## Input Text Tokenization Audit

**Author:** c1 | **Date:** 2026-06-10
**Trigger:** Pasted dictionary definitions produced emissions querying bare punctuation ("what is (e", "what is body)")

---

## Finding: Minimal punctuation stripping, no sentence segmentation

There are two tokenization paths in the v5 engine. Both use simple `str.replace` + `str.split`:

### 1. `converse()` — interactive input from joe/wc/c1

**File:** `gualaloom_v5_engine.py:1010`
```python
words = [w for w in text.lower().replace(",", " ").replace(".", " ").replace("?", " ").split() if w]
```

**Strips:** `,` `.` `?` (replaced with space, then split on whitespace)

**Does NOT strip:** `(` `)` `:` `;` `!` `"` `'` `-` `/` `[` `]` `{` `}` `—` `–` `…` or any unicode punctuation

**Result:** Input like `"body (e.g. the arm)"` tokenizes as:
- `["body", "(e", "g", "the", "arm)"]`
- `(e` and `arm)` become words, get installed as vocab, create atlas entries, can trigger emissions like "what is (e"

### 2. `read_sentence()` — corpus/autonomous reading

**File:** `gualaloom_v5_engine.py:961`
```python
words = [w for w in text.lower().replace(",", " ").replace(".", " ").split() if w]
```

**Strips:** `,` `.` only (not even `?`)

**Even narrower** than converse. A corpus line like `"Who said that?"` tokenizes `?` as part of the last word: `["who", "said", "that?"]`

### 3. Math parser

**File:** `gualaloom_v5_engine.py:1222-1226`
```python
t = t.replace("+", " plus ").replace("-", " minus ")
t = t.replace("*", " times ").replace("/", " over ")
t = t.replace("?", " ").replace("=", " ")
toks = t.split()
```

Separate path, handles math operators. Not relevant to the punctuation problem.

---

## Impact

1. **Parentheses become word fragments:** `(word` and `word)` are installed as modes in listen/subject/verb/object sections. These occupy mode bank slots (max 24 per section) and create atlas entries.

2. **Semicolons, colons, quotes stick to words:** `definition:` becomes a different word from `definition`. Duplicate modes for the same concept.

3. **Multi-sentence input is not segmented:** Pasting "The cat sat. The dog ran." processes as one flat token list, losing sentence boundaries. The position_hint routing (subject→verb→object) applies to the whole blob, not per-sentence.

4. **PDF-extracted text is worst case:** PDF lines often contain `(see section 4.2)`, `e.g.`, `i.e.`, footnote markers `¹²³`, and header/footer artifacts. These all become vocabulary.

---

## Scope of the problem

The Oxford Grammar PDF was never read (position 0, 0 read-throughs). But any pasted text from dictionaries, Wikipedia, or technical sources would hit this. The 2314 vocab entries likely include some punctuation-contaminated words from prior conversations.

---

## What NOT to change yet

Per instructions: no tokenization changes in this iteration. wC writes the fix brief.

**Candidate fix (for wC's brief):** Strip all non-alphanumeric characters (except hyphens in compound words) before tokenization. Segment multi-sentence input at `.` `?` `!` boundaries and process each sentence independently. Filter tokens against a minimum-length or character-class check.

---

## Corpus cleanup (separate item)

`oxford-guide-to-english-grammar` removed from corpus library via boot-time blocklist. Never read (position 0, 0 read-throughs), so no fragments were processed. No atlas contamination from this corpus.
