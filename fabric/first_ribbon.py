"""THE FIRST RIBBON — the language program itself.

Not a description of one. This takes a sentence apart.

The walls in the fabric said how: a word's class comes from how it
distributes, never from what it means; the structure cannot be
read off the order alone; the sense is produced from the company
present, not fetched from a list; and a long sentence is not
understood without its grouping.

So nothing here lists a noun, a verb, or a part of speech. The
classes are learned from how words actually sit next to each
other across the whole fabric — 5,368 entries of ordinary
sentences — and the grouping and nesting are built from those
learned classes.
"""
import os, re, sys, math, collections
import numpy as np
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

class Behaviour:
    """What each word DOES, learned from where it sits."""

    def __init__(self, classes=14):
        F = core.fabric(); self.F = F
        text = []
        for e in F.entries:
            for part in (e["essence"], e["cannot"], e["thread"]):
                for s in re.split(r"[.;]", part.lower()):
                    ws = re.findall(r"[a-z']+", s)
                    if len(ws) > 2: text.append(ws)
        self.sentences = text
        count = collections.Counter(w for s in text for w in s)
        self.count = count
        # the frame words: the commonest, which is what everything
        # else sits beside. Learned, not listed.
        self.frame = [w for w, _ in count.most_common(120)]
        fi = {w: i for i, w in enumerate(self.frame)}
        vocab = [w for w, c in count.items() if c >= 4]
        self.vi = {w: i for i, w in enumerate(vocab)}
        self.vocab = vocab
        P = np.zeros((len(vocab), len(self.frame) * 2), dtype=np.float32)
        for s in text:
            for j, w in enumerate(s):
                k = self.vi.get(w)
                if k is None: continue
                if j and s[j-1] in fi: P[k, fi[s[j-1]]] += 1
                if j + 1 < len(s) and s[j+1] in fi:
                    P[k, len(self.frame) + fi[s[j+1]]] += 1
        n = np.linalg.norm(P, axis=1); n[n == 0] = 1
        self.P = P / n[:, None]
        # words that sit in the same company behave the same way
        rng = np.random.default_rng(3)
        idx = rng.choice(len(vocab), size=min(classes * 40,
                                              len(vocab)), replace=False)
        seeds = self.P[idx[:classes]]
        for _ in range(12):
            a = self.P @ seeds.T
            lab = a.argmax(axis=1)
            for c in range(classes):
                m = self.P[lab == c]
                if len(m): seeds[c] = m.mean(axis=0)
            n2 = np.linalg.norm(seeds, axis=1); n2[n2 == 0] = 1
            seeds /= n2[:, None]
        self.klass = {vocab[i]: int(lab[i]) for i in range(len(vocab))}
        self.seeds = seeds

    def cls(self, w):
        return self.klass.get(w, -1)

    def sample(self, c, n=10):
        ws = [w for w, k in self.klass.items() if k == c]
        ws.sort(key=lambda w: -self.count[w])
        return ws[:n]

BEH = None
def behaviour():
    global BEH
    if BEH is None: BEH = Behaviour()
    return BEH

def group(sentence):
    """Break the sentence where the behaviour changes. A group is
    a run of words that belong together because of how they sit."""
    B = behaviour()
    ws = re.findall(r"[a-z']+", sentence.lower())
    if not ws: return []
    groups, cur = [], [ws[0]]
    for a, b in zip(ws, ws[1:]):
        ca, cb = B.cls(a), B.cls(b)
        # a boundary is where the pair stops being one that the
        # fabric's own sentences ever put together
        if ca != cb and B.count.get(b, 0) > 0 and \
           not (B.count.get(a, 0) < 4 and B.count.get(b, 0) < 4):
            groups.append(cur); cur = [b]
        else:
            cur.append(b)
    groups.append(cur)
    return groups

def nest(groups):
    """Build a nesting: each group hangs on the nearest group whose
    behaviour it usually follows. Not order alone — the pairing is
    what the fabric's sentences show."""
    B = behaviour()
    heads = []
    for g in groups:
        # a group's head is its rarest word: the one carrying most
        h = min(g, key=lambda w: B.count.get(w, 0))
        heads.append(h)
    tree, root = {}, 0
    for i, h in enumerate(heads):
        if i == 0: continue
        best, score = 0, -1.0
        for j in range(len(heads)):
            if j == i: continue
            a, b = B.vi.get(heads[j]), B.vi.get(h)
            if a is None or b is None: continue
            s = float(B.P[a] @ B.P[b]) - 0.08 * abs(i - j)
            if s > score: best, score = j, s
        tree[i] = best
    return heads, tree

if __name__ == "__main__":
    B = behaviour()
    print(f"learned from {len(B.sentences):,} sentences, "
          f"{len(B.vocab):,} words with behaviour")
    for c in range(6):
        print(f"  class {c}: {' '.join(B.sample(c, 9))}")
    for q in sys.argv[1:]:
        gs = group(q)
        heads, tree = nest(gs)
        print(f"\nSENTENCE: {q}")
        print("  groups:", " | ".join(" ".join(g) for g in gs))
        print("  heads: ", heads)
        print("  hangs on:", {heads[i]: heads[j]
                              for i, j in tree.items()})
