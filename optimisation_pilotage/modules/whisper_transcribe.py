import tempfile, uuid
from pathlib import Path
from typing import Optional
from pydub import AudioSegment

def ensure_wav(input_path: str) -> str:
    ext = Path(input_path).suffix.lower()
    if ext in [".wav"]:
        return input_path
    audio = AudioSegment.from_file(input_path)
    tmp_wav = Path(tempfile.gettempdir()) / f"whisper_{uuid.uuid4().hex}.wav"
    audio.set_frame_rate(16000).set_channels(1).export(tmp_wav, format="wav")
    return str(tmp_wav)

def transcribe_offline_faster(input_path: str, language: Optional[str] = "fr", model_size: str = "medium"):
    from faster_whisper import WhisperModel
    wav = ensure_wav(input_path)
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments, info = model.transcribe(wav, language=language, vad_filter=True)
    text = "".join([s.text for s in segments])
    return text.strip()
