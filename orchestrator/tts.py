import os
import subprocess
import uuid

PIPER_MODEL_PATH = os.environ.get("PIPER_MODEL_PATH", "/app/models/es_ES-mls_10246-medium.onnx")
OUTPUT_DIR = "/tmp/tts"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def synthesize(text: str) -> str:
    """Genera un WAV con Piper y devuelve la ruta del fichero (8kHz mono, listo para el canal GSM)."""
    out_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.wav")
    subprocess.run(
        [
            "piper",
            "--model", PIPER_MODEL_PATH,
            "--output_file", out_path,
        ],
        input=text.encode("utf-8"),
        check=True,
    )
    return out_path
