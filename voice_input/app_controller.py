"""應用程式控制器 — 狀態機管理整個語音輸入流程。"""

import logging
from enum import Enum, auto

from .config import AppConfig
from .audio_capture import AudioCapture
from .asr_engine import ASREngine
from .postprocess import TextPostprocessor
from .delivery import deliver

logger = logging.getLogger(__name__)


class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    PROCESSING = auto()
    DELIVERING = auto()
    DONE = auto()
    ERROR = auto()


class AppController:
    """語音輸入狀態機控制器。"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.state = State.IDLE
        self.audio = AudioCapture(
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
        )
        self.asr = ASREngine(
            model=config.asr.model,
            quant=config.asr.quant,
            batch_size=config.asr.batch_size,
            language=config.asr.language,
        )
        self.postprocessor = TextPostprocessor(
            filler_words=config.postprocess.filler_words,
            max_line_length=config.postprocess.max_line_length,
            llm_config=config.llm,
        )

    def initialize(self):
        """預載模型（可能需要一些時間下載）。"""
        logger.info("正在初始化，預載 ASR 模型...")
        self.asr.load_model()
        logger.info("初始化完成")

    def start_recording(self):
        """開始錄音：IDLE → RECORDING。"""
        if self.state != State.IDLE:
            logger.warning("無法開始錄音，目前狀態: %s", self.state)
            return
        self.state = State.RECORDING
        self.audio.start()

    def stop_recording_and_process(self) -> str:
        """停止錄音並執行完整管線，回傳處理後文字。"""
        if self.state != State.RECORDING:
            raise RuntimeError(f"非錄音狀態，無法停止: {self.state}")

        try:
            # RECORDING → TRANSCRIBING
            self.state = State.TRANSCRIBING
            audio_path = self.audio.stop()

            # 轉錄
            result = self.asr.transcribe(audio_path)
            raw_text = result.get("text", "").strip()

            if not raw_text:
                logger.warning("轉錄結果為空")
                self.state = State.DONE
                self.audio.cleanup()
                return ""

            # TRANSCRIBING → PROCESSING
            self.state = State.PROCESSING
            processed_text = self.postprocessor.process(raw_text)

            # PROCESSING → DELIVERING
            self.state = State.DELIVERING
            deliver(
                processed_text,
                clipboard=self.config.delivery.clipboard,
                notification=self.config.delivery.notification,
            )

            # DELIVERING → DONE
            self.state = State.DONE
            self.audio.cleanup()
            return processed_text

        except Exception as e:
            self.state = State.ERROR
            logger.error("處理過程發生錯誤: %s", e)
            self.audio.cleanup()
            raise

    def reset(self):
        """重置狀態回 IDLE。"""
        self.state = State.IDLE
