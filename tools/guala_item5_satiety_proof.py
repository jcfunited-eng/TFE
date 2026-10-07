"""Retained organism autonomously acquires replenished world food to satiety.

The only external intervention is the existing household food-stock operation.
No food is carried to the pupil; no body pose, reserve or learned state is edited.
"""
from pathlib import Path, PurePosixPath
from dataclasses import asdict
import hashlib,json,os,signal,subprocess,sys,tempfile,zipfile
signal.alarm(150)
fresh='--fresh' in sys.argv
if not fresh:
 archive=Path(os.environ['GUALA_ITEM1_CAPTURE_ZIP']);assert hashlib.sha256(archive.read_bytes()).hexdigest()==os.environ['GUALA_ITEM1_CAPTURE_SHA256']
 root=Path(tempfile.mkdtemp(prefix='guala-item5-'));os.environ['GUALA_PAIRED_ROOT']=str(root)
 with zipfile.ZipFile(archive) as z:
  assert len(z.namelist())==5 and all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in z.namelist());z.extractall(root)
else:
 root=Path(os.environ['GUALA_PAIRED_ROOT']);assert root.parent==Path('/tmp') and root.name.startswith('guala-item5-')
from dsf_ai_service.lean_production_app import _restore_production_actor
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission
from dsf_ai_service.guala_functional_organism import SATED_ABOVE,CAPACITY_MICROGRAMS
from dsf_ai_service.guala_caretaker_hand import nothing_left_to_bite
ad=derive_native_resident_resource_admission(root);store=PairedCurrentStore(root,max_body_bytes=ad.max_envelope_bytes,max_world_bytes=16777216)
before=store.restore();actor=_restore_production_actor();rows=[];physical=actor._physical
threshold=CAPACITY_MICROGRAMS*SATED_ABOVE
class Observe:
 def __getattr__(self,n):return getattr(physical,n)
 def record(self,r,w,result,meals,reserve,kind):
  from dsf_ai_service.substrate.embodiment_world import NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM as density
  ob=result.observation
  oral,remainder=divmod(ob['real_nutrition_intake_zeptojoules'],density)
  assert remainder==0
  credited=r.counts['meals_micrograms']-meals
  assert credited==min(oral,CAPACITY_MICROGRAMS-reserve)
  row={'tick':r.live_organism_tick,'kind':kind,'act':ob['her_act'],'oral_intake':oral,'retained_nutrition':credited,'capacity_excess':oral-credited,'reserve':r.reserve_micrograms,'feeding':r.feeding,'refusal':ob['world_action_refusal'],'room':w.canonical_observation_snapshot().room_id}
  rows.append(row);print(json.dumps(row),flush=True);return result
 def settle(self,r,w,o):
  meals=r.counts['meals_micrograms'];reserve=r.reserve_micrograms
  return self.record(r,w,physical.settle(r,w,o),meals,reserve,o.kind)
 def unattended(self,r,w):
  meals=r.counts['meals_micrograms'];reserve=r.reserve_micrograms
  return self.record(r,w,physical.unattended(r,w),meals,reserve,'unattended')
def mass():return sum(o.material.digestible_mass_micrograms for o in actor._world.canonical_observation_snapshot().objects if o.material)
def available():
 snap=actor._world.canonical_observation_snapshot();body=next(b for b in snap.bodies if b.body_id==snap.self_body_id)
 return any(not nothing_left_to_bite(body,o) for o in snap.objects)
def forbidden_transport(*args,**kwargs):raise AssertionError('authored pupil transport is forbidden')
actor._world.admit_authored_body_transport=forbidden_transport
try:
 assert actor._runtime.encoded()==before.body and bytes(actor._world.encoded_snapshot())==before.world and actor._pointer==before.pointer
 assert actor._runtime._modular_substrate.to_dict()==json.loads(before.body[8:])['modular_substrate']
 initial=actor._runtime.counts['meals_micrograms'];initial_mass=mass();supplied=0;provisions=0
 print(json.dumps({'phase':'fresh' if fresh else 'initial','current':asdict(before.pointer.current),'reserve':actor._runtime.reserve_micrograms,'feeding':actor._runtime.feeding,'meals':initial}),flush=True)
 actor._physical=Observe();actor.start()
 if fresh:
  assert actor._runtime.reserve_micrograms>=threshold and not actor._runtime.feeding
  actor.submit(PhysicalOccurrence('unattended',None),timeout=20)
  assert actor._runtime.counts['meals_micrograms']==initial and not actor._runtime.feeding
 else:
  assert actor._runtime.reserve_micrograms<threshold
  for _ in range(160):
   if not available():
    assert provisions<5,'satiety was not attained after five actual stock additions'
    result=actor.submit(PhysicalOccurrence('sensory',LeanSensoryOccurrence('caretaker-food',None,None,present_food='replenish-home-food')),timeout=20)
    provision=result.observation['caregiver_presentation']['provision'];assert provision['status'] in ('applied', 'unchanged'),provision
    supplied+=provision['external_digestible_mass_micrograms']
    # An unchanged request while custody is busy adds no food.
    provisions+=int(provision['status']=='applied')
    snap=actor._world.canonical_observation_snapshot()
    custody=[{'body':b.body_id,'held':b.held_object_id,'contact':b.active_contact.object_id if b.active_contact else None} for b in snap.bodies]
    print(json.dumps({'custody':custody}),flush=True)
    print(json.dumps({'external_food_provision':provision}),flush=True)
   else:actor.submit(PhysicalOccurrence('unattended',None),timeout=20)
   assert mass()+sum(r['oral_intake'] for r in rows)==initial_mass+supplied
   if actor._runtime.reserve_micrograms>=threshold and not actor._runtime.feeding:break
  assert actor._runtime.reserve_micrograms>=threshold and not actor._runtime.feeding,'satiety was not attained'
  assert any(r['kind']=='unattended' and r['oral_intake']>0 for r in rows),'no actual unattended oral intake'
finally:actor.close()
after=store.restore();assert actor._runtime.encoded()==after.body and bytes(actor._world.encoded_snapshot())==after.world and actor._pointer==after.pointer
assert after.pointer.current.identity==before.pointer.current.identity
print(json.dumps({'successor':asdict(after.pointer.current),'reserve':actor._runtime.reserve_micrograms,'feeding':actor._runtime.feeding,'meals':actor._runtime.counts['meals_micrograms'],'exact_current':True}),flush=True)
if not fresh:
 subprocess.run([sys.executable,'-B',__file__,'--fresh'],check=True,timeout=40)
 print('ITEM5_ACTUAL_UNATTENDED_SATIETY_COLD_PASS',flush=True)
