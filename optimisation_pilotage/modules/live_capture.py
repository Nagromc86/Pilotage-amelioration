import threading, wave
from dataclasses import dataclass
from typing import Optional, Callable, List
import numpy as np
import soundcard as sc
from faster_whisper import WhisperModel
@dataclass
class LiveConfig:
    samplerate: int = 16000
    chunk_seconds: int = 15
    language: Optional[str] = "fr"
    model_size: str = "small"
    record_wav: bool = False
    wav_path: Optional[str] = None
@dataclass
class LiveState:
    is_running: bool = False
    transcript: str = ""
    last_error: str = ""
    appended_segments: int = 0
    wav_path: Optional[str] = None
class LiveTranscriber:
    def __init__(self, cfg: LiveConfig, on_update: Optional[Callable[[LiveState], None]] = None):
        self.cfg = cfg
        self.on_update = on_update
        self.state = LiveState()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
    def start(self):
        if self.state.is_running: return
        self._stop.clear()
        self.state = LiveState(is_running=True)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self.state.is_running = False
        if self.on_update: self.on_update(self.state)
    def _run(self):
        wav_writer = None
        try:
            model = WhisperModel(self.cfg.model_size, device="auto", compute_type="auto")
            mic = sc.default_microphone()
            spk = sc.default_speaker()
            mic_rec = mic.recorder(samplerate=self.cfg.samplerate)
            spk_rec = spk.recorder(samplerate=self.cfg.samplerate)
            if self.cfg.record_wav and self.cfg.wav_path:
                wav_writer = wave.open(self.cfg.wav_path, "wb")
                wav_writer.setnchannels(1)
                wav_writer.setsampwidth(2)
                wav_writer.setframerate(self.cfg.samplerate)
                self.state.wav_path = self.cfg.wav_path
            mic_rec.__enter__(); spk_rec.__enter__()
            frames_per_chunk = int(self.cfg.samplerate * self.cfg.chunk_seconds)
            buf: List[np.ndarray] = []
            collected = 0
            while not self._stop.is_set():
                frame_len = min(self.cfg.samplerate, frames_per_chunk - collected)
                a = mic_rec.record(numframes=frame_len)
                b = spk_rec.record(numframes=frame_len)
                rec = (a + b) / 2.0
                if rec.ndim > 1:
                    rec = rec.mean(axis=1)
                if wav_writer is not None:
                    pcm16 = np.clip(rec, -1.0, 1.0)
                    pcm16 = (pcm16 * 32767.0).astype(np.int16).tobytes()
                    wav_writer.writeframes(pcm16)
                buf.append(rec.astype(np.float32))
                collected += len(rec)
                if collected >= frames_per_chunk:
                    chunk = np.concatenate(buf, axis=0)
                    buf.clear(); collected = 0
                    try:
                        segments, info = model.transcribe(chunk, language=self.cfg.language, vad_filter=True)
                        text = "".join(s.text for s in segments).strip()
                        if text:
                            self.state.transcript = (self.state.transcript + " " + text).strip()
                            self.state.appended_segments += 1
                    except Exception as e:
                        self.state.last_error = f"Erreur transcription: {e}"
                    if self.on_update: self.on_update(self.state)
            mic_rec.__exit__(None, None, None); spk_rec.__exit__(None, None, None)
        except Exception as e:
            self.state.last_error = str(e)
        finally:
            if wav_writer is not None:
                try: wav_writer.close()
                except Exception: pass
            self.state.is_running = False
            if self.on_update: self.on_update(self.state)
