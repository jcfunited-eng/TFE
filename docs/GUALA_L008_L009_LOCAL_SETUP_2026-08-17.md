# Guala L-008/L-009 local setup

Date: 2026-08-17

Status: Local setup only. Nothing in this document is deployed, mounted, or
Live-Closed. L-005 remains active; L-006 and L-007 remain prerequisites.

## Requested boundary

- L-008: local pictures, PDFs, books, sounds, songs, and video become bounded
  sensory experiences while their exact source bytes and provenance survive.
- L-009: a guide may offer a named Project Gutenberg source; Guala may select
  one only after an exact native physical-choice path identifies the source.
- Neither route may insert text, filenames, catalogue IDs, titles, transcripts,
  captions, or meanings into cognition.

## Current production truth

- Picture, PDF/book, audio, and song decoding already reach the active retinal
  or cochlear paths through `/api/v1/material/offered`.
- Video is absent.
- The active offered-material route discards original bytes after decoding and
  does not return a source-media receipt. It therefore does not satisfy source
  preservation.
- Guided Gutenberg fetches a bounded public-domain text and renders pages to
  retinal light. It discards the fetched bytes, selects by a process-local
  counter that resets on restart, and does not use the embodied invitation
  gate.
- Autonomous Gutenberg selection is correctly refused because no native
  physical choice has identified a source.

## Prepared local mechanism

`dsf_ai_service/bounded_source_media_store.py` admits only exact original bytes
plus transport provenance. It provides:

- immutable SHA-256-verified source bytes;
- idempotent receipts binding media type, attribution, rights basis, exact
  rights statement, source locator, byte extent, and byte hash;
- required edition and language provenance for a named public-domain Project
  Gutenberg response;
- atomic directory publication without a database;
- 24 MiB per source, 32 committed sources, and 256 MiB total hard limits;
- fail-closed restore on tampering or interrupted admission; and
- explicit false semantic and cognition authority.

`dsf_ai_service/bounded_video_sensory_source.py` converts one preserved video
source into at most 24 successive 250 ms occurrences. Each occurrence has one
sampled 768x432 light frame and exactly 4,000 mono 16 kHz pressure samples. A
silent source produces exact zero pressure. The decoder reads no captions,
transcript, title, object identity, or semantic field.

These mechanisms are compiled but unmounted. Focused local tests exercise only
their bounded custody and physical light/pressure conversion. No native
organism, DSF field, neuron, retained formation, world, deployment, or
production state is used or changed by those tests.

## Required integration after the active learning sequence permits it

The one L-008 integration increment is: preserve the source before decoding,
place books and pictures as physical objects in the study/library or play video
and music through bounded physical screen/speaker sources in the audiovisual
room, then carry only the resulting light/pressure through embodied invitation
and unchanged full-DSF sensory settlement. The response may expose provenance
receipts, but those fields remain outside cognition. A successful HTTP response
is not a learning claim.

The one guided L-009 increment is: require the guide to name one approved
Gutenberg catalogue entry with its edition, language, attribution, public-domain
basis, source URL, and rights statement; preserve the exact fetched response
before page rendering; create a bounded physical book in the study/library; and
present its pages through the same invited visual path. The process-local
next-book counter must not be retained or extended.

The self-selected L-009 increment remains gated. It may open only when an exact
native physical-choice witness selects among physically presented source
objects. Random selection, catalogue order, server choice, scores, labels, or a
Python callback cannot satisfy that gate.

## Acceptance boundary

L-008 cannot be Live-Closed until every requested local kind, including video,
commits once in production after an embodied invitation; exact source bytes
restore after restart; duplicates do not grow storage; and every configured
count/byte limit refuses cleanly.

Guided L-009 cannot be Live-Closed until one exact preserved Gutenberg source
commits as pages of light after an embodied invitation and survives restart.
Self-selected L-009 remains separately open until the native choice witness is
live. No wording may combine those two states.
