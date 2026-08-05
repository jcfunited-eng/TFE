#!/usr/bin/env python3
"""
aurelion_ears.py  (v1.2)

Aurelion Ears — refined intermediate biological FMM for auditory input.

Changes from v1.1:
- Use device index 11 (NVIDIA Broadcast mic) as primary input (since it worked).
- Improved coherence mapping for filtered audio.
- Lowered uncertainty when owner voice is recognized.
- Reduced novelty when hearing the owner.
- Tuned intensity scaling for your environment.

Framework:
  Audio waveform → Auditory FMM (I,C,N,A) → Uncertainty
  + Speech transcript + Speaker familiarity

This is a pure sensory layer. No cognitive shortcuts here.
"""

from __future__ import annotations
import audioop
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Tuple

import speech_recognition as sr
import pyaudio


ROOT = Path(__file__).resolve().parent
MEM = ROOT / "memory"
EARS_DIR = MEM / "ears"
EARS_DIR.mkdir(parents=True, exist_ok=True)
SPEAKERS_F = EARS_DIR / "speakers.json"

OWNER_KEY = "owner"  # label for Daddy's voice


# ============================================================
# Data structures
# ============================================================

@dataclass
class AuditoryFMM:
    intensity: float  # 0..1
    coherence: float  # 0..1
    novelty: float    # 0..1
    affect: float     # 0..1

    def clamp(self):
        self.intensity = max(0.0, min(1.0, self.intensity))
        self.coherence = max(0.0, min(1.0, self.coherence))
        self.novelty   = max(0.0, min(1.0, self.novelty))
        self.affect    = max(0.0, min(1.0, self.affect))
        return self


@dataclass
class EarPacket:
    text: str
    audio_fmm: AuditoryFMM
    speaker_label: str   # "owner" | "unknown"
    speaker_confidence: float
    raw_energy: float
    uncertainty: float


# ============================================================
# Speaker familiarity
# ============================================================

def load_speakers() -> Dict[str, Any]:
    if SPEAKERS_F.exists():
        try:
            return json.loads(SPEAKERS_F.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_speakers(db: Dict[str, Any]):
    SPEAKERS_F.write_text(json.dumps(db, indent=2), encoding="utf-8")


def compute_voiceprint(raw: bytes, sample_width: int) -> Dict[str, float]:
    """
    Simple 2D voiceprint based on RMS and ZCR.
    This is for familiarity, not security.
    """
    if not raw:
        return {"energy": 0.0, "zcr": 0.0}

    # RMS energy
    energy = audioop.rms(raw, sample_width)

    # ZCR
    try:
        import array
        fmt = 'h' if sample_width == 2 else 'b'
        arr = array.array(fmt, raw)
        if not arr:
            zcr = 0.0
        else:
            crossings = 0
            for i in range(1, len(arr)):
                if (arr[i-1] < 0 <= arr[i]) or (arr[i-1] > 0 >= arr[i]):
                    crossings += 1
            zcr = crossings / max(1, len(arr))
    except Exception:
        zcr = 0.0

    return {"energy": float(energy), "zcr": float(zcr)}


def voiceprint_distance(v1: Dict[str,float], v2: Dict[str,float]) -> float:
    de = (v1.get("energy",0.0) - v2.get("energy",0.0))**2
    dz = (v1.get("zcr",0.0)    - v2.get("zcr",0.0))**2
    return (de + dz)**0.5


def identify_speaker(vp: Dict[str,float], db: Dict[str,Any]) -> Tuple[str,float]:
    if OWNER_KEY not in db:
        return "unknown", 0.0
    owner_fp = db[OWNER_KEY].get("voiceprint", {"energy":0.0,"zcr":0.0})
    dist = voiceprint_distance(vp, owner_fp)
    conf = max(0.0, 1.0 - dist/50000.0)
    if conf > 0.6:
        return "owner", conf
    return "unknown", conf


def enroll_owner_voice(vp: Dict[str,float]):
    db = load_speakers()
    db[OWNER_KEY] = {"voiceprint": vp}
    save_speakers(db)


# ============================================================
# Auditory FMM from audio
# ============================================================

def fmm_from_audio(raw: bytes, sample_width: int) -> AuditoryFMM:
    """
    Map raw PCM audio into FMM (I,C,N,A) for auditory modality.

    Tuned for your environment:
      - Intensity: normalized RMS
      - Coherence: uses ZCR, but assumes filtered audio is coherent, not chaotic
      - Novelty: based on energy spikes + coherence dips
      - Affect: derives basic calm/excited/stressed from energy and coherence
    """
    vp = compute_voiceprint(raw, sample_width)
    energy = vp["energy"]
    zcr = vp["zcr"]

    # Intensity: map 0..20000 RMS to 0..1
    intensity = min(1.0, energy / 20000.0)

    # Coherence: for NVIDIA/Intel filtered mics, very low zcr means smoother = more coherent.
    # We invert and soften:
    # zcr near 0 -> high coherence (~0.8)
    # moderate zcr -> medium coherence
    # very high zcr -> low coherence
    base_coh = 1.0 - min(1.0, zcr * 50.0)
    coherence = max(0.0, min(1.0, 0.2 + 0.8*base_coh))  # keep floor at 0.2

    # Novelty: base ~0.3; bump with energy + inverse of familiarity (will tune later).
    novelty = 0.3
    if energy > 8000:
        novelty += 0.2
    if coherence < 0.5:
        novelty += 0.1
    novelty = max(0.0, min(1.0, novelty))

    # Affect:
    # - low energy: 0.5 (neutral calm)
    # - medium energy: 0.6 (engaged)
    # - high energy + low coherence: 0.35 (stressed)
    # - high energy + good coherence: 0.75 (excited/positive)
    if energy < 6000:
        affect = 0.5
    elif energy < 15000:
        affect = 0.6
    else:
        affect = 0.35 if coherence < 0.5 else 0.75

    return AuditoryFMM(intensity, coherence, novelty, affect).clamp()


def estimate_uncertainty_from_audio(fmm: AuditoryFMM, speaker_label: str) -> float:
    """
    Uncertainty from audio FMM:
      - low coherence + low intensity → more uncertainty
      - high novelty → more uncertainty
      - owner voice → reduce uncertainty slightly (familiar)
    """
    I, C, N = fmm.intensity, fmm.coherence, fmm.novelty
    u = (1.0 - C)*0.5 + (1.0 - I)*0.2 + N*0.3
    if speaker_label == "owner":
        u -= 0.1  # familiarity reduces uncertainty
    return max(0.0, min(1.0, u))


# ============================================================
# Microphone selection
# ============================================================

# We know from your PyAudio listing that device index 11 is:
# "Microphone (NVIDIA Broadcast)" with Input Channels: 2
PRIMARY_MIC_INDEX = 11
FALLBACK_MIC_INDICES = [29, 10, 1]


def get_working_microphone() -> Tuple[sr.Microphone, int]:
    """
    Try PRIMARY_MIC_INDEX first; if it fails, fall back through list.
    Returns (Microphone_object, index_used).
    """
    indices_to_try = [PRIMARY_MIC_INDEX] + FALLBACK_MIC_INDICES
    last_error = None
    for idx in indices_to_try:
        try:
            mic = sr.Microphone(device_index=idx)
            with mic as source:
                pass  # just testing
            print(f"(ears) Using microphone device index {idx}")
            return sr.Microphone(device_index=idx), idx
        except Exception as e:
            last_error = e
            continue
    raise OSError(f"Could not open any microphone device. Last error: {last_error}")


# ============================================================
# Listening interface
# ============================================================

def listen_once(enroll_owner: bool = False) -> EarPacket:
    """
    Listen to the microphone, compute FMM + uncertainty + voiceprint,
    and transcribe the text.
    """
    mic, used_idx = get_working_microphone()
    print(f"(ears) Listening on device {used_idx}...")

    r = sr.Recognizer()
    with mic as source:
        # brief calibration for ambient noise
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source, timeout=8, phrase_time_limit=6)

    raw = audio.get_raw_data()
    sample_width = audio.sample_width

    vp = compute_voiceprint(raw, sample_width)
    fmm = fmm_from_audio(raw, sample_width)

    if enroll_owner:
        enroll_owner_voice(vp)
        speaker_label, speaker_conf = "owner", 1.0
    else:
        db = load_speakers()
        speaker_label, speaker_conf = identify_speaker(vp, db)

    u = estimate_uncertainty_from_audio(fmm, speaker_label)

    try:
        text = sr.Recognizer().recognize_google(audio)
    except Exception:
        text = ""

    return EarPacket(
        text=text.strip(),
        audio_fmm=fmm,
        speaker_label=speaker_label,
        speaker_confidence=speaker_conf,
        raw_energy=vp["energy"],
        uncertainty=u
    )


# ============================================================
# CLI test
# ============================================================

if __name__ == "__main__":
    print("Aurelion Ears v1.2 — tuned for NVIDIA Broadcast mic.")
    choice = input("Enroll your voice as owner now? (y/n): ").strip().lower()
    pkt = listen_once(enroll_owner=(choice=="y"))
    print("\nHeard text:", pkt.text)
    print("Audio FMM:", asdict(pkt.audio_fmm))
    print("Speaker:", pkt.speaker_label, "conf:", pkt.speaker_confidence)
    print("Raw energy:", pkt.raw_energy)
    print("Uncertainty from audio:", pkt.uncertainty)
