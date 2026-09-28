#!/usr/bin/env bash
# Fetch the Real-ESRGAN ncnn-vulkan binary + models next to render.py (macOS build; ~70 MB).
# render.py uses it to upscale anime stills and small museum scans to 4K.
set -euo pipefail
cd "$(dirname "$0")"
[ -x esr/realesrgan-ncnn-vulkan ] && { echo "esr already installed"; exit 0; }
curl -sL -o esr.zip https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip
unzip -qo esr.zip -d esr && rm esr.zip
chmod +x esr/realesrgan-ncnn-vulkan
xattr -dr com.apple.quarantine esr 2>/dev/null || true
echo "installed esr/realesrgan-ncnn-vulkan"
