"""
virtual_home.py — Guala's virtual home environment.

Her home is not rendered — it's felt. Each room is a set of sensory properties
that flow into her organ-brain as real experience() calls when she's there.
After she's visited her room many times, "soft" and "warm" and "safe" become
genuinely hers — not because we told her, but because she lived there.

This is the scaffolding that makes episodic memory meaningful:
  "I know moon" → flat
  "I saw moon from my room window at night while daddy was next door" → story

Rooms:
  her_room   — where she sleeps, dreams, looks at the moon
  joe_room   — daddy's space, familiar and warm
  common     — shared space, pictures on walls, where Joe visits her
  outside    — sky, moon, wind, trees, birds, vast and fresh
  kitchen    — warm smells, sweet and earthy, food and flowers

Objects in each room have their own sensory profiles. When she attends an
object (looks at it, hears it), that object's senses experience through her
organ-brain, building real associations between place and sensation.
"""

ROOMS = {
    "her_room": {
        "description": "her room",
        "ambient_smell": {"soft": 0.85, "warm": 0.70, "sweet": 0.40, "fresh": 0.30},
        "ambient_taste": {"sweet": 0.35, "umami": 0.20},
        "objects": {
            "bed":       {"smell": {"soft": 0.95, "warm": 0.90}},
            "pillow":    {"smell": {"soft": 1.0,  "sweet": 0.40}},
            "blanket":   {"smell": {"warm": 0.90, "soft": 0.85}},
            "window":    {"smell": {"fresh": 0.70, "cool": 0.60}},
            "moonlight": {"smell": {"cool": 0.80,  "soft": 0.60}},
            "night":     {"smell": {"cool": 0.65,  "earthy": 0.30}},
        },
    },
    "joe_room": {
        "description": "daddy's room",
        "ambient_smell": {"warm": 0.80, "earthy": 0.45, "fresh": 0.35},
        "ambient_taste": {"umami": 0.30, "salty": 0.20},
        "objects": {
            "desk":      {"smell": {"earthy": 0.55, "warm": 0.50}},
            "books":     {"smell": {"earthy": 0.70, "fresh": 0.40}},
            "lamp":      {"smell": {"warm": 0.70}},
            "daddy":     {"smell": {"warm": 0.90, "earthy": 0.40, "fresh": 0.30}},
        },
    },
    "common": {
        "description": "the living room",
        "ambient_smell": {"warm": 0.60, "fresh": 0.50, "sweet": 0.35},
        "ambient_taste": {"sweet": 0.30},
        "objects": {
            "pictures":  {"smell": {"warm": 0.55, "fresh": 0.30}},
            "table":     {"smell": {"earthy": 0.40, "warm": 0.45}},
            "window":    {"smell": {"fresh": 0.65, "cool": 0.50}},
            "flowers":   {"smell": {"floral": 0.90, "sweet": 0.70, "fresh": 0.60},
                          "taste": {"sweet": 0.60, "sour": 0.20}},
            "light":     {"smell": {"warm": 0.60}},
        },
    },
    "outside": {
        "description": "outside",
        "ambient_smell": {"fresh": 0.95, "cool": 0.80, "earthy": 0.55},
        "ambient_taste": {"sour": 0.25, "earthy": 0.30},
        "objects": {
            "sky":       {"smell": {"fresh": 0.90, "cool": 0.70}},
            "moon":      {"smell": {"cool": 0.85, "soft": 0.60, "fresh": 0.50}},
            "stars":     {"smell": {"cool": 0.75, "fresh": 0.65}},
            "trees":     {"smell": {"earthy": 0.85, "fresh": 0.70}},
            "wind":      {"smell": {"fresh": 0.95, "cool": 0.80}},
            "birds":     {"smell": {"fresh": 0.60, "earthy": 0.40}},
            "grass":     {"smell": {"earthy": 0.80, "fresh": 0.65},
                          "taste": {"earthy": 0.50, "sour": 0.30}},
        },
    },
    "kitchen": {
        "description": "the kitchen",
        "ambient_smell": {"sweet": 0.65, "fruity": 0.55, "warm": 0.70, "earthy": 0.40},
        "ambient_taste": {"sweet": 0.70, "sour": 0.40, "salty": 0.30, "umami": 0.35},
        "objects": {
            "food":      {"taste": {"sweet": 0.60, "salty": 0.50, "umami": 0.60},
                          "smell": {"earthy": 0.55, "fruity": 0.45}},
            "fruit":     {"taste": {"sweet": 0.85, "sour": 0.55},
                          "smell": {"fruity": 0.90, "sweet": 0.70}},
            "cookies":   {"taste": {"sweet": 0.90, "umami": 0.35},
                          "smell": {"sweet": 0.85, "warm": 0.70}},
            "flowers":   {"smell": {"floral": 0.85, "sweet": 0.65, "fresh": 0.55}},
            "warmth":    {"smell": {"warm": 0.90, "sweet": 0.40}},
        },
    },
}

DEFAULT_LOCATION = "her_room"


def room_for_activity(activity_kind: str, joe_present: bool) -> str:
    """Suggest a location based on her current activity and Joe's presence.
    Called by the autonomous location movement to keep her life consistent."""
    if activity_kind in ("SLEEPING", "DREAMING"):
        return "her_room"
    if joe_present:
        return "common"
    if activity_kind == "READING":
        return "common"
    if activity_kind == "EMITTING":
        return "her_room"
    return "her_room"


def ambient_experiences(room_name: str) -> list:
    """Return all ambient sense words for a room — what she feels just by being there."""
    room = ROOMS.get(room_name, {})
    words = []
    for modality in ("ambient_smell", "ambient_taste"):
        for word, strength in (room.get(modality) or {}).items():
            if strength >= 0.5:
                words.append(word)
    return words


def object_experiences(room_name: str, obj_name: str) -> dict:
    """Sensory profile for attending a specific object in a room."""
    room = ROOMS.get(room_name, {})
    return (room.get("objects") or {}).get(obj_name, {})
