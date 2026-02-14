#!/bin/bash
# run_menubar.command — macOS 雙擊啟動 Menubar App
# 在 Finder 中雙擊此檔案即可啟動語音輸入 Menubar 常駐程式

cd "$(dirname "$0")"
source .venv/bin/activate
python -m voice_input.menubar_main
