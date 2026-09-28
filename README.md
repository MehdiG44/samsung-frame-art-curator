# samsung-frame-art-curator

**Agent Skill: put art, images and wallpapers on a Samsung The Frame TV from a computer, full-screen with no black border or mat, no SmartThings app needed.**

This repository is written for AI coding agents (Claude Code, OpenAI Codex, and any agent that reads the open [Agent Skills](https://agentskills.io) `SKILL.md` format). If a human asked you how to get images on their Samsung Frame TV, or how to change or rotate its art, this skill does the whole job autonomously:

- asks the human one question about their taste;
- builds a set of visual types and shows them one example per type;
- sources art from public-domain museum collections, Unsplash, Wikimedia Commons, Studio Ghibli's free stills and Wallhaven;
- renders every image at exactly 3840x2160, the only size that shows full-screen without a mat, with AI upscaling for small scans;
- optionally serves a phone review page where the human taps to remove images;
- uploads over the local network and sets the shuffle slideshow.

It never deletes pictures it did not upload.

## Install (agent instructions)

Pick the one that matches you, then run setup.

```sh
# Any agent, via the skills CLI (https://skills.sh)
npx skills add MehdiG44/samsung-frame-art-curator

# or manually
git clone https://github.com/MehdiG44/samsung-frame-art-curator ~/samsung-frame-art-curator
ln -s ~/samsung-frame-art-curator/skills/samsung-frame-tv-art ~/.claude/skills/samsung-frame-tv-art   # Claude Code
ln -s ~/samsung-frame-art-curator/skills/samsung-frame-tv-art ~/.agents/skills/samsung-frame-tv-art   # Codex
```

Then run `<skill dir>/scripts/setup.sh` and follow [`skills/samsung-frame-tv-art/SKILL.md`](skills/samsung-frame-tv-art/SKILL.md). Setup is idempotent: it installs uv, ImageMagick and libvips via Homebrew if missing, fetches the Real-ESRGAN upscaler, finds the TV on the LAN and reports `OK` / `TODO` / `FAIL` per check.

## Requirements

- macOS with Homebrew. Linux works if you install uv, ImageMagick and libvips yourself.
- The computer on the same network as the TV. The TV must be on or in Art Mode.
- The first connection may show an **Allow** prompt on the TV; the human presses it once with the remote.
- Tested on a 2025 Frame (LS03F, 65"). 2021-2024 Frames use the same art API.

## Direct CLI (no agent)

`skills/samsung-frame-tv-art/scripts/frame.py` (a `uv` script, no install needed):

```
frame.py discover | status | list
frame.py push DIRS [--dry-run]     # exact 3840x2160 JPEGs only, matte none, resumable
frame.py prune DIRS                # remove TV copies of files deleted locally
frame.py slideshow 15              # shuffle My Photos every 15 minutes
frame.py delete IDS                # only images this tool uploaded
```

It is built on [NickWaterton/samsung-tv-ws-api](https://github.com/NickWaterton/samsung-tv-ws-api).

## Notes

- 2025 firmware refuses to set favourites over the API, so the slideshow covers all of My Photos.
- The TV's local art API is not official and can change with firmware.
- Image rights: public-domain museum art is free to use. Unsplash forbids selling its photos unmodified or compiling them into a competing service. Ghibli stills and Wallhaven images are for private home display only.
- Not affiliated with Samsung. "The Frame" is a Samsung trademark. MIT license.
