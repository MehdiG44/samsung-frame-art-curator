#!/usr/bin/env bash
# One-shot, idempotent setup for the samsung-frame-tv-art skill. Safe to re-run any time.
# Installs what is missing, pairs with the TV, and ends with one line per check:  OK|TODO|FAIL <check> <detail>
# An agent should run this first and act on every non-OK line.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="$HOME/.config/frame-tv"; mkdir -p "$CFG"
report=()
ok()   { report+=("OK   $1 $2"); }
todo() { report+=("TODO $1 $2"); }
fail() { report+=("FAIL $1 $2"); }

# 1. tools: uv (runs frame.py), ImageMagick, libvips
for t in uv magick vips; do
  if ! command -v $t >/dev/null; then
    pkg=$t; [ $t = magick ] && pkg=imagemagick
    if command -v brew >/dev/null; then brew install -q $pkg >/dev/null 2>&1; fi
  fi
  command -v $t >/dev/null && ok "tool:$t" "$(command -v $t)" || fail "tool:$t" "install it (macOS: brew install $pkg)"
done

# 2. AI upscaler (optional but used for anime stills and small museum scans)
"$HERE/install_esr.sh" >/dev/null 2>&1 && ok upscaler "$HOME/.local/share/frame-tv/esr" || todo upscaler "run install_esr.sh; without it small images are upscaled plainly"

# 3. project dir
[ -f "$CFG/project" ] || echo "$HOME/frame-tv-art" > "$CFG/project"
P="$(eval echo "$(cat "$CFG/project")")"; mkdir -p "$P"
ok project "$P"

# 4. taste file
[ -f "$CFG/taste.md" ] && ok taste "$CFG/taste.md" || todo taste "ask the human one question (what they love, and for whom), then write $CFG/taste.md from $HERE/../taste.example.md"

# 5. TV: discover if no address yet, then a real round-trip (may pop an Allow prompt on the TV)
if [ -z "${FRAME_TV_HOST:-}" ] && [ ! -s "$CFG/host" ]; then "$HERE/frame.py" discover >/dev/null 2>&1; fi
if [ -n "${FRAME_TV_HOST:-}" ] || [ -s "$CFG/host" ]; then
  H="${FRAME_TV_HOST:-$(cat "$CFG/host")}"
  if out=$("$HERE/frame.py" status 2>&1); then
    ok tv "$H $(echo "$out" | grep -E '^my photos' | sed 's/  */ /g')"
  else
    fail tv "$H did not answer the art API. Likely causes, in order: this machine is not on the TV's network (check with the human); the TV is fully off (Art Mode is fine); an 'Allow' prompt is waiting on the TV (ask the human to press Allow with the remote); the TV changed IP (delete $CFG/host and re-run). Then re-run setup.sh. Last error: $(echo "$out" | tail -1)"
  fi
else
  fail tv "no Frame found on this network. The Mac must be on the same Wi-Fi/LAN as the TV and the TV must be on (Art Mode counts). Or set FRAME_TV_HOST=<ip>."
fi
printf '%s\n' "${report[@]}"
