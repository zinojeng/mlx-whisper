"""結果傳遞 — 剪貼簿複製 + macOS 通知。"""

import logging
import subprocess

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str) -> bool:
    """使用 pbcopy 將文字複製到剪貼簿。"""
    try:
        subprocess.run(
            ["pbcopy"],
            input=text.encode("utf-8"),
            check=True,
            timeout=5,
        )
        logger.info("已複製到剪貼簿 (%d 字元)", len(text))
        return True
    except Exception as e:
        logger.error("複製到剪貼簿失敗: %s", e)
        return False


def _escape_applescript(s: str) -> str:
    """跳脫 AppleScript 雙引號字串中的特殊字元。"""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def show_notification(title: str, message: str) -> bool:
    """使用 osascript 顯示 macOS 通知。"""
    safe_title = _escape_applescript(title)
    safe_message = _escape_applescript(message)
    script = (
        f'display notification "{safe_message}" '
        f'with title "{safe_title}"'
    )
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            timeout=5,
            capture_output=True,
        )
        logger.debug("已顯示通知: %s", title)
        return True
    except Exception as e:
        logger.warning("顯示通知失敗: %s", e)
        return False


def deliver(text: str, clipboard: bool = True, notification: bool = True) -> None:
    """組合傳遞：複製到剪貼簿 + 顯示通知。"""
    if clipboard:
        copy_to_clipboard(text)
    if notification:
        preview = text[:50] + ("..." if len(text) > 50 else "")
        show_notification("語音輸入完成", preview)
