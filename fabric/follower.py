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
