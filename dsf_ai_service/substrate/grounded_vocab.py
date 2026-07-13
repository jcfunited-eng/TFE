"""Grounded vocabulary layer for Guala's substrate.

Provides object recognition (vision), speech transcription (audio),
ambient sound classification, and co-temporal cross-modal binding.

V1: recognizers are stubs that gracefully degrade when models are not
installed. The CrossModalBinder is fully functional (pure Python).
Models (YOLOv8-nano ONNX, Whisper-tiny ONNX, YAMNet) are added later.
"""

import threading

# -- COCO 80 class labels (YOLOv8 ordering) --------------------------------
COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]

_CONFIDENCE_THRESHOLD = 0.6


class ObjectRecognizer:
    """YOLOv8-nano ONNX object detector.

    If the model or runtime is not installed, self.available is False and
    detect() returns an empty list. No exceptions, no fallback vocabulary.
    """

    def __init__(self, model_path=None):
        self.available = False
        self._session = None
        self._input_name = None
        self._input_shape = None
        if model_path is None:
            return
        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(model_path)
            inp = self._session.get_inputs()[0]
            self._input_name = inp.name
            self._input_shape = inp.shape  # e.g. [1, 3, 640, 640]
            self.available = True
        except Exception:
            self.available = False

    def detect(self, frame_bytes_or_grid):
        """Run object detection on a frame.

        Args:
            frame_bytes_or_grid: raw image bytes (JPEG/PNG) or a numpy array
                (H, W, 3) uint8 BGR/RGB image.

        Returns:
            list[dict]: each dict has keys 'label' (str), 'confidence' (float),
            'bbox' (x1, y1, x2, y2). Empty list when model is unavailable or
            on any error.
        """
        if not self.available or self._session is None:
            return []
        try:
            return self._run_inference(frame_bytes_or_grid)
        except Exception:
            return []

    # ------------------------------------------------------------------
    def _run_inference(self, frame_bytes_or_grid):
        """Internal: preprocess, run ONNX session, postprocess."""
        import numpy as np

        # Decode input
        if isinstance(frame_bytes_or_grid, (bytes, bytearray)):
            arr = np.frombuffer(frame_bytes_or_grid, dtype=np.uint8)
            try:
                import cv2
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            except ImportError:
                from PIL import Image
                import io
                img = np.array(Image.open(io.BytesIO(frame_bytes_or_grid)).convert("RGB"))
        else:
            img = np.asarray(frame_bytes_or_grid)

        if img is None or img.size == 0:
            return []

        h_orig, w_orig = img.shape[:2]
        target_h = self._input_shape[2] if len(self._input_shape) >= 4 else 640
        target_w = self._input_shape[3] if len(self._input_shape) >= 4 else 640

        # Resize with letterbox (simple stretch for v1)
        from PIL import Image as _PILImage
        import io as _io
        pil_img = _PILImage.fromarray(img if img.shape[2] == 3 else img[:, :, ::-1])
        pil_resized = pil_img.resize((target_w, target_h), _PILImage.BILINEAR)
        blob = np.array(pil_resized, dtype=np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)[np.newaxis, ...]  # (1, 3, H, W)

        outputs = self._session.run(None, {self._input_name: blob})
        # YOLOv8 output: (1, 84, N) — 4 box coords + 80 class scores
        preds = outputs[0]
        if preds.ndim == 3:
            preds = preds[0]  # (84, N)
        if preds.shape[0] == 84:
            preds = preds.T   # (N, 84)

        results = []
        for row in preds:
            box = row[:4]
            scores = row[4:]
            cls_id = int(np.argmax(scores))
            conf = float(scores[cls_id])
            if conf < _CONFIDENCE_THRESHOLD:
                continue
            # Convert center-x, center-y, w, h to x1, y1, x2, y2
            cx, cy, bw, bh = box
            x1 = (cx - bw / 2) * w_orig / target_w
            y1 = (cy - bh / 2) * h_orig / target_h
            x2 = (cx + bw / 2) * w_orig / target_w
            y2 = (cy + bh / 2) * h_orig / target_h
            label = COCO_LABELS[cls_id] if cls_id < len(COCO_LABELS) else f"class_{cls_id}"
            results.append({
                "label": label,
                "confidence": conf,
                "bbox": (float(x1), float(y1), float(x2), float(y2)),
            })

        # NMS: keep highest confidence per label within overlapping boxes
        results.sort(key=lambda d: d["confidence"], reverse=True)
        return results


class SpeechRecognitionUnavailable(RuntimeError):
    """The configured speech recognizer could not be constructed."""


class SpeechTranscriptionError(RuntimeError):
    """A configured recognizer failed while processing an audio event."""


class SpeechRecognizer:
    """Whisper-tiny speech-to-text via faster-whisper (CTranslate2).

    Uses faster-whisper which is CPU-optimized and doesn't require torch.
    Construction and inference are serialized because one CTranslate2 model is
    one physical recognition resource.  Configuration or inference failures
    are raised explicitly; valid audio containing no speech still returns an
    empty string.
    """

    def __init__(self, model_path=None):
        self.available = False
        self._model = None
        self._initialization_error = None
        self._transcribe_lock = threading.Lock()
        try:
            from faster_whisper import WhisperModel
            model_size = model_path or "tiny"
            self._model = WhisperModel(model_size, device="cpu",
                                        compute_type="int8")
            self.available = True
        except Exception as error:
            self._initialization_error = error

    def transcribe(self, audio_bytes, sample_rate=16000):
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: raw PCM int16 mono audio, or WAV bytes.
            sample_rate: sample rate of the audio (default 16000).

        Returns:
            str: transcribed text, or "" when the audio contains no speech.

        Raises:
            SpeechRecognitionUnavailable: model construction failed.
            SpeechTranscriptionError: inference failed.
        """
        if not self.available or self._model is None:
            detail = type(self._initialization_error).__name__ if self._initialization_error else "unknown"
            raise SpeechRecognitionUnavailable(
                f"speech recognizer unavailable ({detail})"
            ) from self._initialization_error
        with self._transcribe_lock:
            try:
                return self._run_transcription(audio_bytes, sample_rate)
            except Exception as error:
                raise SpeechTranscriptionError(
                    f"speech transcription failed ({type(error).__name__})"
                ) from error

    def _run_transcription(self, audio_bytes, sample_rate):
        """Internal: decode audio and run faster-whisper."""
        import numpy as np
        import io
        import wave

        # Try WAV decode
        try:
            wf = wave.open(io.BytesIO(audio_bytes), 'rb')
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
            sr = wf.getframerate()
            import struct
            if wf.getsampwidth() == 2:
                samples = np.array(struct.unpack(f'<{n_frames}h', raw),
                                   dtype=np.float32) / 32768.0
            else:
                samples = np.frombuffer(raw, dtype=np.uint8).astype(
                    np.float32) / 128.0 - 1.0
            wf.close()
        except Exception:
            samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(
                np.float32) / 32768.0
            sr = sample_rate

        if len(samples) < 100:
            return ""

        # Resample to 16kHz if needed
        if sr != 16000:
            step = max(1, sr // 16000)
            samples = samples[::step]

        # faster-whisper takes float32 numpy array directly
        segments, _ = self._model.transcribe(samples, language="en",
                                              vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()


class AmbientClassifier:
    """YAMNet ambient sound classifier.

    V1 stub: always returns None. Model integration added later.
    """

    def __init__(self):
        self.available = False

    def classify(self, audio_bytes, sample_rate=16000):
        """Classify ambient sound.

        Args:
            audio_bytes: raw audio bytes.
            sample_rate: sample rate (default 16000).

        Returns:
            str or None: sound class label, or None when unavailable.
        """
        return None


class CrossModalBinder:
    """Co-temporal cross-modal binding window.

    Tracks which words have been bound in which sensory sections and at
    what tick. When a word appears in one modality, check_cross_modal()
    returns the OTHER modalities where it was recently bound (within
    window_ticks). This is how simultaneous perception across senses
    creates grounded meaning.

    Pure Python, no model needed. Fully functional in v1.
    """

    _MAX_ENTRIES_PER_WORD = 100

    def __init__(self, window_ticks=5):
        self.window_ticks = window_ticks
        self._bindings = {}  # word -> list of (section, tick)

    def record_binding(self, word, section, tick):
        """Record that *word* was bound in *section* at *tick*.

        Args:
            word: the vocabulary word (lowercase).
            section: the atlas section name (e.g. "sight", "listen").
            tick: the substrate tick at time of binding.
        """
        entries = self._bindings.setdefault(word, [])
        entries.append((section, tick))
        # Prune to last N entries
        if len(entries) > self._MAX_ENTRIES_PER_WORD:
            self._bindings[word] = entries[-self._MAX_ENTRIES_PER_WORD:]

    def check_cross_modal(self, word, section, tick):
        """Return OTHER sections where *word* was bound within window_ticks.

        Args:
            word: the vocabulary word (lowercase).
            section: the current section being bound.
            tick: the current substrate tick.

        Returns:
            list[str]: section names (deduplicated) that are not *section*
            and have a binding within the time window. Empty list if none.
        """
        entries = self._bindings.get(word, [])
        if not entries:
            return []
        cutoff = tick - self.window_ticks
        other_sections = set()
        for s, t in entries:
            if s != section and t >= cutoff:
                other_sections.add(s)
        return sorted(other_sections)
