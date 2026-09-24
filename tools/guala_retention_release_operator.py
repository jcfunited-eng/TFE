"""One-release operator helper: discarded copy proof or immutable final backup."""
import base64
from dataclasses import asdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
import zlib

signal.alarm(240)
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission

root = Path(os.environ["GUALA_PAIRED_ROOT"])
admission = derive_native_resident_resource_admission(root)
store = PairedCurrentStore(root, max_body_bytes=admission.max_envelope_bytes,
    max_world_bytes=int(os.environ["GUALA_MAX_WORLD_BYTES"]))
pair = store.restore()
mode = sys.argv[1]
if mode == "rehearse":
    raw = json.dumps({"pointer": asdict(pair.pointer),
        "body_zlib": base64.b64encode(zlib.compress(pair.body,3)).decode(),
        "world_zlib": base64.b64encode(zlib.compress(pair.world,3)).decode()},
        sort_keys=True,separators=(",",":"))
    path = Path("/tmp/a1-capture.log")
    with path.open("x") as output:
        output.write("A1_CAPTURE_START " + str(len(raw)) + "\n")
        for offset in range(0,len(raw),200000):
            output.write("A1_CAPTURE_PART "+str(offset)+":"+raw[offset:offset+200000]+"\n")
        output.write("A1_CAPTURE_END "+hashlib.sha256(raw.encode()).hexdigest()+"\n")
    subprocess.run([sys.executable, "/opt/a1_retention_actor_proof.py"], check=True, timeout=170)
elif mode == "backup":
    # Caller must first prove every live writer STOPPED. This helper never starts an actor.
    pointer_bytes = (root/"CURRENT").read_bytes()
    assert store.read_pointer() == pair.pointer
    files = {"CURRENT": pointer_bytes}
    for desc in (pair.pointer.current, pair.pointer.predecessor):
        if desc is None:
            continue
        for name, directory, suffix in (("body","body-generations",".glorun.gz"),
                                         ("world","world-generations",".glworld")):
            digest = getattr(desc, name+"_sha256")
            rel = directory+"/"+digest+suffix
            data = (root/rel).read_bytes()
            decoded = gzip.decompress(data) if name == "body" else data
            assert len(decoded) == getattr(desc,name+"_bytes")
            assert hashlib.sha256(decoded).hexdigest() == digest
            files[rel] = data
    assert store.read_pointer() == pair.pointer
    directory = root.parent/"release-backups"
    directory.mkdir(exist_ok=True)
    destination = directory/("a1-retention-"+os.environ["GIT_SHA"]+"-"+str(time.time_ns())+".zip")
    with zipfile.ZipFile(destination,"x",compression=zipfile.ZIP_STORED) as archive:
        for rel,data in sorted(files.items()):
            archive.writestr(rel,data)
    with destination.open("rb") as saved:
        os.fsync(saved.fileno())
    fd = os.open(directory,os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    scratch = Path(tempfile.mkdtemp(prefix="a1-backup-check-"))
    with zipfile.ZipFile(destination) as archive:
        assert set(archive.namelist()) == set(files)
        archive.extractall(scratch)
    check = PairedCurrentStore(scratch,max_body_bytes=admission.max_envelope_bytes,
                              max_world_bytes=int(os.environ["GUALA_MAX_WORLD_BYTES"])).restore()
    assert check == pair
    assert store.read_pointer() == pair.pointer
    print(json.dumps({"schema":"a1.retention.final_backup.v1","path":str(destination),
        "sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),
        "bytes":destination.stat().st_size,"current":asdict(pair.pointer.current)}),flush=True)
else:
    raise ValueError("unknown operator mode")
