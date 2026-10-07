"""Item 1: ordinary food eligibility and exact cold continuation on a private pair."""
from dataclasses import asdict
import hashlib,json,os,signal,subprocess,sys,tempfile,zipfile
from pathlib import Path,PurePosixPath
signal.alarm(100)
fresh='--fresh' in sys.argv
if fresh:
 root=Path(os.environ['GUALA_PAIRED_ROOT'])
 assert root.parent==Path('/tmp') and root.name.startswith('guala-item1-proof-')
else:
 archive=Path(os.environ['GUALA_ITEM1_CAPTURE_ZIP'])
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==os.environ['GUALA_ITEM1_CAPTURE_SHA256']
 root=Path(tempfile.mkdtemp(prefix='guala-item1-proof-'))
 os.environ['GUALA_PAIRED_ROOT']=str(root)
 with zipfile.ZipFile(archive) as z:
  assert len(z.namelist())==5
  assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in z.namelist())
  z.extractall(root)
from dsf_ai_service.lean_production_app import _restore_production_actor
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission
from dsf_ai_service.guala_functional_organism import FunctionalOrganism,is_genuine_food_object
admission=derive_native_resident_resource_admission(root)
store=PairedCurrentStore(root,max_body_bytes=admission.max_envelope_bytes,max_world_bytes=int(os.environ['GUALA_MAX_WORLD_BYTES']))
before=store.restore();actor=_restore_production_actor();rows=[];decisions=[];excluded=[]
try:
 assert actor._runtime.encoded()==before.body
 assert bytes(actor._world.encoded_snapshot())==before.world
 assert actor._pointer==before.pointer
 assert actor._runtime._modular_substrate.to_dict()==json.loads(before.body[8:])['modular_substrate']
 snapshot=actor._world.canonical_observation_snapshot();body=next(b for b in snapshot.bodies if b.body_id==snapshot.self_body_id)
 excluded=[o.object_id for o in snapshot.objects if is_genuine_food_object(o) and not is_genuine_food_object(o,body)]
 print(json.dumps({'phase':'fresh' if fresh else 'initial','predecessor':asdict(before.pointer.current),'native_exact':True,'untransferable_positive_remainders':excluded,'reserve':actor._runtime.reserve_micrograms}),flush=True)
 if not fresh:assert excluded,'no actual untransferable retained stock in the authenticated predecessor'
 original_decide=FunctionalOrganism.decide
 def observed_decide(self,sensed):
  d=original_decide(self,sensed)
  snap=actor._world.canonical_observation_snapshot();her=next(b for b in snap.bodies if b.body_id==snap.self_body_id)
  item=next((o for o in snap.objects if o.object_id==d.target_object_id),None)
  if d.act in ('toward_food','bite') or (self.feeding and d.act in ('grasp','take')):
   assert is_genuine_food_object(item,her),(d.act,d.target_object_id)
   assert d.target_object_id not in excluded
  decisions.append({'tick':self.live_organism_tick,'act':d.act,'target':d.target_object_id,'mass':None if item is None or item.material is None else item.material.digestible_mass_micrograms})
  return d
 FunctionalOrganism.decide=observed_decide
 physical=actor._physical
 class ObservedPhysical:
  def __getattr__(self,name):return getattr(physical,name)
  def record(self,runtime,world,result):
   o=result.observation;w=o.get('caregiver_withdrawal')
   row={'tick':runtime.live_organism_tick,'act':o.get('her_act'),'reason':o.get('act_reason'),'motion':o.get('actual_root_motion'),'intake':o.get('intake_micrograms'),'withdrawal':w}
   rows.append(row);print(json.dumps(row),flush=True)
   assert not w or not any(str(s.get('reason','')).startswith('failed:') for s in w.get('steps',[])),w
   return result
  def settle(self,runtime,world,occurrence):return self.record(runtime,world,physical.settle(runtime,world,occurrence))
  def unattended(self,runtime,world):return self.record(runtime,world,physical.unattended(runtime,world))
 actor._physical=ObservedPhysical();actor.start()
 for _ in range(1 if fresh else 16):
  actor.submit(PhysicalOccurrence('unattended',None),timeout=20)
  if not fresh and any(r['act']=='toward_food' and any(r['motion'] or ()) for r in rows):break
finally:actor.close()
after=store.restore()
assert actor._runtime.encoded()==after.body
assert bytes(actor._world.encoded_snapshot())==after.world
assert actor._pointer==after.pointer
assert before.pointer.current.identity==after.pointer.current.identity
assert after.pointer.current.organism_tick>before.pointer.current.organism_tick
assert before.pointer.current.body_sha256!=after.pointer.current.body_sha256
if not fresh:
 assert any(r['act']=='toward_food' and any(r['motion'] or ()) for r in rows),'no ordinary food-directed physical action'
 snap=actor._world.canonical_observation_snapshot()
 for oid in excluded:
  old=next(o for o in snapshot.objects if o.object_id==oid)
  new=next(o for o in snap.objects if o.object_id==oid)
  assert old.material.digestible_mass_micrograms == new.material.digestible_mass_micrograms, 'positive digestible residue changed'
  assert old.material.tastant_mass_micrograms == new.material.tastant_mass_micrograms, 'taste residue changed' 
print(json.dumps({'phase':'fresh' if fresh else 'initial','successor':asdict(after.pointer.current),'ordinary_intervals':len(rows),'decisions':decisions,'checkpoint_exact':True,'excluded_matter_preserved':True}),flush=True)
if not fresh:
 subprocess.run([sys.executable,'-B',__file__,'--fresh'],check=True,timeout=40)
 print('ITEM1_ELIGIBILITY_CAUSAL_PERSISTENCE_FRESH_PROCESS_PASS',flush=True)
