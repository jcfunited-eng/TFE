"""Preserve complete kernel histories separately at each observed close.

Observation only: no candidate law, ranking, trade, or performance estimate.
Each prefix is recomputed because segmentation can revise earlier gates.
The date range limits observation dates, never the raw history given to L0.
One process, streaming storage, no background workers. Existing outputs refused.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.tfe_field_receipt import capture, kernel_hashes


def write_evolution(market, symbol, start, end, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    frame = market.loc[market.Symbol == symbol].copy()
    frame["Date"] = pd.to_datetime(frame.Date)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start > end:
        raise ValueError("start follows end")
    dates = frame.loc[frame.Date.between(start, end), "Date"].sort_values()
    if dates.empty or dates.iloc[0] != start or dates.iloc[-1] != end:
        raise ValueError("exact observation endpoints missing")
    if dates.duplicated().any():
        raise ValueError("duplicate observation dates")
    source_hashes = kernel_hashes()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".field-evolution-", dir=output.parent)
    digest = hashlib.sha256()
    gate_counts = []
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as stream:
                for date in dates:
                    receipt = capture(frame, symbol, date)
                    if receipt["kernel_sha256"] != source_hashes:
                        raise RuntimeError("kernel source changed between observations")
                    encoded = (json.dumps(receipt, allow_nan=False, separators=(",", ":")) + "\n").encode()
                    stream.write(encoded)
                    digest.update(encoded)
                    gate_counts.append(len(receipt["gate_history"]))
            raw.flush()
            os.fsync(raw.fileno())
        if kernel_hashes() != source_hashes:
            raise RuntimeError("kernel source changed before publication")
        # Atomic create without overwriting a concurrent publisher's receipt.
        os.link(temporary, output)
        directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)
    return {"symbol": symbol, "start": str(start.date()), "end": str(end.date()),
            "observations": len(dates), "gate_counts": gate_counts,
            "uncompressed_sha256": digest.hexdigest(), "output": str(output),
            "scope": "complete supplied-history receipt at every observed close; listing completeness unverified",
            "strategy_result": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frame = pd.read_parquet(args.bars, columns=["Symbol", "Date", "Close"],
                            filters=[("Symbol", "==", args.symbol)])
    print(json.dumps(write_evolution(frame, args.symbol, args.start, args.end, args.output)))


if __name__ == "__main__":
    main()
