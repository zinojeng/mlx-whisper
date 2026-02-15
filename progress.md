# 語音輸入系統 — 開發進度

## Phase 1：macOS CLI 語音輸入 ✅

| 項目 | 狀態 | 說明 |
|------|------|------|
| `config_default.yaml` + `__init__.py` | ✅ 完成 | YAML 設定檔含 asr/audio/postprocess/delivery/llm/logging 區塊 |
| `voice_input/config.py` | ✅ 完成 | 6 個 dataclass（含 LLMConfig）+ `load_config()` 含 deep-merge + .env |
| `voice_input/audio_capture.py` | ✅ 完成 | sounddevice InputStream，thread-safe，輸出 16kHz WAV |
| `voice_input/asr_engine.py` | ✅ 完成 | lazy-load LightningWhisperMLX，自動切換 CWD |
| `voice_input/postprocess.py` | ✅ 完成 | LLM 優先 → 規則 fallback，regex 預編譯 |
| `voice_input/llm_refine.py` | ✅ 完成 | xAI Grok API 文字修飾，client 快取 + threading.Lock |
| `voice_input/delivery.py` | ✅ 完成 | pbcopy 剪貼簿 + osascript 通知 |
| `voice_input/app_controller.py` | ✅ 完成 | 7 狀態狀態機，含錯誤處理 |
| `voice_input/main.py` | ✅ 完成 | argparse CLI（含 --no-llm / --context / --style） |
| `install_and_run.sh` + `.command` | ✅ 完成 | brew/ffmpeg/venv 自動安裝，雙擊啟動 |

## Phase 2：macOS Menubar App ✅

| 項目 | 狀態 | 說明 |
|------|------|------|
| `voice_input/menubar_app.py` | ✅ 完成 | rumps Menubar 常駐 App，右 Option push-to-talk |
| `voice_input/menubar_main.py` | ✅ 完成 | Menubar 進入點 |
| `run_menubar.command` | ✅ 完成 | macOS 雙擊啟動器 |
| 熱鍵 push-to-talk | ✅ 完成 | 右側 Option 鍵按住錄音、放開轉錄 |
| 自動貼上（Cmd+V） | ✅ 完成 | 轉錄完成後自動貼上到當前視窗 |
| Context / Style 選單 | ✅ 完成 | Menubar 選單切換領域上下文和輸出風格 |
| API Key 管理 | ✅ 完成 | 首次啟動提示輸入，存入 .env |
| Thread safety | ✅ 完成 | `_hotkey_lock` 保護 `_hotkey_held` / `_recording` / `_processing` |

## Phase 3：iOS App ✅

| 項目 | 狀態 | 說明 |
|------|------|------|
| `VoiceInputApp.swift` | ✅ 完成 | SwiftUI App 進入點 |
| `ContentView.swift` | ✅ 完成 | Push-to-talk 按鈕（LongPressGesture 0.2s 最短按住時間） |
| `VoiceInputViewModel.swift` | ✅ 完成 | Apple Speech 錄音/辨識，isFinal 處理，AVAudioSession 相容 API |
| `GrokService.swift` | ✅ 完成 | xAI Grok API，HTTP 401/429/5xx 分類錯誤處理 |
| `SettingsView.swift` | ✅ 完成 | API Key / Context / Style / Language 設定頁 |
| `Assets.xcassets` | ✅ 完成 | AppIcon + AccentColor asset catalog |
| `project.pbxproj` | ✅ 完成 | Resources build phase，asset catalog 編譯設定 |
| `Info.plist` | ✅ 完成 | 麥克風 + 語音辨識權限宣告 |
| Simulator build | ✅ 通過 | iPhone 17 Pro Simulator (iOS 26.2) BUILD SUCCEEDED |
| 實機 build | ✅ 通過 | iPhone 14 Pro (Ander's iPhone) BUILD SUCCEEDED + 已安裝 |

## 程式碼品質改善紀錄

| 日期 | commit | 改動 |
|------|--------|------|
| 2025-xx | `bef1013` | Codex review 修正：recording flag、thread safety、escaping |
| 2025-xx | `e0f7e6d` | iOS build 修正 + macOS/iOS 程式碼品質改善（10 項） |

### e0f7e6d 詳細內容
- **A1** Assets.xcassets 建立（Contents.json + AccentColor + AppIcon）
- **A2** project.pbxproj 加 Resources build phase + asset catalog 設定
- **A3** `AVAudioApplication.requestRecordPermission()` → `AVAudioSession` 相容寫法
- **A4** Speech recognition task 加 error logging + isFinal 處理
- **A5** GrokService HTTP 錯誤分類（401/429/5xx）
- **A6** Push-to-talk 改用 `LongPressGesture(minimumDuration: 0.2)` 防誤觸
- **B1** `menubar_app.py` 加 `threading.Lock` 保護共享狀態
- **B2** `audio_capture.py` stream 建立失敗時正確 cleanup
- **B3** `llm_refine.py` OpenAI client 加 `threading.Lock`
- **B4** `postprocess.py` regex 預編譯移至 `__init__`

## 驗證清單

| 項目 | 狀態 | 備註 |
|------|------|------|
| Python 語法檢查（全部模組） | ✅ 通過 | import 測試全部通過 |
| macOS menubar import 測試 | ✅ 通過 | `from voice_input.menubar_app import VoiceInputMenuBarApp` |
| postprocess regex 預編譯測試 | ✅ 通過 | 10 patterns pre-compiled，filler removal 正常 |
| llm_refine threading.Lock 測試 | ✅ 通過 | `_client_lock` 型別驗證 |
| iOS Simulator build | ✅ 通過 | 0 errors, 0 warnings |
| iOS 實機 build + 安裝 | ✅ 通過 | iPhone 14 Pro, bundle: com.voiceinput.app |
| iOS 實機語音辨識測試 | ⬜ 待測 | 需要在 iPhone 上實際操作 |
| iOS LLM 後處理測試 | ⬜ 待測 | 需要在設定頁輸入 API Key |
| macOS menubar 完整流程測試 | ⬜ 待測 | 需要實機測試 |

## 下一步

1. **iOS 實機測試**：在 iPhone 上打開 App 測試語音辨識 + LLM 後處理完整流程
2. **Unit Tests**：`postprocess.py` 規則管線 + `llm_refine.py` prompt 組裝
3. **iOS XCTest**：GrokService HTTP error handling + ViewModel 狀態流轉
4. **CI/CD**：GitHub Actions 跑 xcodebuild + pytest
5. **功能擴展**：iOS Widget / Live Activity、CloudKit 設定同步、Whisper on-device (whisper.cpp)
