# macOS 語音輸入系統 v0.1 — 開發進度

## 實作進度

| 步驟 | 項目 | 狀態 | 說明 |
|------|------|------|------|
| Step 1 | `config_default.yaml` + `__init__.py` | ✅ 完成 | YAML 設定檔含 asr/audio/postprocess/delivery/llm/logging 區塊 |
| Step 2 | `voice_input/config.py` | ✅ 完成 | 6 個 dataclass（含 LLMConfig）+ `load_config()` 含 deep-merge + .env |
| Step 3 | `voice_input/audio_capture.py` | ✅ 完成 | sounddevice InputStream，thread-safe，輸出 16kHz WAV |
| Step 4 | `voice_input/asr_engine.py` | ✅ 完成 | lazy-load LightningWhisperMLX，自動切換 CWD |
| Step 5 | `voice_input/postprocess.py` | ✅ 完成 | LLM 優先 → 規則 fallback（去口頭禪→去重複→加標點→換行） |
| Step 6 | `voice_input/llm_refine.py` | ✅ 完成 | xAI Grok API 文字修飾，client 快取，None 防護 |
| Step 7 | `voice_input/delivery.py` | ✅ 完成 | pbcopy 剪貼簿 + osascript 通知 |
| Step 8 | `voice_input/app_controller.py` | ✅ 完成 | 7 狀態狀態機，含錯誤處理，傳遞 llm_config |
| Step 9 | `voice_input/main.py` | ✅ 完成 | argparse CLI（含 --no-llm），LLM 狀態顯示，繁體中文 UI |
| Step 10 | `install_and_run.sh` + `.command` | ✅ 完成 | brew/ffmpeg/venv 自動安裝，雙擊啟動 |

## 驗證清單

| 項目 | 狀態 | 備註 |
|------|------|------|
| Python 語法檢查（全部 8 個檔案） | ✅ 通過 | `py_compile` 驗證無語法錯誤 |
| 腳本執行權限 | ✅ 設定 | `install_and_run.sh` 和 `.command` 已 `chmod +x` |
| `bash install_and_run.sh` 安裝無錯誤 | ⬜ 待測 | 需要實機測試 |
| 按 Enter 錄音 / 停止 / 轉錄 | ⬜ 待測 | 需要麥克風 + 模型下載 |
| 辨識結果含標點、無口頭禪 | ⬜ 待測 | postprocess 管線已實作 |
| 剪貼簿貼上結果 | ⬜ 待測 | pbcopy 已整合 |
| macOS 通知彈出 | ⬜ 待測 | osascript 已整合 |
| Ctrl+C 優雅退出 | ⬜ 待測 | KeyboardInterrupt handler 已實作 |
| `--model tiny` 參數覆蓋 | ⬜ 待測 | argparse 已實作 |

## 已建立的檔案

### 新增檔案（13 個）
- `voice_input/__init__.py`
- `voice_input/config.py`
- `voice_input/audio_capture.py`
- `voice_input/asr_engine.py`
- `voice_input/postprocess.py`
- `voice_input/llm_refine.py`
- `voice_input/delivery.py`
- `voice_input/app_controller.py`
- `voice_input/main.py`
- `config_default.yaml`
- `.env`（範本，不入版控）
- `install_and_run.sh`
- `run_voice_input.command`

### 未修改的檔案
- 原始 `lightning_whisper_mlx/` 套件未做任何更動
- `setup.py` 未做任何更動

## 下一步

1. 實機測試完整流程（安裝 → 錄音 → 轉錄 → 剪貼簿）
2. 設定真實 `XAI_API_KEY` 測試 LLM 後處理路徑
3. 測試 `--no-llm` 與無 API Key 時的 fallback 行為
4. 根據實測結果調整 postprocess 規則 / LLM prompt
5. 考慮加入 VAD（語音活動偵測）自動停止錄音
6. 考慮加入更多語言支援
