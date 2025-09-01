import threading, queue, time
from pathlib import Path
import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

class LiveMixTranscriber:
    def __init__(self, model_dir: Path, model_size: str = "small", step_seconds: int = 15, on_text=None, on_state=None):
        self.model_dir = Path(model_dir)
        self.model_size = model_size
        self.step_seconds = step_seconds
        self.on_text = on_text
        self.on_state = on_state
        self._stop = threading.Event()
        self._th = None
        self._q = queue.Queue()
        self._model = None

    def start(self):
        if self._th and self._th.is_alive(): return
        self._stop.clear()
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def stop(self):
        self._stop.set()
        if self._th: self._th.join(timeout=2)

    def _run(self):
        if self.on_state: self.on_state("init")
        # load model
        if WhisperModel is None:
            if self.on_state: self.on_state("error: faster-whisper manquant")
            return
        repo = "faster-whisper-small" if self.model_size.lower().startswith("small") else "faster-whisper-medium"
        self._model = WhisperModel(str(self.model_dir/repo), compute_type="int8", cpu_threads=4)
        if self.on_state: self.on_state("ready")

        if sd is None:
            if self.on_state: self.on_state("error: sounddevice manquant")
            return

        # pick default microphone and loopback for speakers (WASAPI)
        try:
            hostapi = next((h for h in sd.query_hostapis() if "WASAPI" in h['name']), None)
            if hostapi is None:
                in_dev = sd.default.device[0]
                out_dev = sd.default.device[1]
            else:
                in_dev = sd.default.device[0]
                out_dev = sd.default.device[1]
        except Exception:
            in_dev = None; out_dev = None

        samplerate = 16000
        blocksize = 1024

        def callback(indata, frames, time_info, status):
            if status: pass
            # mono mix
            x = indata.copy().astype(np.float32)
            if x.ndim == 2:
                x = x.mean(axis=1)
            self._q.put(x)

        try:
            with sd.InputStream(channels=1, samplerate=samplerate, blocksize=blocksize, callback=callback):
                if self.on_state: self.on_state("listening")
                buf = np.zeros(0, dtype=np.float32)
                step = int(self.step_seconds * samplerate)
                last_emit = time.time()
                while not self._stop.is_set():
                    try:
                        chunk = self._q.get(timeout=0.2)
                        buf = np.concatenate([buf, chunk])
                    except queue.Empty:
                        pass
                    if buf.size >= step or (time.time()-last_emit > self.step_seconds*1.5 and buf.size > samplerate*2):
                        audio = buf[:step]
                        buf = buf[step:]
                        last_emit = time.time()
                        if self.on_state: self.on_state("transcribing")
                        segments, _ = self._model.transcribe(audio, language="fr", beam_size=1)
                        txt = " ".join([s.text for s in segments])
                        if self.on_text: self.on_text(txt.strip())
                        if self.on_state: self.on_state("listening")
        except Exception as e:
            if self.on_state: self.on_state(f"error: {e}")
        if self.on_state: self.on_state("stopped")
