#!/usr/bin/env bash
# Fetch the Real-ESRGAN ncnn-vulkan binary + models (~70 MB) into ~/.local/share/frame-tv/esr.
# Kept outside the skill folder so skill updates never delete it. render.py finds it there.
set -euo pipefail
DEST="${FRAME_ESR_DIR:-$HOME/.local/share/frame-tv/esr}"
[ -x "$DEST/realesrgan-ncnn-vulkan" ] && { echo "esr: already installed at $DEST"; exit 0; }
case "$(uname -s)" in
  Darwin) ZIP=realesrgan-ncnn-vulkan-20220424-macos.zip ;;
  Linux)  ZIP=realesrgan-ncnn-vulkan-20220424-ubuntu.zip ;;
  *) echo "esr: unsupported OS $(uname -s); render.py will skip AI upscaling" >&2; exit 1 ;;
esac
mkdir -p "$DEST"; TMP=$(mktemp -d)
curl -sfL -o "$TMP/esr.zip" "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/$ZIP"
unzip -qo "$TMP/esr.zip" -d "$DEST" && rm -rf "$TMP"
chmod +x "$DEST/realesrgan-ncnn-vulkan"
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
echo "esr: installed at $DEST"
