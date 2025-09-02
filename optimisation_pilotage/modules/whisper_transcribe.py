from pathlib import Path
from faster_whisper import WhisperModel
from .utils import MODELS_DIR

def transcribe_file(wav_path: Path, model_size: str='small', device: str='cpu'):
    model = WhisperModel(model_size, device=device, compute_type='int8', download_root=str(MODELS_DIR))
    segments, info = model.transcribe(str(wav_path), vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))
    text='\n'.join([seg.text.strip() for seg in segments])
    return text, info
