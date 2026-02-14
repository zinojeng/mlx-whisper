"""設定管理 — YAML 載入 + dataclass 定義"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class ASRConfig:
    model: str = "small"
    quant: Optional[str] = None
    batch_size: int = 12
    language: str = "zh"


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class PostprocessConfig:
    locale: str = "zh-TW"
    filler_words: list = field(default_factory=lambda: [
        "嗯", "啊", "就是", "然後", "那個", "對", "所以", "基本上", "就是說", "反正"
    ])
    max_line_length: int = 40


@dataclass
class DeliveryConfig:
    clipboard: bool = True
    notification: bool = True


@dataclass
class LLMConfig:
    enabled: bool = True
    provider: str = "xai"
    model: str = "grok-4-1-fast-reasoning"
    base_url: str = "https://api.x.ai/v1"
    api_key: str = ""
    timeout: int = 30
    context: str = ""       # 領域上下文，如 "醫學研究"、"軟體開發"
    style: str = "professional"  # professional | concise | bullet | casual


@dataclass
class AppConfig:
    asr: ASRConfig = field(default_factory=ASRConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    postprocess: PostprocessConfig = field(default_factory=PostprocessConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    log_level: str = "INFO"


def _deep_merge(base: dict, override: dict) -> dict:
    """遞迴合併兩個 dict，override 優先。"""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _find_default_config() -> Optional[Path]:
    """找到 repo root 的 config_default.yaml。"""
    candidates = [
        Path(__file__).resolve().parent.parent / "config_default.yaml",
        Path.cwd() / "config_default.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """載入設定，解析順序：hardcoded defaults → config_default.yaml → 使用者自訂 YAML → .env。"""
    raw: dict = {}

    # 0. 載入 .env（不覆蓋已存在的環境變數）
    load_dotenv()

    # 1. 載入 config_default.yaml
    default_path = _find_default_config()
    if default_path:
        try:
            with open(default_path, "r", encoding="utf-8") as f:
                default_data = yaml.safe_load(f) or {}
            raw = _deep_merge(raw, default_data)
        except Exception as e:
            logger.warning("無法載入預設設定檔 %s: %s", default_path, e)

    # 2. 載入使用者自訂 YAML
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_data = yaml.safe_load(f) or {}
            raw = _deep_merge(raw, user_data)
        except Exception as e:
            logger.warning("無法載入使用者設定檔 %s: %s", config_path, e)

    # 3. 建立 AppConfig
    try:
        asr = ASRConfig(**raw.get("asr", {}))
        audio = AudioConfig(**raw.get("audio", {}))
        postprocess_data = raw.get("postprocess", {})
        postprocess = PostprocessConfig(**postprocess_data)
        delivery = DeliveryConfig(**raw.get("delivery", {}))

        # LLM 設定：YAML + .env API key（API key 只從環境變數讀取）
        llm_data = raw.get("llm", {})
        llm_data.pop("api_key", None)
        llm = LLMConfig(**llm_data)
        llm.api_key = os.environ.get("XAI_API_KEY", "")

        log_level = raw.get("logging", {}).get("level", "INFO")
        return AppConfig(
            asr=asr, audio=audio, postprocess=postprocess,
            delivery=delivery, llm=llm, log_level=log_level,
        )
    except Exception as e:
        logger.warning("設定檔解析失敗，使用預設值: %s", e)
        return AppConfig()
