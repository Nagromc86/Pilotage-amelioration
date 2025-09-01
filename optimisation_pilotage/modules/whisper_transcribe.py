from typing import Optional
from pathlib import Path

def transcribe_offline_faster(input_path: str, language: Optional[str] = "fr", model_size: str = "medium"):
    from faster_whisper import WhisperModel
    p = Path(input_path)
    if p.suffix.lower() != ".wav":
        raise RuntimeError("Import de fichiers WAV uniquement. Convertissez votre audio en .wav (16kHz mono) avant import.")
    from .utils import MODELS_DIR
    local_small = MODELS_DIR / "faster-whisper-small"
    local_medium = MODELS_DIR / "faster-whisper-medium"
    model_path = None
    if model_size == "small" and local_small.exists():
        model_path = str(local_small)
    elif model_size == "medium" and local_medium.exists():
        model_path = str(local_medium)
    else:
        model_path = model_size
    model = WhisperModel(model_path, device="auto", compute_type="auto")
    segments, info = model.transcribe(str(p), language=language, vad_filter=True)
    text = "".join([s.text for s in segments])
    return text.strip()
