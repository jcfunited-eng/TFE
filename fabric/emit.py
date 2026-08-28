"""EMISSION — the fabric writes the program.

A making that survives is already a specification: the laws that
grip it are what the built thing may never violate. So the last
step is not more judging, it is writing the artifact out — a
standalone program that carries those laws and enforces them,
with each law quoted in its own words as the reason.

The fabric does not become the accounting system. It writes it.
"""
import os, re, sys, datetime
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa
import maker

def laws_about(want, top_fields=3, min_laws=2):
    """The laws that GOVERN a want are the ones whose own words are
    about its subject. A law from optics is not made relevant to a
    ledger by the word 'view'."""
    es_all = fa.load()
    qs = fa.words(want)
    df = {}
    for e in es_all:
        for w in fa.words(e["essence"] + " " + e["cannot"] + " "
                          + e["ask"]):
            df[w] = df.get(w, 0) + 1
    key = {w for w in qs if df.get(w, 99) <= 30} or qs
    score = {}
    for e in es_all:
        own = fa.words(e["essence"] + " " + e["cannot"])
        hit = len(key & own)
        if hit:
            score[e["field"]] = score.get(e["field"], 0) + hit
    if not score: return ["accounting control"]
    home = max(score, key=score.get)
    # the fabric declares its own neighbours in every entry's
    # thread line — follow those instead of counting shared words,
    # so a law from optics cannot wander into a ledger
    named = set()
    for e in es_all:
        if e["field"] != home: continue
        th = (e.get("thread") or "").lower()
        for o in es_all:
            tail = o["field"].split()[-1]
            if tail and tail in th and o["field"] != home:
                named.add(o["field"])
    # a neighbour only governs if the want itself reaches it too
    ranked = [f for f in sorted(named, key=lambda f: -score.get(f, 0))
              if score.get(f, 0) >= max(2, score[home] // 6)]
    return [home] + ranked[:top_fields - 1]

def laws_for(fields):
    es = [e for e in fa.load()
          if any(f in e["field"] for f in fields)]
    req, forb = maker.constraints(es)
    out = []
    for a, b, e, txt in req:
        out.append(dict(kind="requires", needs=sorted(a),
                        then=sorted(b), law=txt.strip(),
                        source=e["field"]))
    for a, b, e, txt in forb:
        out.append(dict(kind="forbids", needs=sorted(a),
                        then=sorted(b), law=txt.strip(),
                        source=e["field"]))
    return out, es

def emit(fields, out_path, title):
    laws, es = laws_for(fields)
    body = ['"""' + title,
            "",
            "Written by the compute fabric from its own knowledge.",
            "Every rule below was read out of a knowledge entry's",
            "own words; none was hand-written here. Each check",
            "quotes the law it enforces and names where it came",
            "from, so a person can argue with the law rather than",
            "with the code.",
            '"""',
            "LAWS = ["]
    for L in laws:
        body.append("    " + repr(L) + ",")
    body += ["]", "",
             "def check(record):",
             '    """record: {"tags": set of words describing what',
             '    this transaction has and is. Returns the laws it',
             '    violates, each with its own words."""',
             "    tags = {t.lower() for t in record.get('tags', [])}",
             "    found = []",
             "    for L in LAWS:",
             "        has = all(n in tags for n in L['needs'])",
             "        if not has: continue",
             "        if L['kind'] == 'requires':",
             "            if not any(t in tags for t in L['then']):",
             "                found.append((L['law'], L['source']))",
             "        else:",
             "            if any(t in tags for t in L['then']):",
             "                found.append((L['law'], L['source']))",
             "    return found", "",
             "def audit(records):",
             '    """A running audit: every record, every law."""',
             "    report = []",
             "    for r in records:",
             "        v = check(r)",
             "        if v:",
             "            report.append((r.get('id', '?'), v))",
             "    return report", ""]
    open(out_path, "w").write("\n".join(body) + "\n")
    return len(laws), out_path

if __name__ == "__main__":
    n, p = emit(["accounting", "law agreements", "evidence"],
                os.path.join(BASE, "emitted_accounting_rules.py"),
                "ACCOUNTING RULES — emitted by the compute fabric")
    print(f"emitted {n} enforceable rules to {os.path.basename(p)}")

# A hand-written SYSTEM_TEMPLATE stood here: an accounting module
# I wrote myself, with the fabric's laws pasted in as quotes. It
# ran, and it was a lie about provenance — the checks were mine,
# derived by me reading the laws, not by the machine deriving them.
# Removed. What stays is generation from the laws' own parsed form
# ("no A without B" becomes a check for A present and B absent),
# which is crude and honest. If a domain needs hand-written logic,
# the hands write it separately and say so.
