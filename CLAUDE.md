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
