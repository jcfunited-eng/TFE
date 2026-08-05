#!/usr/bin/env python3
"""Losslessly stream a deep_atlas_v1 envelope into deep_atlas_v2.

The v2 representation content-addresses identical per-section motif maps.
Every entry retains an exact reference to every original association and
weight.  SQLite holds unique tables on disk so migration memory is bounded by
one chi bucket rather than the whole legacy JSON document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import time
from pathlib import Path

import ijson


def _first_item(path: Path, prefix: str):
    with path.open("rb") as handle:
        return next(ijson.items(handle, prefix, use_float=True))


def _tail_integer(path: Path, field: str) -> int:
    size = path.stat().st_size
    with path.open("rb") as handle:
        handle.seek(max(0, size - 1024 * 1024))
        tail = handle.read()
    matches = re.findall(
        rb'"' + re.escape(field.encode("ascii")) + rb'"\s*:\s*(\d+)',
        tail,
    )
    if len(matches) != 1:
        raise ValueError(f"expected one trailing integer field {field!r}")
    return int(matches[0])


def _canonical(value) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def migrate(source: Path, destination: Path) -> dict:
    source = source.resolve()
    destination = destination.resolve()
    if source == destination:
        raise ValueError("source and destination must be different paths")
    if destination.exists():
        raise FileExistsError(destination)
    if _first_item(source, "data.schema") != "deep_atlas_v1":
        raise ValueError("source is not deep_atlas_v1")

    outer = {
        "schema_version": _first_item(source, "schema_version"),
        "guala_identity": _first_item(source, "guala_identity"),
        "saved_at_tick": int(_first_item(source, "saved_at_tick")),
        "saved_at_timestamp": _first_item(source, "saved_at_timestamp"),
    }
    deep = {
        "tick": int(_first_item(source, "data.tick")),
        "saved_n_entries": int(
            _first_item(source, "data.saved_n_entries")),
        "promotions_survival": _tail_integer(
            source, "promotions_survival"),
        "promotions_episodic": _tail_integer(
            source, "promotions_episodic"),
        "reinstatements": _tail_integer(source, "reinstatements"),
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    output_fd, output_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp",
        dir=destination.parent,
    )
    database_fd, database_name = tempfile.mkstemp(
        prefix=".deep-atlas-v2-", suffix=".sqlite3",
        dir=destination.parent,
    )
    os.close(database_fd)
    started = time.monotonic()
    entry_count = 0
    section_reference_count = 0
    input_section_bytes = 0
    try:
        connection = sqlite3.connect(database_name)
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute(
            "CREATE TABLE tables (hash TEXT PRIMARY KEY, payload BLOB NOT NULL)")
        with os.fdopen(output_fd, "w", encoding="utf-8") as output:
            output.write("{")
            for index, (key, value) in enumerate(outer.items()):
                if index:
                    output.write(",")
                output.write(json.dumps(key))
                output.write(":")
                output.write(json.dumps(value, allow_nan=False))
            output.write(',"data":{"schema":"deep_atlas_v2"')
            output.write(',"tick":')
            output.write(str(deep["tick"]))
            output.write(',"saved_n_entries":')
            output.write(str(deep["saved_n_entries"]))
            output.write(',"entries":{')

            first_bucket = True
            with source.open("rb") as source_handle:
                for chi, entries in ijson.kvitems(
                        source_handle, "data.entries", use_float=True):
                    if not first_bucket:
                        output.write(",")
                    first_bucket = False
                    output.write(json.dumps(str(chi)))
                    output.write(":[")
                    for entry_index, entry in enumerate(entries):
                        if entry_index:
                            output.write(",")
                        co_occurrence = entry.pop("co_occurrence", None)
                        if not isinstance(co_occurrence, dict):
                            raise ValueError(
                                f"entry {chi}/{entry_index} has no co-occurrence object")
                        references = {}
                        for section, motif_values in co_occurrence.items():
                            if not isinstance(motif_values, dict):
                                raise ValueError(
                                    f"entry {chi}/{entry_index} section is not an object")
                            payload = _canonical(motif_values)
                            reference = hashlib.sha256(payload).hexdigest()
                            existing = connection.execute(
                                "SELECT payload FROM tables WHERE hash = ?",
                                (reference,),
                            ).fetchone()
                            if existing is None:
                                connection.execute(
                                    "INSERT INTO tables(hash, payload) VALUES (?, ?)",
                                    (reference, payload),
                                )
                            elif bytes(existing[0]) != payload:
                                raise ValueError(
                                    "co-occurrence content-address collision")
                            references[str(section)] = reference
                            section_reference_count += 1
                            input_section_bytes += len(payload)
                        entry["co_occurrence_refs"] = references
                        output.write(_canonical(entry).decode("utf-8"))
                        entry_count += 1
                    output.write("]")
                    if entry_count and entry_count % 5000 < len(entries):
                        print(
                            f"[deep-atlas-v2] entries={entry_count} "
                            f"elapsed={time.monotonic() - started:.1f}s",
                            flush=True,
                        )
            output.write('},"co_occurrence_tables":{')
            first_table = True
            unique_bytes = 0
            unique_tables = 0
            for reference, payload in connection.execute(
                    "SELECT hash, payload FROM tables ORDER BY hash"):
                if not first_table:
                    output.write(",")
                first_table = False
                output.write(json.dumps(reference))
                output.write(":")
                payload = bytes(payload)
                output.write(payload.decode("utf-8"))
                unique_bytes += len(payload)
                unique_tables += 1
            output.write("}")
            for field in (
                    "promotions_survival", "promotions_episodic",
                    "reinstatements"):
                output.write(",")
                output.write(json.dumps(field))
                output.write(":")
                output.write(str(deep[field]))
            output.write("}}")
            output.flush()
            os.fsync(output.fileno())
        connection.close()
        os.replace(output_name, destination)
        directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return {
            "entries": entry_count,
            "section_references": section_reference_count,
            "unique_tables": unique_tables,
            "input_section_bytes": input_section_bytes,
            "unique_section_bytes": unique_bytes,
            "output_bytes": destination.stat().st_size,
            "seconds": round(time.monotonic() - started, 3),
        }
    finally:
        if os.path.exists(output_name):
            os.unlink(output_name)
        if os.path.exists(database_name):
            os.unlink(database_name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(migrate(arguments.source, arguments.destination)))


if __name__ == "__main__":
    main()
