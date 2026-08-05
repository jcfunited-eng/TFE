#!/usr/bin/env python3
"""
GL-AUDIT-SEC4 code-truth generator.

Re-runnable, mechanical inventory generator supporting section 4 ("Code
truth at the running SHA") of GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210.
Per audit law 0.2 (GENERATED, NOT WRITTEN), every raw inventory in the
audit report is produced by this script, not hand-transcribed. Judgment
calls (LIVE/DEAD resolution, PHYSICS/TUNED classification, dead-code
true-positive vs false-positive) are made by a human reading this
script's output, and recorded in the report -- this script only surfaces
candidates with file:line evidence.

Usage:
    python3 tools/audit/sec4_code_truth.py env        --root dsf_ai_service
    python3 tools/audit/sec4_code_truth.py deadcode    --root dsf_ai_service
    python3 tools/audit/sec4_code_truth.py stubs       --root dsf_ai_service
    python3 tools/audit/sec4_code_truth.py todo        --root .
    python3 tools/audit/sec4_code_truth.py exceptpass  --root dsf_ai_service
    python3 tools/audit/sec4_code_truth.py constants   --root dsf_ai_service
    python3 tools/audit/sec4_code_truth.py all         --root dsf_ai_service

No third-party dependencies (stdlib only: os, re, sys, ast, ...) so it
runs in any Python 3 environment without a venv.
"""
import argparse
import ast
import os
import re
import sys


def iter_py_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (
            ".git", "__pycache__", "node_modules", ".venv", "venv")]
        for fn in filenames:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def read_lines(path):
    with open(path, "r", errors="replace") as f:
        return f.readlines()


# ---------------------------------------------------------------------------
# 1. env var reads (os.environ.get / os.getenv / os.environ[...])
# ---------------------------------------------------------------------------
ENV_PATTERNS = [
    re.compile(r"os\.environ\.get\(\s*[\"']([A-Z0-9_]+)[\"']"),
    re.compile(r"os\.getenv\(\s*[\"']([A-Z0-9_]+)[\"']"),
    re.compile(r"os\.environ\[\s*[\"']([A-Z0-9_]+)[\"']\s*\]"),
    re.compile(r"os\.environ\.setdefault\(\s*[\"']([A-Z0-9_]+)[\"']"),
]


def cmd_env(root):
    hits = []
    for path in sorted(iter_py_files(root)):
        lines = read_lines(path)
        for i, line in enumerate(lines, 1):
            if "environ" not in line and "getenv" not in line:
                continue
            for pat in ENV_PATTERNS:
                m = pat.search(line)
                if m:
                    hits.append((path, i, m.group(1), line.strip()))
    for path, i, name, line in hits:
        print(f"{path}:{i}: {name} :: {line}")
    print(f"\n# TOTAL env-read call sites: {len(hits)}", file=sys.stderr)
    print(f"# DISTINCT env var names:    {len(set(h[2] for h in hits))}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 2. dead-code candidates: top-level def/class with zero other references
# ---------------------------------------------------------------------------
def cmd_deadcode(root):
    defs = []  # (path, lineno, name, kind)
    for path in sorted(iter_py_files(root)):
        try:
            src = "".join(read_lines(path))
            tree = ast.parse(src, filename=path)
        except SyntaxError as e:
            print(f"# SKIP (SyntaxError) {path}: {e}", file=sys.stderr)
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    continue  # pytest test functions: "called" by the runner, not by name
                defs.append((path, node.lineno, node.name, "def"))
            elif isinstance(node, ast.ClassDef):
                defs.append((path, node.lineno, node.name, "class"))

    # Build a name -> total occurrence count across the whole tree (cheap grep-based, not AST-scoped).
    all_text = {}
    for path in sorted(iter_py_files(root)):
        all_text[path] = "".join(read_lines(path))

    candidates = []
    for path, lineno, name, kind in defs:
        if name.startswith("__") and name.endswith("__"):
            continue  # dunder methods
        pattern = re.compile(r"\b" + re.escape(name) + r"\b")
        total = 0
        for p, text in all_text.items():
            total += len(pattern.findall(text))
        # subtract 1 for the definition itself
        refs_elsewhere = total - 1
        if refs_elsewhere <= 0:
            candidates.append((path, lineno, name, kind, refs_elsewhere))

    for path, lineno, name, kind, refs in sorted(candidates):
        print(f"{path}:{lineno}: {kind} {name}  (name occurs {refs+1}x total, 0 refs beyond definition)")
    print(f"\n# candidate dead {sum(1 for c in candidates if c[3]=='def')} defs, "
          f"{sum(1 for c in candidates if c[3]=='class')} classes "
          f"out of {len(defs)} total top-level def/class scanned", file=sys.stderr)
    print("# METHOD LIMITS: whole-repo substring \\bname\\b count, not call-graph or AST-scoped;"
          " does not resolve dynamic dispatch (getattr, **kwargs handlers), string-based routing,"
          " decorators registering by name, or use via a differently-imported alias.", file=sys.stderr)


# ---------------------------------------------------------------------------
# 3. stub / unimplemented markers
# ---------------------------------------------------------------------------
STUB_RE = re.compile(
    r"NotImplementedError|#\s*STUB\b|#\s*stub\b|not implemented|NotImplemented\b",
    re.IGNORECASE)


def cmd_stubs(root):
    hits = []
    for path in sorted(iter_py_files(root)):
        for i, line in enumerate(read_lines(path), 1):
            if STUB_RE.search(line):
                hits.append((path, i, line.strip()))
    for path, i, line in hits:
        print(f"{path}:{i}: {line}")
    print(f"\n# TOTAL stub/unimplemented marker lines: {len(hits)}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 4. TODO / FIXME / XXX sweep (comments only)
# ---------------------------------------------------------------------------
TODO_RE = re.compile(r"#.*\b(TODO|FIXME|XXX)\b")


def cmd_todo(root):
    hits = []
    for path in sorted(iter_py_files(root)):
        for i, line in enumerate(read_lines(path), 1):
            m = TODO_RE.search(line)
            if m:
                hits.append((path, i, m.group(1), line.strip()))
    for path, i, tag, line in hits:
        print(f"{path}:{i}: [{tag}] {line}")
    print(f"\n# TOTAL TODO/FIXME/XXX comment hits: {len(hits)}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 5. except: / except Exception: immediately followed by pass
# ---------------------------------------------------------------------------
def cmd_exceptpass(root):
    hits = []
    for path in sorted(iter_py_files(root)):
        lines = read_lines(path)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r"^except(\s+\w+(\s+as\s+\w+)?)?\s*:", stripped):
                # find the first non-blank, non-comment following line at same or greater indent
                indent = len(line) - len(line.lstrip())
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j < len(lines):
                    body = lines[j].strip()
                    body_indent = len(lines[j]) - len(lines[j].lstrip())
                    if body_indent > indent and body == "pass":
                        # also check it's truly the whole block (next line dedents or is comment-only pass)
                        hits.append((path, i + 1, stripped))
    for path, lineno, line in hits:
        print(f"{path}:{lineno}: {line}  => pass")
    print(f"\n# TOTAL except:/except Exception: immediately-pass sites: {len(hits)}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 6. module-level constants (ALL_CAPS = <literal-ish> at column 0)
# ---------------------------------------------------------------------------
CONST_RE = re.compile(r"^([A-Z][A-Z0-9_]{2,})\s*(:\s*[\w\.\[\], ]+)?=\s*(.+)$")


def cmd_constants(root):
    hits = []
    for path in sorted(iter_py_files(root)):
        for i, line in enumerate(read_lines(path), 1):
            if line.startswith(" ") or line.startswith("\t"):
                continue  # module-level only: no leading whitespace
            m = CONST_RE.match(line.rstrip("\n"))
            if not m:
                continue
            name, _, rhs = m.groups()
            if name in ("TRUE", "FALSE", "NONE"):
                continue
            if rhs.strip().startswith(("os.environ", "os.getenv")):
                tag = "ENV-DERIVED"
            elif re.match(r"^[\-\d.eE]+$", rhs.strip().rstrip(",")):
                tag = "NUMERIC-LITERAL"
            else:
                tag = "OTHER"
            hits.append((path, i, name, rhs.strip(), tag))
    for path, i, name, rhs, tag in hits:
        print(f"{path}:{i}: {name} = {rhs}  [{tag}]")
    print(f"\n# TOTAL module-level ALL_CAPS constant assignments: {len(hits)}", file=sys.stderr)
    print(f"# NUMERIC-LITERAL subset: {sum(1 for h in hits if h[4]=='NUMERIC-LITERAL')}", file=sys.stderr)


COMMANDS = {
    "env": cmd_env,
    "deadcode": cmd_deadcode,
    "stubs": cmd_stubs,
    "todo": cmd_todo,
    "exceptpass": cmd_exceptpass,
    "constants": cmd_constants,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=list(COMMANDS.keys()) + ["all"])
    ap.add_argument("--root", default="dsf_ai_service")
    args = ap.parse_args()

    if args.command == "all":
        for name, fn in COMMANDS.items():
            print(f"\n{'='*20} {name} {'='*20}")
            fn(args.root)
    else:
        COMMANDS[args.command](args.root)


if __name__ == "__main__":
    main()
