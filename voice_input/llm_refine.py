"""LLM 文字修飾模組 — 使用 xAI Grok API 修正語音辨識文字。"""

import logging
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

_BASE_PROMPT = """\
你是專業的語音辨識後處理助手。使用者的文字來自語音辨識（ASR），品質可能很差。

## 你的任務
將雜亂的 ASR 原始文字，重寫為清晰、結構化的書面文字。

## 處理規則
1. **語意推論**：ASR 常產生同音錯字，你必須根據上下文推斷正確用詞。\
例如「口號研究」→「世代研究（Cohort Study）」、「城市」→「程式」、「資料褲」→「資料庫」
2. **專業術語**：遇到專業詞彙時，使用正確術語，必要時加註英文。\
例如「隨機分配」→「隨機分派（Randomization）」
3. **結構化**：當內容包含多個要點時，使用編號列表呈現。長段落適當分段
4. **去蕪存菁**：移除所有口頭禪（嗯、啊、然後、就是、那個、對、所以、基本上等）和重複贅詞
5. **標點與格式**：加入正確標點符號
6. **中英夾雜**：正確保留英文品牌名、技術術語、縮寫（如 iPhone、API、COVID-19）。\
辨識台灣在地用語（如全聯、高鐵、健保）
7. **數字處理**：口語數字轉為阿拉伯數字（「三百五十萬」→「350 萬」），\
日期時間使用標準格式（「十一月三號」→「11 月 3 日」）
8. **保留原意**：可以重組句子結構讓表達更清晰，但不可添加原文沒有的資訊
"""

_STYLE_INSTRUCTIONS = {
    "professional": "使用專業書面語，語氣正式、用詞精確。",
    "concise": "極度精簡，只保留核心資訊，每句話盡量簡短。",
    "bullet": "將所有內容整理為條列式要點（使用編號或項目符號），不使用段落敘述。",
    "casual": "使用自然口語風格，保持親切感，但仍修正錯字和標點。",
}

_OUTPUT_INSTRUCTIONS = """\

## 輸出要求
- 只回傳修正後的文字，不要加任何解釋、前綴或後綴
- 使用繁體中文"""


def build_system_prompt(context: str = "", style: str = "professional") -> str:
    """根據上下文和風格動態組裝 system prompt。"""
    parts = [_BASE_PROMPT]

    # 上下文感知（限制長度，移除特殊字元以防 prompt injection）
    if context:
        safe_context = context[:50].replace("\n", " ").replace("#", "")
        parts.append(f"\n## 領域上下文\n目前使用者正在談論「{safe_context}」相關內容。"
                     f"請優先使用該領域的專業術語和慣用表達來修正文字。")

    # 風格指示
    style_key = style if style in _STYLE_INSTRUCTIONS else "professional"
    if style and style not in _STYLE_INSTRUCTIONS:
        logger.warning("未知的 style '%s'，使用預設 'professional'", style)
    parts.append(f"\n## 輸出風格\n{_STYLE_INSTRUCTIONS[style_key]}")

    parts.append(_OUTPUT_INSTRUCTIONS)
    return "".join(parts)


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
    context: str = "",
    style: str = "professional",
) -> str:
    """呼叫 LLM API 修飾語音辨識文字。"""
    client = _get_client(api_key, base_url, timeout)
    system_prompt = build_system_prompt(context=context, style=style)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
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
