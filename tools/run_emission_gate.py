#!/usr/bin/env python3
"""
EVE-GATE-EMISSION-HBASE-FREE-20260626

GL-CMD-EMISSION-HBASE-FREE gate test.
Run against the live substrate to verify committed_sections >= 3 for >= 3 of 5 inputs.

For each input:
1. Get current tick via /status
2. Call /converse with emission_mode=grandurun
3. Call /events?since_tick=N to find the emission_dynamics event
4. Read committed_sections and n_commits from that event

Prints per-input result: which sections committed, n_commits, timing.

Usage:
    python3 tools/run_emission_gate.py [--host HOST] [--key APIKEY]
    Default: HOST=http://localhost:8080, reads GUALALOOM_API_KEY from env.

Exit codes:
    0 = PASS (>= 3 of 5 inputs with committed_sections >= 3)
    1 = FAIL
    2 = ERROR (cannot reach substrate)
"""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.error

GATE_INPUTS = [
    "hello who are you",
    "what is the moon",
    "tell me about water",
    "do you know daddy",
    "what do you see",
]

PASS_THRESHOLD_INPUTS = 3
PASS_THRESHOLD_SECTIONS = 3


def post_json(url, body, api_key=None, timeout=30):
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def guala_post(host, api_key, command, text="", source="gate_test",
               emission_mode=None, timeout=30):
    body = {"command": command, "text": text, "source": source}
    if emission_mode:
        body["emission_mode"] = emission_mode
    return post_json(f"{host}/api/v1/gualaloom", body, api_key=api_key, timeout=timeout)


def get_tick(host, api_key):
    """Get current engine tick. Parses from status response text string
    since /status doesn't expose tick as a top-level JSON field."""
    resp = guala_post(host, api_key, "/status", timeout=10)
    # Try top-level "tick" first (future-proofed)
    if "tick" in resp:
        return int(resp["tick"])
    # Parse from response text: "vocab: N | reads: N | tick: N"
    import re
    text = resp.get("response", "")
    m = re.search(r"tick:\s*(\d+)", text)
    if m:
        return int(m.group(1))
    return 0


def get_emission_event(host, api_key, since_tick, max_retries=3):
    """Poll /events since_tick for emission_dynamics event.
    Event structure: {"tick": N, "kind": "emission_dynamics", "detail": {...}}
    Returns flattened event dict (kind+detail merged) or None."""
    for attempt in range(max_retries):
        if attempt > 0:
            time.sleep(0.5)
        resp = guala_post(host, api_key, "/events", text=str(since_tick), timeout=10)
        events = resp.get("events", [])
        for ev in reversed(events):
            if ev.get("kind") == "emission_dynamics":
                # Flatten: merge detail fields into top level for easy access
                flat = {"tick": ev.get("tick"), "kind": "emission_dynamics"}
                flat.update(ev.get("detail", {}))
                return flat
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8080")
    parser.add_argument("--key", default=os.environ.get("GUALALOOM_API_KEY", ""))
    args = parser.parse_args()

    host = args.host.rstrip("/")
    key = args.key

    print("GL-CMD-EMISSION-HBASE-FREE gate test")
    print(f"Target: {host}")
    print(f"Pass: >= {PASS_THRESHOLD_SECTIONS} committed_sections on >= {PASS_THRESHOLD_INPUTS}/5 inputs")
    print()

    try:
        tick = get_tick(host, key)
        print(f"Substrate reachable: tick={tick}")
    except Exception as e:
        print(f"ERROR: cannot reach substrate: {e}", file=sys.stderr)
        return 2

    results = []
    for i, text in enumerate(GATE_INPUTS):
        print(f"\nInput {i+1}/5: \"{text}\"")
        tick_before = get_tick(host, key)
        t0 = time.time()

        try:
            resp = guala_post(host, key, "/converse", text=text,
                              source="gate_test", emission_mode="grandurun",
                              timeout=30)
        except Exception as e:
            print(f"  ERROR converse: {e}")
            results.append({"input": text, "error": str(e), "pass": False})
            continue

        elapsed_converse = time.time() - t0
        emission_text = resp.get("response", "")

        # Fetch emission event from event log
        ev = get_emission_event(host, key, since_tick=tick_before)
        elapsed_total = time.time() - t0

        if ev is None:
            print(f"  [{elapsed_converse:.3f}s] response: \"{emission_text}\"")
            print(f"  WARNING: no emission_dynamics event found after tick {tick_before}")
            print(f"  This means emission ran TOPK path (no dynamics) or events not flushed.")
            committed = []
            n_commits = 0
            dynamics_ticks = 0
        else:
            committed = ev.get("committed_sections", [])
            n_commits = ev.get("n_commits", 0)
            dynamics_ticks = ev.get("dynamics_ticks", 0)
            print(f"  [{elapsed_converse:.3f}s converse, {elapsed_total:.3f}s total]")
            print(f"  response: \"{emission_text}\"")
            print(f"  committed_sections={len(committed)} {committed}")
            print(f"  n_commits={n_commits} dynamics_ticks={dynamics_ticks}")

        n_committed = len(committed)
        passed = n_committed >= PASS_THRESHOLD_SECTIONS
        print(f"  => {'PASS' if passed else 'FAIL'}")

        results.append({
            "input": text,
            "elapsed_converse": round(elapsed_converse, 3),
            "committed_sections": committed,
            "n_committed": n_committed,
            "n_commits": n_commits,
            "dynamics_ticks": dynamics_ticks,
            "response": emission_text,
            "pass": passed,
        })

    n_pass = sum(1 for r in results if r.get("pass"))
    gate_pass = n_pass >= PASS_THRESHOLD_INPUTS

    print(f"\n{'='*60}")
    print(f"Gate result: {n_pass}/5 inputs passed (need >= {PASS_THRESHOLD_INPUTS})")
    print(f"Verdict: {'PASS' if gate_pass else 'FAIL'}")

    print(f"\nPer-input summary:")
    for r in results:
        if "error" in r:
            print(f"  [ERR] {r.get('elapsed_converse','?')}s | \"{r['input']}\"")
        else:
            status = "PASS" if r.get("pass") else "FAIL"
            print(f"  [{status}] {r.get('elapsed_converse','?')}s | "
                  f"n={r.get('n_committed',0)} "
                  f"{r.get('committed_sections',[])} | \"{r['input']}\"")

    out_path = os.path.join(os.path.dirname(__file__), "emission_gate_result.json")
    with open(out_path, "w") as f:
        json.dump({
            "gate": "GL-CMD-EMISSION-HBASE-FREE",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "host": host,
            "n_pass": n_pass,
            "gate_pass": gate_pass,
            "results": results,
        }, f, indent=2)
    print(f"\nResult written to: {out_path}")

    return 0 if gate_pass else 1


if __name__ == "__main__":
    sys.exit(main())
