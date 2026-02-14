"""LLM 文字修飾模組 — 使用 xAI Grok API 修正語音辨識文字。"""

import logging
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是語音辨識後處理助手。使用者的文字來自語音辨識（ASR），可能有：\n"
    "1. 同音錯字（如「整理上」應為「整體上」）\n"
    "2. 缺少標點符號\n"
    "3. 口頭禪和贅詞（嗯、啊、然後、就是、那個等）\n"
    "4. 語句不通順\n\n"
    "請修正以上問題，保留原意，只回傳修正後的文字，不要加任何解釋。"
)

# 模組層級快取，避免每次呼叫都建立新連線
_client: Optional[OpenAI] = None
_client_key: Optional[tuple] = None


def _get_client(api_key: str, base_url: str, timeout: int) -> OpenAI:
    """取得或重用 OpenAI client。參數變更時重新建立。"""
    global _client, _client_key
    key = (api_key, base_url, timeout)
    if _client is None or _client_key != key:
        _client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)
        _client_key = key
    return _client


def refine_text(
    text: str,
    api_key: str,
    model: str = "grok-4-1-fast-reasoning",
    base_url: str = "https://api.x.ai/v1",
    timeout: int = 30,
) -> str:
    """呼叫 LLM API 修飾語音辨識文字。"""
    client = _get_client(api_key, base_url, timeout)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.3,
        max_tokens=2048,
    )

    result = response.choices[0].message.content
    if result is None:
        raise ValueError("LLM 回傳內容為空 (content=None)")
    logger.debug("LLM 修飾結果: %s → %s", text, result)
    return result
