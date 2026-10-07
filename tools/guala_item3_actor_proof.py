"""Retained-pair caretaker movement, actual recorded PCM hearing and cold restore.

External teaching is explicitly presented, not counted as learned pupil speech.
No body transport, reserve edit or learned-state migration is allowed.
"""
from dataclasses import asdict
from pathlib import Path, PurePosixPath
import base64,hashlib,json,os,signal,subprocess,sys,tempfile,zipfile,wave
signal.alarm(150)
fresh = '--fresh' in sys.argv
if not fresh:
    archive = Path(os.environ['GUALA_ITEM1_CAPTURE_ZIP'])
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == os.environ['GUALA_ITEM1_CAPTURE_SHA256']
    root = Path(tempfile.mkdtemp(prefix='guala-item3-'))
    os.environ['GUALA_PAIRED_ROOT'] = str(root)
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist()) == 5
        assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in z.namelist())
        z.extractall(root)
else:
    root = Path(os.environ['GUALA_PAIRED_ROOT'])
    assert root.parent == Path('/tmp') and root.name.startswith('guala-item3-')
from dsf_ai_service.lean_production_app import _restore_production_actor
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission
from dsf_ai_service import guala_functional_loop as loop
ad=derive_native_resident_resource_admission(root)
store=PairedCurrentStore(root,max_body_bytes=ad.max_envelope_bytes,max_world_bytes=int(os.environ['GUALA_MAX_WORLD_BYTES']))
before=store.restore();actor=_restore_production_actor();presentations=[];hearings=[]
def body_pose(world):
    snap=world.canonical_observation_snapshot()
    return next(b for b in snap.bodies if b.body_id==snap.self_body_id).pose
original=loop.present_food

def checked_presentation(world, object_id):
    prior=body_pose(world)
    result=original(world,object_id)
    assert body_pose(world)==prior,'caregiver relocated pupil'
    presentations.append(result)
    print(json.dumps({'presentation':result,'pupil_pose_preserved':True}),flush=True)
    return result
loop.present_food=checked_presentation

def forbidden_transport(*args,**kwargs):
    raise AssertionError('authored body transport is forbidden in caretaker accompaniment')
actor._world.admit_authored_body_transport=forbidden_transport
try:
    assert actor._runtime.encoded()==before.body
    assert bytes(actor._world.encoded_snapshot())==before.world and actor._pointer==before.pointer
    assert actor._runtime._modular_substrate.to_dict()==json.loads(before.body[8:])['modular_substrate']
    print(json.dumps({'phase':'fresh' if fresh else 'initial','current':asdict(before.pointer.current)}),flush=True)
    actor.start()
    if fresh:
        actor.submit(PhysicalOccurrence('unattended',None),timeout=20)
    else:
        room=actor._world.canonical_observation_snapshot().room_id
        actor.submit(PhysicalOccurrence('sensory',LeanSensoryOccurrence('caretaker-food',None,None,present_food='patrol-'+room)),timeout=30)
        assert presentations[-1]['presented'],presentations[-1]
        # A real approved recording and card, frozen with this proof artifact.
        manifest=json.loads(Path('/opt/item3_asset.json').read_text())
        for filename,digest in manifest.items():
            assert hashlib.sha256(Path('/opt/'+filename).read_bytes()).hexdigest()==digest
        from PIL import Image
        rgb=[]
        with Image.open('/opt/item3_card.png') as img:
            for size in ((9,3),(18,6)):
                for pixel in img.convert('RGB').resize(size).getdata():rgb.extend(pixel)
        with wave.open('/opt/item3_tutor.wav','rb') as wav:
            assert (wav.getframerate(),wav.getnchannels(),wav.getsampwidth())==(16000,1,2)
            raw=wav.readframes(wav.getnframes())
        assert len(raw)%2==0 and len(raw)%8000!=0
        for offset in range(0,len(raw),8000):
            pcm=raw[offset:offset+8000]  # real finite last fragment, no truncation
            result=actor.submit(PhysicalOccurrence('sensory',LeanSensoryOccurrence('card-microphone',tuple(rgb),pcm)),timeout=20)
            ob=result.observation
            assert ob['external_heard_sample_count']==len(pcm)//2,(len(pcm),ob['external_heard_sample_count'])
            assert ob['external_retinal_site_count']==135
            hearings.append({'tick':actor._runtime.live_organism_tick,'samples':ob['external_heard_sample_count'],'sites':ob['external_retinal_site_count'],'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'her_act':ob['her_act']})
            print(json.dumps({'heard':hearings[-1]}),flush=True)
        assert sum(r['samples'] for r in hearings)==len(raw)//2
        # Subsequent ordinary quiet intervals release the external turn.
        for _ in range(2):actor.submit(PhysicalOccurrence('unattended',None),timeout=20)
finally:
    actor.close()
after=store.restore()
assert actor._runtime.encoded()==after.body and bytes(actor._world.encoded_snapshot())==after.world and actor._pointer==after.pointer
assert before.pointer.current.identity==after.pointer.current.identity
assert after.pointer.current.organism_tick>before.pointer.current.organism_tick
print(json.dumps({'successor':asdict(after.pointer.current),'checkpoint_exact':True,'learned_speech_claim':False}),flush=True)
if not fresh:
    subprocess.run([sys.executable,'-B',__file__,'--fresh'],check=True,timeout=45)
    print('ITEM3_PHYSICAL_CARETAKER_PCM_COLD_PASS',flush=True)
