#!/usr/bin/env bash
# install_and_run.sh — 一鍵安裝並啟動語音輸入系統
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "  macOS 語音輸入系統 — 安裝腳本"
echo "=================================================="
echo

# 1. 檢查 Apple Silicon
if [[ "$(uname -m)" != "arm64" ]]; then
    echo "⚠️  警告：此程式針對 Apple Silicon (arm64) 設計，目前偵測到 $(uname -m)"
    echo "    MLX 框架可能無法正常運作"
    echo
fi

# 2. 檢查 / 安裝 Homebrew
if ! command -v brew &>/dev/null; then
    echo "正在安裝 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "✅ Homebrew 已安裝"
fi

# 3. 檢查 / 安裝 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "正在安裝 ffmpeg..."
    brew install ffmpeg
else
    echo "✅ ffmpeg 已安裝"
fi

# 4. 檢查 / 安裝 Python 3
if ! command -v python3 &>/dev/null; then
    echo "正在安裝 Python 3..."
    brew install python@3.11
else
    echo "✅ Python 3 已安裝 ($(python3 --version))"
fi

# 5. 建立虛擬環境
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "正在建立虛擬環境..."
    python3 -m venv "$VENV_DIR"
else
    echo "✅ 虛擬環境已存在"
fi

# 啟動虛擬環境
source "$VENV_DIR/bin/activate"

# 6. 安裝套件
echo "正在安裝相依套件..."
pip install --upgrade pip --quiet
pip install -e "$SCRIPT_DIR" --quiet
pip install sounddevice PyYAML --quiet
echo "✅ 套件安裝完成"

echo
echo "=================================================="
echo "  安裝完成，啟動語音輸入系統"
echo "=================================================="
echo

# 7. 啟動
python -m voice_input.main "$@"
