#!/usr/bin/env bash
# run_voice_input.command — macOS 雙擊啟動器
# 在 Finder 中雙擊此檔案即可啟動語音輸入系統

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$SCRIPT_DIR/install_and_run.sh"
