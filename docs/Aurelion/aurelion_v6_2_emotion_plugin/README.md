
# Aurelion v6.2 — Emotional Cognition Layer (Option 2: Plugin for v6.1)

This add‑on drops into your v6.1 tree and exposes an EmotionEngine that:
- infers affect from text (valence ∈ [−1,1], arousal ∈ [0,1])
- decays/smooths state between turns
- blends user tone with system target tone
- returns a meta summary object for your Self‑Explaining monitor

## File Map
- `emotion_layer.py` — main engine
- `modules/affective_mapper.py` — lexical/emoji→affect
- `modules/emotion_reflector.py` — mirroring & stabilization
- `modules/state_manager.py` — system tone target (helper)
- `schemas/emotion_schema.json` — state schema
- `schemas/meta_schema.json` — meta extension
- `config_emotion.json` — tunables

## Quick Integration with v6.1

In your `aurelion_core_v6_1_self_explaining.py`:

```python
# 1) import
from emotion_layer import EmotionEngine
from modules.state_manager import SystemToneTarget

# 2) initialize once (after your core init)
emo = EmotionEngine(config_path="config_emotion.json")

# 3) each user turn, update from text
emo_state = emo.update_from_text(user_text)

# 4) before generating your response, blend with your desired tone target
system_target = SystemToneTarget(valence=0.25, arousal=0.3, label="supportive").to_tone()
blended_tone = emo.blend_with_system_tone(system_target)

# 5) attach meta for your Self‑Explaining output (intent is your core's decision)
meta = emo.meta_summary(intent=current_intent, tone=blended_tone)
# -> include `meta` in your existing explanation block
```

## Minimal Demo (without touching v6.1)
Run `python run_emotion_demo.py` and type text to see valence/arousal + suggested tone.

## Tuning
- `blend.mirror_strength` ↑ to mirror user more; ↓ to stay steady
- `decay.half_life_turns` ↑ for slower mood decay
- `safety.max_shift_per_turn` caps abrupt tone jumps
- Add terms/emoji to `AffectiveMapper.lexicon` for domain tone

## Notes
- No network, no external deps.
- Deterministic, fast, and sandbox‑friendly.
- Designed so you can later “promote” it into a v6.2 core rewrite.
