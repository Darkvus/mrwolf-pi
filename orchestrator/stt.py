import os
from faster_whisper import WhisperModel

WHISPER_MODEL_PATH = os.environ.get("WHISPER_MODEL_PATH", "/app/models/ggml-small.bin")

_model = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        # "small" en CPU int8 es un buen equilibrio latencia/precisión en RPi4
        _model = WhisperModel("small", device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> str:
    model = get_model()
    segments, _ = model.transcribe(audio_path, language="es", beam_size=1)
    return " ".join(s.text.strip() for s in segments)
