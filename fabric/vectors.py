"""THE VECTORS — where each piece of knowledge actually points.

A piece of knowledge is a coordinate and a direction. The coordinate
is the entry. The direction is written in its own ROOT and THREAD
lines, and until now nothing had ever resolved it.

What was there before collapsed every declaration to a SUBJECT and
then spread to every entry in that subject. That keeps the position
and throws the direction away, and a thing with a position and no
direction does not travel, it diffuses — which is exactly what was
measured: a question reaching two fifths of the whole fabric.

Both lines are read here, and they are not the same kind of thing:

  ROOT    points DOWN, to the one thing this stands on. Written as
          "subject / the particular claim". The claim after the
          slash is what makes it a coordinate rather than an area.
  THREAD  points ACROSS, to kin in other subjects. Written as
          "subject (the particular claim), subject (...)".

So a root is one edge and a thread is several, and the walk that
uses them should not treat them alike. Nothing here decides what
anything means; it reads declarations and finds which entry each
one names.
"""
import os, re, sys, json, time, hashlib
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

CACHE = os.path.join(BASE, "life", "vectors.json")


def _subject_index(F):
    """Subject name and file number -> the entries standing there."""
    by_name, by_num = {}, {}
    for field, ids in F.fields.items():
        by_name[field] = ids
        for e in (F.entries[i] for i in ids[:1]):
            m = re.match(r"(\d+)_", os.path.basename(e["file"]))
            if m:
                by_num[int(m.group(1))] = ids
    return by_name, by_num


def _name_to_ids(text, by_name, by_num):
    """Which subject does this declaration name? A number is exact;
    a word is matched against the subject names themselves."""
    m = re.search(r"\((\d{1,3})\s*[:\)]", text)
    if m and int(m.group(1)) in by_num:
        return by_num[int(m.group(1))]
    low = text.lower()
    best, hit = None, 0
    for name, ids in by_name.items():
        for w in name.split():
            if len(w) > 3 and re.search(rf"\b{re.escape(w)}", low):
                if len(w) > hit:
                    best, hit = ids, len(w)
    return best


def _pick(F, ids, claim, exclude):
    """Of the entries in that subject, which one does this claim
    name? The declaration's own words decide it — the entry whose
    essence and wall share most uncommon ground with the claim.
    A declaration that matches nothing lands nowhere, and that is
    reported rather than rounded to the first entry in the file."""
    cm = F.mask(claim, learn=False)
    if not cm or not ids:
        return None, 0
    best, score = None, 0
    for i in ids:
        if i == exclude:
            continue
        e = F.entries[i]
        shared = cm & (e["color"] | e["askm"])
        n = 0
        m = shared
        while m:
            n += m & 1
            m >>= 1
        if n > score:
            best, score = i, n
    return best, score


def build(F=None, need=2):
    """Resolve every declaration to a coordinate. `need` is how much
    shared ground a match must have before it counts as naming an
    entry rather than merely landing in the right subject."""
    F = F or core.fabric()
    by_name, by_num = _subject_index(F)
    root = {}          # entry id -> the one entry it stands on
    floors = []        # entries that stand on nothing: the ground
    thread = {}        # entry id -> the entries it reaches across to
    unplaced_root = unplaced_thread = 0
    for e in F.entries:
        eid = e["id"]
        # ---- the root: one edge, downward ----
        r = e["root"]
        if r:
            head, sep, claim = r.partition("/")
            # Only the head may name the subject, and only if it is
            # short enough to BE a name. Scanning the whole line for
            # any subject word invents edges: four physics entries
            # that declare a premise and stand on nothing were being
            # sent to belief, chance, time and money by a stray word.
            # An entry that names no subject is a FLOOR — it has
            # nothing under it, and that is a finding, not a gap to
            # be filled.
            ids = None
            if sep and len(head.strip()) <= 40:
                ids = _name_to_ids(head, by_name, by_num)
            elif re.search(r"\(\d{1,3}\s*[:\)]", head):
                ids = _name_to_ids(head, by_name, by_num)
            if ids is None:
                floors.append(eid)
            else:
                tgt, sc = _pick(F, ids, claim or head, eid)
                if tgt is not None and sc >= need:
                    root[eid] = tgt
                else:
                    unplaced_root += 1
        # ---- the threads: several edges, across ----
        outs = []
        for piece in re.split(r"\),\s*|;\s*", e["thread"] or ""):
            piece = piece.strip()
            if not piece:
                continue
            m = re.match(r"([^(]{2,40}?)\s*\((.*)", piece)
            head = m.group(1) if m else piece
            claim = m.group(2) if m else piece
            ids = _name_to_ids(head, by_name, by_num)
            if ids is None:
                continue
            tgt, sc = _pick(F, ids, claim, eid)
            if tgt is not None and sc >= need:
                outs.append(tgt)
            else:
                unplaced_thread += 1
        if outs:
            thread[eid] = sorted(set(outs))
    return dict(root=root, thread=thread, floors=floors,
                unplaced_root=unplaced_root,
                unplaced_thread=unplaced_thread, sig=F.sig)


VEC = None


def vectors(F=None):
    """Built once and kept, because resolving every declaration is
    the expensive part and the answer only changes when the written
    knowledge does."""
    global VEC
    F = F or core.fabric()
    if VEC is not None and VEC.get("sig") == F.sig:
        return VEC
    try:
        with open(CACHE) as f:
            got = json.load(f)
        if got.get("sig") == F.sig:
            got["root"] = {int(k): v for k, v in got["root"].items()}
            got["thread"] = {int(k): v
                             for k, v in got["thread"].items()}
            VEC = got
            return VEC
    except (OSError, ValueError, KeyError):
        pass
    VEC = build(F)
    try:
        with open(CACHE, "w") as f:
            json.dump(VEC, f)
    except OSError:
        pass
    return VEC


if __name__ == "__main__":
    F = core.fabric()
    t0 = time.perf_counter()
    V = build(F)
    n_root = len(V["root"])
    n_thread = sum(len(v) for v in V["thread"].values())
    print(f"resolved in {time.perf_counter() - t0:.0f}s")
    print(f"  coordinates: {len(F.entries)}")
    print(f"  ROOT edges (one each, downward): {n_root} "
          f"({V['unplaced_root']} declarations landed nowhere)")
    print(f"  THREAD edges (across): {n_thread} "
          f"({V['unplaced_thread']} landed nowhere)")
    print(f"  entries with any vector at all: "
          f"{len(set(V['root']) | set(V['thread']))}")
    print(f"  FLOORS — entries that stand on nothing: "
          f"{len(V['floors'])}")
    import collections
    c = collections.Counter(F.entries[i]["field"] for i in V["floors"])
    for nm, n in c.most_common(6):
        print(f"      {n:4d} in {nm}")
