#!/usr/bin/env python3
"""Append-only metabolic-need receptor anatomy (stage 2 of the drive organ).

Parses the exact 988-port declared anatomy (legacy 220 + focal 768) and appends
TWO body-sense interoceptors, templated byte-for-byte on the thermoreceptor
records except for their identity texts: the organism's own aggregate reserve
deficit and thermal load, each a fraction of declared capacity. No native or
body execution; the output is a compressed asset for guala_receptor_anatomy.py.
"""
import ast
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

SOURCE = Path(__file__).resolve().parents[1] / "dsf_ai_service" / "guala_receptor_anatomy.py"
tree = ast.parse(SOURCE.read_text())
compressed = next(
    ast.literal_eval(node.value) for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "_FOCAL_COMPRESSED_BASE85" for target in node.targets)
)
raw = zlib.decompress(base64.b85decode(b"".join(compressed.split())))
assert hashlib.sha256(raw).hexdigest() == "d37dc4223aac3c8ce2988c7fd7fb1b1ba95ef83baacbb03262e9fbd3d1e70384"
offset = 0


def take(count):
    global offset
    value = raw[offset:offset + count]
    assert len(value) == count
    offset += count
    return value


def number(width):
    return int.from_bytes(take(width), "little")


def text():
    return take(number(2)).decode("utf-8")


def ratio():
    return text(), text()


def blob():
    return take(number(4))


def u32(value):
    return struct.pack("<I", value)


def encoded_text(value):
    body = value.encode("utf-8")
    return struct.pack("<H", len(body)) + body


assert take(8) == b"GLJSRC02"
assert number(2) == 2
assembly = text()
assert take(6) == bytes(6)
count_offset = offset
assert number(4) == 988
port_start = offset
ports = []
for index in range(988):
    begin = offset
    sense, topology = number(1), number(4)
    sensor, stream = text(), text()
    coordinates = tuple((text(), text()) for _ in range(number(2)))
    suffix_start = offset
    quantity, unit = text(), text()
    rest_start = offset
    relevance, origin, input_map = (text() for _ in range(3))
    mapping = tuple(ratio() for _ in range(4))
    blob()
    sample_count = number(4)
    assert sample_count == 4
    for _ in range(sample_count):
        ratio()
        assert struct.unpack("<d", take(8))[0] == 0.0
        ratio()
        ratio()
        ratio()
    ports.append((raw[begin:offset], sense, topology, sensor, stream, coordinates, quantity, unit, raw[rest_start:offset]))
port_end = offset
assert number(4) == 1
assert number(4) == 988
assert tuple(number(4) for _ in range(988)) == tuple(range(988))
clock_start = offset
frames = number(4)
assert frames == 4
for _ in range(frames):
    ratio()
blob()
clock_and_profile = raw[clock_start:offset]
group_count = number(4)
groups = tuple(tuple(number(4) for _ in range(number(4))) for _ in range(group_count))
assert tuple(map(len, groups)) == (27, 108, 2, 16, 16, 28, 5, 8, 4, 4, 2, 768)
assert tuple(vertex for group in groups for vertex in group) == tuple(range(988))
tail_start = offset
blob()
assert number(4) == frames
for _ in range(frames):
    ratio()
assert offset == len(raw)
tail = raw[tail_start:]

core = ports[219]
assert core[1:5] == (5, 9, "organism-core-and-cutaneous-thermoreceptors", "temperature-core")
need = []
for topology, stream, compartment, quantity in (
    (10, "metabolic-need-reserve-deficit", "whole-organism-recovery-reserves", "reserve-deficit"),
    (11, "metabolic-need-thermal-load", "whole-organism-thermal-reserves", "thermal-load"),
):
    record = bytes([5]) + u32(topology) + encoded_text("organism-metabolic-interoceptors")
    record += encoded_text(stream) + struct.pack("<H", 2)
    record += encoded_text("body-compartment") + encoded_text(compartment)
    record += encoded_text("reference-interval") + encoded_text("0-to-1-fraction-of-declared-capacity")
    record += encoded_text(quantity) + encoded_text("fraction-of-declared-reserve-material")
    record += core[8]
    need.append(record)
count = 990
occurrence = u32(1) + u32(count) + b"".join(u32(i) for i in range(count)) + clock_and_profile
new_groups = groups + (tuple(range(988, count)),)
occurrence += u32(len(new_groups))
occurrence += b"".join(u32(len(group)) + b"".join(u32(i) for i in group) for group in new_groups)
occurrence += tail
upgraded = raw[:count_offset] + u32(count) + raw[port_start:port_end] + b"".join(need) + occurrence
assert upgraded[port_start:port_end] == raw[port_start:port_end]
encoded = base64.b85encode(zlib.compress(upgraded, level=9)).decode("ascii")
result = {
    "focal_sha256": hashlib.sha256(raw).hexdigest(),
    "need_sha256": hashlib.sha256(upgraded).hexdigest(),
    "need_bytes": len(upgraded), "ports": count, "group_widths": list(map(len, new_groups)),
    "need_streams": ["metabolic-need-reserve-deficit", "metabolic-need-thermal-load"],
    "compressed_base85": encoded,
}
print(json.dumps({k: v for k, v in result.items() if k != "compressed_base85"}, sort_keys=True))
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(json.dumps(result, sort_keys=True))
