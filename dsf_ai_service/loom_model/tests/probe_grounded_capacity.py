"""probe_grounded_capacity.py — FIX the blindfold: run the capacity test on REAL
grounded senses (CatalogAtlasReader) instead of NullAtlasReader (synthetic hashes).

The capacity probes (-144/-146/diversity) all used NullAtlasReader, which returns
"no bindings" -> every modality falls back to hash(word) synthetic noise. This wires
the real CatalogAtlasReader on a POPULATED catalog so words arrive as structured,
genuinely-different sensory experience.

Grounding provenance: the catalog_generator design sources per-word sensory mean/std
from an LLM (ANTHROPIC_API_KEY). No key here, so c1 authored GROUNDED below directly
(c1 is an LLM; this is the same mechanism, inline). These are real semantic profiles,
not vetted by Joe. Channels per modality match MODALITY_CHANNELS.

Compares, on the SAME corpus words, grounded (CatalogAtlasReader) vs hash
(NullAtlasReader), via real brain.recall, at n=25/50/100 (where hash drops 96->73%).

Run: PYTHONHASHSEED=0 python -m dsf_ai_service.loom_model.tests.probe_grounded_capacity
"""
import sys, os, tempfile, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.brain import LoomBrain
from dsf_ai_service.loom_model.experience import ExperiencePipeline
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader, MODALITY_CHANNELS
from dsf_ai_service.curriculum.sensory_catalog import SensoryCatalog
from dsf_ai_service.curriculum.catalog_atlas_reader import CatalogAtlasReader
from dsf_ai_service.loom_model.tests.sweep_137_scaling_probe import generate_concepts

# Channels: visual=dominant_hue,saturation,brightness,spatial_complexity,motion
#           touch=temperature,pressure,texture_freq,sharpness,wetness
#           smell=sweet,putrid,floral,fruity,smoky,earthy,sour,fresh
#           taste=sweet,sour,salty,bitter,umami
#           sound=fundamental_freq,harmonic_richness,amplitude,duration_class
# Only salient channels specified; unspecified default to 0.5 at sample time.
V = "visual"; T = "touch"; S = "smell"; G = "taste"; A = "sound"
GROUNDED = {
 # --- fire / light / warm ---
 "flame":   {V:{"dominant_hue":0.05,"brightness":0.95,"saturation":0.9,"motion":0.8}, T:{"temperature":0.98}, A:{"amplitude":0.4,"fundamental_freq":0.3}, S:{"smoky":0.7}},
 "ember":   {V:{"dominant_hue":0.05,"brightness":0.6,"saturation":0.8}, T:{"temperature":0.85}, S:{"smoky":0.6}},
 "candle":  {V:{"dominant_hue":0.1,"brightness":0.55,"motion":0.3}, T:{"temperature":0.6}, S:{"smoky":0.3}},
 "lantern": {V:{"dominant_hue":0.12,"brightness":0.6}, T:{"temperature":0.5}},
 "hearth":  {V:{"dominant_hue":0.06,"brightness":0.7}, T:{"temperature":0.9}, S:{"smoky":0.6}},
 "beacon":  {V:{"brightness":0.95,"dominant_hue":0.1,"motion":0.2}, A:{"amplitude":0.3}},
 "thunder": {A:{"amplitude":0.98,"fundamental_freq":0.1,"harmonic_richness":0.7,"duration_class":0.6}, V:{"brightness":0.2}},
 # --- water ---
 "river":   {V:{"dominant_hue":0.55,"brightness":0.6,"motion":0.7}, T:{"temperature":0.35,"wetness":0.95}, A:{"amplitude":0.4,"fundamental_freq":0.5}},
 "ocean":   {V:{"dominant_hue":0.6,"brightness":0.5,"motion":0.85}, T:{"temperature":0.3,"wetness":1.0}, A:{"amplitude":0.7,"fundamental_freq":0.2}},
 "fountain":{V:{"dominant_hue":0.55,"brightness":0.7,"motion":0.8}, T:{"wetness":0.95}, A:{"amplitude":0.45,"fundamental_freq":0.6}},
 "glacier": {V:{"dominant_hue":0.6,"brightness":0.85,"saturation":0.3}, T:{"temperature":0.02,"wetness":0.7,"pressure":0.9}},
 "harbor":  {V:{"dominant_hue":0.58,"motion":0.4}, T:{"wetness":0.8}, A:{"amplitude":0.45}},
 "breeze":  {T:{"temperature":0.45,"texture_freq":0.2}, A:{"amplitude":0.2,"fundamental_freq":0.6}, V:{"motion":0.5}},
 # --- stone / metal / material ---
 "stone":   {V:{"dominant_hue":0.4,"saturation":0.1,"brightness":0.4}, T:{"temperature":0.3,"pressure":0.95,"texture_freq":0.3}},
 "pebble":  {V:{"saturation":0.2,"brightness":0.45}, T:{"pressure":0.9,"texture_freq":0.4}},
 "marble":  {V:{"brightness":0.8,"saturation":0.15,"spatial_complexity":0.5}, T:{"temperature":0.25,"pressure":0.95}},
 "quartz":  {V:{"brightness":0.85,"saturation":0.2,"spatial_complexity":0.6}, T:{"pressure":0.9,"sharpness":0.6}},
 "copper":  {V:{"dominant_hue":0.07,"saturation":0.7,"brightness":0.55}, T:{"temperature":0.4,"pressure":0.85}},
 "silver":  {V:{"brightness":0.9,"saturation":0.1}, T:{"temperature":0.35,"pressure":0.85}},
 "golden":  {V:{"dominant_hue":0.13,"saturation":0.9,"brightness":0.85}},
 "crystal": {V:{"brightness":0.9,"saturation":0.1,"spatial_complexity":0.7}, T:{"sharpness":0.7,"pressure":0.8}},
 "ivory":   {V:{"dominant_hue":0.12,"saturation":0.15,"brightness":0.85}, T:{"pressure":0.8}},
 "amber":   {V:{"dominant_hue":0.1,"saturation":0.8,"brightness":0.7}, T:{"pressure":0.6}},
 "jasper":  {V:{"dominant_hue":0.04,"saturation":0.6,"brightness":0.4}, T:{"pressure":0.9}},
 "onyx":    {V:{"saturation":0.05,"brightness":0.1}, T:{"pressure":0.9}},
 "anchor":  {V:{"saturation":0.1,"brightness":0.3}, T:{"temperature":0.3,"pressure":0.98,"wetness":0.5}},
 "hammer":  {V:{"saturation":0.2,"brightness":0.4}, T:{"pressure":0.95}, A:{"amplitude":0.7,"fundamental_freq":0.3}},
 "kettle":  {V:{"brightness":0.6,"saturation":0.2}, T:{"temperature":0.8}, A:{"amplitude":0.5,"fundamental_freq":0.8}},
 "bridge":  {V:{"saturation":0.2,"spatial_complexity":0.6}, T:{"pressure":0.9}},
 "signal":  {V:{"brightness":0.8,"motion":0.6}, A:{"amplitude":0.5,"fundamental_freq":0.7}},
 "echo":    {A:{"amplitude":0.4,"harmonic_richness":0.8,"duration_class":0.7}},
 "arcade":  {V:{"brightness":0.7,"spatial_complexity":0.8,"motion":0.6}, A:{"amplitude":0.6}},
 "pavilion":{V:{"brightness":0.6,"spatial_complexity":0.5}},
 # --- structures / domestic ---
 "castle":  {V:{"saturation":0.2,"brightness":0.4,"spatial_complexity":0.8}, T:{"pressure":0.9}},
 "cottage": {V:{"dominant_hue":0.1,"brightness":0.5,"spatial_complexity":0.4}, T:{"temperature":0.55}},
 "library": {V:{"dominant_hue":0.08,"brightness":0.4,"spatial_complexity":0.7}, S:{"earthy":0.4,"sweet":0.2}},
 "attic":   {V:{"brightness":0.25,"spatial_complexity":0.6}, S:{"earthy":0.6,"smoky":0.2}, T:{"temperature":0.6}},
 "cellar":  {V:{"brightness":0.15}, T:{"temperature":0.25,"wetness":0.5}, S:{"earthy":0.8,"putrid":0.2}},
 "kitchen": {V:{"brightness":0.6}, T:{"temperature":0.65}, S:{"fruity":0.4,"sweet":0.4}},
 "doorway": {V:{"brightness":0.5,"spatial_complexity":0.4}},
 "window":  {V:{"brightness":0.8,"spatial_complexity":0.3}},
 "basket":  {V:{"dominant_hue":0.11,"saturation":0.5}, T:{"texture_freq":0.7,"pressure":0.3}},
 "ribbon":  {V:{"saturation":0.8,"dominant_hue":0.85,"motion":0.4}, T:{"texture_freq":0.3,"pressure":0.1}},
 "linen":   {V:{"saturation":0.15,"brightness":0.8}, T:{"texture_freq":0.5,"pressure":0.2,"temperature":0.45}},
 "blanket": {V:{"saturation":0.4}, T:{"texture_freq":0.6,"pressure":0.2,"temperature":0.7}},
 "feather": {V:{"brightness":0.7,"saturation":0.3,"motion":0.5}, T:{"texture_freq":0.4,"pressure":0.02}},
 # --- landscape / sky ---
 "mountain":{V:{"saturation":0.25,"brightness":0.55,"spatial_complexity":0.8}, T:{"temperature":0.2}},
 "canyon":  {V:{"dominant_hue":0.06,"saturation":0.6,"spatial_complexity":0.8}, A:{"harmonic_richness":0.7}},
 "valley":  {V:{"dominant_hue":0.3,"brightness":0.6,"spatial_complexity":0.6}},
 "meadow":  {V:{"dominant_hue":0.3,"saturation":0.6,"brightness":0.7,"motion":0.3}, S:{"floral":0.6,"fresh":0.7}},
 "prairie": {V:{"dominant_hue":0.16,"saturation":0.5,"motion":0.4}, S:{"fresh":0.6,"earthy":0.4}},
 "pasture": {V:{"dominant_hue":0.28,"saturation":0.55}, S:{"earthy":0.5,"fresh":0.5}},
 "harvest": {V:{"dominant_hue":0.13,"saturation":0.7}, S:{"earthy":0.6,"sweet":0.4}},
 "orchard": {V:{"dominant_hue":0.25,"saturation":0.6}, S:{"fruity":0.7,"sweet":0.5,"floral":0.4}},
 "garden":  {V:{"dominant_hue":0.3,"saturation":0.7,"brightness":0.7}, S:{"floral":0.8,"fresh":0.7}},
 "thicket": {V:{"dominant_hue":0.3,"brightness":0.3,"spatial_complexity":0.9}, S:{"earthy":0.6}},
 "forest":  {V:{"dominant_hue":0.33,"saturation":0.5,"brightness":0.35,"spatial_complexity":0.9}, S:{"earthy":0.7,"fresh":0.6}, A:{"amplitude":0.2}},
 "shadow":  {V:{"brightness":0.05,"saturation":0.05}},
 "cloud":   {V:{"brightness":0.85,"saturation":0.05,"motion":0.4}, T:{"wetness":0.4}},
 "winter":  {V:{"brightness":0.8,"saturation":0.1}, T:{"temperature":0.05}},
 "summer":  {V:{"brightness":0.95,"saturation":0.7}, T:{"temperature":0.85}},
 "autumn":  {V:{"dominant_hue":0.08,"saturation":0.8,"brightness":0.6}, T:{"temperature":0.4}},
 "spring":  {V:{"dominant_hue":0.28,"saturation":0.6,"brightness":0.75}, S:{"floral":0.7,"fresh":0.8}},
 "whisper": {A:{"amplitude":0.08,"fundamental_freq":0.55,"harmonic_richness":0.3}},
 "music":   {A:{"amplitude":0.55,"harmonic_richness":0.9,"fundamental_freq":0.5,"duration_class":0.6}},
 "dragon":  {V:{"dominant_hue":0.33,"saturation":0.6,"brightness":0.4,"spatial_complexity":0.7}, T:{"temperature":0.7}, A:{"amplitude":0.7}},
 # --- trees / plants ---
 "tree":    {V:{"dominant_hue":0.3,"saturation":0.5,"spatial_complexity":0.7}, S:{"earthy":0.5,"fresh":0.4}},
 "willow":  {V:{"dominant_hue":0.27,"saturation":0.45,"motion":0.5}, S:{"fresh":0.4}},
 "spruce":  {V:{"dominant_hue":0.34,"saturation":0.5,"brightness":0.35}, S:{"fresh":0.7,"earthy":0.4}},
 "cedar":   {V:{"dominant_hue":0.07,"saturation":0.5}, S:{"earthy":0.6,"fresh":0.5,"smoky":0.3}},
 "maple":   {V:{"dominant_hue":0.05,"saturation":0.8,"brightness":0.6}, G:{"sweet":0.7}, S:{"sweet":0.5}},
 "birch":   {V:{"saturation":0.1,"brightness":0.85}, S:{"fresh":0.5}},
 "sycamore":{V:{"dominant_hue":0.2,"saturation":0.4,"spatial_complexity":0.7}},
 "reed":    {V:{"dominant_hue":0.18,"saturation":0.5,"motion":0.4}, A:{"fundamental_freq":0.6,"amplitude":0.2}},
 "clover":  {V:{"dominant_hue":0.3,"saturation":0.6}, S:{"floral":0.5,"fresh":0.6,"sweet":0.3}},
 "marigold":{V:{"dominant_hue":0.11,"saturation":0.95,"brightness":0.8}, S:{"floral":0.7,"earthy":0.3}},
 "iris":    {V:{"dominant_hue":0.78,"saturation":0.8,"brightness":0.6}, S:{"floral":0.7}},
 "lily":    {V:{"dominant_hue":0.9,"saturation":0.3,"brightness":0.9}, S:{"floral":0.9,"sweet":0.4}},
 "tulip":   {V:{"dominant_hue":0.0,"saturation":0.85,"brightness":0.7}, S:{"floral":0.5,"fresh":0.4}},
 "flower":  {V:{"dominant_hue":0.85,"saturation":0.8,"brightness":0.75}, S:{"floral":0.85,"sweet":0.4}},
 "leaf":    {V:{"dominant_hue":0.3,"saturation":0.6}, S:{"fresh":0.6,"earthy":0.3}},
 # --- fruits ---
 "apple":   {V:{"dominant_hue":0.0,"saturation":0.8,"brightness":0.6}, G:{"sweet":0.7,"sour":0.4}, S:{"fruity":0.8,"fresh":0.5}, T:{"texture_freq":0.7,"pressure":0.6}},
 "pear":    {V:{"dominant_hue":0.18,"saturation":0.5}, G:{"sweet":0.7}, S:{"fruity":0.7,"sweet":0.5}, T:{"texture_freq":0.5}},
 "cherry":  {V:{"dominant_hue":0.99,"saturation":0.9,"brightness":0.5}, G:{"sweet":0.7,"sour":0.5}, S:{"fruity":0.8,"sweet":0.6}},
 "peach":   {V:{"dominant_hue":0.06,"saturation":0.6,"brightness":0.7}, G:{"sweet":0.8}, S:{"fruity":0.9,"sweet":0.6,"floral":0.3}, T:{"texture_freq":0.6}},
 "plum":    {V:{"dominant_hue":0.8,"saturation":0.7,"brightness":0.4}, G:{"sweet":0.7,"sour":0.4}, S:{"fruity":0.7}},
 "melon":   {V:{"dominant_hue":0.25,"saturation":0.4,"brightness":0.7}, G:{"sweet":0.8}, S:{"fruity":0.7,"fresh":0.6}, T:{"wetness":0.7}},
 "quince":  {V:{"dominant_hue":0.15,"saturation":0.6}, G:{"sour":0.6,"bitter":0.3}, S:{"fruity":0.6,"floral":0.4}},
 "pomelo":  {V:{"dominant_hue":0.16,"saturation":0.5,"brightness":0.7}, G:{"sour":0.6,"sweet":0.4,"bitter":0.3}, S:{"fruity":0.7,"fresh":0.7}},
 "almond":  {V:{"dominant_hue":0.1,"saturation":0.3}, G:{"sweet":0.4,"bitter":0.3,"umami":0.3}, S:{"sweet":0.5,"earthy":0.3}, T:{"pressure":0.7}},
 "chestnut":{V:{"dominant_hue":0.06,"saturation":0.6,"brightness":0.3}, G:{"sweet":0.5,"umami":0.4}, S:{"earthy":0.6,"sweet":0.4}},
 # --- herbs / spices (smell+taste rich) ---
 "fennel":  {S:{"sweet":0.6,"fresh":0.6,"earthy":0.3}, G:{"sweet":0.5,"bitter":0.3}},
 "thyme":   {S:{"earthy":0.6,"fresh":0.7}, G:{"bitter":0.4,"umami":0.3}},
 "sage":    {S:{"earthy":0.7,"smoky":0.3,"fresh":0.5}, G:{"bitter":0.5}},
 "basil":   {S:{"floral":0.5,"fresh":0.8,"sweet":0.4}, G:{"sweet":0.4,"bitter":0.3}},
 "mint":    {S:{"fresh":0.95,"sweet":0.4}, G:{"sweet":0.5}, T:{"temperature":0.3}},
 "rosemary":{S:{"earthy":0.5,"fresh":0.7,"smoky":0.3}, G:{"bitter":0.4}},
 "parsley": {S:{"fresh":0.8,"earthy":0.3}, G:{"bitter":0.3}},
 "tarragon":{S:{"sweet":0.5,"fresh":0.6}, G:{"sweet":0.4,"bitter":0.3}},
 "chive":   {S:{"fresh":0.6,"putrid":0.3}, G:{"umami":0.4,"salty":0.3}},
 "clove":   {S:{"smoky":0.5,"sweet":0.5,"earthy":0.4}, G:{"bitter":0.5,"sweet":0.3}},
 "nutmeg":  {S:{"sweet":0.6,"earthy":0.5,"smoky":0.3}, G:{"sweet":0.4,"bitter":0.3}},
 "ginger":  {S:{"fresh":0.6,"earthy":0.4}, G:{"sour":0.3,"bitter":0.4}, T:{"temperature":0.6}},
 "cardamom":{S:{"sweet":0.5,"fresh":0.6,"floral":0.4}, G:{"sweet":0.3,"bitter":0.3}},
 "cinnamon":{V:{"dominant_hue":0.06,"saturation":0.7}, S:{"sweet":0.8,"smoky":0.4,"earthy":0.4}, G:{"sweet":0.5}},
 "vanilla": {V:{"dominant_hue":0.11,"saturation":0.2,"brightness":0.8}, S:{"sweet":0.9,"floral":0.5}, G:{"sweet":0.7}},
 "pepper":  {S:{"smoky":0.4,"earthy":0.4}, G:{"bitter":0.5}, T:{"sharpness":0.6,"temperature":0.6}},
 "saffron": {V:{"dominant_hue":0.1,"saturation":0.95,"brightness":0.6}, S:{"floral":0.5,"earthy":0.5,"smoky":0.3}, G:{"bitter":0.5,"sweet":0.3}},
 "turmeric":{V:{"dominant_hue":0.12,"saturation":0.95,"brightness":0.7}, S:{"earthy":0.7,"smoky":0.2}, G:{"bitter":0.5,"umami":0.3}},
 # --- animals ---
 "rabbit":  {V:{"dominant_hue":0.08,"saturation":0.2,"brightness":0.55}, T:{"texture_freq":0.5,"pressure":0.2,"temperature":0.7}, A:{"amplitude":0.1}},
 "bird":    {V:{"saturation":0.6,"motion":0.7}, A:{"amplitude":0.4,"fundamental_freq":0.85,"harmonic_richness":0.7}},
 "heron":   {V:{"saturation":0.2,"brightness":0.7,"motion":0.5}, A:{"amplitude":0.3,"fundamental_freq":0.4}},
}


def build_catalog(words):
    tmp = tempfile.mkdtemp()
    cat = SensoryCatalog(db_path=os.path.join(tmp, "grounded.sqlite3"))
    for w in words:
        prof = GROUNDED.get(w)
        if prof is None:
            continue
        for mod, chans in MODALITY_CHANNELS.items():
            if mod in prof:
                mean = {ch: float(prof[mod].get(ch, 0.5)) for ch in chans}
                std = {ch: 0.05 for ch in chans}
                cat.set_entry(w, mod, applicable=True, mean=mean, std=std)
            else:
                cat.set_entry(w, mod, applicable=False)
    return cat


def t5(n, reader_factory):
    corpus = generate_concepts(n, seed=42)
    brain = LoomBrain(brain_seed=42, seed_size=8)
    pipe = ExperiencePipeline(brain, SensoryTransducer(reader_factory(corpus)))
    tick = 0
    for _ in range(3):
        for w in corpus:
            pipe.deliver_word(w, tick, ticks_per_word=1); tick += 1
    correct = 0
    for w in corpus:
        top = brain.recall(pipe._build_multi_modal_signals(w)).most_common(1)
        if top and top[0][0] == w:
            correct += 1
    return correct / n * 100.0


def main():
    # coverage check
    miss = [w for w in generate_concepts(105, seed=42) if w not in GROUNDED]
    print(f"GROUNDED covers {105-len(miss)}/105 stems; missing: {miss}", flush=True)
    print(f"{'n':>5} {'hash(NullAtlas)':>16} {'grounded(Catalog)':>18}", flush=True)
    for n in [25, 50, 100]:
        t0 = time.time()
        h = t5(n, lambda c: NullAtlasReader())
        g = t5(n, lambda c: CatalogAtlasReader(build_catalog(c)))
        print(f"{n:>5} {h:>15.1f}% {g:>17.1f}%   ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
