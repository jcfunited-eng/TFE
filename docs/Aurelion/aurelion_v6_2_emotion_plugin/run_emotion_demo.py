
# Simple REPL demo for the Emotional Cognition plugin
from emotion_layer import EmotionEngine
from modules.state_manager import SystemToneTarget

emo = EmotionEngine()

print("Aurelion v6.2 Emotion Demo — type text; 'quit' to exit")
while True:
    try:
        txt = input("You: ")
    except EOFError:
        break
    if txt.strip().lower() in {"quit","exit"}:
        break
    state = emo.update_from_text(txt)
    target = SystemToneTarget().to_tone()
    tone = emo.blend_with_system_tone(target)
    meta = emo.meta_summary(intent="respond", tone=tone)
    print(f"  ↳ state: v={state.valence:.2f}, a={state.arousal:.2f}, tags={state.tags}, conf={state.confidence:.2f}")
    print(f"  ↳ tone:  {tone.label} (v={tone.valence:.2f}, a={tone.arousal:.2f})")
    print(f"  ↳ meta:  {meta['explain']}")
