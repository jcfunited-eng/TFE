#!/bin/bash
# preflight.sh — kills the recorded harness-mistake classes (shared
# ledger 2026-09-11, C1; Sol coordinated). Never touches speech logic:
# it only resolves paths/test names mechanically and refuses ambiguity
# BEFORE anything expensive runs.
#
#   preflight.sh file <fragment>          resolve one real file or fail
#   preflight.sh test <fragment> [--dry]  resolve ONE test name from the
#                                         newest built test binary, run
#                                         it exactly, require "1 passed"
#   preflight.sh cargo <args...>          cargo with the explicit crate
#                                         manifest, from anywhere
#
# Env: WORKTREE (default /tmp/guala-speech-existing-organ). All
# GUALA_* env vars pass through untouched. Output is bounded: full log
# to a file, only the verdict and tail to the terminal.
set -u
WORKTREE="${WORKTREE:-/tmp/guala-speech-existing-organ}"
CRATE="$WORKTREE/native/guala_core"
MANIFEST="$CRATE/Cargo.toml"

die() { echo "PREFLIGHT REFUSED: $*" >&2; exit 2; }

[ -d "$WORKTREE" ] || die "worktree missing: $WORKTREE"

newest_bin() {
  ls -t "$CRATE"/target/debug/deps/guala_core-* 2>/dev/null \
    | grep -v '\.d$' | head -1
}

case "${1:-}" in
  file)
    frag="${2:?fragment required}"
    hits=$(cd "$WORKTREE" && rg --files 2>/dev/null | grep -F -- "$frag")
    n=$(printf '%s' "$hits" | grep -c . || true)
    [ "$n" -eq 0 ] && die "no file matches '$frag'"
    [ "$n" -gt 1 ] && { echo "$hits" >&2; die "$n files match '$frag' — be exact"; }
    echo "$WORKTREE/$hits"
    ;;
  test)
    frag="${2:?test fragment required}"
    dry="${3:-}"
    bin=$(newest_bin)
    [ -n "$bin" ] || die "no built test binary under $CRATE/target/debug/deps — build first with: preflight.sh cargo test --locked --lib --no-run"
    names=$("$bin" --list 2>/dev/null | sed -n 's/: test$//p' | grep -F -- "$frag")
    n=$(printf '%s' "$names" | grep -c . || true)
    [ "$n" -eq 0 ] && die "no test matches '$frag' in $(basename "$bin")"
    [ "$n" -gt 1 ] && { echo "$names" >&2; die "$n tests match '$frag' — use the full name"; }
    full=$(printf '%s' "$names")
    log="/tmp/preflight-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
    echo "resolved: $full"
    echo "binary:   $bin"
    [ "$dry" = "--dry" ] && { echo "(dry run — not executed)"; exit 0; }
    "$bin" --exact "$full" --nocapture > "$log" 2>&1
    rc=$?
    if [ $rc -eq 0 ] && grep -q "1 passed" "$log" && ! grep -q "0 passed" "$log"; then
      echo "PREFLIGHT OK: 1 passed — full log: $log"
      tail -3 "$log"
      exit 0
    fi
    echo "PREFLIGHT FAIL (exit $rc) — full log: $log" >&2
    tail -15 "$log" >&2
    exit 1
    ;;
  cargo)
    shift
    [ -f "$MANIFEST" ] || die "manifest missing: $MANIFEST"
    exec cargo "$@" --manifest-path "$MANIFEST"
    ;;
  *)
    grep '^#   ' "$0" | sed 's/^#   //'
    exit 2
    ;;
esac
