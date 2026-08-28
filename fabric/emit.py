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
