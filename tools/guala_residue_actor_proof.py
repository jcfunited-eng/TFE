"""Actual retained-pair household waste export, renewed intake and cold proof."""
from pathlib import Path, PurePosixPath
from dataclasses import asdict
import hashlib, json, os, signal, subprocess, sys, tempfile, zipfile
signal.alarm(145)
fresh = '--fresh' in sys.argv
if not fresh:
    archive = Path(os.environ['GUALA_ITEM1_CAPTURE_ZIP'])
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == os.environ['GUALA_ITEM1_CAPTURE_SHA256']
    root = Path(tempfile.mkdtemp(prefix='guala-residue-'))
    os.environ['GUALA_PAIRED_ROOT'] = str(root)
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist()) == 5 and all((not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in z.namelist()))
        z.extractall(root)
else:
    root = Path(os.environ['GUALA_PAIRED_ROOT'])
    assert root.parent == Path('/tmp') and root.name.startswith('guala-residue-')
from dsf_ai_service.lean_production_app import _restore_production_actor
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission
from dsf_ai_service.substrate.embodiment_world import NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM as density
from dsf_ai_service.guala_functional_organism import SATED_ABOVE, CAPACITY_MICROGRAMS
from dsf_ai_service import guala_home_world as home
ad = derive_native_resident_resource_admission(root)
store = PairedCurrentStore(root, max_body_bytes=ad.max_envelope_bytes, max_world_bytes=16777216)
before = store.restore()
actor = _restore_production_actor()
physical = actor._physical
rows = []
provisions = []

def mass(w):
    return sum((o.material.digestible_mass_micrograms for o in w.canonical_observation_snapshot().objects if o.material))
original = home.replenish_home_food

def observe_supply(w):
    state = actor._runtime.encoded()
    snap = w.canonical_observation_snapshot()
    old = mass(w)
    receipt = original(w)
    after = w.canonical_observation_snapshot()
    assert actor._runtime.encoded() == state and after.bodies == snap.bodies
    assert mass(w) + receipt['external_removed_digestible_mass_micrograms'] == old + receipt['external_digestible_mass_micrograms']
    provisions.append(receipt)
    print(json.dumps({'provision': receipt, 'world_objects_before': len(snap.objects), 'world_objects_after': len(after.objects), 'organism_unchanged_at_supply': True}), flush=True)
    from dsf_ai_service.substrate.embodiment_world import _floor_discs_overlap
    prior = {item.object_id: item for item in snap.objects}
    for item in after.objects:
        if item.object_id in receipt['replenished'] and item.object_id in prior:
            previous = prior[item.object_id]
            assert previous.position is None or not _floor_discs_overlap(item.position, item.radius_mm, previous.position, previous.radius_mm)
    return receipt
home.replenish_home_food = observe_supply

class Observe:

    def __getattr__(self, n):
        return getattr(physical, n)

    def record(self, r, result, kind):
        ob = result.observation
        oral, remainder = divmod(ob['real_nutrition_intake_zeptojoules'], density)
        assert remainder == 0
        row = {'tick': r.live_organism_tick, 'kind': kind, 'act': ob['her_act'], 'oral_intake': oral, 'reserve': r.reserve_micrograms, 'feeding': r.feeding, 'room': ob['embodiment']['room_id'], 'refusal': ob['world_action_refusal']}
        rows.append(row)
        print(json.dumps(row), flush=True)
        return result

    def settle(self, r, w, o):
        return self.record(r, physical.settle(r, w, o), o.kind)

    def unattended(self, r, w):
        return self.record(r, physical.unattended(r, w), 'unattended')

def forbidden(*args, **kwargs):
    raise AssertionError('authored pupil transport is forbidden')
actor._world.admit_authored_body_transport = forbidden
try:
    assert actor._runtime.encoded() == before.body and bytes(actor._world.encoded_snapshot()) == before.world and (actor._pointer == before.pointer)
    assert actor._runtime._modular_substrate.to_dict() == json.loads(before.body[8:])['modular_substrate']
    initial_mass = mass(actor._world)
    initial_reserve = actor._runtime.reserve_micrograms
    initial_feeding = actor._runtime.feeding
    initial_meals = actor._runtime.counts['meals_micrograms']
    actor._physical = Observe()
    print(json.dumps({'phase': 'fresh' if fresh else 'initial', 'current': asdict(before.pointer.current), 'reserve': initial_reserve, 'feeding': actor._runtime.feeding}), flush=True)
    actor.start()
    if not fresh:
        actor.submit(PhysicalOccurrence('sensory', LeanSensoryOccurrence('caretaker-food', None, None, present_food='replenish-home-food')), timeout=20)
        assert provisions and provisions[0]['external_removed_digestible_mass_micrograms'] > 0, 'actual predecessor has no demonstrated residual cleanup'
        assert 'garden-apple' in provisions[0]['replenished']
        if initial_feeding:
            for _ in range(160):
                actor.submit(PhysicalOccurrence('unattended', None), timeout=20)
                if actor._runtime.reserve_micrograms >= CAPACITY_MICROGRAMS * SATED_ABOVE and (not actor._runtime.feeding):
                    break
            assert actor._runtime.reserve_micrograms >= CAPACITY_MICROGRAMS * SATED_ABOVE and (not actor._runtime.feeding)
            assert any((r['kind'] == 'unattended' and r['oral_intake'] > 0 for r in rows))
        else:
            actor.submit(PhysicalOccurrence('unattended', None), timeout=20)
        assert mass(actor._world) + sum((r['oral_intake'] for r in rows)) + sum((p['external_removed_digestible_mass_micrograms'] for p in provisions)) == initial_mass + sum((p['external_digestible_mass_micrograms'] for p in provisions))
    else:
        actor.submit(PhysicalOccurrence('unattended', None), timeout=20)
        assert actor._runtime.counts['meals_micrograms'] == initial_meals and (not actor._runtime.feeding)
finally:
    actor.close()
after = store.restore()
assert actor._runtime.encoded() == after.body and bytes(actor._world.encoded_snapshot()) == after.world and (actor._pointer == after.pointer)
assert before.pointer.current.identity == after.pointer.current.identity
print(json.dumps({'successor': asdict(after.pointer.current), 'reserve': actor._runtime.reserve_micrograms, 'feeding': actor._runtime.feeding, 'exact_current': True}), flush=True)
if not fresh:
    subprocess.run([sys.executable, '-B', __file__, '--fresh'], check=True, timeout=35)
    print('RESIDUE_REAL_EXPORT_RENEWAL_RETAINED_COLD_PASS', flush=True)
