import os

ROOT = os.path.dirname(os.path.abspath(__file__))

TARGET_STRINGS = [
    "uf_structural_engine",
    "compute_structural_state",
    "compute_sev_series",
    "segment_gates",
    "compute_resonance",
    "compute_directional_signal",
    "compute_dsf",
]

def scan_file(path: str):
    hits = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                for target in TARGET_STRINGS:
                    if target in line:
                        hits.append((i, target, line.rstrip()))
    except UnicodeDecodeError:
        return []
    return hits

def main():
    print(f"[UF-CORE USAGE SCAN] Root: {ROOT}")
    for dirpath, dirnames, filenames in os.walk(ROOT):
        for name in filenames:
            if not name.endswith(".py"):
                continue
            if name == os.path.basename(__file__):
                continue
            full_path = os.path.join(dirpath, name)
            rel_path = os.path.relpath(full_path, ROOT)
            hits = scan_file(full_path)
            if hits:
                print(f"\n--- {rel_path} ---")
                for line_no, target, snippet in hits:
                    print(f"  L{line_no:4d}: {target} :: {snippet}")

if __name__ == "__main__":
    main()
