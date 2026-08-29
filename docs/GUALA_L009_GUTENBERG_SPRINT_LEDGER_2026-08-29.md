# Guala L-009 Project Gutenberg sprint ledger

Date: 2026-08-29

Status: **IN PROGRESS — guided live, self-selected open**

## Requested boundary

- A guide may name one exact approved Project Gutenberg edition.
- Its original response bytes and immutable public-domain provenance must be
  preserved before presentation.
- Only rendered page light may reach Guala's retinal receptors. Catalogue
  fields, decoded text, titles, authors, labels, and meanings have no cognitive
  authority.
- A self-selected source requires Guala's own physical action to identify one
  physically presented source object. Server order, randomness, scores, or a
  Python callback are not selection.

## Deployed correction

Task `dsf-ai-task:1323` runs commit
`ecb8180d2b33a82fb3ddddbe6fbcb4d29b539f5a`, immutable image
`sha256:d3b2c6a3429baeceb61caa28db1decad0c677314dbe4820dd1dbb9d4ea59c999`,
and the unchanged resident identity
`1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.

The obsolete process-local next-book counter and its direct fetch/discard path
were deleted. The guided route now:

1. requires one exact catalogue record, including edition, language,
   attribution, public-domain basis, source URL, and rights statement;
2. fetches only the named HTTPS `www.gutenberg.org/files/.../*.txt` edition;
3. refuses redirects, non-plain-text responses, empty responses, and responses
   over 2 MiB;
4. admits the exact source to the existing bounded immutable media custody;
5. prepares one physical curriculum occurrence bound to that custody receipt;
6. renders bounded pages and settles only their light through the resident
   27-receptor retinal path.

## Guided live proof — Alice's Adventures in Wonderland

- Named source: `https://www.gutenberg.org/files/11/11-0.txt`
- Edition/language: `11-0.txt` / `en`
- Exact source extent: 151,191 bytes
- Source SHA-256:
  `a3a27f8edbf7fcd9b8ba8435494440e24952deaa3e2f2d65192d4cb7ca403754`
- Custody receipt:
  `d978bd54e65c7f859c059d80ba20b6c6e4a96ddda7bcdb04fd5b468c0b34df64`
- Physical presentation settled at organism tick `260970` and was durable
  through CURRENT state
  `d4c7a740911756c3e36993ec34717a8acdce4dde352033bde2c765a04d4223f0`.
- The edge returned HTTP 504 after its response window expired. The single
  backend request completed; it was not repeated. The public resident record
  reports `experience_kind=gutenberg`, `outcome=presented`,
  `status=gutenberg_presentation_settled`, and
  `presentation_durable=true`.
- A direct custody read restored and rehashed the exact source bytes to the
  same SHA-256. The record explicitly carries
  `cognition_authority=false`, `semantic_authority=false`, and
  `transport_metadata_only=true`.

## Self-selected truth

The live autonomous request correctly returned HTTP 503. The resident body can
produce native motor action and has previously produced a narrow physical-choice
witness, but no current mechanism binds one exact endogenous body action to one
particular physically presented book object. Therefore self-selection is not
claimed.

The remaining L-009 item is one physical source-object/action boundary. It must
present distinguishable source objects, accept only an exact causal native
action whose geometry reaches one of them, and then present the selected
source's pages. It may not infer selection from an arbitrary mouth/limb motion
or from transport metadata.

