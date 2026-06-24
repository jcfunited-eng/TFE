"""loom_cognition.py — the organ-brain speaking from her own exposure.

The pure LoomTapestry.compose() converged every mosaic on the query word (echo).
This composes a real SEQUENCE by walking the transitions she learns from exposure:
each word leads to the word that most often followed it in what she's heard — moon →
is → bright. Selection over learned succession, seeded by what she's attending to.
It learns continuously: every exposure updates the walk. The substrate grows.
"""
from collections import Counter, defaultdict
from typing import Dict, List, Optional

# Generic openers/function words make poor seeds — every query collapses onto the
# single dominant opener (e.g. always "the moon is bright"). When the query carries
# a content word she knows, steer from THAT instead so her reply tracks the prompt.
_STOPWORD_SEEDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "i", "you", "we", "it",
    "to", "of", "and", "or", "at", "in", "on", "my", "your", "this", "that",
})


class GualaCognition:
    """Her language from exposure: learned word-succession, walked into sentences."""

    def __init__(self):
        self.trans: Dict[str, Counter] = defaultdict(Counter)  # word -> successors
        self.starts: Counter = Counter()                        # sentence openers
        self.vocab: set = set()

    def expose(self, sentences: List[str]) -> None:
        """Learn succession from what she hears. Called on every experience."""
        for s in sentences:
            ws = [w for w in s.lower().split() if w]
            if not ws:
                continue
            self.starts[ws[0]] += 1
            self.vocab.update(ws)
            for a, b in zip(ws, ws[1:]):
                self.trans[a][b] += 1

    def compose(self, query: str = "", max_len: int = 7) -> List[str]:
        """Walk her learned succession into a sentence, seeded by the query.

        Seed selection prefers a CONTENT word from the query (one she can continue),
        so 'the cat ...' walks from 'cat', not from the generic 'the'. Falls back to
        any known query word, then to her most common opener."""
        toks = (query or "").lower().split()
        # query tokens she can actually continue (have learned successors)
        steerable = [t for t in toks if t in self.trans]
        seed = ""
        if steerable:
            content = [t for t in steerable if t not in _STOPWORD_SEEDS]
            pool = content or steerable
            # richest continuation among the preferred pool
            seed = max(pool, key=lambda w: len(self.trans.get(w, ())))
        if not seed:
            for tok in toks:           # any word she at least knows
                if tok in self.vocab:
                    seed = tok
                    break
        if not seed:
            seed = self.starts.most_common(1)[0][0] if self.starts else ""
        if not seed:
            return []
        out, seen = [seed], {seed}
        cur = seed
        for _ in range(max_len - 1):
            nxt = self.trans.get(cur)
            if not nxt:
                break
            cand = [w for w, _ in nxt.most_common() if w not in seen]
            if not cand:
                break
            cur = cand[0]
            out.append(cur)
            seen.add(cur)
        return out

    def say(self, query: str = "") -> str:
        return " ".join(self.compose(query))
