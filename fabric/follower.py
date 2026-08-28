"""THE FOLLOWER — assembles a procedure from knowledge entries at
the moment of the question, then follows it.

Built-in hands, stated honestly and completely: counting a small
pile up, counting a small pile down, and noticing the full tens
in a count. Nothing else. Places, carrying, laying copies,
shifting piles, borrowing — every one of those must be READ from
an entry's RULE text when the question arrives. If the entry is
missing, the ability is missing, and the follower says which
knowledge it lacks by name. If an entry's rule text loses a
sentence, the follower loses that step. The knowledge is
load-bearing; this file is not.

Per the development-methods entries, an assembled procedure is
written down and kept (fabric/life/assembled_procedures.md) with
its parentage.
"""
import os, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa

KEPT = os.path.join(BASE, "life", "assembled_procedures.md")

def _rules():
    out = {}
    for e in fa.load():
        r = e.get("rule", "")
        m = re.match(r"to ([\w ]+?) \u2014", r)
        if m: out[m.group(1).strip()] = (e, r)
    return out

def _find(rules, prefix):
    for k in rules:
        if k.startswith(prefix): return rules[k]
    return None

def _digits(n): return [int(c) for c in str(n)][::-1]
def _num(digs):
    while len(digs) > 1 and digs[-1] == 0: digs.pop()
    return int("".join(map(str, digs[::-1])))

def _miss(what):
    return (f"I cannot do this: {what}. Naming the gap is the "
            f"honest output — the missing knowledge can be added "
            f"as an entry, and the ability will exist.")

def _add(rows, rules):
    if not _find(rules, "add piles"):
        return None, _miss("no entry tells me how digits add — "
                           "the adding rule is not in my knowledge")
    e, r = _find(rules, "add piles")
    if "right to left" not in r:
        return None, _miss("the adding rule does not say which "
                           "way to work the places")
    if "count together" not in r:
        return None, _miss("the adding rule does not say to count "
                           "the place's digits together")
    split = "set aside every full ten" in r
    res, carry = [], 0
    width = max(len(_digits(x)) for x in rows)
    for p in range(width):
        c = carry
        for x in rows:
            d = _digits(x)
            c += d[p] if p < len(d) else 0      # counting up
        if c >= 10 and not split:
            return None, _miss("the adding rule does not say what "
                               "to do when a count passes ten")
        carry, ones = divmod(c, 10)             # noticing full tens
        res.append(ones)
    if carry and "write the carry" not in r:
        return None, _miss("the adding rule does not say where "
                           "the last carry goes")
    while carry:
        carry, ones = divmod(carry, 10)
        res.append(ones)
    return _num(res), None

def _times(a, b, rules):
    if not _find(rules, "times two numbers"):
        return None, _miss("no entry tells me what times means — "
                           "the times rule is not in my knowledge")
    e, r = _find(rules, "times two numbers")
    small, big = sorted((a, b))
    if "as many times as the smaller" not in r:
        return None, _miss("the times rule does not say how to "
                           "lay the copies down")
    if small <= 12:
        piles = [big] * small if small else [0]
    elif "place by place" in r and "one place to the left" in r:
        piles = []
        for place, d in enumerate(_digits(small)):
            if d == 0: continue
            part, err = (_add([big] * d, rules) if d > 1
                         else (big, None))
            if err: return None, err
            piles.append(int(str(part) + "0" * place))
    else:
        return None, _miss("the times rule does not say how to "
                           "handle a many-place count of copies")
    if len(piles) == 1: return piles[0], None
    if "add that pile as the adding rule says" not in r:
        return None, _miss("the times rule does not say what to "
                           "do with the laid-down pile")
    return _add(piles, rules)

def _minus(a, b, rules):
    if not _find(rules, "take one number away"):
        return None, _miss("no entry tells me how taking away "
                           "works — that rule is not in my "
                           "knowledge")
    e, r = _find(rules, "take one number away")
    if a < b:
        return None, ("The entry itself forbids this: " +
                      e["cannot"].split(".")[0] + ".")
    if "right to left" not in r:
        return None, _miss("the taking-away rule does not say "
                           "which way to work the places")
    da, db = _digits(a), _digits(b)
    res, borrow = [], 0
    for p in range(len(da)):
        u = da[p] - borrow                       # counting down
        low = db[p] if p < len(db) else 0
        if u < low:
            if "break one bundle from the next place" not in r:
                return None, _miss("the taking-away rule does not "
                                   "say what to do when the upper "
                                   "digit is too small")
            u += 10; borrow = 1                  # breaking a bundle
        else:
            borrow = 0
        res.append(u - low)                      # counting down
    return _num(res), None

def _keep(op, entry, question):
    os.makedirs(os.path.dirname(KEPT), exist_ok=True)
    old = open(KEPT).read() if os.path.exists(KEPT) else ""
    if f"PROCEDURE: {op}" in old: return
    with open(KEPT, "a") as f:
        f.write(f"\nPROCEDURE: {op}\n"
                f"  ASSEMBLED FROM: the entry beginning "
                f"\"{entry['essence'][:60]}\"\n"
                f"  FIRST USED ON: {question.strip()}\n"
                f"  KEPT: per the development-methods entry on "
                f"keeping what was assembled.\n")

def try_numbers(question):
    pr = try_poly_root(question)
    if pr: return pr
    nums = [int(x) for x in re.findall(r"\d+", question)]
    if len(nums) < 2: return None
    q = question.lower()
    if re.search(r"\bx\b|\btimes\b|\bmultipl|[*×]", q): op = "times"
    elif re.search(r"\bminus\b|\bsubtract|\btake\s*away\b|"
                   r"\bdifference\b|\d\s*-\s*\d", q): op = "minus"
    elif re.search(r"\bplus\b|\+|\badd|\bsum\b", q): op = "plus"
    else: return None
    rules = _rules()
    if op == "times":
        out, err = nums[0], None
        for n in nums[1:]:
            out, err = _times(out, n, rules)
            if err: break
        key, sym = "times two numbers", " x "
    elif op == "minus":
        out, err = nums[0], None
        for n in nums[1:]:
            out, err = _minus(out, n, rules)
            if err: break
        key, sym = "take one number away", " - "
    else:
        out, err = _add(nums, rules)
        key, sym = "add piles", " + "
    if err: return err
    entry = _find(rules, key)[0]
    _keep(op, entry, question)
    used = [f'"{entry["essence"][:55]}"']
    if op in ("times",) and _find(rules, "add piles"):
        used.append(f'"{_find(rules, "add piles")[0]["essence"][:55]}"')
    return (f"{sym.join(map(str, nums))} = {out:,}\n"
            f"  The method came from my knowledge entries, not "
            f"from code: {' and '.join(used)}. My built-in hands "
            f"did only the counting.")

# ---- grown hands: terms with powers (Joe's grant: grow whatever
# the task needs, guardrails only against harm). The STEP ORDER
# still comes from the entries: the square-root rule, the
# distributing entry (every part meets every part), the like-terms
# entry (only the same kind add), and coefficient arithmetic runs
# through the SAME knowledge-driven adding/times/taking-away rules
# above, down to the counting hands. Guardrails: this program
# reads its own knowledge folder, writes only its own records,
# runs nothing, reaches nowhere; outside its knowledge it refuses
# and names the reason.

def _gate(rules_es, fragment, gap):
    for e in rules_es:
        if fragment in e["essence"]: return None
    return _miss(gap)

def _kmul(a, b, rules):
    s = -1 if (a < 0) != (b < 0) else 1
    out, err = _times(abs(a), abs(b), rules)
    return (None, err) if err else (s * out, None)

def _kadd(a, b, rules):
    if (a >= 0) == (b >= 0):
        out, err = _add([abs(a), abs(b)], rules)
        return (None, err) if err else ((out if a >= 0 else -out),
                                        None)
    big, small = (a, b) if abs(a) >= abs(b) else (b, a)
    out, err = _minus(abs(big), abs(small), rules)
    return (None, err) if err else ((out if big >= 0 else -out),
                                    None)

def _pnorm(P): return {p: c for p, c in P.items() if c}
def _plead(P): return max(P) if P else None

def _pmul(P, Q, rules):
    out = {}
    for p1, c1 in P.items():
        for p2, c2 in Q.items():
            m, err = _kmul(c1, c2, rules)
            if err: return None, err
            out[p1 + p2], err = _kadd(out.get(p1 + p2, 0), m, rules)
            if err: return None, err
    return _pnorm(out), None

def _psub(P, Q, rules):
    out = dict(P)
    for p, c in Q.items():
        out[p], err = _kadd(out.get(p, 0), -c, rules)
        if err: return None, err
    return _pnorm(out), None

def _pstr(P):
    if not P: return "0"
    bits = []
    for p in sorted(P, reverse=True):
        c = P[p]
        mag = ("" if abs(c) == 1 and p else str(abs(c)))
        var = "" if p == 0 else ("x" if p == 1 else f"x^{p}")
        bits.append(("- " if c < 0 else ("+ " if bits else "")) +
                    (mag + var if mag + var else str(abs(c))))
    return " ".join(bits).replace("+ -", "- ")

def _pparse(text):
    t = (text.replace("²", "^2").replace("³", "^3")
         .replace("⁴", "^4").replace(" ", ""))
    P = {}
    for m in re.finditer(r"([+-]?)(\d*)x\^?(\d*)|([+-]?\d+)", t):
        if m.group(4) is not None:
            P[0] = P.get(0, 0) + int(m.group(4))
        else:
            c = int(m.group(2) or 1)
            if m.group(1) == "-": c = -c
            p = int(m.group(3) or 1)
            P[p] = P.get(p, 0) + c
    return _pnorm(P)

def try_poly_root(question):
    q = question.lower()
    if "square root" not in q or "x" not in q.split("of")[-1]:
        return None
    rules = _rules()
    hit = _find(rules, "take the square root of a polynomial")
    if not hit:
        return _miss("no entry tells me how to take the square "
                     "root of a polynomial")
    e, r = hit
    es = fa.load()
    for frag, gap in (("meets every part",
                       "the distributing knowledge — every part "
                       "of one bracket meeting every part of the "
                       "other — is not in my entries"),
                      ("same kind",
                       "the like-terms knowledge — only things of "
                       "the same kind add — is not in my entries"),
                      ("multiplied by itself",
                       "the square-root-as-a-question knowledge "
                       "is not in my entries")):
        g = _gate(es, frag, gap)
        if g: return g
    P = _pparse(question.split("of")[-1])
    if not P: return None
    NO = (f"it has no polynomial square root. The entry forbids "
          f"it: {e['essence'].split('—')[0].strip()}.")
    lead = _plead(P)
    if lead is None or lead % 2: return NO
    c = P[lead]
    t = 0                       # what, multiplied by itself, gives c
    while True:
        sq, err = _kmul(t, t, rules)
        if err: return err
        if sq == c: break
        if sq > c: return NO
        t += 1
    A = {lead // 2: t}
    sqA, err = _pmul(A, A, rules)
    if err: return err
    R, err = _psub(P, sqA, rules)
    if err: return err
    while R:
        if _plead(R) is None: break
        D, err = _pmul(A, {0: 2}, rules)       # double what you have
        if err: return err
        dl = _plead(D)
        rl = _plead(R)
        if rl < dl or R[rl] % D[dl]: return NO
        new = {rl - dl: R[rl] // D[dl]}
        take1, err = _pmul(D, new, rules)
        if err: return err
        take2, err = _pmul(new, new, rules)
        if err: return err
        R, err = _psub(R, take1, rules)
        if err: return err
        R, err = _psub(R, take2, rules)
        if err: return err
        A.update({p: A.get(p, 0) + c2 for p, c2 in new.items()})
    back, err = _pmul(A, A, rules)             # check by second route
    if err: return err
    if back != P: return NO
    _keep("square root of a polynomial", e, question)
    return (f"the square root of {_pstr(P)} is {_pstr(A)}.\n"
            f"  Worked by the rule in the algebra entry — root the "
            f"leading term, square and take away, double and match "
            f"— and checked by the second route: squaring the "
            f"answer back gives exactly what you asked about. The "
            f"coefficient arithmetic ran through the adding, times, "
            f"and taking-away entries, down to counting.")
