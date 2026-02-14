"""CLI 進入點 — 語音輸入主程式。"""

import argparse
import logging
import sys

from .config import load_config
from .app_controller import AppController


def parse_args():
    parser = argparse.ArgumentParser(description="macOS 語音輸入系統 (基於 lightning-whisper-mlx)")
    parser.add_argument("--config", type=str, default=None,
                        help="自訂設定檔路徑 (YAML)")
    parser.add_argument("--model", type=str, default=None,
                        help="ASR 模型名稱 (tiny/base/small/medium/large)")
    parser.add_argument("--quant", type=str, default=None,
                        help="量化模式 (4bit/8bit)")
    parser.add_argument("--language", type=str, default=None,
                        help="語言代碼 (預設: zh)")
    parser.add_argument("--debug", action="store_true",
                        help="啟用 debug 模式")
    parser.add_argument("--no-llm", action="store_true",
                        help="停用 LLM 後處理，僅使用規則管線")
    parser.add_argument("--context", type=str, default=None,
                        help="領域上下文 (如「醫學研究」「軟體開發」「財務報告」)")
    parser.add_argument("--style", type=str, default=None,
                        choices=["professional", "concise", "bullet", "casual"],
                        help="輸出風格 (預設: professional)")
    return parser.parse_args()


def main():
    args = parse_args()

    # 載入設定
    config = load_config(args.config)

    # CLI 參數覆蓋設定檔
    if args.model:
        config.asr.model = args.model
    if args.quant:
        config.asr.quant = args.quant
    if args.language:
        config.asr.language = args.language
    if args.debug:
        config.log_level = "DEBUG"
    if args.no_llm:
        config.llm.enabled = False
    if args.context:
        config.llm.context = args.context
    if args.style:
        config.llm.style = args.style

    # 設定 logging
    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # LLM 狀態
    if config.llm.enabled and config.llm.api_key:
        llm_status = f"ON ({config.llm.model})"
    elif config.llm.enabled and not config.llm.api_key:
        llm_status = "OFF (未設定 API Key)"
    else:
        llm_status = "OFF"

    print("=" * 50)
    print("  macOS 語音輸入系統 v0.1")
    print(f"  模型: {config.asr.model} | 語言: {config.asr.language}")
    print(f"  LLM 後處理: {llm_status}")
    if config.llm.enabled and config.llm.api_key:
        print(f"  風格: {config.llm.style}", end="")
        if config.llm.context:
            print(f" | 上下文: {config.llm.context}", end="")
        print()
    print("=" * 50)
    print()

    # 初始化
    controller = AppController(config)
    print("正在載入模型，請稍候...")
    try:
        controller.initialize()
    except Exception as e:
        print(f"模型載入失敗: {e}")
        sys.exit(1)
    print("模型載入完成！")
    print()

    # 主迴圈
    print("使用方式：按 Enter 開始錄音 → 再按 Enter 停止 → 自動轉錄")
    print("按 Ctrl+C 退出")
    print()

    try:
        while True:
            input("按 Enter 開始錄音...")
            controller.start_recording()
            print("🎙 錄音中... 按 Enter 停止")

            input()

            print("處理中...")
            try:
                result = controller.stop_recording_and_process()
                if result:
                    print()
                    print("─" * 40)
                    print(result)
                    print("─" * 40)
                    print("✅ 已複製到剪貼簿")
                else:
                    print("（未偵測到語音）")
            except Exception as e:
                print(f"錯誤: {e}")

            controller.reset()
            print()

    except KeyboardInterrupt:
        print("\n\n正在退出...")
        controller.reset()
        print("再見！")
        sys.exit(0)


if __name__ == "__main__":
    main()
