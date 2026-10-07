"""Actual ordinary food acquisition/intake and canonical fresh continuation."""
from dataclasses import asdict
from pathlib import Path,PurePosixPath
import os,json,hashlib,zipfile,tempfile,signal,subprocess,sys
signal.alarm(150)
fresh='--fresh' in sys.argv
if not fresh:
 archive=Path(os.environ['GUALA_ITEM1_CAPTURE_ZIP'])
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==os.environ['GUALA_ITEM1_CAPTURE_SHA256']
 root=Path(tempfile.mkdtemp(prefix='guala-item2-'));os.environ['GUALA_PAIRED_ROOT']=str(root)
 with zipfile.ZipFile(archive) as z:
  assert len(z.namelist())==5 and all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in z.namelist());z.extractall(root)
else:
 root=Path(os.environ['GUALA_PAIRED_ROOT']);assert root.parent==Path('/tmp') and root.name.startswith('guala-item2-')
from dsf_ai_service.lean_production_app import _restore_production_actor
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission
ad=derive_native_resident_resource_admission(root);store=PairedCurrentStore(root,max_body_bytes=ad.max_envelope_bytes,max_world_bytes=int(os.environ['GUALA_MAX_WORLD_BYTES']))
before=store.restore();actor=_restore_production_actor();rows=[]
try:
 assert actor._runtime.encoded()==before.body and bytes(actor._world.encoded_snapshot())==before.world and actor._pointer==before.pointer
 assert actor._runtime._modular_substrate.to_dict()==json.loads(before.body[8:])['modular_substrate']
 start_meals=actor._runtime.counts['meals_micrograms'];start_reserve=actor._runtime.reserve_micrograms
 print(json.dumps({'phase':'fresh' if fresh else 'initial','current':asdict(before.pointer.current),'meals':start_meals,'reserve':start_reserve}),flush=True)
 physical=actor._physical
 class Observe:
  def __getattr__(self,n):return getattr(physical,n)
  def record(self,runtime,world,result,prior):
   ob=result.observation;snap=world.canonical_observation_snapshot();her=next(b for b in snap.bodies if b.body_id==snap.self_body_id)
   lost=sum(o.material.digestible_mass_micrograms for o in prior.objects if o.material)-sum(o.material.digestible_mass_micrograms for o in snap.objects if o.material)
   gain=runtime.counts['meals_micrograms']-self.meals;self.meals=runtime.counts['meals_micrograms']
   row={'tick':runtime.live_organism_tick,'act':ob['her_act'],'reason':ob['act_reason'],'refusal':ob['world_action_refusal'],'room':snap.room_id,'held':her.held_object_id,'position':asdict(her.pose),'lost_digestible':lost,'credited_intake':gain,'reserve':runtime.reserve_micrograms,'nutrition':ob['real_nutrition_intake_zeptojoules']}
   assert lost==gain,(lost,gain)
   rows.append(row);print(json.dumps(row),flush=True);return result
  def settle(self,r,w,o):
   prior=w.canonical_observation_snapshot();return self.record(r,w,physical.settle(r,w,o),prior)
  def unattended(self,r,w):
   prior=w.canonical_observation_snapshot();return self.record(r,w,physical.unattended(r,w),prior)
 observer=Observe();observer.meals=start_meals;actor._physical=observer;actor.start()
 for _ in range(1 if fresh else 32):
  actor.submit(PhysicalOccurrence('unattended',None),timeout=20)
  if not fresh and any(r['credited_intake']>0 for r in rows):break
finally:actor.close()
after=store.restore();assert actor._runtime.encoded()==after.body and bytes(actor._world.encoded_snapshot())==after.world and actor._pointer==after.pointer
assert before.pointer.current.identity==after.pointer.current.identity and after.pointer.current.organism_tick>before.pointer.current.organism_tick
if not fresh:assert any(r['credited_intake']>0 for r in rows),'no actual autonomous intake'
print(json.dumps({'phase':'fresh' if fresh else 'initial','successor':asdict(after.pointer.current),'new_intake':actor._runtime.counts['meals_micrograms']-start_meals,'checkpoint_exact':True}),flush=True)
if not fresh:
 subprocess.run([sys.executable,'-B',__file__,'--fresh'],check=True,timeout=45)
 print('ITEM2_ACTUAL_UNATTENDED_INTAKE_COLD_PASS',flush=True)
