import threading, time, numpy as np, sounddevice as sd, soundfile as sf
from pathlib import Path
from typing import Optional, Callable
class LiveMixer:
    def __init__(self, samplerate=16000, channels=1, chunk_seconds=15, mic_device=None, sys_device=None, on_chunk: Optional[Callable[[Path],None]]=None, out_dir: Optional[Path]=None):
        self.samplerate=samplerate; self.channels=channels; self.chunk_seconds=chunk_seconds
        self.mic_device=mic_device; self.sys_device=sys_device; self.on_chunk=on_chunk; self.out_dir = out_dir or Path.cwd()
        self._stop=threading.Event(); self._thread=None
    @staticmethod
    def list_devices(): return sd.query_devices()
    def _record_stream(self, device, loopback=False):
        q=[]
        def cb(indata, frames, time_info, status): q.append(indata.copy())
        extra=None
        try:
            if loopback and hasattr(sd,'WasapiSettings'): extra=sd.WasapiSettings(loopback=True)
        except Exception: extra=None
        s=sd.InputStream(samplerate=self.samplerate, channels=self.channels, device=device, callback=cb, dtype='float32', blocksize=0, latency='low', extra_settings=extra)
        return s,q
    def start(self):
        self._stop.clear(); self._thread=threading.Thread(target=self._run, daemon=True); self._thread.start()
    def stop(self):
        self._stop.set(); 
        if self._thread: self._thread.join(timeout=2)
    def _run(self):
        mic_stream,mic_q=(None,[]); sys_stream,sys_q=(None,[])
        try:
            if self.mic_device is not None:
                mic_stream,mic_q=self._record_stream(self.mic_device, loopback=False); mic_stream.start()
            if self.sys_device is not None:
                sys_stream,sys_q=self._record_stream(self.sys_device, loopback=True); sys_stream.start()
        except Exception:
            pass
        chunk_samples=int(self.samplerate*self.chunk_seconds); import numpy as np
        buf=np.zeros((0,self.channels), dtype=np.float32)
        while not self._stop.is_set():
            time.sleep(0.2); parts=[]
            if mic_q: parts.append(mic_q.pop(0))
            if sys_q: parts.append(sys_q.pop(0))
            if parts:
                stk=[p if p.ndim==2 else p[:,None] for p in parts]; mix=np.mean(np.stack(stk,axis=0),axis=0)
                buf=np.vstack([buf,mix])
                if len(buf)>=chunk_samples:
                    chunk=buf[:chunk_samples]; buf=buf[chunk_samples:]
                    path=self.out_dir / f'chunk_{int(time.time())}.wav'
                    sf.write(str(path), chunk, self.samplerate)
                    if self.on_chunk:
                        try: self.on_chunk(path)
                        except Exception: pass
        try:
            if mic_stream: mic_stream.stop(); mic_stream.close()
            if sys_stream: sys_stream.stop(); sys_stream.close()
        except Exception: pass
