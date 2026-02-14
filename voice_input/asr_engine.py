"""ASR 引擎 — 封裝 LightningWhisperMLX，lazy-load 模型。"""

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# repo root（lightning_whisper_mlx 套件所在目錄）
REPO_ROOT = Path(__file__).resolve().parent.parent


class ASREngine:
    """語音辨識引擎，包裝 LightningWhisperMLX。"""

    def __init__(self, model: str = "small", quant: Optional[str] = None,
                 batch_size: int = 12, language: str = "zh"):
        self.model_name = model
        self.quant = quant
        self.batch_size = batch_size
        self.language = language
        self._whisper = None

    def load_model(self):
        """載入模型（必須在 repo root 目錄下執行）。"""
        import os
        os.chdir(REPO_ROOT)
        logger.info("工作目錄切換至 %s", REPO_ROOT)

        # 確保 repo root 在 sys.path 中
        repo_str = str(REPO_ROOT)
        if repo_str not in sys.path:
            sys.path.insert(0, repo_str)

        from lightning_whisper_mlx import LightningWhisperMLX

        logger.info("正在載入模型 %s (quant=%s, batch_size=%d)...",
                     self.model_name, self.quant, self.batch_size)
        self._whisper = LightningWhisperMLX(
            model=self.model_name,
            batch_size=self.batch_size,
            quant=self.quant,
        )
        logger.info("模型載入完成")

    def transcribe(self, audio_path: str) -> dict:
        """轉錄音訊檔案，回傳 {'text', 'segments', 'language'}。"""
        if self._whisper is None:
            self.load_model()

        logger.info("開始轉錄: %s (language=%s)", audio_path, self.language)
        result = self._whisper.transcribe(audio_path, language=self.language)
        logger.info("轉錄完成: %s", result.get("text", "")[:80])
        return result
