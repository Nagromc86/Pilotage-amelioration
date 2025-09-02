import threading, time
import numpy as np
import soundcard as sc
import soundfile as sf
from pathlib import Path

class MixerRecorder:
    def __init__(self, samplerate=16000, blocksize=2048):
        self.samplerate=samplerate; self.blocksize=blocksize
        self._stop=threading.Event(); self._thread=None; self._out_path=None
    def start(self, out_path: Path, duration_limit_s=None):
        self._stop.clear(); self._out_path=Path(out_path)
        self._thread=threading.Thread(target=self._loop, args=(duration_limit_s,), daemon=True)
        self._thread.start()
    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=2.0)
        return self._out_path
    def _loop(self, duration_limit_s):
        speaker=sc.default_speaker(); mic=sc.default_microphone()
        with speaker.recorder(samplerate=self.samplerate, blocksize=self.blocksize) as spk_rec, \
             mic.recorder(samplerate=self.samplerate, blocksize=self.blocksize) as mic_rec, \
             sf.SoundFile(str(self._out_path), mode='w', samplerate=self.samplerate, channels=1, subtype='PCM_16') as wav:
            t0=time.time()
            while not self._stop.is_set():
                spk=spk_rec.record(numframes=self.blocksize)
                micb=mic_rec.record(numframes=self.blocksize)
                spk_mono=spk.mean(axis=1) if spk.ndim==2 else spk
                mic_mono=micb.mean(axis=1) if micb.ndim==2 else micb
                mix=0.5*spk_mono+0.5*mic_mono
                mix=np.clip(mix,-1.0,1.0)
                wav.write(mix.astype('float32'))
                if duration_limit_s and (time.time()-t0)>=duration_limit_s:
                    break
