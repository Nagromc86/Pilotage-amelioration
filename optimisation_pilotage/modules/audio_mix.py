
import threading, time
import numpy as np
import soundcard as sc
import soundfile as sf
from pathlib import Path

class MixerRecorder:
    def __init__(self, samplerate=16000, blocksize=2048, mic_name=None, sys_name=None, on_tick=None):
        self.samplerate=samplerate; self.blocksize=blocksize
        self._stop=threading.Event(); self._thread=None; self._out_path=None
        self.mic_name=mic_name; self.sys_name=sys_name
        self.on_tick=on_tick
        self._seconds=0

    def set_devices(self, mic_name, sys_name):
        self.mic_name=mic_name; self.sys_name=sys_name

    def start(self, out_path: Path, duration_limit_s=None):
        self._stop.clear(); self._out_path=Path(out_path); self._seconds=0
        self._thread=threading.Thread(target=self._loop, args=(duration_limit_s,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=2.0)
        return self._out_path

    def _get_mic(self, name):
        if name and name!='(défaut)':
            try:
                return sc.get_microphone(name=name, include_loopback=True)
            except Exception:
                pass
        return sc.default_microphone()

    def _get_sys_loopback(self, name):
        if name and name!='(défaut)':
            try:
                return sc.get_microphone(name=name, include_loopback=True)
            except Exception:
                pass
        return sc.default_speaker()

    def _loop(self, duration_limit_s):
        mic_dev = self._get_mic(self.mic_name)
        sys_dev = self._get_sys_loopback(self.sys_name)
        if hasattr(sys_dev, 'recorder'):
            sys_ctx = sys_dev.recorder(samplerate=self.samplerate, blocksize=self.blocksize)
        else:
            sys_ctx = sys_dev.recorder(samplerate=self.samplerate, blocksize=self.blocksize)

        with sys_ctx as spk_rec,                  mic_dev.recorder(samplerate=self.samplerate, blocksize=self.blocksize) as mic_rec,                  sf.SoundFile(str(self._out_path), mode='w', samplerate=self.samplerate, channels=1, subtype='PCM_16') as wav:
            t0=time.time()
            while not self._stop.is_set():
                spk=spk_rec.record(numframes=self.blocksize)
                micb=mic_rec.record(numframes=self.blocksize)
                spk_mono=spk.mean(axis=1) if spk.ndim==2 else spk
                mic_mono=micb.mean(axis=1) if micb.ndim==2 else micb
                mix=0.6*spk_mono+0.4*mic_mono
                mix=np.clip(mix,-1.0,1.0)
                wav.write(mix.astype('float32'))
                secs=int(time.time()-t0)
                self._seconds=secs
                if self.on_tick: 
                    try: self.on_tick(secs)
                    except Exception: pass
                if duration_limit_s and (time.time()-t0)>=duration_limit_s:
                    break
