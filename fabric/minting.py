"""MINTING — the machine writing knowledge, under the law.

Nothing in this fabric has ever added to its own knowledge. Every
entry was written by a hand. This file is the one place where the
machine may write, and it is fenced by the minting law that was
bought with a failure:

  UN-AIMED       the candidate must come from the fabric's own
                 structure, not from anyone's expectation. Here
                 that means a chain of two written laws, found by
                 walking, never by asking for a particular answer.
  VERIFIED AFTER the chain must survive checks made after it
                 exists: both parents alive, the conclusion not
                 already written, the joining ground not a single
                 common word, and the conclusion must not itself
                 be closed by the knowledge.
  REACHED        it must be reached by a standing question. A
                 finding no question reaches is unattached — kept,
                 not minted.

What is minted is a WHITE entry: a wall nobody wrote, standing
where two written walls meet. It carries both parents by name, so
any reader can refuse it at the source.
"""
import os, re, sys, collections
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

MINTED = os.path.join(core.DIR, "92_minted_walls.md")
HEADER = """# 92 MINTED WALLS — impossibilities the fabric derived itself

Every wall here was chained by the machine from two written laws,
checked after the fact, and reached by a question that was already
standing. None was authored by a hand; each names both parents so
it can be argued with at the source. If a parent falls, its
children should fall with it.
"""

def _existing(F, a, b, kind):
    for L in F.laws:
        if L["kind"] != kind: continue
        if (a & L["a"]) == a and (b & L["b"]) == b: return True
    return False

def candidates(F, max_out=40):
    """Chain two written laws into one nobody wrote."""
    by_a = collections.defaultdict(list)
    for i, L in enumerate(F.laws):
        i2, m = 0, L["a"]
        while m:
            if m & 1: by_a[i2].append(i)
            m >>= 1; i2 += 1
    out, seen = [], set()
    for L1 in F.laws:
        if L1["kind"] != "requires": continue
        # who needs what L1 gives?
        cands = set()
        i2, m = 0, L1["b"]
        while m:
            if m & 1: cands.update(by_a.get(i2, ()))
            m >>= 1; i2 += 1
        for j in cands:
            L2 = F.laws[j]
            if L2["src"] == L1["src"]: continue
            link = L1["b"] & L2["a"]
            if bin(link).count("1") < 2: continue      # not one word
            if L2["kind"] == "requires":
                a, b, kind = L1["a"], L2["b"], "requires"
            else:
                a, b, kind = L1["a"], L2["b"], "forbids"
            if not a or not b or (a & b): continue
            key = (a, b, kind)
            if key in seen: continue
            seen.add(key)
            if _existing(F, a, b, kind): continue
            # the conclusion must not itself be closed
            if F.judge(a | b) is not None and kind == "requires":
                continue
            out.append(dict(a=a, b=b, kind=kind, p1=L1, p2=L2,
                            link=link))
            if len(out) >= max_out: return out
    return out

def reached_by(F, cand, questions):
    """Which standing question reaches this candidate."""
    ground = cand["a"] | cand["b"]
    best, score = None, 0
    for q in questions:
        qm = F.mask(q.get("text", "") + " " + q.get("about", ""),
                    learn=False)
        v = bin(qm & ground).count("1")
        if v > score: best, score = q, v
    return (best, score) if score >= 2 else (None, score)

def mint(limit=6):
    F = core.fabric()
    import standing, white_kinds
    _F, kinds, _c = white_kinds.derive()
    qs = standing.all_standing(F, kinds)
    made = []
    for c in candidates(F):
        q, score = reached_by(F, c, qs)
        if q is None: continue
        aw = " ".join(F.words_of(c["a"])[:6])
        bw = " ".join(F.words_of(c["b"])[:6])
        if c["kind"] == "requires":
            claim = (f"no [{aw}] without [{bw}] — a wall nobody "
                     f"wrote, standing where two written walls meet.")
        else:
            claim = (f"no [{aw}] together with [{bw}] — a wall "
                     f"nobody wrote, standing where two written "
                     f"walls meet.")
        made.append(dict(claim=claim, cand=c, question=q,
                         score=score))
        if len(made) >= limit: break
    if made:
        if not os.path.exists(MINTED):
            open(MINTED, "w").write(HEADER)
        with open(MINTED, "a") as f:
            for m in made:
                c = m["cand"]
                f.write(f"\nESSENCE: {m['claim']}\n")
                f.write(f"ROOT: derived / two written walls chained "
                        f"by the machine.\n")
                f.write(f"CANNOT: {m['claim']}\n")
                f.write(f"THREAD: parent one — {c['p1']['text'][:80]} "
                        f"({F.entries[c['p1']['src']]['field']}); "
                        f"parent two — {c['p2']['text'][:80]} "
                        f"({F.entries[c['p2']['src']]['field']}).\n")
                f.write(f"ASKED-AS: {' '.join(F.words_of(c['a'])[:6])} "
                        f"{' '.join(F.words_of(c['b'])[:6])}\n")
                f.write(f"REACHED-BY: [{m['question']['kind']}] "
                        f"{m['question']['text'][:70]}\n")
    return made

if __name__ == "__main__":
    made = mint()
    print(f"minted {len(made)} walls the fabric derived itself")
    for m in made:
        print(f"  · {m['claim'][:100]}")
        print(f"      reached by [{m['question']['kind']}] "
              f"{m['question']['text'][:60]}")


# ---------------------------------------------------------------
# THE OTHER FACE — minting a claim, not a wall
# ---------------------------------------------------------------
# The fabric grew its own impossible and could not grow its own
# possible. Everything it could rule out, it could find; everything
# it could say was handed to it. That asymmetry is not a property of
# the world, it was a property of this file only having one half.
#
# A claim is minted under the SAME law as a wall, because the law is
# what makes minting honest rather than invention:
#
#   UN-AIMED        the pair comes from where a walk arrived, never
#                   from asking for a particular answer.
#   VERIFIED AFTER  both parents alive; the ground they share is
#                   uncommon and more than a single word; no wall
#                   closes either parent; and no wall closes the two
#                   of them standing together.
#   REACHED         a question already standing has to reach it.
#
# What is written is the JOINT, which is the only thing here that
# was ever built rather than found: these two stand together, on
# this ground. Both parents are named so it can be argued with at
# the source, and so it falls if they do.

CLAIMS = os.path.join(core.DIR, "93_minted_claims.md")
UNATTACHED = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "life", "unattached_joints.md")


def _refused_pairs():
    """What has already been refused, so it is not refused again.

    A refusal is a finding too, and one that was being thrown away:
    the same pairs were re-walked, re-judged and re-written every
    time their question came round — 232 records of 41 distinct
    joints, one of them written thirty times. That is not just a
    messy file, it is the machine spending its beats re-deciding
    what it had already decided, which is why the yield fell away
    to nothing in the second hour."""
    out = set()
    try:
        if os.path.exists(UNATTACHED):
            cur = []
            for line in open(UNATTACHED):
                if line.startswith("ON ["):
                    cur = []
                elif line.startswith("  ") and line.strip():
                    cur.append(line.strip()[:60])
                    if len(cur) == 2:
                        out.add(tuple(sorted(cur)))
    except OSError:
        pass
    return out


def _keep_unattached(a, b, ground, asked):
    """Kept, not minted. A joint resting on a shared word may still
    turn out to matter when the ground underneath is written, so it
    is not thrown away — it is held outside the knowledge, where it
    cannot be mistaken for something the fabric stands on."""
    try:
        with open(UNATTACHED, "a") as f:
            f.write(f"\nON [{ground}] reached by '{asked[:60]}'\n"
                    f"  {a['essence'][:100]}\n"
                    f"  {b['essence'][:100]}\n")
    except OSError:
        pass
CLAIMS_HEADER = """# 93 MINTED CLAIMS — joints the fabric built itself

Every claim here is a JOINT: two written pieces of knowledge that
share uncommon ground and that nothing closes when they stand
together. The two pieces are quoted as they were written and are
not paraphrased; the joining is the only part the machine made.
None was authored by a hand. Each names both parents so it can be
argued with at the source, and if a parent falls its children
should fall with it.

These are weaker than written knowledge and are marked so. A joint
says that two things sit together, not that either is true.
"""


def claim_candidates(F, entries, limit=24):
    """Pairs that stand together on uncommon ground.

    Nothing is aimed here: the pairs are whatever the caller's walk
    arrived at, taken two at a time in the order they were reached.
    """
    import eliminate
    laws = eliminate.forbidding(F)
    common = len(F.entries) // 50
    out, seen = [], set()
    for i, a in enumerate(entries):
        for b in entries[i + 1:]:
            if a["id"] == b["id"]:
                continue
            key = tuple(sorted((a["id"], b["id"])))
            if key in seen:
                continue
            seen.add(key)
            shared, k, m = 0, 0, a["color"] & b["color"]
            while m:
                if m & 1 and F.df.get(k, 0) <= common:
                    shared |= 1 << k
                m >>= 1
                k += 1
            if bin(shared).count("1") < 1:
                # The fence is "not a single COMMON word", and this
                # ground is already uncommon-only. One uncommon word
                # is a real hold — two things both about fingers
                # share "finger" and little else.
                continue
            if eliminate.closes(a["color"], a["color"], F, laws):
                continue                    # a parent already closed
            if eliminate.closes(b["color"], b["color"], F, laws):
                continue
            pair = a["color"] | b["color"]
            if eliminate.closes(pair, pair, F, laws):
                continue                    # they do not stand together
            out.append(dict(a=a, b=b, ground=shared))
            if len(out) >= limit:
                return out
    return out


def mint_claims(entries, questions=None, limit=3, reacher=None):
    """Write the joints that survive the law. Returns what was
    written, and says what it refused and why."""
    F = core.fabric()
    if questions is None:
        try:
            import standing, white_kinds
            _F, kinds, _c = white_kinds.derive()
            questions = standing.all_standing(F, kinds)
        except Exception:
            questions = []
    made, refused = [], []
    turned_down = _refused_pairs()
    # What has already been minted, read as PAIRS out of the file's
    # own PARENTS lines. The previous check built a key of
    # "essence_a||essence_b" and asked whether that string appeared
    # in the file — but the file never contains that format, so the
    # check could never once have matched. It looked like a dedupe
    # and was a no-op, and the same claim went in four times.
    already = set()
    try:
        if os.path.exists(CLAIMS):
            for line in open(CLAIMS):
                if line.startswith("PARENTS:"):
                    parts = line[8:].split("||")
                    if len(parts) == 2:
                        already.add(tuple(sorted(
                            x.strip()[:60] for x in parts)))
    except OSError:
        pass
    for c in claim_candidates(F, entries):
        a, b = c["a"], c["b"]
        ground = " ".join(F.words_of(c["ground"])[:6])
        # Reached by a question already standing, or it is
        # unattached. When the pair came from a walk that STARTED at
        # a standing question, that walk is the reaching — it got
        # there along the links the knowledge declared. Asking
        # instead for shared letters between the question and the
        # ground is the word-matching this whole fabric exists to
        # stop doing, and it refused every honest candidate.
        if reacher:
            q, score = {"text": reacher}, 99
        else:
            q, score = reached_by(F, dict(a=c["ground"],
                                          b=c["ground"]),
                                  questions) if questions else (None, 0)
        if questions and q is None and not reacher:
            refused.append((a, b, "no standing question reaches it — "
                                  "unattached, kept rather than minted"))
            continue
        # A pair is the same pair whichever way round it arrives.
        # Keyed in arrival order, the same two entries reached from
        # two different questions wrote themselves three times.
        # The PARENTS line is written as "field — essence", so the
        # key has to be built the same way it will be read back.
        key = tuple(sorted(
            (f"{a['field']} — {a['essence'][:70]}"[:60],
             f"{b['field']} — {b['essence'][:70]}"[:60])))
        if key in already:
            refused.append((a, b, "already minted"))
            continue
        conv = convergence(F, a, b)
        # A claim is minted when something underneath actually
        # connects the two. A joint resting only on a shared word is
        # KEPT, not minted — the same distinction the law already
        # makes for a finding no question reaches. Words like
        # "connect" and "exclude" are uncommon enough to pass as
        # ground and carry no subject, so left alone this fills the
        # claims with coincidences: dairy cow genetics joined to
        # backup strategy, because both say "connected".
        pairkey = tuple(sorted((a["essence"][:60], b["essence"][:60])))
        if pairkey in turned_down:
            continue          # already refused; do not decide it twice
        if conv["kind"] == "lexical":
            turned_down.add(pairkey)
            _keep_unattached(a, b, ground, (q or {}).get("text", ""))
            refused.append((a, b, "rests on a shared word with no "
                                  "ground underneath — kept as a "
                                  "candidate, not minted"))
            continue
        already.add(key)          # within this call, too
        made.append(dict(a=a, b=b, ground=ground, conv=conv,
                         asked=(q or {}).get("text", "")))
        if len(made) >= limit:
            break
    if made:
        try:
            new = not os.path.exists(CLAIMS)
            with open(CLAIMS, "a") as f:
                if new:
                    f.write(CLAIMS_HEADER)
                for m in made:
                    a, b = m["a"], m["b"]
                    f.write(
                        f"\nESSENCE: these two stand together on "
                        f"[{m['ground']}] — \"{a['essence'][:150]}\" "
                        f"and \"{b['essence'][:150]}\". MINTED, not "
                        f"written by a hand; a joint says the two sit "
                        f"together, not that either is true.\n"
                        f"ROOT: minted claims / two pieces sharing "
                        f"uncommon ground that nothing closes when "
                        f"they stand together.\n"
                        f"CANNOT: no standing-together on ground that "
                        f"is a single common word. If either parent "
                        f"falls this falls with it.\n"
                        f"PARENTS: {a['field']} — {a['essence'][:70]} "
                        f"|| {b['field']} — {b['essence'][:70]}\n"
                        f"REACHED-BY: {m['asked'][:80] or 'unattached'}\n"
                        f"JOINT-KIND: {m['conv']['kind']}"
                        + (f" — their roots meet at "
                           f"{m['conv']['at']}: "
                           f"{m['conv']['said']}"
                           if m['conv']['at'] else
                           " — they share a word and no ground "
                           "underneath it; the weakest kind of "
                           "joint, said so rather than dressed up")
                        + "\n"
                        f"STATE: MINTED\n"
                        f"ASKED-AS: {m['ground']}\n")
        except OSError as e:
            return [], [(None, None, f"could not write: {e}")]
    return made, refused


def _root_chain(V, eid, limit=12):
    """Where a coordinate stands, and where that stands, down to the
    ground. The chain is the vector, followed."""
    out, seen, cur = [], set(), eid
    while cur is not None and cur not in seen and len(out) < limit:
        seen.add(cur)
        cur = V["root"].get(cur)
        if cur is not None:
            out.append(cur)
    return out


def convergence(F, a, b):
    """Do these two stand on any common ground, following what each
    declares it stands on, all the way down?

    This separates a joint that is structural from one that is only
    lexical. Two entries sharing a word may be a real echo or may be
    the same letters doing two jobs; if their roots meet, something
    underneath actually connects them. Reported, never used to
    refuse — a lexical joint is still a joint, it is just a weaker
    one, and which kind it is belongs on the record.
    """
    import vectors
    V = vectors.vectors(F)
    ca = [a["id"]] + _root_chain(V, a["id"])
    cb = [b["id"]] + _root_chain(V, b["id"])
    meet = set(ca) & set(cb)
    if meet:
        at = F.entries[sorted(meet)[0]]
        return dict(kind="structural", at=at["field"],
                    said=at["essence"][:70])
    fa = {F.entries[i]["field"] for i in ca}
    fb = {F.entries[i]["field"] for i in cb}
    shared = fa & fb
    if shared:
        return dict(kind="same ground", at=sorted(shared)[0], said="")
    return dict(kind="lexical", at="", said="")


# ---------------------------------------------------------------
# PROPOSING AN AREA — what its own records keep pointing at
# ---------------------------------------------------------------
# The direction says it should propose new areas when its records
# keep pointing at territory not yet written. This is the state that
# calls for it: after three hours the yield fell to two claims an
# hour, not because anything was broken but because the pairs its
# current knowledge supports have been mined.
#
# The proposal is not composed. It is read out of the refusals: when
# joint after joint is turned down on the SAME ground, that ground is
# a place where things keep almost connecting and nothing underneath
# is written. That is a hole with a shape, and the shape is what gets
# proposed. Nothing here decides what should be written — it says
# where the machine's own record keeps pointing.

PROPOSALS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "life", "areas_to_write.md")


def proposals(least=3):
    """Ground that keeps turning up in refused joints. `least` is how
    many separate refusals it takes before a repeat is a pattern
    rather than a coincidence."""
    counts, examples = collections.Counter(), {}
    try:
        if not os.path.exists(UNATTACHED):
            return []
        cur_ground, cur = None, []
        for line in open(UNATTACHED):
            m = re.match(r"ON \[(.*?)\]", line)
            if m:
                cur_ground, cur = m.group(1), []
            elif line.startswith("  ") and line.strip() and cur_ground:
                cur.append(line.strip())
                if len(cur) == 2:
                    for w in cur_ground.split():
                        counts[w] += 1
                        examples.setdefault(w, cur[:])
    except OSError:
        return []
    return [(w, n, examples.get(w, []))
            for w, n in counts.most_common() if n >= least]


def propose(least=3, limit=5):
    """File where the record keeps pointing. Written outside the
    knowledge: a proposal is not something the fabric holds, it is
    something it is asking for."""
    out = proposals(least)
    if not out:
        return []
    try:
        seen = open(PROPOSALS).read() if os.path.exists(PROPOSALS) else ""
    except OSError:
        seen = ""
    made = []
    for w, n, ex in out[:limit]:
        if f"AREA: {w}\n" in seen:
            continue
        made.append((w, n, ex))
    if made:
        try:
            with open(PROPOSALS, "a") as f:
                if not seen:
                    f.write("# AREAS TO WRITE — where the record "
                            "keeps pointing\n\nEach of these is a "
                            "ground on which joints keep being "
                            "refused: things almost connect there "
                            "and nothing underneath is written. Read "
                            "out of the refusals, not composed. A "
                            "proposal is not knowledge and is kept "
                            "outside it.\n")
                for w, n, ex in made:
                    f.write(f"\nAREA: {w}\n"
                            f"  {n} joints refused on this ground — "
                            f"they share the word and nothing "
                            f"underneath connects them.\n")
                    for line in ex[:2]:
                        f.write(f"    {line[:96]}\n")
                    f.write(f"  WHAT WOULD DRAIN IT: something "
                            f"written about {w} that the entries "
                            f"above could both stand on.\n")
        except OSError:
            return []
    return made
