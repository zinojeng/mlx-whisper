"""中文後處理模組 — 移除口頭禪、去重複、加標點、自動換行。"""

import logging
import re
from typing import Optional

from . import llm_refine
from .config import LLMConfig

logger = logging.getLogger(__name__)


class TextPostprocessor:
    """文字後處理管線。"""

    def __init__(self, filler_words: Optional[list] = None, max_line_length: int = 40,
                 llm_config: Optional[LLMConfig] = None):
        self.filler_words = filler_words or [
            "嗯", "啊", "就是", "然後", "那個", "對", "所以", "基本上", "就是說", "反正"
        ]
        self.max_line_length = max_line_length
        self.llm_config = llm_config

        # 預編譯口頭禪 regex（按長度降序以避免部分匹配問題）
        sorted_fillers = sorted(self.filler_words, key=len, reverse=True)
        self._filler_patterns = [
            re.compile(
                r'(?:^|(?<=[\s，。！？、；：\u3000]))' +
                re.escape(filler) +
                r'(?:[\s，。！？、；：\u3000]|$)'
            )
            for filler in sorted_fillers
        ]
        self._whitespace_pattern = re.compile(r'\s+')

    def _llm_available(self) -> bool:
        """檢查 LLM 是否可用。"""
        return (self.llm_config is not None
                and self.llm_config.enabled
                and bool(self.llm_config.api_key))

    def process(self, text: str) -> str:
        """執行完整後處理管線。啟用 LLM 時優先使用，失敗時 fallback 到規則管線。"""
        original = text

        # LLM 路徑
        if self._llm_available():
            try:
                result = llm_refine.refine_text(
                    text,
                    api_key=self.llm_config.api_key,
                    model=self.llm_config.model,
                    base_url=self.llm_config.base_url,
                    timeout=self.llm_config.timeout,
                    context=self.llm_config.context,
                    style=self.llm_config.style,
                )
                return result.strip()
            except Exception as e:
                logger.warning("LLM 修飾失敗，改用規則處理: %s", e)

        # 規則管線 fallback
        try:
            text = self._remove_fillers(text)
            text = self._remove_repeated_chars(text)
            text = self._add_punctuation(text)
            text = self._auto_line_break(text)
            return text.strip()
        except Exception as e:
            logger.warning("後處理失敗，回傳原始文字: %s", e)
            return original.strip()

    def _remove_fillers(self, text: str) -> str:
        """移除口頭禪（使用預編譯的 regex）。"""
        for pattern in self._filler_patterns:
            text = pattern.sub('', text)
        text = self._whitespace_pattern.sub('', text)
        return text

    def _remove_repeated_chars(self, text: str) -> str:
        """移除連續重複字詞（好好好→好、對對對→對）。"""
        # 處理單字重複 (3 次以上)
        text = re.sub(r'(.)\1{2,}', r'\1', text)
        # 處理雙字詞重複 (如「就是就是就是」→「就是」)
        text = re.sub(r'(.{2,3})\1{2,}', r'\1', text)
        return text

    def _add_punctuation(self, text: str) -> str:
        """為缺少標點的中文文字加入基礎標點。"""
        # 如果文字已有足夠標點，不再處理
        punctuation_chars = set("，。！？、；：")
        punct_count = sum(1 for c in text if c in punctuation_chars)
        if len(text) > 0 and punct_count / len(text) > 0.03:
            return text

        # 在疑問詞句尾加問號
        text = re.sub(r'((?:嗎|呢|吧|麼|什麼|怎麼|為什麼|哪裡|誰|幾|多少)[^，。！？]*?)$', r'\1？', text)
        text = re.sub(r'((?:嗎|呢|吧|麼|什麼|怎麼|為什麼|哪裡|誰|幾|多少)[^，。！？]*?)(?=[\u4e00-\u9fff])', r'\1，', text)

        # 如果結尾沒有標點，加句號
        if text and text[-1] not in punctuation_chars and text[-1] != '？':
            text += '。'

        return text

    def _auto_line_break(self, text: str) -> str:
        """超過 max_line_length 時在標點處自動換行。"""
        if len(text) <= self.max_line_length:
            return text

        result = []
        current_line = ""
        for char in text:
            current_line += char
            if char in "，。！？；：" and len(current_line) >= self.max_line_length:
                result.append(current_line)
                current_line = ""

        if current_line:
            result.append(current_line)

        return "\n".join(result)
