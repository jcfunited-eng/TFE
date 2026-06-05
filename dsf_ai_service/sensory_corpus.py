"""
GUALALOOM-SENSES-WC-2026-06-05
Sensory corpus: hand-built signatures for seed words.

Each entry maps a word to its sensory experience across up to five
modalities (sight, sound, smell, taste, touch). Values are floats in
[0, 1] representing plausible normalized sensor outputs.

These are scaffolding. When Joseph's physical avatar comes online,
the same krimelack channels receive real sensor data instead. The
atlas binding mechanism stays identical — only the signal source
changes.

Not every word has every modality. Abstract words have none and
that's correct — they ground through co-occurrence with grounded
words, not through fake sensor values.
"""

SENSORY_EXPERIENCES = {
    # ── natural objects ──
    "sun": {
        "sight":  {"hue": 0.15, "saturation": 0.9, "lightness": 0.95,
                   "edge_density": 0.1, "motion": 0.0, "shape_signature": 0.9},
        "touch":  {"temperature": 0.95, "pressure": 0.0, "vibration": 0.0,
                   "texture_freq": 0.0, "sharpness": 0.0, "wetness": 0.0},
    },
    "moon": {
        "sight":  {"hue": 0.15, "saturation": 0.1, "lightness": 0.7,
                   "edge_density": 0.15, "motion": 0.0, "shape_signature": 0.9},
    },
    "star": {
        "sight":  {"hue": 0.17, "saturation": 0.2, "lightness": 0.85,
                   "edge_density": 0.05, "motion": 0.1, "shape_signature": 0.3},
    },
    "sky": {
        "sight":  {"hue": 0.58, "saturation": 0.6, "lightness": 0.8,
                   "edge_density": 0.05, "motion": 0.1, "shape_signature": 0.0},
    },
    "cloud": {
        "sight":  {"hue": 0.0, "saturation": 0.05, "lightness": 0.9,
                   "edge_density": 0.2, "motion": 0.15, "shape_signature": 0.2},
        "touch":  {"temperature": 0.4, "pressure": 0.0, "vibration": 0.0,
                   "texture_freq": 0.0, "sharpness": 0.0, "wetness": 0.8},
    },
    "rain": {
        "sight":  {"hue": 0.55, "saturation": 0.15, "lightness": 0.4,
                   "edge_density": 0.7, "motion": 0.9, "shape_signature": 0.1},
        "sound":  {"spectral_centroid": 0.5, "spectral_bandwidth": 0.8,
                   "attack": 0.3, "decay": 0.4, "harmonicity": 0.2, "loudness": 0.5},
        "touch":  {"temperature": 0.35, "pressure": 0.2, "vibration": 0.3,
                   "texture_freq": 0.6, "sharpness": 0.1, "wetness": 1.0},
        "smell":  {"sweet": 0.0, "putrid": 0.0, "floral": 0.1, "fruity": 0.0,
                   "smoky": 0.0, "earthy": 0.6, "sour": 0.0, "fresh": 0.8},
    },
    "water": {
        "sight":  {"hue": 0.55, "saturation": 0.3, "lightness": 0.7,
                   "edge_density": 0.4, "motion": 0.5, "shape_signature": 0.0},
        "sound":  {"spectral_centroid": 0.4, "spectral_bandwidth": 0.6,
                   "attack": 0.2, "decay": 0.7, "harmonicity": 0.3, "loudness": 0.3},
        "touch":  {"temperature": 0.4, "pressure": 0.15, "vibration": 0.5,
                   "texture_freq": 0.1, "sharpness": 0.0, "wetness": 1.0},
        "taste":  {"sweet": 0.0, "sour": 0.0, "bitter": 0.0,
                   "salty": 0.05, "umami": 0.0, "intensity": 0.1},
    },
    "ice": {
        "sight":  {"hue": 0.55, "saturation": 0.15, "lightness": 0.9,
                   "edge_density": 0.6, "motion": 0.0, "shape_signature": 0.4},
        "touch":  {"temperature": 0.02, "pressure": 0.7, "vibration": 0.0,
                   "texture_freq": 0.05, "sharpness": 0.3, "wetness": 0.6},
        "sound":  {"spectral_centroid": 0.7, "spectral_bandwidth": 0.3,
                   "attack": 0.9, "decay": 0.3, "harmonicity": 0.5, "loudness": 0.3},
    },
    "snow": {
        "sight":  {"hue": 0.0, "saturation": 0.0, "lightness": 0.95,
                   "edge_density": 0.1, "motion": 0.4, "shape_signature": 0.15},
        "touch":  {"temperature": 0.05, "pressure": 0.05, "vibration": 0.0,
                   "texture_freq": 0.3, "sharpness": 0.0, "wetness": 0.7},
    },
    "fire": {
        "sight":  {"hue": 0.08, "saturation": 0.95, "lightness": 0.85,
                   "edge_density": 0.8, "motion": 0.9, "shape_signature": 0.15},
        "sound":  {"spectral_centroid": 0.45, "spectral_bandwidth": 0.7,
                   "attack": 0.3, "decay": 0.5, "harmonicity": 0.2, "loudness": 0.5},
        "smell":  {"sweet": 0.0, "putrid": 0.0, "floral": 0.0, "fruity": 0.0,
                   "smoky": 0.95, "earthy": 0.2, "sour": 0.0, "fresh": 0.0},
        "touch":  {"temperature": 0.99, "pressure": 0.0, "vibration": 0.3,
                   "texture_freq": 0.0, "sharpness": 0.5, "wetness": 0.0},
    },
    "stone": {
        "sight":  {"hue": 0.1, "saturation": 0.1, "lightness": 0.4,
                   "edge_density": 0.5, "motion": 0.0, "shape_signature": 0.5},
        "touch":  {"temperature": 0.35, "pressure": 0.9, "vibration": 0.0,
                   "texture_freq": 0.6, "sharpness": 0.3, "wetness": 0.0},
        "sound":  {"spectral_centroid": 0.6, "spectral_bandwidth": 0.3,
                   "attack": 0.95, "decay": 0.2, "harmonicity": 0.4, "loudness": 0.4},
    },
    "earth": {
        "sight":  {"hue": 0.08, "saturation": 0.4, "lightness": 0.3,
                   "edge_density": 0.6, "motion": 0.0, "shape_signature": 0.0},
        "smell":  {"sweet": 0.0, "putrid": 0.1, "floral": 0.0, "fruity": 0.0,
                   "smoky": 0.1, "earthy": 0.95, "sour": 0.0, "fresh": 0.3},
        "touch":  {"temperature": 0.4, "pressure": 0.5, "vibration": 0.0,
                   "texture_freq": 0.7, "sharpness": 0.1, "wetness": 0.3},
    },
    "wind": {
        "sound":  {"spectral_centroid": 0.3, "spectral_bandwidth": 0.9,
                   "attack": 0.1, "decay": 0.8, "harmonicity": 0.15, "loudness": 0.4},
        "touch":  {"temperature": 0.35, "pressure": 0.4, "vibration": 0.2,
                   "texture_freq": 0.1, "sharpness": 0.0, "wetness": 0.0},
    },
    # ── living things ──
    "bird": {
        "sight":  {"hue": 0.1, "saturation": 0.5, "lightness": 0.5,
                   "edge_density": 0.7, "motion": 0.8, "shape_signature": 0.6},
        "sound":  {"spectral_centroid": 0.7, "spectral_bandwidth": 0.4,
                   "attack": 0.8, "decay": 0.5, "harmonicity": 0.85, "loudness": 0.4},
    },
    "cat": {
        "sight":  {"hue": 0.1, "saturation": 0.3, "lightness": 0.45,
                   "edge_density": 0.6, "motion": 0.5, "shape_signature": 0.65},
        "sound":  {"spectral_centroid": 0.5, "spectral_bandwidth": 0.3,
                   "attack": 0.4, "decay": 0.6, "harmonicity": 0.6, "loudness": 0.25},
        "touch":  {"temperature": 0.6, "pressure": 0.2, "vibration": 0.4,
                   "texture_freq": 0.8, "sharpness": 0.2, "wetness": 0.0},
    },
    "dog": {
        "sight":  {"hue": 0.1, "saturation": 0.35, "lightness": 0.45,
                   "edge_density": 0.6, "motion": 0.7, "shape_signature": 0.6},
        "sound":  {"spectral_centroid": 0.35, "spectral_bandwidth": 0.5,
                   "attack": 0.7, "decay": 0.4, "harmonicity": 0.4, "loudness": 0.7},
        "touch":  {"temperature": 0.6, "pressure": 0.3, "vibration": 0.1,
                   "texture_freq": 0.7, "sharpness": 0.05, "wetness": 0.1},
    },
    "fish": {
        "sight":  {"hue": 0.45, "saturation": 0.5, "lightness": 0.55,
                   "edge_density": 0.5, "motion": 0.6, "shape_signature": 0.7},
        "touch":  {"temperature": 0.3, "pressure": 0.1, "vibration": 0.2,
                   "texture_freq": 0.15, "sharpness": 0.0, "wetness": 0.9},
        "smell":  {"sweet": 0.0, "putrid": 0.3, "floral": 0.0, "fruity": 0.0,
                   "smoky": 0.0, "earthy": 0.2, "sour": 0.1, "fresh": 0.3},
    },
    "tree": {
        "sight":  {"hue": 0.33, "saturation": 0.6, "lightness": 0.4,
                   "edge_density": 0.7, "motion": 0.15, "shape_signature": 0.5},
        "touch":  {"temperature": 0.4, "pressure": 0.8, "vibration": 0.0,
                   "texture_freq": 0.8, "sharpness": 0.2, "wetness": 0.1},
        "smell":  {"sweet": 0.1, "putrid": 0.0, "floral": 0.1, "fruity": 0.0,
                   "smoky": 0.0, "earthy": 0.5, "sour": 0.0, "fresh": 0.5},
    },
    "flower": {
        "sight":  {"hue": 0.85, "saturation": 0.9, "lightness": 0.7,
                   "edge_density": 0.6, "motion": 0.05, "shape_signature": 0.7},
        "smell":  {"sweet": 0.8, "putrid": 0.0, "floral": 0.95, "fruity": 0.3,
                   "smoky": 0.0, "earthy": 0.1, "sour": 0.0, "fresh": 0.6},
        "touch":  {"temperature": 0.45, "pressure": 0.05, "vibration": 0.0,
                   "texture_freq": 0.2, "sharpness": 0.0, "wetness": 0.2},
    },
    "grass": {
        "sight":  {"hue": 0.33, "saturation": 0.7, "lightness": 0.5,
                   "edge_density": 0.5, "motion": 0.2, "shape_signature": 0.1},
        "smell":  {"sweet": 0.2, "putrid": 0.0, "floral": 0.1, "fruity": 0.0,
                   "smoky": 0.0, "earthy": 0.4, "sour": 0.0, "fresh": 0.7},
        "touch":  {"temperature": 0.45, "pressure": 0.1, "vibration": 0.0,
                   "texture_freq": 0.6, "sharpness": 0.15, "wetness": 0.3},
    },
    # ── food ──
    "apple": {
        "sight":  {"hue": 0.0, "saturation": 0.85, "lightness": 0.6,
                   "edge_density": 0.3, "motion": 0.0, "shape_signature": 0.9},
        "smell":  {"sweet": 0.7, "putrid": 0.0, "floral": 0.1, "fruity": 0.95,
                   "smoky": 0.0, "earthy": 0.0, "sour": 0.1, "fresh": 0.9},
        "taste":  {"sweet": 0.7, "sour": 0.4, "bitter": 0.05,
                   "salty": 0.0, "umami": 0.0, "intensity": 0.7},
        "touch":  {"temperature": 0.4, "pressure": 0.6, "vibration": 0.0,
                   "texture_freq": 0.1, "sharpness": 0.0, "wetness": 0.3},
        "sound":  {"spectral_centroid": 0.7, "spectral_bandwidth": 0.3,
                   "attack": 0.95, "decay": 0.1, "harmonicity": 0.3, "loudness": 0.4},
    },
    "bread": {
        "sight":  {"hue": 0.1, "saturation": 0.5, "lightness": 0.55,
                   "edge_density": 0.4, "motion": 0.0, "shape_signature": 0.4},
        "smell":  {"sweet": 0.4, "putrid": 0.0, "floral": 0.0, "fruity": 0.0,
                   "smoky": 0.1, "earthy": 0.3, "sour": 0.15, "fresh": 0.5},
        "taste":  {"sweet": 0.3, "sour": 0.15, "bitter": 0.05,
                   "salty": 0.3, "umami": 0.2, "intensity": 0.5},
        "touch":  {"temperature": 0.5, "pressure": 0.4, "vibration": 0.0,
                   "texture_freq": 0.5, "sharpness": 0.0, "wetness": 0.15},
    },
    "honey": {
        "sight":  {"hue": 0.12, "saturation": 0.8, "lightness": 0.6,
                   "edge_density": 0.1, "motion": 0.1, "shape_signature": 0.0},
        "smell":  {"sweet": 0.95, "putrid": 0.0, "floral": 0.6, "fruity": 0.3,
                   "smoky": 0.0, "earthy": 0.1, "sour": 0.0, "fresh": 0.3},
        "taste":  {"sweet": 0.95, "sour": 0.05, "bitter": 0.0,
                   "salty": 0.0, "umami": 0.0, "intensity": 0.85},
        "touch":  {"temperature": 0.45, "pressure": 0.1, "vibration": 0.0,
                   "texture_freq": 0.02, "sharpness": 0.0, "wetness": 0.7},
    },
    "salt": {
        "taste":  {"sweet": 0.0, "sour": 0.0, "bitter": 0.05,
                   "salty": 0.95, "umami": 0.1, "intensity": 0.8},
        "sight":  {"hue": 0.0, "saturation": 0.0, "lightness": 0.95,
                   "edge_density": 0.7, "motion": 0.0, "shape_signature": 0.2},
        "touch":  {"temperature": 0.4, "pressure": 0.3, "vibration": 0.0,
                   "texture_freq": 0.8, "sharpness": 0.1, "wetness": 0.0},
    },
    "milk": {
        "sight":  {"hue": 0.0, "saturation": 0.0, "lightness": 0.95,
                   "edge_density": 0.05, "motion": 0.1, "shape_signature": 0.0},
        "taste":  {"sweet": 0.3, "sour": 0.05, "bitter": 0.0,
                   "salty": 0.05, "umami": 0.15, "intensity": 0.4},
        "touch":  {"temperature": 0.35, "pressure": 0.05, "vibration": 0.0,
                   "texture_freq": 0.02, "sharpness": 0.0, "wetness": 0.8},
    },
    "lemon": {
        "sight":  {"hue": 0.17, "saturation": 0.9, "lightness": 0.7,
                   "edge_density": 0.3, "motion": 0.0, "shape_signature": 0.8},
        "smell":  {"sweet": 0.1, "putrid": 0.0, "floral": 0.1, "fruity": 0.8,
                   "smoky": 0.0, "earthy": 0.0, "sour": 0.6, "fresh": 0.9},
        "taste":  {"sweet": 0.1, "sour": 0.95, "bitter": 0.2,
                   "salty": 0.0, "umami": 0.0, "intensity": 0.9},
        "touch":  {"temperature": 0.4, "pressure": 0.5, "vibration": 0.0,
                   "texture_freq": 0.3, "sharpness": 0.0, "wetness": 0.4},
    },
    "smoke": {
        "sight":  {"hue": 0.0, "saturation": 0.05, "lightness": 0.5,
                   "edge_density": 0.3, "motion": 0.7, "shape_signature": 0.0},
        "smell":  {"sweet": 0.0, "putrid": 0.1, "floral": 0.0, "fruity": 0.0,
                   "smoky": 0.95, "earthy": 0.2, "sour": 0.1, "fresh": 0.0},
        "touch":  {"temperature": 0.6, "pressure": 0.0, "vibration": 0.0,
                   "texture_freq": 0.0, "sharpness": 0.1, "wetness": 0.0},
    },
    # ── body / human experience ──
    "hand": {
        "sight":  {"hue": 0.08, "saturation": 0.3, "lightness": 0.6,
                   "edge_density": 0.6, "motion": 0.5, "shape_signature": 0.7},
        "touch":  {"temperature": 0.55, "pressure": 0.5, "vibration": 0.1,
                   "texture_freq": 0.4, "sharpness": 0.0, "wetness": 0.1},
    },
    "voice": {
        "sound":  {"spectral_centroid": 0.45, "spectral_bandwidth": 0.5,
                   "attack": 0.3, "decay": 0.6, "harmonicity": 0.8, "loudness": 0.5},
    },
    "song": {
        "sound":  {"spectral_centroid": 0.5, "spectral_bandwidth": 0.6,
                   "attack": 0.3, "decay": 0.7, "harmonicity": 0.9, "loudness": 0.5},
    },
    "cry": {
        "sound":  {"spectral_centroid": 0.6, "spectral_bandwidth": 0.7,
                   "attack": 0.8, "decay": 0.6, "harmonicity": 0.3, "loudness": 0.8},
    },
    "breath": {
        "sound":  {"spectral_centroid": 0.25, "spectral_bandwidth": 0.6,
                   "attack": 0.1, "decay": 0.8, "harmonicity": 0.15, "loudness": 0.15},
        "touch":  {"temperature": 0.6, "pressure": 0.15, "vibration": 0.0,
                   "texture_freq": 0.0, "sharpness": 0.0, "wetness": 0.3},
    },
    # ── materials / objects ──
    "metal": {
        "sight":  {"hue": 0.0, "saturation": 0.05, "lightness": 0.6,
                   "edge_density": 0.4, "motion": 0.0, "shape_signature": 0.3},
        "touch":  {"temperature": 0.3, "pressure": 0.95, "vibration": 0.3,
                   "texture_freq": 0.1, "sharpness": 0.4, "wetness": 0.0},
        "sound":  {"spectral_centroid": 0.8, "spectral_bandwidth": 0.4,
                   "attack": 0.95, "decay": 0.7, "harmonicity": 0.7, "loudness": 0.5},
    },
    "wood": {
        "sight":  {"hue": 0.08, "saturation": 0.45, "lightness": 0.45,
                   "edge_density": 0.5, "motion": 0.0, "shape_signature": 0.3},
        "touch":  {"temperature": 0.45, "pressure": 0.7, "vibration": 0.0,
                   "texture_freq": 0.6, "sharpness": 0.1, "wetness": 0.0},
        "smell":  {"sweet": 0.1, "putrid": 0.0, "floral": 0.0, "fruity": 0.0,
                   "smoky": 0.2, "earthy": 0.6, "sour": 0.0, "fresh": 0.3},
    },
    "glass": {
        "sight":  {"hue": 0.55, "saturation": 0.05, "lightness": 0.85,
                   "edge_density": 0.3, "motion": 0.0, "shape_signature": 0.3},
        "touch":  {"temperature": 0.3, "pressure": 0.9, "vibration": 0.1,
                   "texture_freq": 0.02, "sharpness": 0.7, "wetness": 0.0},
        "sound":  {"spectral_centroid": 0.85, "spectral_bandwidth": 0.3,
                   "attack": 0.95, "decay": 0.8, "harmonicity": 0.85, "loudness": 0.4},
    },
    # ── adjectives (single-modality grounding) ──
    "warm": {
        "touch":  {"temperature": 0.8, "pressure": 0.0, "vibration": 0.0,
                   "texture_freq": 0.0, "sharpness": 0.0, "wetness": 0.0},
    },
    "hot": {
        "touch":  {"temperature": 0.95, "pressure": 0.0, "vibration": 0.0,
                   "texture_freq": 0.0, "sharpness": 0.2, "wetness": 0.0},
    },
    "cold": {
        "touch":  {"temperature": 0.05, "pressure": 0.0, "vibration": 0.0,
                   "texture_freq": 0.0, "sharpness": 0.1, "wetness": 0.0},
    },
    "wet": {
        "touch":  {"temperature": 0.4, "pressure": 0.05, "vibration": 0.0,
                   "texture_freq": 0.1, "sharpness": 0.0, "wetness": 0.95},
    },
    "dry": {
        "touch":  {"temperature": 0.45, "pressure": 0.3, "vibration": 0.0,
                   "texture_freq": 0.5, "sharpness": 0.1, "wetness": 0.0},
    },
    "soft": {
        "touch":  {"temperature": 0.5, "pressure": 0.1, "vibration": 0.0,
                   "texture_freq": 0.15, "sharpness": 0.0, "wetness": 0.0},
    },
    "hard": {
        "touch":  {"temperature": 0.4, "pressure": 0.9, "vibration": 0.1,
                   "texture_freq": 0.3, "sharpness": 0.2, "wetness": 0.0},
    },
    "sharp": {
        "touch":  {"temperature": 0.4, "pressure": 0.7, "vibration": 0.0,
                   "texture_freq": 0.1, "sharpness": 0.95, "wetness": 0.0},
    },
    "smooth": {
        "touch":  {"temperature": 0.45, "pressure": 0.3, "vibration": 0.0,
                   "texture_freq": 0.02, "sharpness": 0.0, "wetness": 0.1},
    },
    "rough": {
        "touch":  {"temperature": 0.4, "pressure": 0.5, "vibration": 0.1,
                   "texture_freq": 0.9, "sharpness": 0.3, "wetness": 0.0},
    },
    "bright": {
        "sight":  {"hue": 0.15, "saturation": 0.6, "lightness": 0.95,
                   "edge_density": 0.2, "motion": 0.0, "shape_signature": 0.0},
    },
    "dark": {
        "sight":  {"hue": 0.0, "saturation": 0.1, "lightness": 0.05,
                   "edge_density": 0.05, "motion": 0.0, "shape_signature": 0.0},
    },
    "red": {
        "sight":  {"hue": 0.0, "saturation": 0.9, "lightness": 0.5,
                   "edge_density": 0.0, "motion": 0.0, "shape_signature": 0.0},
    },
    "blue": {
        "sight":  {"hue": 0.6, "saturation": 0.8, "lightness": 0.5,
                   "edge_density": 0.0, "motion": 0.0, "shape_signature": 0.0},
    },
    "green": {
        "sight":  {"hue": 0.33, "saturation": 0.7, "lightness": 0.5,
                   "edge_density": 0.0, "motion": 0.0, "shape_signature": 0.0},
    },
    "white": {
        "sight":  {"hue": 0.0, "saturation": 0.0, "lightness": 0.95,
                   "edge_density": 0.0, "motion": 0.0, "shape_signature": 0.0},
    },
    "black": {
        "sight":  {"hue": 0.0, "saturation": 0.0, "lightness": 0.02,
                   "edge_density": 0.0, "motion": 0.0, "shape_signature": 0.0},
    },
    "sweet": {
        "taste":  {"sweet": 0.9, "sour": 0.0, "bitter": 0.0,
                   "salty": 0.0, "umami": 0.0, "intensity": 0.7},
    },
    "sour": {
        "taste":  {"sweet": 0.0, "sour": 0.9, "bitter": 0.1,
                   "salty": 0.0, "umami": 0.0, "intensity": 0.7},
    },
    "bitter": {
        "taste":  {"sweet": 0.0, "sour": 0.1, "bitter": 0.9,
                   "salty": 0.0, "umami": 0.0, "intensity": 0.7},
    },
    "loud": {
        "sound":  {"spectral_centroid": 0.5, "spectral_bandwidth": 0.6,
                   "attack": 0.7, "decay": 0.5, "harmonicity": 0.3, "loudness": 0.95},
    },
    "quiet": {
        "sound":  {"spectral_centroid": 0.3, "spectral_bandwidth": 0.2,
                   "attack": 0.1, "decay": 0.7, "harmonicity": 0.5, "loudness": 0.05},
    },
    # ── from the seed corpus ──
    "mat": {
        "sight":  {"hue": 0.08, "saturation": 0.3, "lightness": 0.35,
                   "edge_density": 0.3, "motion": 0.0, "shape_signature": 0.3},
        "touch":  {"temperature": 0.45, "pressure": 0.3, "vibration": 0.0,
                   "texture_freq": 0.7, "sharpness": 0.0, "wetness": 0.0},
    },
    "truth": {},   # abstract — no sensory grounding, binds through co-occurrence
    "mind": {},    # abstract
    "field": {
        "sight":  {"hue": 0.33, "saturation": 0.5, "lightness": 0.55,
                   "edge_density": 0.3, "motion": 0.15, "shape_signature": 0.0},
        "smell":  {"sweet": 0.1, "putrid": 0.0, "floral": 0.2, "fruity": 0.0,
                   "smoky": 0.0, "earthy": 0.5, "sour": 0.0, "fresh": 0.6},
    },
    # ── things with strong multi-modal presence ──
    "thunder": {
        "sound":  {"spectral_centroid": 0.3, "spectral_bandwidth": 0.95,
                   "attack": 0.95, "decay": 0.9, "harmonicity": 0.1, "loudness": 0.95},
        "sight":  {"hue": 0.0, "saturation": 0.0, "lightness": 0.9,
                   "edge_density": 0.9, "motion": 0.95, "shape_signature": 0.1},
    },
    "river": {
        "sight":  {"hue": 0.5, "saturation": 0.35, "lightness": 0.5,
                   "edge_density": 0.5, "motion": 0.7, "shape_signature": 0.1},
        "sound":  {"spectral_centroid": 0.35, "spectral_bandwidth": 0.7,
                   "attack": 0.1, "decay": 0.9, "harmonicity": 0.25, "loudness": 0.4},
        "touch":  {"temperature": 0.35, "pressure": 0.3, "vibration": 0.4,
                   "texture_freq": 0.1, "sharpness": 0.0, "wetness": 1.0},
    },
    "ocean": {
        "sight":  {"hue": 0.55, "saturation": 0.6, "lightness": 0.45,
                   "edge_density": 0.4, "motion": 0.6, "shape_signature": 0.0},
        "sound":  {"spectral_centroid": 0.3, "spectral_bandwidth": 0.8,
                   "attack": 0.2, "decay": 0.9, "harmonicity": 0.2, "loudness": 0.6},
        "smell":  {"sweet": 0.0, "putrid": 0.1, "floral": 0.0, "fruity": 0.0,
                   "smoky": 0.0, "earthy": 0.2, "sour": 0.1, "fresh": 0.5},
        "touch":  {"temperature": 0.35, "pressure": 0.4, "vibration": 0.5,
                   "texture_freq": 0.1, "sharpness": 0.0, "wetness": 1.0},
    },
    "mountain": {
        "sight":  {"hue": 0.25, "saturation": 0.3, "lightness": 0.5,
                   "edge_density": 0.6, "motion": 0.0, "shape_signature": 0.7},
    },
    "night": {
        "sight":  {"hue": 0.6, "saturation": 0.2, "lightness": 0.05,
                   "edge_density": 0.05, "motion": 0.0, "shape_signature": 0.0},
        "sound":  {"spectral_centroid": 0.2, "spectral_bandwidth": 0.3,
                   "attack": 0.05, "decay": 0.8, "harmonicity": 0.3, "loudness": 0.1},
    },
    "morning": {
        "sight":  {"hue": 0.12, "saturation": 0.5, "lightness": 0.7,
                   "edge_density": 0.2, "motion": 0.1, "shape_signature": 0.0},
        "sound":  {"spectral_centroid": 0.6, "spectral_bandwidth": 0.4,
                   "attack": 0.5, "decay": 0.4, "harmonicity": 0.7, "loudness": 0.3},
        "smell":  {"sweet": 0.1, "putrid": 0.0, "floral": 0.2, "fruity": 0.0,
                   "smoky": 0.0, "earthy": 0.3, "sour": 0.0, "fresh": 0.8},
    },
    "rose": {
        "sight":  {"hue": 0.95, "saturation": 0.85, "lightness": 0.55,
                   "edge_density": 0.5, "motion": 0.0, "shape_signature": 0.7},
        "smell":  {"sweet": 0.7, "putrid": 0.0, "floral": 0.95, "fruity": 0.1,
                   "smoky": 0.0, "earthy": 0.05, "sour": 0.0, "fresh": 0.4},
        "touch":  {"temperature": 0.45, "pressure": 0.05, "vibration": 0.0,
                   "texture_freq": 0.15, "sharpness": 0.6, "wetness": 0.2},
    },
}

# Canonical component lists per modality — used by sensory_krimelacks.py
# to build fixed-length signal vectors from partial dicts.
MODALITY_COMPONENTS = {
    "sight": ["hue", "saturation", "lightness", "edge_density", "motion", "shape_signature"],
    "sound": ["spectral_centroid", "spectral_bandwidth", "attack", "decay", "harmonicity", "loudness"],
    "smell": ["sweet", "putrid", "floral", "fruity", "smoky", "earthy", "sour", "fresh"],
    "taste": ["sweet", "sour", "bitter", "salty", "umami", "intensity"],
    "touch": ["pressure", "temperature", "vibration", "texture_freq", "sharpness", "wetness"],
}

MODALITIES = list(MODALITY_COMPONENTS.keys())
