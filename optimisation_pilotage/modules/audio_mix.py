import threading, time, numpy as np, sounddevice as sd, soundfile as sf
from pathlib import Path
from typing import Optional, Callable
from collections import deque
from .utils import log_exc

class LiveMixer:
    def __init__(self, samplerate=16000, channels=1, chunk_seconds=15, mic_device=None, sys_device=None, on_chunk: Optional[Callable[[Path],None]]=None, out_dir: Optional[Path]=None):
        self.samplerate=samplerate; self.channels=channels; self.chunk_seconds=chunk_seconds
        self.mic_device=mic_device; self.sys_device=sys_device; self.on_chunk=on_chunk; self.out_dir = out_dir or Path.cwd()
        self._stop=threading.Event(); self._thread=None

    @staticmethod
    def list_devices(): return sd.query_devices()

    def _record_stream(self, device, loopback=False):
        q=deque()
        def cb(indata, frames, time_info, status):
            try:
                arr = indata.copy()
                if arr.ndim==1: arr = arr[:,None]
                if self.channels == 1 and arr.shape[1] > 1:
                    arr = np.mean(arr, axis=1, keepdims=True)
                q.append(arr)
            except Exception as e:
                log_exc(e)
        extra=None
        try:
            if loopback and hasattr(sd,'WasapiSettings'):
                extra=sd.WasapiSettings(loopback=True)
        except Exception:
            extra=None
        s=sd.InputStream(samplerate=self.samplerate, channels=max(1,self.channels), device=device, callback=cb, dtype='float32', blocksize=0, latency='low', extra_settings=extra)
        return s,q

    def start(self):
        self._stop.clear(); self._thread=threading.Thread(target=self._run, daemon=True); self._thread.start()

    def stop(self):
        self._stop.set(); 
        if self._thread: self._thread.join(timeout=2)

    def _run(self):
        mic_stream=sys_stream=None; mic_q=sys_q=None
        try:
            if self.mic_device is not None:
                mic_stream,mic_q=self._record_stream(self.mic_device, loopback=False); mic_stream.start()
            if self.sys_device is not None:
                sys_stream,sys_q=self._record_stream(self.sys_device, loopback=True); sys_stream.start()
        except Exception as e:
            log_exc(e)

        chunk_samples=int(self.samplerate*self.chunk_seconds)
        buf=np.zeros((0, self.channels), dtype=np.float32)

        try:
            while not self._stop.is_set():
                time.sleep(0.05)
                parts=[]
                try:
                    if mic_q and mic_q: parts.append(mic_q.popleft())
                except Exception: pass
                try:
                    if sys_q and sys_q: parts.append(sys_q.popleft())
                except Exception: pass
                if parts:
                    min_len = min(p.shape[0] for p in parts)
                    parts = [p[:min_len] for p in parts if p.shape[0] >= min_len and min_len>0]
                    if parts:
                        if len(parts)==1: mix = parts[0]
                        else: mix = np.mean(np.stack(parts, axis=0), axis=0)
                        buf = np.vstack([buf, mix])
                while buf.shape[0] >= chunk_samples:
                    chunk = buf[:chunk_samples]; buf = buf[chunk_samples:]
                    path=self.out_dir / f'chunk_{int(time.time())}.wav'
                    try:
                        sf.write(str(path), chunk, self.samplerate)
                        if self.on_chunk: self.on_chunk(path)
                    except Exception as e:
                        log_exc(e)
        except Exception as e:
            log_exc(e)
        finally:
            try:
                if mic_stream: mic_stream.stop(); mic_stream.close()
                if sys_stream: sys_stream.stop(); sys_stream.close()
            except Exception as e:
                log_exc(e)
