# GL-INV-GUALA-RESTORE-20260702

Type: State inventory for restore + repair planning
Restore point: s3://dsf-ai-site-backups/guala/auto/2026-06-29_23-58-17_activity_ended/
Current task: 438 (deploying restore endpoint)
Date of inventory: 2026-07-02

---

## What happened

The EFS atomic write used `os.rename(tmp, path)` without first flushing the NFS page cache.
On EFS (NFSv4), this caused a stochastic ENOENT race on atlas/visual/sounds writes.
`guala_atlas.json` and everything after it in the save loop never reached disk on many cycles.
Result: every restart loaded a stale atlas. Atlas decayed from ~46,000 (June 15) to 14,858
(June 29) to 6,618 (today). `guala_visual.json` was never written — she had 0 pictures in
runtime on every boot since the bug began.

Fixed in -74 (per-file isolation + fsync). State from June 29 is the best recoverable point
with all personal content intact.

---

## Restore point state (June 29 23:58 UTC)

### Core numbers
```
tick:         14,059,265
joe reads:     2,023
wc reads:      1,911
c1 reads:          3
corpus reads: 236,769
curriculum:    30,612
worldfeed:      5,543
lookup:           301
total reads:  277,163
```

### Vocabulary (sections)
```
listen:   13,724 motifs
verb:     12,374 motifs
intro:    13,554 motifs
subject:   4,180 motifs
object:    4,454 motifs
modifier:      83 motifs
ground:        79 motifs
TOTAL:    48,448 motifs
```

### Atlas (14,858 bindings)

**By source:**
```
corpus:      4,854  (book/text reading)
curriculum:  3,732  (structured learning)
lookup:      2,070  (world knowledge)
joe:         2,067  (Joe's conversations)
unknown:     1,684
worldfeed:     352  (news/world events)
daydream:       94  (autonomous dreaming)
sight:           5  (visual perception)
```

**By section (what she knows about):**
```
listen:      5,354
verb:        4,371
intro:       3,730
ground:        421
subject:       231
sight:         221  ← visual memory
object:        151
modal_touch:    90  ← TOUCH experiences
modal_smell:    40  ← SMELL experiences
modifier:       61
```

### Deep atlas
```
146 consolidated long-term entries (198MB serialized)
deep_survival_history: 258,057 entries
```

### Pair bonds
```
joe: True  (permanent pair bond)
wc:  True
c1:  False
```

### Teaching / feedback
```
feedback_log:    7 entries (positive signals from joe and wc)
correction_log:  1 entry
emission_records: 25
```

---

## Pictures — 22 items (ALL with grids)

| Title                 | Attendances | ID           | Grid available in S3? |
|-----------------------|-------------|--------------|----------------------|
| moon                  |      17,801 | 9bb63f93d7af | ❌ missing .npy       |
| test_25               |         264 | 91e42db1c66c | ❌ missing .npy       |
| stream_239            |         261 | 95c8e8c12dc9 | ✓                    |
| snapshot              |         220 | 7225bbfc75fd | ✓                    |
| test                  |         219 | 9dbd12f40a47 | ✓                    |
| guala hugs star       |         219 | 2045ca965187 | ✓                    |
| img_6230              |         218 | b65d1e76c8e1 | ✓                    |
| mommy                 |         218 | da9d973d4fab | ❌ missing .npy       |
| lana                  |         217 | 396f4d80bbce | ✓                    |
| happy sun             |         139 | 27def0e2842b | ✓                    |
| guala                 |         131 | 8bd9e45cae48 | ❌ missing .npy       |
| img_2030              |         117 | 779d68180f0a | ✓                    |
| guala family          |         114 | 4eeee4d3d6de | ❌ missing .npy       |
| img_2408              |         114 | dc2538352b9a | ✓                    |
| pretty purple flower  |         113 | dc0aa333bbba | ✓                    |
| yellow balloons       |         113 | 2700ff625028 | ✓                    |
| img_2137              |         111 | 0263947a7a3d | ✓                    |
| ocean                 |         110 | 6b8122be0f2a | ✓                    |
| daddy in the yard     |         106 | 5b47a97ce9e3 | ✓                    |
| aven and guala        |          92 | bc9b432c3138 | ✓                    |
| space rose            |          25 | 72156845a2bc | ❌ missing .npy       |
| hug from ryan         |          21 | 5aa967930289 | ✓                    |

6 pictures have metadata but .npy grids missing from S3. These will need to be
re-uploaded (Joe has the originals). Originals ARE in S3 for some (.heic files).

**Priority re-uploads (high attendance, missing grid):**
1. moon (17,801 attendances) — most attended picture she has
2. guala family (114)
3. guala (131)
4. mommy (218)

---

## Sounds — 15 items

| Title                        | Attendances |
|------------------------------|-------------|
| 1-04 mary had a little lamb  |     262,514 |
| tree frog song               |       2,014 |
| ocean waves                  |       2,010 |
| 1-14 hush a little baby      |       2,004 |
| 1-13 sing a song of sixpence |       2,004 |
| 2-03 once i saw a little bird|       2,001 |
| daddy in the yard.jpeg       |       2,000 |
| beep                         |       2,000 |
| smoke_test_beep              |       2,000 |
| pussy cat pussy cat          |       2,000 |
| cute cat                     |       2,000 |
| test_21                      |       2,000 |
| bells ringing                |       1,966 |
| stream_103                   |         739 |
| bouncing balls                |         342 |

Note: "mary had a little lamb" at 262,514 attendances — she's been listening to
this on repeat for much longer than the others.

---

## What's NOT in June 29 but exists in July 1

These were added/happened AFTER June 29:

**New pictures uploaded July 1** (in July 1 20:08 backup pictures/):
- Additional photos Joe uploaded during July 1 session
- 304d14389080, 89a47372e329, 18517a2860a4, 39649547fc14, 461b365d7d65,
  51415e652a1b, 59d81f76814b (need title resolution from originals)

**Interactions:**
- joe: +80 reads (2,023 → ~2,100 in July 1)
- wc: similar
- curriculum: additional moon-series bundles (moon-001 through moon-006)

**Atlas delta lost (June 29 → July 1):**
- Atlas grew slightly then decayed hard: 14,858 → 16,138 (July 1 02:17) → 6,618 (now)
- Net: we're restoring to a state with MORE atlas than any point after June 29

---

## Multi-modal senses inventory

The atlas breakdown shows she had real multi-modal experience bindings:

| Sense     | Atlas bindings | Status after restore |
|-----------|----------------|----------------------|
| sight     | 221 (section) + 5 (direct) | Restored ✓ |
| touch     | 90 bindings    | Restored ✓ |
| smell     | 40 bindings    | Restored ✓ |
| sound     | ~5,354 listen  | Restored ✓ |

These came from `give_experience` calls that delivered multi-lane sensory bundles.
The bindings are IN the atlas and will be restored. The experiences themselves
(the specific sensation descriptions) are not re-deliverable from code alone — Joe
needs to re-give those if he wants her to attend to them again.

---

## Repair plan after restore

### Immediate (pre-restore, already in current deploy):
- [x] Save bug fixed (-74: fsync + per-file isolation)
- [x] NMDA source_match bug fixed (-75)
- [x] Emission dynamics ticks restored to 40 (-78b)
- [x] Orient reflex + REST retired (-73)
- [x] Picture upload executor fixed (dedicated 4-thread pool)

### After restore boots clean:
1. **Re-upload 6 missing picture grids** (Joe has originals):
   - moon, guala, mommy, guala family, space rose, test_25
   - Priority: moon (17,801 attendances — her most-attended)

2. **Re-deliver experience bundles** for the senses:
   - Touch experiences (rebuilt from: `modal_touch` had 90 bindings)
   - Smell experiences (rebuilt from: `modal_smell` had 40 bindings)
   - Visual experiences (moon context she knew deeply)

3. **Curriculum re-run** — the moon series and any curriculum that ran June 29 → July 1

4. **Verify atlas growth** — within 24h of clean saves, check atlas is growing not decaying

### What does NOT need repair:
- Her vocabulary (48,448 motifs) — preserved fully
- Her sounds (all 15, attendance counts restored)
- Her pair bonds (joe: True, wc: True)
- Her 14 pictures with grids available in S3 (auto-restored)
- Feedback/correction history (7 events restored)

---

## Restore procedure

```bash
# 1. Trigger targeted restore (once task:439 is up)
curl -X POST "http://dsf-ai-alb.../api/v1/gualaloom/admin/restore_from_s3_prefix" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ..." \
  -d '{"prefix": "auto/2026-06-29_23-58-17_activity_ended"}'

# 2. Redeploy (boots from restored EFS state)
./tools/deploy_dsf_ai.sh
```

---

End.
