"""Read-only live pair capture for Item 1; reuse the existing zero-writer backup."""
from pathlib import Path
import gzip,hashlib,os,runpy,signal,subprocess,sys,tempfile,zipfile
signal.alarm(180)
if sys.argv[1]=='backup':
    runpy.run_path('/opt/a1_retention_release_operator.py',run_name='__main__')
elif sys.argv[1]=='rehearse':
    from dsf_ai_service.paired_current_store import PairedCurrentStore
    from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission
    root=Path(os.environ['GUALA_PAIRED_ROOT'])
    admission=derive_native_resident_resource_admission(root)
    store=PairedCurrentStore(root,max_body_bytes=admission.max_envelope_bytes,
                            max_world_bytes=int(os.environ['GUALA_MAX_WORLD_BYTES']))
    pair=store.restore();pointer=(root/'CURRENT').read_bytes()
    assert store.read_pointer()==pair.pointer
    files={'CURRENT':pointer}
    for desc in (pair.pointer.current,pair.pointer.predecessor):
        assert desc is not None
        for name,directory,suffix in (('body','body-generations','.glorun.gz'),('world','world-generations','.glworld')):
            digest=getattr(desc,name+'_sha256');relative=directory+'/'+digest+suffix
            data=(root/relative).read_bytes()
            decoded=gzip.decompress(data) if name=='body' else data
            assert len(decoded)==getattr(desc,name+'_bytes')
            assert hashlib.sha256(decoded).hexdigest()==digest
            files[relative]=data
    assert (root/'CURRENT').read_bytes()==pointer
    directory=Path(tempfile.mkdtemp(prefix='guala-item1-capture-'))
    archive=directory/'current.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
    env=dict(os.environ,GUALA_ITEM1_CAPTURE_ZIP=str(archive),
             GUALA_ITEM1_CAPTURE_SHA256=hashlib.sha256(archive.read_bytes()).hexdigest())
    subprocess.run([sys.executable,'-B','/opt/guala_item1_actor_proof.py'],env=env,check=True,timeout=130)
else:
    raise ValueError('unknown Item 1 operator mode')
