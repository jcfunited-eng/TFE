"""OSC-01 ordinary-loop acceptance; run only in a discarded, offline container.

No food provisioning, altered reserves/memory, imposed actions or caregiver
presentation. The interval count is an observer bound, never a runtime rule.
"""
import argparse
import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import zlib


def emit(event, **data):
    print(json.dumps(dict(event=event, **data)), flush=True)


def advance(actor):
    from dsf_ai_service.lean_actor import PhysicalOccurrence
    actor._adopt_checkpoint_if_ready()
    if actor._durability_blocked():
        actor._receive_required_checkpoint()
    tick = actor._runtime.live_organism_tick
    result = actor._settle(PhysicalOccurrence('unattended', None))
    if result.native_interval_count != 1 or actor._runtime.live_organism_tick != tick + 1:
        raise RuntimeError('interval changed clock semantics')
    o = result.observation
    if o['caregiver_presentation'] is not None or o['caregiver_withdrawal'] is not None:
        raise RuntimeError('witness was caregiver-assisted')
    if o['world_action_refusal'] is not None and o['her_act'] in ('step','toward_food','toward_bed','toward_thing','toward_door','toward_person'):
        raise RuntimeError('witness movement refused: '+str(o['world_action_refusal']))
    e = o['embodiment']
    pose = next(b['pose'] for b in e['bodies'] if b['body_id'] == 'guala-body-1')
    row = dict(tick=tick+1, room=e['room_id'], pose=pose, act=o['her_act'],
               motion=o['actual_root_motion'], reason=o['act_reason'], reserve=o['reserve_micrograms'], refusal=o['world_action_refusal'])
    emit('interval', **row)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cold', action='store_true')
    parser.add_argument('--capture', default='/tmp/capture.json')
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    from dsf_ai_service.paired_current_store import PairedCurrentStore
    from dsf_ai_service.lean_production_app import _restore_production_actor
    root = Path('/tmp/osc01-proof-store')
    os.environ['GUALA_PAIRED_ROOT'] = str(root)
    os.environ['GUALA_MAX_WORLD_BYTES'] = '16777216'
    store = PairedCurrentStore(root, max_body_bytes=67108864, max_world_bytes=16777216)
    if not args.cold:
        raw = Path(args.capture).read_bytes()
        if hashlib.sha256(raw).hexdigest() != args.sha256:
            raise RuntimeError('wrong capture')
        capture = json.loads(raw)
        desc = capture['pointer']['current']
        decoded = {}
        for name in ('body', 'world'):
            data = zlib.decompress(base64.b64decode(capture[name+'_zlib']))
            if len(data) != desc[name+'_bytes'] or hashlib.sha256(data).hexdigest() != desc[name+'_sha256']:
                raise RuntimeError('corrupt '+name)
            decoded[name] = data
        if root.exists():
            raise RuntimeError('proof requires empty discarded store')
        store.publish(identity=desc['identity'], organism_tick=desc['organism_tick'],
                      body=decoded['body'], world=decoded['world'], expected_current_body_sha256=None)
    before = store.restore()
    if args.cold:
        expected = json.loads(Path('/tmp/osc01-successor.json').read_text())
        if asdict(before.pointer.current) != expected:
            raise RuntimeError('cold proof restored a different successor')
    actor = _restore_production_actor()
    started = time.monotonic()
    try:
        if actor._runtime.encoded() != before.body or bytes(actor._world.encoded_snapshot()) != before.world:
            raise RuntimeError('startup changed copied experience/world')
        from dsf_ai_service.substrate import native_core
        import guala_core
        if not native_core.is_installed():
            raise RuntimeError('production native acceleration missing')
        emit('predecessor', current=asdict(before.pointer.current), native=guala_core.__file__,
             native_sha256=hashlib.sha256(Path(guala_core.__file__).read_bytes()).hexdigest(),
             source_sha256=hashlib.sha256(Path('/app/dsf_ai_service/guala_functional_organism.py').read_bytes()).hexdigest())
        rows = [advance(actor) for _ in range(4 if args.cold else 64)]
        if not args.cold:
            if not any(r['room'] != 'hallway' for r in rows[:32]):
                raise RuntimeError('did not leave the measured hallway trap')
            positions = {(r['pose']['position']['x_mm'],r['pose']['position']['y_mm']) for r in rows}
            if positions <= {(8178,7802),(8380,8024)}:
                raise RuntimeError('original reversal persists')
        actor._finish_checkpoint()
        saved = store.restore()
        if saved.pointer != actor._pointer or saved.body != actor._runtime.encoded() or saved.world != bytes(actor._world.encoded_snapshot()):
            raise RuntimeError('committed/persisted successor mismatch')
        if actor._checkpoint_error or actor._cleanup_error or actor._pending_intervals:
            raise RuntimeError('custody error')
        if saved.pointer.current.identity != before.pointer.current.identity:
            raise RuntimeError('identity changed')
        emit('persisted', current=asdict(saved.pointer.current))
        if not args.cold:
            Path('/tmp/osc01-successor.json').write_text(json.dumps(asdict(saved.pointer.current)))
    finally:
        actor.close()
    if not args.cold:
        subprocess.run([sys.executable,'-B',__file__,'--cold','--sha256',args.sha256],check=True,timeout=40)
    r=resource.getrusage(resource.RUSAGE_SELF)
    emit('OSC01_COLD_PASS' if args.cold else 'OSC01_MATURE_PASS', wall=time.monotonic()-started,
         cpu=r.ru_utime+r.ru_stime, rss_kib=r.ru_maxrss)


if __name__ == '__main__':
    main()
