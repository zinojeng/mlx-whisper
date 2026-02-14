"""LLM 文字修飾模組 — 使用 xAI Grok API 修正語音辨識文字。"""

import logging
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是專業的語音辨識後處理助手。使用者的文字來自語音辨識（ASR），品質可能很差。\n\n"
    "## 你的任務\n"
    "將雜亂的 ASR 原始文字，重寫為清晰、專業、結構化的書面文字。\n\n"
    "## 處理規則\n"
    "1. **語意推論**：ASR 常產生同音錯字，你必須根據上下文推斷正確用詞。"
    "例如「口號研究」→「世代研究（Cohort Study）」、「城市」→「程式」、「資料褲」→「資料庫」\n"
    "2. **專業術語**：遇到專業詞彙時，使用正確術語，必要時加註英文。"
    "例如「隨機分配」→「隨機分派（Randomization）」\n"
    "3. **結構化**：當內容包含多個要點時，使用編號列表呈現。長段落適當分段\n"
    "4. **去蕪存菁**：移除所有口頭禪（嗯、啊、然後、就是、那個、對、所以、基本上等）和重複贅詞\n"
    "5. **標點與格式**：加入正確標點符號，使用書面語表達\n"
    "6. **保留原意**：可以重組句子結構讓表達更清晰，但不可添加原文沒有的資訊\n\n"
    "## 輸出要求\n"
    "- 只回傳修正後的文字，不要加任何解釋、前綴或後綴\n"
    "- 使用繁體中文\n"
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
