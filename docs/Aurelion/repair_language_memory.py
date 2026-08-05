# repair_language_memory.py
# Quick repair for truncated or malformed language_memory.json files.
# Creates language_memory_repaired.json alongside your backup.

import json, re, os

SRC = "language_memory_corrupt_backup.json"
DST = "language_memory_repaired.json"

if not os.path.exists(SRC):
    print(f"[error] Could not find {SRC}. Place this script in the same folder as your backup.")
    raise SystemExit

good = {}
buf = []
count = 0

with open(SRC, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        buf.append(line.strip())

text = " ".join(buf)

for m in re.finditer(r'"([^"]+)":\s*\{([^}]*)\}', text):
    key = m.group(1)
    valtxt = "{" + m.group(2) + "}"
    try:
        val = json.loads(valtxt)
        good[key] = val
        count += 1
    except Exception:
        continue

with open(DST, "w", encoding="utf-8") as out:
    json.dump(good, out, indent=2)

print(f"[repair] recovered {count} entries → {DST}")
print("[done] You can rename this to language_memory.json if Aurelion loads it cleanly.")
