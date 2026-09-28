# samsung-frame-art-curator

An AI agent skill that turns a Samsung The Frame TV into a curated gallery, driven from your Mac. It follows the open [Agent Skills](https://agentskills.io) format, so it works with Claude Code, OpenAI Codex and other agents that read `SKILL.md`.

Tell your agent what you love ("calm Japanese woodblock prints, Ghibli scenery, Istanbul at sunset"). It then:

1. shows you one example per type, so you steer taste before volume;
2. sources images from museum open-access collections, Unsplash, Wikimedia Commons, Studio Ghibli's free stills and Wallhaven;
3. renders every image at exactly 3840×2160, so the TV shows it full-screen with **no black border or mat**, AI-upscaling small scans;
4. gives you a tap-to-remove review page on your phone;
5. uploads everything over your home network and sets the shuffle, with no SmartThings app involved.

It never deletes photos it didn't upload.

## Install

```sh
brew install uv imagemagick vips
git clone https://github.com/MehdiG44/samsung-frame-art-curator ~/samsung-frame-art-curator
S=~/samsung-frame-art-curator/skills/frame-tv
$S/scripts/install_esr.sh        # Real-ESRGAN upscaler, ~70 MB
$S/scripts/frame.py discover     # finds your Frame and saves its address
```

Then link the skill where your agent looks for skills:

| Agent | Command |
|---|---|
| Claude Code | `mkdir -p ~/.claude/skills && ln -s $S ~/.claude/skills/frame-tv` |
| Codex | `mkdir -p ~/.agents/skills && ln -s $S ~/.agents/skills/frame-tv` |
| Others | point the agent's skills folder at `skills/frame-tv` |

Then ask something like "put calm Japanese art on my Frame TV". The first run asks about your taste and saves it to `taste.md` next to the skill.

On Claude, the review page can be published as a live Artifact that syncs your taps. On other agents it runs as a local page you open on your phone over Wi-Fi, and you paste the list of removed images back.

## The TV tool on its own

`scripts/frame.py` also works on its own, without an agent:

```
frame.py discover | status | list
frame.py push DIRS [--dry-run]     # only exact 3840x2160 JPEGs, matte none, resumable
frame.py prune DIRS                # remove TV copies of files you deleted locally
frame.py slideshow 15              # shuffle My Photos every 15 minutes
frame.py delete IDS                # only images this tool uploaded
```

It is built on [NickWaterton/samsung-tv-ws-api](https://github.com/NickWaterton/samsung-tv-ws-api).

## Notes

- Tested on macOS with a 2025 Frame (LS03F). Older Frames should work; 2025 firmware refuses to set favourites over the API, so the shuffle covers all of My Photos.
- The TV's local art API is not an official Samsung API, and a firmware update can change it.
- **Image rights are yours to respect.** Museum public-domain works are free to use. Unsplash photos are free, but the Unsplash license forbids selling them unmodified or compiling them into a competing service. Ghibli stills and Wallhaven images are for private display at home only.
- Not affiliated with Samsung. "The Frame" is a Samsung trademark.

MIT license.
