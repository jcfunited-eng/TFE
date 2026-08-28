"""STANDING QUESTIONS — found in the fabric, not composed.

The questions were always there. This file does not write any; it
walks the structure of the knowledge and reports the places where
a question is already standing, the way a gap in a wall is already
a doorway.

Four places, all found by discrete structure, none by template:

  UNBORNE LAW      a law requires something no entry supplies.
                   The question standing there is: what bears it?
  UNTHREADED KIN   two entries share uncommon ground and neither
                   names the other in its threads. The question
                   standing there is: what connects them?
  SILENT KIND      a white kind whose walls all come from one
                   subject. The question: where else does this
                   kind of wall stand?
  FADED GROUND     knowledge that has undulated out of the
                   coloured sheet. The question is its own absence.

Cheap by construction: the first uses the reach index, the second
walks only entries sharing a rare word, the rest are counting.
"""
import os, sys, collections
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

def unborne(F, limit=40):
    """Laws whose requirement nothing in the knowledge supplies."""
    out = []
    for L in F.laws:
        if L["kind"] != "requires": continue
        need = L["b"]
        # is there any entry whose colored face supplies it?
        borne = False
        i, m = 0, need
        wanted = bin(need).count("1")
        while m and not borne:
            if m & 1:
                for eid in F.index.get(i, ()):
                    e = F.entries[eid]
                    if eid == L["src"]: continue
                    have = bin(e["color"] & need).count("1")
                    if have >= max(2, (wanted + 1) // 2):
                        borne = True; break
            m >>= 1; i += 1
        if not borne:
            words = " ".join(F.words_of(need)[:6])
            out.append(("what bears this?", L["text"][:90], words,
                        F.entries[L["src"]]["field"]))
        if len(out) >= limit: break
    return out

def unthreaded(F, limit=40, rare_at=8):
    """Entries that share rare ground but do not name each other."""
    byrare = collections.defaultdict(list)
    for e in F.entries:
        i, m = 0, e["color"]
        while m:
            if m & 1 and F.df.get(i, 99) <= rare_at:
                byrare[i].append(e["id"])
            m >>= 1; i += 1
    seen, out = set(), []
    for wid, ids in byrare.items():
        if len(ids) < 2 or len(ids) > 6: continue
        for i in ids:
            for j in ids:
                if i >= j: continue
                a, b = F.entries[i], F.entries[j]
                if a["field"] == b["field"]: continue
                key = (i, j)
                if key in seen: continue
                seen.add(key)
                ta = (a.get("thread") or "").lower()
                tb = (b.get("thread") or "").lower()
                if b["field"].split()[-1] in ta: continue
                if a["field"].split()[-1] in tb: continue
                out.append(("what connects these?", F.words[wid],
                            a["field"], a["essence"][:70],
                            b["field"], b["essence"][:70]))
                if len(out) >= limit: return out
    return out

def silent_kinds(F, kinds, limit=20):
    """A kind of wall that has so far been seen in one subject
    only — the question is where else it stands."""
    out = []
    for k in kinds:
        if len(k["fields"]) == 1 and len(k["members"]) >= 3:
            fld = list(k["fields"])[0]
            top = " ".join(w for w, _ in k["words"].most_common(3))
            out.append(("where else does this wall stand?", top, fld,
                        len(k["members"])))
        if len(out) >= limit: break
    return out

def faded(F, limit=20):
    import glob, re
    out = []
    for path in glob.glob(os.path.join(core.DIR, "[0-9][0-9]_*.md")):
        t = open(path).read()
        for m in re.finditer(r"STATE: FADED\nESSENCE: ([^\n]{0,80})", t):
            out.append(("what was held here?", m.group(1)))
            if len(out) >= limit: return out
    return out

def all_standing(F, kinds=None):
    qs = []
    for kind, *rest in unborne(F):
        qs.append(dict(kind="unborne law", text=rest[1],
                       about=rest[0], field=rest[2]))
    for kind, word, fa, ea, fb, eb in unthreaded(F):
        qs.append(dict(kind="unthreaded kin", text=word,
                       about=f"{fa}: {ea} || {fb}: {eb}",
                       field=fa))
    if kinds:
        for kind, top, fld, n in silent_kinds(F, kinds):
            qs.append(dict(kind="silent kind", text=top,
                           about=f"{n} walls, all in {fld}",
                           field=fld))
    for kind, ess in faded(F):
        qs.append(dict(kind="faded ground", text=ess,
                       about="knowledge that undulated out",
                       field="—"))
    return qs

if __name__ == "__main__":
    F = core.fabric()
    import white_kinds
    _F, kinds, _cov = white_kinds.derive()
    qs = all_standing(F, kinds)
    counts = collections.Counter(q["kind"] for q in qs)
    print(f"questions standing in the fabric right now: {len(qs)}")
    for k, n in counts.items(): print(f"  {k}: {n}")
    print()
    for q in qs[:6]:
        print(f"  [{q['kind']}] {q['text'][:80]}")
        print(f"      {q['about'][:100]}")
