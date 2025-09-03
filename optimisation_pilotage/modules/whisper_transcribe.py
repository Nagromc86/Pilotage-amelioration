from pathlib import Path
from faster_whisper import WhisperModel
class Transcriber:
    def __init__(self, models_dir: Path, size: str='small'):
        mp = models_dir / f'faster-whisper-{size}'
        if not mp.exists() or not any(mp.iterdir()): raise RuntimeError(f'Modèle {size} introuvable. Téléchargez-le dans Paramètres.')
        self.model = WhisperModel(str(mp), device='cpu', compute_type='int8')
    def transcribe_wav(self, wav_path: Path) -> str:
        segments, info = self.model.transcribe(str(wav_path), beam_size=1, vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments if seg.text).strip()