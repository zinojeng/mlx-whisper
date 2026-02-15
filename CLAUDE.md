
# lightning-whisper-mlx — 專案筆記

## 專案概覽

基於 [lightning-whisper-mlx](https://github.com/mustafaaljadery/lightning-whisper-mlx) 的跨平台語音輸入系統。macOS 版使用 MLX 框架在 Apple Silicon 上進行高效語音辨識；iOS 版使用 Apple Speech Framework。兩者皆透過 xAI Grok API 進行 LLM 後處理。

## 專案結構

```
lightning-whisper-mlx/
├── lightning_whisper_mlx/     # 原始 ASR 引擎（第三方）
│   ├── lightning.py           # LightningWhisperMLX 主類別
│   ├── transcribe.py          # 轉錄核心
│   ├── load_models.py         # 模型載入
│   └── ...
├── voice_input/               # macOS 語音輸入系統
│   ├── config.py              # 設定管理（YAML + dataclass + .env）
│   ├── audio_capture.py       # 麥克風錄音（sounddevice）
│   ├── asr_engine.py          # 封裝 LightningWhisperMLX
│   ├── postprocess.py         # 後處理（LLM 優先 → 規則 fallback）
│   ├── menubar_app.py         # macOS Menubar 常駐 App（rumps）
│   ├── menubar_main.py        # Menubar 進入點
│   ├── llm_refine.py          # LLM 文字修飾（xAI Grok API）
│   ├── delivery.py            # 剪貼簿 + macOS 通知
│   ├── app_controller.py      # 狀態機控制器
│   └── main.py                # CLI 進入點
├── ios-app/                   # iOS App（SwiftUI）
│   └── VoiceInput/
│       ├── VoiceInput.xcodeproj/
│       └── VoiceInput/
│           ├── VoiceInputApp.swift      # App 進入點
│           ├── ContentView.swift        # 主畫面 + push-to-talk 按鈕
│           ├── VoiceInputViewModel.swift # 錄音/辨識/LLM ViewModel
│           ├── GrokService.swift        # xAI Grok API 客戶端
│           ├── SettingsView.swift       # 設定頁面
│           ├── Assets.xcassets/         # App Icon + AccentColor
│           └── Info.plist               # 權限宣告（麥克風/語音辨識）
├── config_default.yaml        # 預設設定檔
├── .env                       # API Key（不入版控）
├── install_and_run.sh         # 一鍵安裝啟動腳本
├── run_voice_input.command    # macOS 雙擊啟動器（CLI 模式）
├── run_menubar.command        # macOS 雙擊啟動器（Menubar 模式）
└── setup.py                   # 原始套件安裝
```

## 關鍵限制 & 注意事項

1. **macOS 必須在 repo root 執行**：`LightningWhisperMLX` 使用 `./mlx_models/` 相對路徑存放模型（`lightning.py:79-91`），`asr_engine.py` 會自動 `os.chdir()` 到 repo root
2. **macOS：Apple Silicon 限定**：MLX 框架僅支援 arm64
3. **macOS：需要 ffmpeg**：ASR 音訊載入依賴 ffmpeg
4. **預設模型**：macOS `small` + `language="zh"`；iOS 使用 Apple Speech（`zh-TW`）
5. **iOS deployment target**：iOS 17.0+（支援 iPhone 14 Pro 及以上）
6. **iOS 簽名**：使用 Personal Team（`F287UM4MK5`），bundle ID `com.voiceinput.app`

## 額外相依套件（macOS voice_input 需要）

- `sounddevice` — 麥克風錄音
- `PyYAML` — 設定檔解析
- `openai` — xAI Grok API 客戶端（OpenAI 相容格式）
- `python-dotenv` — `.env` 檔案載入
- `rumps` — macOS Menubar App 框架（Menubar 模式需要）
- 不需要 pyperclip，直接用 macOS 內建 `pbcopy`

## 常用指令

```bash
# 一鍵安裝 + 啟動
bash install_and_run.sh

# 手動執行（已安裝情況下）
python -m voice_input.main

# 啟動 Menubar 常駐模式（免終端機操作）
python -m voice_input.menubar_main

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

# iOS build（需要 Xcode）
xcodebuild -project ios-app/VoiceInput/VoiceInput.xcodeproj -scheme VoiceInput \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' build

# iOS 安裝到實機（替換 DEVICE_ID）
xcrun devicectl device install app --device DEVICE_ID \
  ~/Library/Developer/Xcode/DerivedData/VoiceInput-*/Build/Products/Debug-iphoneos/VoiceInput.app
```

## 資料流

### macOS
```
麥克風 → WAV temp file → LightningWhisperMLX.transcribe() → raw_text
→ [LLM 路徑] Grok API 一次完成修正錯字+標點+去口頭禪+潤飾 → final_text
→ [規則 fallback] 移除口頭禪 → 去重複 → 加標點 → 換行 → final_text
→ pbcopy + 通知 + 自動貼上（Cmd+V）
```

### iOS
```
麥克風 → Apple Speech (SFSpeechRecognizer) → raw_text
→ [LLM 路徑] Grok API 修飾 → final_text
→ UIPasteboard
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
- **Thread safety**：`_get_client()` 使用 `threading.Lock` 保護全域 client 快取

### 上下文感知（`--context`）

指定領域讓 LLM 更準確推斷同音錯字和專業術語：

| `--context` | 效果範例 |
|-------------|---------|
| `"醫學研究"` | 「口號研究」→「世代研究（Cohort Study）」 |
| `"軟體開發"` | 「城市」→「程式」、「愛批愛」→「API」 |
| `"財務報告"` | 「應收帳款」「毛利率」等術語正確辨識 |
| （空）| 無領域偏好，通用處理 |

### 輸出風格（`--style`）

| `--style` | 說明 |
|-----------|------|
| `professional`（預設）| 專業書面語，語氣正式 |
| `concise` | 極度精簡，只留核心 |
| `bullet` | 條列式要點 |
| `casual` | 口語親切風格 |

## Git Remote

- `origin` → `mustafaaljadery/lightning-whisper-mlx`（上游，唯讀）
- `my-repo` → `zinojeng/mlx-whisper`（fork，push 用這個）
