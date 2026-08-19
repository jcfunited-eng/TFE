"""ch2_refusal_report.py — why CH2 bought nothing today (2026-08-10)

READ-ONLY. This tool does not touch CH2's code, configuration, flags or
positions. It reads what production already writes to its log and reports
it, because the daily summary says only "0 entries placed" and gives no
reason — which is why four days of CH2 refusing every candidate looked
like a quiet market.

What it answers, in one screen:
  * how many names passed the scan and how many orders were actually placed
  * every name that was turned down and the exact reason
  * when the same names are being refused day after day, so a static set of
    rejects is not mistaken for a stream of missed opportunities

Usage: python tools/ch2_refusal_report.py [DAYS]   (default 5)
"""

import collections
import datetime
import json
import re
import subprocess
import sys

LOG_GROUP = "/ecs/tfe-web"


def _fetch(pattern: str, days: int) -> list[tuple[int, str]]:
    start = int(
        (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=days)
        ).timestamp()
        * 1000
    )
    out = subprocess.run(
        [
            "aws", "logs", "filter-log-events",
            "--log-group-name", LOG_GROUP,
            "--start-time", str(start),
            "--filter-pattern", pattern,
            "--max-items", "500",
            "--query", "events[*].[timestamp,message]",
            "--output", "json",
        ],
        capture_output=True, text=True, timeout=280,
    )
    try:
        return [(int(t), m) for t, m in json.loads(out.stdout or "[]")]
    except (ValueError, TypeError):
        return []


def _day(ms: int) -> str:
    return datetime.datetime.fromtimestamp(
        ms / 1000, datetime.timezone.utc
    ).date().isoformat()


def main() -> int:
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    passes = _fetch('"[DAILY-ENTRY] Pass complete"', days)
    scans = _fetch('"passed V3 basin"', days)
    rejects = _fetch('"[BRIDGE] REJECT"', days)

    by_day_scan: dict[str, str] = {}
    for ts, msg in scans:
        found = re.search(
            r"(\d+) candidates → (\d+) passed .*? → (\d+) after", msg
        )
        if found:
            by_day_scan[_day(ts)] = (
                f"{found.group(1)} scanned, {found.group(2)} passed the "
                f"entry test, {found.group(3)} reached the order stage"
            )

    by_day_placed: dict[str, str] = {}
    for ts, msg in passes:
        found = re.search(r"(\d+) entries placed", msg)
        if found:
            by_day_placed[_day(ts)] = found.group(1)

    by_day_reject: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    seen_dates: dict[str, set[str]] = collections.defaultdict(set)
    for ts, msg in rejects:
        found = re.search(r"REJECT (\S+) \| (.+)$", msg.strip())
        if found:
            day = _day(ts)
            by_day_reject[day].append((found.group(1), found.group(2)))
            seen_dates[found.group(1)].add(day)

    every_day = sorted(
        set(by_day_scan) | set(by_day_placed) | set(by_day_reject), reverse=True
    )
    if not every_day:
        print("No CH2 entry activity found in the log window.")
        return 0

    print(f"CH2 ENTRY REPORT — last {days} days\n")
    for day in every_day:
        placed = by_day_placed.get(day, "?")
        print(f"{day}: {placed} bought")
        if day in by_day_scan:
            print(f"   {by_day_scan[day]}")
        turned_down = by_day_reject.get(day, [])
        if turned_down:
            reasons = collections.Counter(r for _, r in turned_down)
            plain = collections.Counter()
            for reason, count in reasons.items():
                if reason.startswith("s_uf_out_of_ch2_band"):
                    plain["already past the sell line — too strong to buy"] += count
                else:
                    plain[reason.split(":")[0]] += count
            for reason, count in plain.most_common():
                print(f"   {count} turned down: {reason}")
            print("   " + ", ".join(sorted({t for t, _ in turned_down})))
        print()

    repeats = {
        ticker: sorted(dates)
        for ticker, dates in seen_dates.items()
        if len(dates) > 1
    }
    if repeats:
        print("SAME NAMES, TURNED DOWN AGAIN AND AGAIN")
        print("(a static set of rejects, not a stream of missed chances)")
        for ticker, dates in sorted(
            repeats.items(), key=lambda kv: -len(kv[1])
        )[:15]:
            print(f"   {ticker:<6} refused on {len(dates)} days: {dates[0]} … {dates[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
