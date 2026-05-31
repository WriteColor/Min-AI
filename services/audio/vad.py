import numpy as np

try:
    import webrtcvad as _webrtcvad
    _HAS_WEBRTCVAD = True
except ImportError:
    _HAS_WEBRTCVAD = False


class VAD:
    def __init__(self, sample_rate: int = 16000, rms_threshold: float = 0.003,
                 webrtc_mode: int = 1):
        self.sample_rate = sample_rate
        self.rms_threshold = rms_threshold
        self._webrtc = None
        if _HAS_WEBRTCVAD:
            try:
                self._webrtc = _webrtcvad.Vad(webrtc_mode)
                self._webrtc.set_mode(webrtc_mode)
            except Exception:
                self._webrtc = None

    def is_speech(self, indata: np.ndarray) -> tuple[bool, float]:
        rms = self._calc_rms(indata)
        if rms < self.rms_threshold:
            return False, rms
        if self._webrtc is not None and self.sample_rate in (8000, 16000, 32000, 48000):
            try:
                audio_bytes = (indata.astype(np.float32) * 32768).astype(np.int16).tobytes()
                return self._webrtc.is_speech(audio_bytes, self.sample_rate), rms
            except Exception:
                pass
        return True, rms

    def _calc_rms(self, indata: np.ndarray) -> float:
        try:
            return float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
        except Exception:
            return 0.0
