"""麥克風錄音模組 — 使用 sounddevice 擷取音訊並寫入 WAV 暫存檔。"""

import logging
import tempfile
import threading
import wave

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioCapture:
    """錄音控制器：start() 開始收音，stop() 停止並回傳 WAV 檔路徑。"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._lock = threading.Lock()
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._temp_path: str | None = None

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.warning("sounddevice 狀態: %s", status)
        with self._lock:
            if self._recording:
                self._frames.append(indata.copy())

    def start(self):
        """開始錄音。"""
        with self._lock:
            if self._recording:
                logger.warning("已在錄音中，忽略重複呼叫")
                return
            self._frames = []

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            self._stream = None
            logger.error("無法開啟麥克風: %s", e)
            raise

        with self._lock:
            self._recording = True
        logger.info("錄音開始 (sample_rate=%d, channels=%d)", self.sample_rate, self.channels)

    def stop(self) -> str:
        """停止錄音，將音訊寫入暫存 WAV 檔，回傳檔案路徑。"""
        with self._lock:
            self._recording = False

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if not self._frames:
                raise RuntimeError("沒有錄到任何音訊")
            audio_data = np.concatenate(self._frames, axis=0)

        # 寫入 WAV
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self._temp_path = tmp.name
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())
        tmp.close()

        duration = len(audio_data) / self.sample_rate
        logger.info("錄音結束，時長 %.1f 秒，已存至 %s", duration, self._temp_path)
        return self._temp_path

    def cleanup(self):
        """刪除暫存 WAV 檔。"""
        if self._temp_path:
            import os
            try:
                os.unlink(self._temp_path)
                logger.debug("已刪除暫存檔 %s", self._temp_path)
            except OSError:
                pass
            self._temp_path = None
