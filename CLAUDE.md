# lightning-whisper-mlx — 專案筆記

## 專案概覽

基於 [lightning-whisper-mlx](https://github.com/mustafaaljadery/lightning-whisper-mlx) 的 macOS 語音輸入系統。使用 MLX 框架在 Apple Silicon 上進行高效語音辨識，並透過 CLI 操作完成中文語音轉文字。

## 專案結構

```
lightning-whisper-mlx/
├── lightning_whisper_mlx/     # 原始 ASR 引擎（第三方）
│   ├── lightning.py           # LightningWhisperMLX 主類別
│   ├── transcribe.py          # 轉錄核心
│   ├── load_models.py         # 模型載入
│   └── ...
├── voice_input/               # 語音輸入系統 v0.1（新增）
│   ├── config.py              # 設定管理（YAML + dataclass + .env）
│   ├── audio_capture.py       # 麥克風錄音（sounddevice）
│   ├── asr_engine.py          # 封裝 LightningWhisperMLX
│   ├── postprocess.py         # 後處理（LLM 優先 → 規則 fallback）
│   ├── llm_refine.py          # LLM 文字修飾（xAI Grok API）
│   ├── delivery.py            # 剪貼簿 + macOS 通知
│   ├── app_controller.py      # 狀態機控制器
│   └── main.py                # CLI 進入點
├── config_default.yaml        # 預設設定檔
├── .env                       # API Key（不入版控）
├── install_and_run.sh         # 一鍵安裝啟動腳本
├── run_voice_input.command    # macOS 雙擊啟動器
└── setup.py                   # 原始套件安裝
```

## 關鍵限制 & 注意事項

1. **必須在 repo root 執行**：`LightningWhisperMLX` 使用 `./mlx_models/` 相對路徑存放模型（`lightning.py:79-91`），`asr_engine.py` 會自動 `os.chdir()` 到 repo root
2. **Apple Silicon 限定**：MLX 框架僅支援 arm64
3. **需要 ffmpeg**：ASR 音訊載入依賴 ffmpeg
4. **預設模型**：`small` + `language="zh"`，可透過 `--model` / `--language` 覆蓋

## 額外相依套件（voice_input 需要）

- `sounddevice` — 麥克風錄音
- `PyYAML` — 設定檔解析
- `openai` — xAI Grok API 客戶端（OpenAI 相容格式）
- `python-dotenv` — `.env` 檔案載入
- 不需要 pyperclip，直接用 macOS 內建 `pbcopy`

## 常用指令

```bash
# 一鍵安裝 + 啟動
bash install_and_run.sh

# 手動執行（已安裝情況下）
python -m voice_input.main

# 指定模型 / debug 模式
python -m voice_input.main --model tiny --debug

# 指定語言
python -m voice_input.main --language en

# 停用 LLM 後處理（僅用規則管線）
python -m voice_input.main --no-llm

# 指定領域上下文（提高專業術語辨識）
python -m voice_input.main --context "醫學研究"
python -m voice_input.main --context "軟體開發"

# 指定輸出風格
python -m voice_input.main --style bullet
python -m voice_input.main --style concise

# 組合使用
python -m voice_input.main --context "醫學研究" --style bullet --debug
```

## 資料流

```
麥克風 → WAV temp file → LightningWhisperMLX.transcribe() → raw_text
→ [LLM 路徑] Grok API 一次完成修正錯字+標點+去口頭禪+潤飾 → final_text
→ [規則 fallback] 移除口頭禪 → 去重複 → 加標點 → 換行 → final_text
→ pbcopy + 通知
```

## 狀態機流程

```
IDLE → RECORDING → TRANSCRIBING → PROCESSING → DELIVERING → DONE → (reset) → IDLE
任何錯誤 → ERROR → (reset) → IDLE
```

## 設定檔優先順序

hardcoded defaults → `config_default.yaml` → 使用者自訂 YAML（`--config`）→ CLI 參數

## LLM 後處理（Grok API）

- **模型**：`grok-4-1-fast-reasoning`（xAI OpenAI-compatible endpoint）
- **API Key**：僅從 `.env` 檔的 `XAI_API_KEY` 環境變數讀取（YAML 中不可設定 api_key，防止洩漏）
- **行為**：啟用且有 API Key 時優先走 LLM；LLM 失敗或未設定時自動 fallback 到規則管線
- **停用**：`--no-llm` CLI 參數 或 `config_default.yaml` 中 `llm.enabled: false`
- **Timeout**：預設 30 秒，不重試（`max_retries=0`），失敗直接 fallback

### 上下文感知（`--context`）

指定領域讓 LLM 更準確推斷同音錯字和專業術語：

| `--context` | 效果範例 |
|-------------|---------|
| `"醫學研究"` | 「口號研究」→「世代研究（Cohort Study）」 |
| `"軟體開發"` | 「城市」→「程式」、「愛批愛」→「API」 |
| `"財務報告"` | 「應收帳款」「毛利率」等術語正確辨識 |
| （空）| 無領域偏好，通用處理 |

也可在 `config_default.yaml` 中設定 `llm.context`，CLI `--context` 會覆蓋。

### 輸出風格（`--style`）

| `--style` | 說明 | 輸出範例 |
|-----------|------|---------|
| `professional`（預設）| 專業書面語，語氣正式 | 程式的效能表現不錯，但可再優化。API 回應時間約 350 毫秒。 |
| `concise` | 極度精簡，只留核心 | 程式效能尚可，API 回應 350ms，需優化。 |
| `bullet` | 條列式要點 | - 程式效能不錯，可再優化<br>- API 回應時間約 350 毫秒 |
| `casual` | 口語親切風格 | 程式跑起來還不錯啦，API 大概 350 毫秒。 |

### Prompt 架構（`llm_refine.py`）

動態組裝 system prompt：`_BASE_PROMPT` + 領域上下文（選填）+ 風格指示 + `_OUTPUT_INSTRUCTIONS`

處理能力：語意推論、專業術語加註英文、中英夾雜保留、台灣在地用語、口語數字轉阿拉伯數字、去口頭禪、結構化分段

安全措施：`context` 截斷 50 字並移除 `\n` / `#` 防止 prompt injection
