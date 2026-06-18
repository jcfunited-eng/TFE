"""Integration layer: wires grounded vocabulary into the Guala substrate.

Called from process_sight_frame / process_sound_frame after raw krimelack
binding. Runs object detection or speech transcription, then binds
recognized words into the atlas with cross-modal linking.

V1: recognizers are stubs (return empty). CrossModalBinder is live.
"""

import os

from dsf_ai_service.substrate.grounded_vocab import (
    ObjectRecognizer,
    SpeechRecognizer,
    AmbientClassifier,
    CrossModalBinder,
)

# ---------------------------------------------------------------------------
# Model paths (set via env or default container paths)
# ---------------------------------------------------------------------------
YOLO_MODEL_PATH = os.environ.get(
    "YOLO_MODEL_PATH", "/app/models/yolov8n.onnx")
WHISPER_MODEL_PATH = os.environ.get(
    "WHISPER_MODEL_PATH", "/app/models/whisper-tiny")

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------
_object_recognizer = None
_speech_recognizer = None
_ambient_classifier = None
_cross_modal_binder = None


def get_object_recognizer():
    """Return the singleton ObjectRecognizer."""
    global _object_recognizer
    if _object_recognizer is None:
        path = YOLO_MODEL_PATH if os.path.exists(YOLO_MODEL_PATH) else None
        _object_recognizer = ObjectRecognizer(model_path=path)
    return _object_recognizer


def get_speech_recognizer():
    """Return the singleton SpeechRecognizer.
    faster-whisper downloads the tiny model on first use (~39MB)."""
    global _speech_recognizer
    if _speech_recognizer is None:
        _speech_recognizer = SpeechRecognizer(model_path="tiny")
    return _speech_recognizer


def get_ambient_classifier():
    """Return the singleton AmbientClassifier."""
    global _ambient_classifier
    if _ambient_classifier is None:
        _ambient_classifier = AmbientClassifier()
    return _ambient_classifier


def get_cross_modal_binder():
    """Return the singleton CrossModalBinder (window=5 ticks)."""
    global _cross_modal_binder
    if _cross_modal_binder is None:
        _cross_modal_binder = CrossModalBinder(window_ticks=5)
    return _cross_modal_binder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chi_for_word(word):
    """Compute chi (winding number) for a word via LanguageKrimelack."""
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
    krim = LanguageKrimelack()
    krim.transduce(word)
    return krim.winding


def _deterministic_motif_id(name):
    """Deterministic motif ID from a name string."""
    import hashlib
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 10000


# ---------------------------------------------------------------------------
# Sight integration
# ---------------------------------------------------------------------------

def process_sight_with_recognition(guala, grid, source="camera_stream"):
    """Run object detection on a sight frame and bind recognized objects.

    Called after raw krimelack binding in process_sight_frame. Each detected
    object whose label is in guala.vocab gets recorded in the atlas with its
    krimelack chi value and a cross-modal check.

    Args:
        guala: the GualaLoom engine instance.
        grid: the image frame (numpy array or bytes).
        source: source identifier for sensory refs.

    Returns:
        list[dict]: bindings created, each with 'word', 'chi', 'confidence'.
    """
    recognizer = get_object_recognizer()
    if not recognizer.available:
        return []

    detections = recognizer.detect(grid)
    bindings = []

    for det in detections:
        label = det["label"].lower()
        if label not in guala.vocab:
            continue

        chi = _chi_for_word(label)
        motif_id = _deterministic_motif_id(f"sight_{label}")

        guala.atlas.record(
            "sight", motif_id, chi, guala.tick,
            salience=det["confidence"],
            sensory_refs=[f"visual_recognition:{label}"],
            source="sight",
            **guala._affect_kwargs(),
        )

        bindings.append({
            "word": label,
            "chi": chi,
            "confidence": det["confidence"],
        })

        # Cross-modal check
        binder = get_cross_modal_binder()
        cross = binder.check_cross_modal(label, "sight", guala.tick)
        if cross:
            guala._log_substrate_event(
                "cross_modal_link",
                word=label,
                modalities=["sight"] + cross,
            )
        binder.record_binding(label, "sight", guala.tick)

    if bindings:
        guala._log_substrate_event(
            "visual_recognition",
            n_objects=len(bindings),
            objects=[b["word"] for b in bindings],
        )

    return bindings


# ---------------------------------------------------------------------------
# Sound integration
# ---------------------------------------------------------------------------

def process_sound_with_recognition(guala, audio_bytes, source="ambient"):
    """Run speech transcription or ambient classification on audio.

    Called after raw cochlear binding in process_sound_frame. For voice
    input, each transcribed word in guala.vocab gets recorded in the atlas
    with cross-modal linking.

    Args:
        guala: the GualaLoom engine instance.
        audio_bytes: raw audio data (WAV or PCM).
        source: "joe_voice" for speech transcription, anything else for
                ambient classification.

    Returns:
        list[dict]: bindings created (voice), or empty list (ambient stub).
    """
    bindings = []

    if source == "joe_voice":
        recognizer = get_speech_recognizer()
        if not recognizer.available:
            return []

        text = recognizer.transcribe(audio_bytes)
        if not text:
            return []

        for raw_word in text.lower().split():
            word = raw_word.strip(".,!?;:'\"")
            if not word or word not in guala.vocab:
                continue

            chi = _chi_for_word(word)
            motif_id = _deterministic_motif_id(f"listen_{word}")

            guala.atlas.record(
                "listen", motif_id, chi, guala.tick,
                salience=0.8,
                sensory_refs=[f"speech_heard:{word}"],
                source="joe_voice",
                **guala._affect_kwargs(),
            )

            bindings.append({
                "word": word,
                "chi": chi,
                "confidence": 0.8,
            })

            # Cross-modal check
            binder = get_cross_modal_binder()
            cross = binder.check_cross_modal(word, "listen", guala.tick)
            if cross:
                guala._log_substrate_event(
                    "cross_modal_link",
                    word=word,
                    modalities=["listen"] + cross,
                )
            binder.record_binding(word, "listen", guala.tick)

        if bindings:
            guala._log_substrate_event(
                "speech_recognition",
                n_words=len(bindings),
                words=[b["word"] for b in bindings],
            )

    else:
        # Ambient classification (v1 stub)
        classifier = get_ambient_classifier()
        label = classifier.classify(audio_bytes)
        if label and label.lower() in guala.vocab:
            # Placeholder for ambient sound binding — model needed
            pass

    return bindings
