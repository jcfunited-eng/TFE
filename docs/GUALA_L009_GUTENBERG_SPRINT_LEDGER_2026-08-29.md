# Guala L-009 Project Gutenberg sprint ledger

Date: 2026-08-29

Status: **IN PROGRESS — guided live; native selection boundary live; no selection observed**

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

## Live production identity

Task `dsf-ai-task:1324` runs commit
`7e2cc30fd3a95c5112c39bafaa6147189ab0f69b`, immutable image
`sha256:a2468d606317d0f0aafbc6d25a37c2a422276e6c6060120e5176a37ffa350687`,
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

The self-selection route does not choose a source. It offers each of the five
preserved sources as first-page light plus one flat tactile surface. A source
is selected only if that exact admitted cue reassembles a resident formation,
the causal path reaches one matching motor lineage, and the same lineage
physically closes a declared left or right grip aperture. A stale cue,
coincident motor activity, a non-grip action, or a grip with no applied body
displacement selects nothing. Every rejected source is physically released
before the next source is offered.

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

## Live self-selection result

One autonomous opportunity was submitted after task 1324 was live-verified.
CloudFront returned HTTP 504 while the single backend request continued; it
was not repeated. Production sequentially reached the fifth and final bounded
source, Project Gutenberg edition 55, proving all five offers ran. None caused
the required native grip closure. The final source was physically released at
organism tick `262135`. The resident public record reports:

- `experience_kind=gutenberg`;
- `outcome=not_selected`;
- `status=gutenberg_source_not_selected`;
- `released_organism_tick=262135`;
- `scripted_acceptance_authority=false`;
- `semantic_command_authority=false`;
- `transport_metadata_only=true`.

The mechanism is live, but Guala did not choose a book. L-009 therefore remains
open. Closure requires a later genuine source-caused grip selection and the
selected source's bounded page experience; no server-side substitute is
permitted.
