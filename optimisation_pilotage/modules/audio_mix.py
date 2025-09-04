import threading, time, numpy as np, sounddevice as sd, soundfile as sf
from pathlib import Path
from typing import Optional, Callable
from collections import deque
from .utils import log_exc

def _safe_mean(x, axis=1):
    try:
        return np.mean(x, axis=axis, keepdims=True)
    except Exception:
        return x

class LiveMixer:
    def __init__(self, samplerate=16000, channels=1, chunk_seconds=15,
                 mic_device=None, sys_device=None, on_chunk: Optional[Callable[[Path],None]]=None,
                 out_dir: Optional[Path]=None):
        # samplerate = cible (on rééchantillonne si besoin)
        self.samplerate=samplerate
        self.channels=max(1, channels)   # 1 pour Whisper
        self.mic_device=mic_device
        self.sys_device=sys_device
        self.on_chunk=on_chunk
        self.out_dir = out_dir or Path.cwd()
        self.chunk_seconds=chunk_seconds
        self._stop=threading.Event()
        self._thread=None

    @staticmethod
    def list_devices():
        return sd.query_devices()

    def _open_input(self, device, loopback=False):
        """Ouvre un InputStream robuste: essaie plusieurs (samplerate, channels).
           Retourne (stream, queue, stream_samplerate, stream_channels) ou (None, None, None, None) si échec.
        """
        if device is None:
            return None, None, None, None
        info = sd.query_devices(device)
        # candidats de canaux: pour loopback (sortie), certains drivers n'acceptent que 2
        chan_candidates = []
        if loopback:
            # WASAPI loopback sur périphérique de sortie
            out_ch = int(info.get('max_output_channels') or 2)
            in_ch  = int(info.get('max_input_channels') or 0)
            chan_candidates = [out_ch, in_ch, 2, 1]
        else:
            in_ch  = int(info.get('max_input_channels') or 1)
            chan_candidates = [in_ch, 2, 1]

        # candidats de samplerate: on commence par le défaut du device
        sr_candidates = []
        try:
            default_sr = int(round(info.get('default_samplerate') or 0))
        except Exception:
            default_sr = 0
        for sr in [default_sr, 48000, 44100, 32000, 16000]:
            if sr and sr not in sr_candidates:
                sr_candidates.append(sr)

        # Param WASAPI loopback si dispo
        extra = None
        try:
            if loopback and hasattr(sd, 'WasapiSettings'):
                extra = sd.WasapiSettings(loopback=True)
        except Exception:
            extra = None

        q = deque()
        def cb(indata, frames, time_info, status):
            try:
                arr = indata.copy()
                # downmix en mono pour la suite
                if arr.ndim == 1:
                    arr = arr[:, None]
                if self.channels == 1 and arr.shape[1] > 1:
                    arr = _safe_mean(arr, axis=1)
                q.append(arr.astype(np.float32, copy=False))
            except Exception as e:
                log_exc(e)

        for sr in sr_candidates:
            for ch in chan_candidates:
                if not isinstance(ch, int) or ch <= 0:
                    continue
                try:
                    s = sd.InputStream(
                        samplerate=sr,
                        channels=ch,
                        device=device,
                        callback=cb,
                        dtype='float32',
                        blocksize=0,
                        latency='low',
                        extra_settings=extra
                    )
                    s.start()
                    return s, q, sr, ch
                except Exception as e:
                    # on essaie la prochaine combinaison
                    continue

        return None, None, None, None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self):
        mic_stream=sys_stream=None
        mic_q=sys_q=None
        mic_sr=mic_ch=None
        sys_sr=sys_ch=None

        try:
            if self.mic_device is not None:
                mic_stream, mic_q, mic_sr, mic_ch = self._open_input(self.mic_device, loopback=False)
            if self.sys_device is not None:
                sys_stream, sys_q, sys_sr, sys_ch = self._open_input(self.sys_device, loopback=True)
        except Exception as e:
            log_exc(e)

        # s'il n'y a aucun stream, on s'arrête proprement
        if mic_stream is None and sys_stream is None:
            return

        # on choisit un samplerate de référence (priorité système, sinon micro)
        ref_sr = sys_sr or mic_sr or 16000
        target_sr = self.samplerate or 16000
        chunk_samples = int(target_sr * self.chunk_seconds)
        buf = np.zeros((0, 1), dtype=np.float32)  # on travaille déjà en mono pour la pile

        def _resample_mono(x, sr_from, sr_to):
            if sr_from == sr_to:
                return x
            # x est (N, 1)
            N = x.shape[0]
            if N == 0:
                return x
            M = int(round(N * (sr_to / sr_from)))
            t_old = np.linspace(0.0, 1.0, N, endpoint=False)
            t_new = np.linspace(0.0, 1.0, M, endpoint=False)
            y = np.interp(t_new, t_old, x[:, 0]).astype(np.float32)
            return y[:, None]

        try:
            while not self._stop.is_set():
                time.sleep(0.03)
                parts = []

                # on dépile quelques blocs si dispo (pour lisser)
                for _ in range(3):
                    try:
                        if mic_q and mic_q:
                            parts.append((mic_q.popleft(), mic_sr))
                    except Exception:
                        break
                for _ in range(3):
                    try:
                        if sys_q and sys_q:
                            parts.append((sys_q.popleft(), sys_sr))
                    except Exception:
                        break

                # mix + resample vers target_sr
                if parts:
                    mono_chunks = []
                    for arr, sr in parts:
                        if arr is None or arr.size == 0:
                            continue
                        # arr est déjà mono (voir cb)
                        if sr and sr != target_sr:
                            arr = _resample_mono(arr, sr, target_sr)
                        mono_chunks.append(arr)

                    if mono_chunks:
                        mix = np.vstack(mono_chunks)
                        buf = np.vstack([buf, mix])

                # dès qu'on atteint chunk_samples, on écrit
                while buf.shape[0] >= chunk_samples:
                    chunk = buf[:chunk_samples]
                    buf = buf[chunk_samples:]
                    path = self.out_dir / f'chunk_{int(time.time())}.wav'
                    try:
                        sf.write(str(path), chunk, target_sr)
                        if self.on_chunk:
                            self.on_chunk(path)
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
