"""DOING — one walking rule for every doing.

Grow candidates from the instance; every law that grips kills
what it must; a kill is forever and everything downstream of it
is born dead; what survives is the arrival. The receipt shows
which laws fired and how many candidates died — you can read WHY
the answer survived.

There is NO routine per task. Not for times, not for seating, not
for coins. Laws live in lawbook.md and descend from floors;
instances declare their things, their want, and their own local
cannots. The walker below never learns what task it is doing.
"""
import os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))

def _compile(expr, names):
    code = compile(expr, "<law>", "eval")
    def fn(env):
        return eval(code, {"__builtins__": {}}, env)
    fn.names = names
    return fn

def walk(slots, laws, ring=None, rank=None, cap=20000):
    """slots: [(name, values)] · laws: [(name, kind, data)]
    kinds: alldiff | beside | not-beside | expr. Returns receipt."""
    order = [s[0] for s in slots]
    domains = {n: list(v) for n, v in slots}
    adj = set()
    if ring:
        for i, a in enumerate(ring):
            adj.add(frozenset((a, ring[(i + 1) % len(ring)])))
    prepared = []
    for name, kind, data in laws:
        if kind == "expr":
            names = [n for n in order if re.search(
                rf"\b{re.escape(n)}\b", data)]
            prepared.append((name, kind, _compile(data, names), names))
        else:
            prepared.append((name, kind, data,
                             list(data) if data else order))
    kills = {name: 0 for name, *_ in laws}
    unborn = {name: 0 for name, *_ in laws}
    visited = 0
    survivors = []
    assign = {}

    def chairs_of(pair):
        found = {}
        for s, g in assign.items():
            if g in pair: found[g] = s
        return found

    def violated(i):
        nm = order[i]
        for name, kind, data, names in prepared:
            if kind == "alldiff":
                if list(assign.values()).count(assign[nm]) > 1:
                    return name
            elif kind in ("beside", "not-beside"):
                found = chairs_of(data)
                if len(found) == 2:
                    a, b = (found[data[0]], found[data[1]])
                    near = frozenset((a, b)) in adj
                    if kind == "beside" and not near: return name
                    if kind == "not-beside" and near: return name
            elif kind == "expr":
                if all(n in assign for n in names) and nm in names:
                    if not data(assign): return name
        return None

    def grow(i):
        nonlocal visited
        if i == len(order):
            if len(survivors) < cap:
                survivors.append(dict(assign))
            return
        nm = order[i]
        rest = 1
        for j in range(i + 1, len(order)):
            rest *= len(domains[order[j]])
        for v in domains[nm]:
            assign[nm] = v
            visited += 1
            dead = violated(i)
            if dead:
                kills[dead] += 1
                unborn[dead] += rest
            else:
                grow(i + 1)
        del assign[nm]

    grow(0)
    if rank and survivors:
        rfn = _compile(rank, None)
        survivors.sort(key=lambda s: rfn(s))
    return dict(survivors=survivors, visited=visited,
                kills=kills, unborn=unborn)

# ---- numbers: instances built from the bundles + copies laws ----

def _digits(n):
    return [int(c) for c in str(n)][::-1]

def _add(rows, receipts):
    """Count several piles as one, by the column-count law only.
    The walker tries every digit; the law kills nine of ten."""
    width = max(len(_digits(r)) for r in rows)
    cols = [[_digits(r)[i] if i < len(_digits(r)) else 0
             for r in rows] for i in range(width)]
    hi = len(rows)
    slots, laws = [], []
    for i, col in enumerate(cols):
        slots.append((f"out{i}", list(range(10))))
        slots.append((f"c{i+1}", list(range(hi + 1))))
        cin = "0" if i == 0 else f"c{i}"
        laws.append((f"column-count col{i} "
                     f"(from: mathematics/bundles+counting)", "expr",
                     f"{' + '.join(map(str, col))} + {cin} "
                     f"== out{i} + 10*c{i+1}"))
    r = walk(slots, laws)
    receipts.append(r)
    s = r["survivors"]
    assert len(s) == 1, "the column law must force one survivor"
    a = s[0]
    digs = [a[f"out{i}"] for i in range(width)]
    carry = a[f"c{width}"]
    while carry:
        digs.append(carry % 10); carry //= 10
    while len(digs) > 1 and digs[-1] == 0: digs.pop()
    return int("".join(map(str, digs[::-1])))

def _times(a, b, receipts):
    """times-is-copies: lay the copies down and count them.
    Many copies go down in bundles, one place at a time."""
    k, big = (a, b) if a <= b else (b, a)
    if k == 0: return 0
    if k <= 12:
        return _add([big] * k, receipts)
    piles = []
    for place, d in enumerate(_digits(k)):
        if d == 0: continue
        part = _add([big] * d, receipts) if d > 1 else big
        piles.append(int(str(part) + "0" * place))
    return _add(piles, receipts) if len(piles) > 1 else piles[0]

def try_numbers(question):
    """The doings the lawbook holds today: adding and times."""
    q = question.lower()
    nums = [int(x) for x in re.findall(r"\d+", question)]
    if len(nums) < 2: return None
    if re.search(r"\bx\b|\btimes\b|[*×]", q): op = "times"
    elif re.search(r"\bplus\b|\+|\badd", q): op = "plus"
    else: return None
    receipts = []
    if op == "times":
        out = nums[0]
        for n in nums[1:]: out = _times(out, n, receipts)
        sym = " x "
    else:
        out = _add(nums, receipts)
        sym = " + "
    visited = sum(r["visited"] for r in receipts)
    died = sum(sum(r["kills"].values()) for r in receipts)
    unborn = sum(sum(r["unborn"].values()) for r in receipts)
    return (f"ARRIVED BY DOING — {sym.join(map(str, nums))} = {out:,}\n"
            f"  one survivor; {visited:,} candidates walked, {died:,} "
            f"killed by the column-count law, {unborn:,} more died "
            f"unborn by inheritance.\n"
            f"  laws walked: times-is-copies, column-count — both "
            f"descend from the mathematics floors (bundles, copies, "
            f"counting). No times-routine exists in me: the same "
            f"walking rule seats guests and counts coins.")

# ---- declared instances (things + want + local cannots) ----

def run_instance(path):
    g = {}
    exec(open(path).read(),
         {"__builtins__": {}, "range": range, "list": list}, g)
    r = walk(g["SLOTS"], g["LAWS"], ring=g.get("RING"),
             rank=g.get("RANK"))
    lines = [f"DOING: {g['NAME']}"]
    tot = sum(r["kills"].values())
    if r["survivors"]:
        n = len(r["survivors"])
        lines.append(f"ARRIVED — {n} lawful "
                     f"way{'s' if n > 1 else ''} survive of "
                     f"{r['visited']:,} candidates walked "
                     f"({tot:,} killed, "
                     f"{sum(r['unborn'].values()):,} died unborn).")
        best = r["survivors"][0]
        lines.append("  " + ("best by the declared measure: "
                     if g.get("RANK") else "one of them: ") +
                     ", ".join(f"{k}={v}" for k, v in best.items()))
    else:
        lines.append(f"CANNOT BE DONE — proven. All "
                     f"{r['visited']:,} candidates died "
                     f"({sum(r['unborn'].values()):,} more unborn); "
                     f"no survivor exists.")
    lines.append("  the laws and their receipts:")
    for name in r["kills"]:
        lines.append(f"    {name}: killed {r['kills'][name]:,} "
                     f"(+{r['unborn'][name]:,} unborn)")
    return "\n".join(lines)

if __name__ == "__main__":
    if sys.argv[1] == "numbers":
        print(try_numbers(" ".join(sys.argv[2:])) or
              "(no doing my lawbook holds yet)")
    else:
        print(run_instance(sys.argv[1]))
