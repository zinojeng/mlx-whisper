"""macOS Menubar 常駐 App — 從選單列操作錄音和轉錄。"""

import logging
import os
import threading
from pathlib import Path

import time

import rumps
from AppKit import NSEvent, NSFlagsChangedMask
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventSetFlags,
    CGEventPost,
    kCGHIDEventTap,
    kCGEventFlagMaskCommand,
)

from .config import AppConfig
from .app_controller import AppController

logger = logging.getLogger(__name__)

# 狀態圖示
ICON_IDLE = "🎤"
ICON_RECORDING = "🎙"
ICON_PROCESSING = "⏳"
ICON_INIT = "⚙"

# Context 選項
CONTEXT_OPTIONS = ["", "醫學研究", "軟體開發", "財務報告"]
CONTEXT_LABELS = {"": "無", "醫學研究": "醫學研究", "軟體開發": "軟體開發", "財務報告": "財務報告"}

# Style 選項
STYLE_OPTIONS = ["professional", "concise", "bullet", "casual"]
STYLE_LABELS = {
    "professional": "Professional",
    "concise": "Concise",
    "bullet": "Bullet",
    "casual": "Casual",
}

# Hotkey: Right Option (push-to-talk)
_RIGHT_OPTION_KEYCODE = 61
_OPTION_FLAG = 1 << 19  # NSAlternateKeyMask / NSEventModifierFlagOption

# Auto-paste: Cmd+V keyCode
_V_KEYCODE = 9

# .env 路徑（repo root）
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _simulate_paste() -> None:
    """模擬 Cmd+V 貼上到當前使用中的視窗。"""
    time.sleep(0.05)  # 等待剪貼簿就緒
    # Key down
    event_down = CGEventCreateKeyboardEvent(None, _V_KEYCODE, True)
    CGEventSetFlags(event_down, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event_down)
    # Key up
    event_up = CGEventCreateKeyboardEvent(None, _V_KEYCODE, False)
    CGEventSetFlags(event_up, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event_up)


def _save_api_key_to_env(api_key: str) -> None:
    """將 API Key 寫入 .env 檔（新增或更新 XAI_API_KEY）。"""
    lines = []
    found = False
    if _ENV_PATH.exists():
        lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("XAI_API_KEY="):
                lines[i] = f"XAI_API_KEY={api_key}"
                found = True
                break
    if not found:
        lines.append(f"XAI_API_KEY={api_key}")
    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _prompt_api_key(title: str = "設定 API Key",
                    message: str = "請輸入 xAI (Grok) API Key：") -> str:
    """顯示輸入視窗，回傳使用者輸入的 key（可能為空）。"""
    window = rumps.Window(
        message=message,
        title=title,
        default_text="",
        ok="儲存",
        cancel="跳過",
        dimensions=(320, 24),
    )
    resp = window.run()
    return resp.text.strip() if resp.clicked == 1 else ""


class VoiceInputMenuBarApp(rumps.App):
    """語音輸入 Menubar App。"""

    def __init__(self, config: AppConfig):
        super().__init__(ICON_INIT, quit_button=None)
        self.config = config
        self.controller = AppController(config)
        self._recording = False
        self._processing = False
        self._hotkey_monitor = None
        self._hotkey_held = False  # push-to-talk 狀態
        self._auto_paste = True  # 自動貼上到當前視窗

        # --- 選單建構 ---
        self.record_button = rumps.MenuItem(
            "Start Recording  (hold R⌥)", callback=self._toggle_recording)

        # Context 子選單
        self.context_menu = rumps.MenuItem("Context")
        self._context_items = {}
        for ctx in CONTEXT_OPTIONS:
            label = CONTEXT_LABELS[ctx]
            item = rumps.MenuItem(label, callback=self._make_context_callback(ctx))
            if ctx == config.llm.context:
                item.state = 1
            self._context_items[ctx] = item
            self.context_menu.add(item)

        # Style 子選單
        self.style_menu = rumps.MenuItem("Style")
        self._style_items = {}
        for style in STYLE_OPTIONS:
            label = STYLE_LABELS[style]
            item = rumps.MenuItem(label, callback=self._make_style_callback(style))
            if style == config.llm.style:
                item.state = 1
            self._style_items[style] = item
            self.style_menu.add(item)

        # LLM 開關
        llm_on = config.llm.enabled and bool(config.llm.api_key)
        self.llm_toggle = rumps.MenuItem(
            f"LLM 後處理 {'ON' if llm_on else 'OFF'}",
            callback=self._toggle_llm,
        )

        # 自動貼上開關
        self.paste_toggle = rumps.MenuItem(
            "自動貼上 ON", callback=self._toggle_auto_paste)

        # API Key 設定
        api_key_button = rumps.MenuItem("Set API Key...", callback=self._set_api_key)

        quit_button = rumps.MenuItem("Quit", callback=self._quit)

        self.menu = [
            self.record_button,
            None,
            self.context_menu,
            self.style_menu,
            self.llm_toggle,
            self.paste_toggle,
            api_key_button,
            None,
            quit_button,
        ]

        # 背景初始化模型 + API Key 檢查
        timer = rumps.Timer(self._init_model, 0.5)
        timer.start()

    # --- 模型初始化 + API Key 首次設定 ---

    def _init_model(self, timer):
        """one-shot Timer callback：檢查 API Key → 背景載入模型。"""
        timer.stop()

        # 首次啟動若無 API Key，彈出輸入框
        if not self.config.llm.api_key:
            self._prompt_and_save_key(
                title="首次設定 API Key",
                message="未偵測到 xAI API Key。\n請輸入 API Key 以啟用 LLM 後處理（可稍後從選單設定）：",
            )

        try:
            logger.info("Menubar: 正在載入模型...")
            self.controller.initialize()
            logger.info("Menubar: 模型載入完成")
            self.title = ICON_IDLE
        except Exception as e:
            logger.error("模型載入失敗: %s", e)
            rumps.notification("語音輸入", "模型載入失敗", str(e))
            self.title = ICON_IDLE

        # 模型載入完成後註冊全域熱鍵
        self._register_hotkey()

    # --- API Key 管理 ---

    def _prompt_and_save_key(self, title="設定 API Key",
                             message="請輸入 xAI (Grok) API Key："):
        """彈出輸入框，儲存 key 到 .env 並更新 runtime config。"""
        key = _prompt_api_key(title=title, message=message)
        if key:
            _save_api_key_to_env(key)
            self.config.llm.api_key = key
            self.controller.postprocessor.llm_config.api_key = key
            os.environ["XAI_API_KEY"] = key
            self._update_llm_label()
            logger.info("API Key 已更新並儲存至 .env")
            rumps.notification("語音輸入", "API Key 已儲存", "LLM 後處理已啟用")

    def _set_api_key(self, sender):
        """選單：Set API Key...。"""
        self._prompt_and_save_key()

    def _update_llm_label(self):
        """更新 LLM 選單文字。"""
        on = self.config.llm.enabled and bool(self.config.llm.api_key)
        self.llm_toggle.title = f"LLM 後處理 {'ON' if on else 'OFF'}"

    # --- 全域熱鍵 (Right ⌥) Push-to-Talk ---

    def _register_hotkey(self):
        """註冊右側 Option 鍵 push-to-talk：按住錄音，放開轉錄。"""
        def handler(event):
            if event.keyCode() != _RIGHT_OPTION_KEYCODE:
                return
            # 按下右 Option → 開始錄音
            if event.modifierFlags() & _OPTION_FLAG and not self._hotkey_held:
                self._hotkey_held = True
                rumps.Timer(lambda t: (t.stop(), self._hotkey_start()), 0).start()
            # 放開右 Option → 停止錄音
            elif not (event.modifierFlags() & _OPTION_FLAG) and self._hotkey_held:
                self._hotkey_held = False
                rumps.Timer(lambda t: (t.stop(), self._hotkey_stop()), 0).start()

        self._hotkey_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSFlagsChangedMask, handler
        )
        logger.info("全域熱鍵已註冊: 右側 Option (push-to-talk)")

    def _hotkey_start(self):
        """熱鍵按下：開始錄音。"""
        if not self._recording and not self._processing:
            self._start_recording()

    def _hotkey_stop(self):
        """熱鍵放開：停止錄音並轉錄。"""
        if self._recording:
            self._stop_recording()

    # --- 錄音控制 ---

    def _toggle_recording(self, sender):
        """切換錄音狀態。"""
        if self._processing:
            return

        if not self._recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        """開始錄音。"""
        try:
            self.controller.start_recording()
            self._recording = True
            self.title = ICON_RECORDING
            self.record_button.title = "Stop Recording  (hold R⌥)"
        except Exception as e:
            logger.error("開始錄音失敗: %s", e)
            rumps.notification("語音輸入", "錄音失敗", str(e))

    def _stop_recording(self):
        """停止錄音並在背景執行轉錄。"""
        self._recording = False
        self._processing = True
        self.title = ICON_PROCESSING
        self.record_button.title = "Processing..."

        thread = threading.Thread(target=self._process_in_background, daemon=True)
        thread.start()

    def _process_in_background(self):
        """背景執行轉錄 + 後處理 + 剪貼簿 + 自動貼上（UI 更新交回主執行緒）。"""
        result = None
        error = None
        try:
            result = self.controller.stop_recording_and_process()
            if result and self._auto_paste:
                _simulate_paste()
        except Exception as e:
            logger.error("處理失敗: %s", e)
            error = e
        finally:
            self.controller.reset()
            # 所有 UI 更新交回主執行緒
            rumps.Timer(lambda t: (t.stop(), self._on_process_done(result, error)), 0).start()

    def _on_process_done(self, result, error):
        """主執行緒回呼：更新 UI 狀態。"""
        self._processing = False
        self.title = ICON_IDLE
        self.record_button.title = "Start Recording  (hold R⌥)"
        if error:
            rumps.notification("語音輸入", "處理失敗", str(error))
        elif result:
            preview = result[:80] + ("..." if len(result) > 80 else "")
            rumps.notification("語音輸入完成", "已複製到剪貼簿", preview)
        else:
            rumps.notification("語音輸入", "未偵測到語音", "")

    # --- Context 切換 ---

    def _make_context_callback(self, ctx):
        def callback(sender):
            self._set_context(ctx)
        return callback

    def _set_context(self, ctx):
        for key, item in self._context_items.items():
            item.state = 1 if key == ctx else 0
        self.config.llm.context = ctx
        self.controller.postprocessor.llm_config.context = ctx
        logger.info("Context 切換為: %s", ctx or "(無)")

    # --- Style 切換 ---

    def _make_style_callback(self, style):
        def callback(sender):
            self._set_style(style)
        return callback

    def _set_style(self, style):
        for key, item in self._style_items.items():
            item.state = 1 if key == style else 0
        self.config.llm.style = style
        self.controller.postprocessor.llm_config.style = style
        logger.info("Style 切換為: %s", style)

    # --- 自動貼上開關 ---

    def _toggle_auto_paste(self, sender):
        self._auto_paste = not self._auto_paste
        self.paste_toggle.title = f"自動貼上 {'ON' if self._auto_paste else 'OFF'}"
        logger.info("自動貼上: %s", "ON" if self._auto_paste else "OFF")

    # --- LLM 開關 ---

    def _toggle_llm(self, sender):
        self.config.llm.enabled = not self.config.llm.enabled
        self._update_llm_label()
        self.controller.postprocessor.llm_config.enabled = self.config.llm.enabled
        on = self.config.llm.enabled and bool(self.config.llm.api_key)
        logger.info("LLM 後處理: %s", "ON" if on else "OFF")

    # --- 退出 ---

    def _quit(self, sender):
        if self._hotkey_monitor:
            NSEvent.removeMonitor_(self._hotkey_monitor)
        self.controller.reset()
        rumps.quit_application()
