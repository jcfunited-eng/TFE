"""THE WHITE'S OWN PHYLUMS — kinds of impossibility, derived.

The colored sheet has always had kinds: physics, cooking, algebra.
The white had none — it was only the underside of the coloured
entries. But impossibility has kinds of its own, and they cut
across subjects: a wall that says a thing needs something it
hasn't got is a different kind of wall from one that says two
things cannot share a place.

Nothing here is labelled by hand. Each law is described by
discrete features taken from its own words and form, and the
kinds fall out of grouping laws that share features. A kind is
named after the words its members actually use most.

Algorithm, all discrete, no model anywhere:
  1. every law -> a small feature set (its form, its shape, and
     the few rarest words it uses)
  2. group laws that share enough features (union-find)
  3. name each group from the words its members share most
"""
import os, re, sys, collections
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

OUT = os.path.join(core.DIR, "91_white_kinds.md")

def features(F, L):
    """What this wall is like, in discrete terms it states itself."""
    f = set()
    f.add("form:" + L["kind"])
    aw = F.words_of(L["a"]); bw = F.words_of(L["b"])
    f.add("width:%d" % min(3, len(aw)))
    # the rarest words on each side carry the wall's character
    for side, ws in (("needs", aw), ("gives", bw)):
        rare = sorted(ws, key=lambda w: F.df.get(F.vocab.get(w, -1), 0))
        for w in rare[:3]:
            d = F.df.get(F.vocab.get(w, -1), 99)
            if d <= 60:
                f.add(f"{side}:{w}")
                f.add(f"any:{w}")          # side-blind kinship
        if len(rare) >= 2:
            f.add("pair:" + ":".join(sorted(rare[:2])))
    # the root the entry stands on is part of the wall's kind
    root = (F.entries[L["src"]].get("root") or "").lower()
    for key in ("physic", "chemistr", "mathematic", "premise",
                "law", "trade", "life", "body", "language",
                "craft", "evidence", "people"):
        if key in root: f.add("root:" + key)
    return f

def derive(min_share=2, min_size=3):
    """Leader clustering: pick the law with the most kin, take
    everything close to IT (never transitively), set them aside,
    repeat. Transitive joining collapses every wall into one blob;
    this cannot, because closeness is always measured to a seed."""
    F = core.fabric()
    feats = [features(F, L) for L in F.laws]
    n = len(feats)
    byfeat = collections.defaultdict(set)
    for i, f in enumerate(feats):
        for x in f: byfeat[x].add(i)
    # a feature carried by most walls says nothing about kind
    weight = {x: (1.0 if len(m) <= max(4, n // 8) else 0.0)
              for x, m in byfeat.items()}
    def kin(i):
        c = collections.Counter()
        for x in feats[i]:
            if weight.get(x, 0) <= 0: continue
            for j in byfeat[x]:
                if j != i: c[j] += 1
        return c
    left = set(range(n))
    kins = {i: kin(i) for i in range(n)}
    kinds = []
    while left:
        seed = max(left, key=lambda i: sum(
            1 for j, v in kins[i].items() if j in left
            and v >= min_share))
        group = [seed] + [j for j, v in kins[seed].items()
                          if j in left and v >= min_share]
        group = list(dict.fromkeys(group))
        for j in group: left.discard(j)
        if len(group) < min_size:
            continue
        words, fields, forms = (collections.Counter(),
                                collections.Counter(),
                                collections.Counter())
        for i in group:
            L = F.laws[i]
            for w in F.words_of(L["a"] | L["b"]):
                if F.df.get(F.vocab.get(w, -1), 99) <= 60:
                    words[w] += 1
            fields[F.entries[L["src"]]["field"]] += 1
            forms[L["kind"]] += 1
        kinds.append(dict(members=group, words=words, fields=fields,
                          forms=forms))
    kinds.sort(key=lambda k: -len(k["members"]))
    covered = sum(len(k["members"]) for k in kinds)
    return F, kinds, covered

def write(kinds_limit=12):
    F, kinds, covered = derive()
    lines = ["# 91 THE WHITE'S OWN KINDS — phylums of impossibility",
             "",
             "Derived by the fabric from its own walls, not written",
             "by a hand. Each kind is a group of laws that share",
             "their form, their shape and their rarest words; the",
             "name is taken from the words its members use most.",
             "These are kinds of CANNOT, and they cut across the",
             "coloured subjects: a wall about needing something is",
             "the same kind of wall in a kitchen and in a ledger.",
             ""]
    for n, k in enumerate(kinds[:kinds_limit], 1):
        top = [w for w, _ in k["words"].most_common(6)]
        fields = [f for f, _ in k["fields"].most_common(4)]
        form = k["forms"].most_common(1)[0][0]
        lines.append(f"WHITE KIND {n}: walls of "
                     f"{' / '.join(top[:3]) or 'unnamed ground'}")
        lines.append(f"  FORM: {form} — "
                     + ("a thing that cannot stand without another"
                        if form == "requires" else
                        "two things that cannot stand together"))
        lines.append(f"  SIZE: {len(k['members'])} walls")
        lines.append(f"  CROSSES: {', '.join(fields)}")
        lines.append(f"  WORDS IT SPEAKS IN: {' '.join(top)}")
        for i in k["members"][:3]:
            lines.append(f"    · {F.laws[i]['text'][:96]}")
        lines.append("")
    lines.append(f"({len(kinds)} kinds hold {covered} of "
                 f"{len(F.laws)} walls; the rest stand alone so far "
                 f"— a wall with no kin yet is not a failure, it is "
                 f"a kind with one member. Derived, not authored.)")
    open(OUT, "w").write("\n".join(lines) + "\n")
    return len(kinds), covered, len(F.laws), OUT

if __name__ == "__main__":
    n, covered, walls, path = write()
    print(f"derived {n} kinds of impossibility holding {covered} "
          f"of {walls} walls")
    print(f"written to {os.path.basename(path)}")
