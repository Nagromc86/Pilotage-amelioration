from pathlib import Path
from faster_whisper import WhisperModel
import soundfile as sf

class Transcriber:
    def __init__(self, models_dir: Path, size: str='small'):
        mp = models_dir / f'faster-whisper-{size}'
        if not mp.exists() or not any(mp.iterdir()):
            raise RuntimeError(f'Modèle {size} introuvable. Téléchargez-le dans Paramètres.')
        # int8 = léger CPU; tu peux passer en int8_float32 si souci de qualité
        self.model = WhisperModel(str(mp), device='cpu', compute_type='int8')

    def transcribe_wav(self, wav_path: Path) -> str:
        # ignore proprement les fichiers vides
        try:
            inf = sf.info(str(wav_path))
            if inf.frames == 0 or inf.duration == 0:
                return ""
        except Exception:
            pass

        # fixer la langue à 'fr' évite une détection sur silence
        segments, info = self.model.transcribe(
            str(wav_path),
            beam_size=1,
            vad_filter=True,
            language='fr'
        )
        return " ".join(seg.text.strip() for seg in segments if getattr(seg, 'text', '').strip())
