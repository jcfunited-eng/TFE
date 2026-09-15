import base64, gzip, hashlib, io, json, os, sys, urllib.request, zipfile
from pathlib import Path
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission
url = base64.b64decode(sys.argv[1]).decode()
root = Path(os.environ["GUALA_PAIRED_ROOT"])
adm = derive_native_resident_resource_admission(root)
store = PairedCurrentStore(root, max_body_bytes=adm.max_envelope_bytes, max_world_bytes=int(os.environ["GUALA_MAX_WORLD_BYTES"]))
pointer = store.read_pointer(); cur = pointer.current
saved = store.restore()
body, world = bytes(saved.body), bytes(saved.world)
assert hashlib.sha256(body).hexdigest() == cur.body_sha256 and hashlib.sha256(world).hexdigest() == cur.world_sha256
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("body.glorun.gz", gzip.compress(body))
    z.writestr("world.json", world)
    z.writestr("pointer.json", json.dumps({"current": {"identity": cur.identity, "organism_tick": cur.organism_tick, "body_bytes": len(body), "body_sha256": cur.body_sha256, "world_bytes": len(world), "world_sha256": cur.world_sha256}}, sort_keys=True))
data = buf.getvalue()
req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": "application/zip"})
resp = urllib.request.urlopen(req, timeout=120)
print(json.dumps({"tick": cur.organism_tick, "body_bytes": len(body), "world_bytes": len(world), "body_sha256": cur.body_sha256, "archive_bytes": len(data), "put_status": resp.status, "functional": body.startswith(b"GLFUNC01")}))
