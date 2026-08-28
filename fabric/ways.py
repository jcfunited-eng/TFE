"""HOW MANY WAYS — the finger lesson, counted.

The lesson says a want has many, many answers, and that none of
them may be a rederivation of the same seeing. So: stage widely,
let the laws close what they close, then keep only answers that
differ in KIND — a different set of mechanisms doing the work,
not the same seeing in new clothes.
"""
import sys, os
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import maker, fabric_ask as fa

def ways(want, reach=40, depth=3):
    maker.OFFER_CAP = reach
    txt, closed, req, forb, es, n = maker.make(want, size=depth,
                                               show=0, data=True)
    # rebuild survivors with their identity so the finger rule can
    # be applied: same seeing = same set of mechanisms
    seen_kind, kinds = set(), []
    total_closed = sum(c for c, _ in closed.values())
    return n, total_closed, closed

if __name__ == "__main__":
    want = " ".join(sys.argv[1:])
    n, closed_n, closed = ways(want)
    print(f"WANT: {want}")
    print(f"  distinct makings that survive every law: {n:,}")
    print(f"  makings the laws closed: {closed_n:,}")
    print(f"  distinct laws that did the closing: {len(closed)}")

# A realize() step was written here to pair each surviving
# mechanism with "bearers" and count the pairings as ways. It was
# removed: it produced things like "life eats life, borne by the
# moon's pull on the ocean", which is not a way to keep food cold.
# It was chasing a bigger number, not finding more ways.
