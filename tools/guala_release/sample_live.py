"""Sample her live observation N times: act, reason, sleep, position, bedding, room.
Usage: python3 sample_live.py [beats] [pause_seconds]"""
import json, sys, time, urllib.request, collections

BASE = "https://dsf-ai.com/api/v1/guala"
n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
pause = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
acts = collections.Counter(); seen_ticks = set(); motion = 0; syll = 0; last_pos = None
for i in range(n):
    try:
        with urllib.request.urlopen(f"{BASE}/observation", timeout=25) as r:
            o = json.load(r)
    except Exception as err:  # noqa: BLE001
        print("refused:", err); time.sleep(pause); continue
    lo = o.get("last_occurrence") or {}
    tick = lo.get("native_tick")
    if tick in seen_ticks:
        time.sleep(pause); continue
    seen_ticks.add(tick)
    emb = lo.get("embodiment") or {}
    self_id = emb.get("self_body_id")
    pos = None
    for b in emb.get("bodies") or []:
        if b.get("body_id") == self_id or b.get("object_id") == self_id or b.get("id") == self_id:
            pos = b.get("pose", {}).get("position")
    if pos is None and emb.get("bodies"):
        pos = emb["bodies"][0].get("pose", {}).get("position")
    act = lo.get("her_act"); acts[act] += 1
    if lo.get("actual_root_motion"): motion += 1
    if lo.get("external_guided_vocal_axis_count") or (act == "say"): syll += 1
    sl = lo.get("her_sleep") or {}
    beds = {ob.get("object_id"): ob.get("position") for ob in emb.get("objects") or [] if str(ob.get("object_id", "")).startswith(("bed", "pillow", "blanket"))}
    print(f"{i} tick {tick} room {emb.get('room_id')} pos {pos} act {act} sleep {sl} | {str(lo.get('act_reason'))[:90]}")
    if i == 0:
        print("  bedding:", beds, "reserve", lo.get("reserve_micrograms"))
    time.sleep(pause)
print("acts", dict(acts), "motion", motion, "syllables", syll, "distinct beats", len(seen_ticks))
