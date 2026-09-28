---
name: samsung-frame-tv-art
description: Put images, art, photos or wallpapers on a Samsung The Frame TV (Art Mode) from a computer, with no SmartThings phone app, and fix the black border or mat around uploaded pictures. Curates art from what the human loves (museum paintings, woodblock prints, anime, game art, travel photos), renders each image full-screen at exactly 3840x2160 with AI upscaling, uploads over the home network, and sets the shuffle slideshow. Use when someone asks how to get images on their Frame or Samsung TV, wants rotating art or wallpapers on it, complains about borders or mats in Art Mode, or wants to add, remove or change the art on the TV.
---

# Samsung Frame TV art

You can do this whole job alone, from a Mac (Linux works with small adaptations) on the same network as the TV. The human is needed for exactly three things:
1. one question about taste;
2. pressing **Allow** on the TV remote if a prompt appears the first time you connect;
3. optionally, removing pictures they dislike on the review page.

Everything else, decide yourself using the defaults below.

## Step 0: setup (every session; it's idempotent)
```
<skill>/scripts/setup.sh
```
It installs missing tools (uv, ImageMagick, libvips, via Homebrew), the AI upscaler, finds the TV and checks the connection. It prints one line per check: `OK`, `TODO` or `FAIL`. Act on every non-OK line; each one says what to do. When the TV line fails, relay the listed causes to the human in plain words.

User data lives outside the skill folder, so updating the skill never loses it:
- `~/.config/frame-tv/`: `host` (TV address), `token.txt` (pairing), `taste.md` (the human's taste and decisions; **read it first**), `project` (path of the project dir).
- Project dir, default `~/frame-tv-art`: `types.json`, `regions.json`, `reviewed.json`, `cand/`, `stage/final/<TYPE>/`, `stage/rejected/`, `review/`, `uploaded.json` (everything this skill put on the TV).

## Step 1: taste (only if `taste.md` is missing or the human wants something new)
Ask ONE short question, e.g. "What should the TV show? Places, art styles, games or shows you love, and who it's for?" Then write `taste.md` from `taste.example.md`, filling it with sensible defaults:
- calm and beautiful imagery;
- no text, logos, crowds or close-up faces;
- if two people give different tastes, split roughly 50/50 between them;
- the human approves the type sheet (step 2) but not every image.

Anything the human says later about taste or approval goes into `taste.md` immediately.

## Step 2: types
Turn the taste into 8-30 **types**, each a coherent visual family, e.g. "Hokusai & Hiroshige prints", "Kyoto temples in autumn", "Zelda landscapes". Give each a code: first letter = region (who or what it's for), then a number, like J01 or S07. Write them to `types.json` as `[code, label, source note, kind]`, where kind is `photo`, `print` or `anime`, and describe the regions in `regions.json`.

Render one example per type (`scripts/render.py`), put them on one labelled sheet (`scripts/sheet.py sheet.png 4 files...`), show it to the human and let them drop types by code. This single check is what makes the rest land. Never show the human hundreds of images to rate.

## Step 3: source ~7 images per type into `cand/<TYPE>/`
Pick the best source for each kind:
- **Museum art (public domain, best quality):**
  - Art Institute of Chicago API: POST `/api/v1/artworks/search`; IIIF `https://www.artic.edu/iiif/2/<image_id>/full/3000,/0/default.jpg`; send an `AIC-User-Agent` header. It caps works that are not public domain at 843px.
  - Minneapolis Institute of Art: 7-14k px scans at `img.artsmia.org/web_objects_cache/<Cache_Location>/<rendition>_full.jpg`, with values from `search.artsmia.org`. Strong for Japanese prints.
  - The Met (`collectionapi.metmuseum.org`, `isPublicDomain=true`), Rijksmuseum.
  - Wikimedia Commons: search `<q> filew:>2000 filemime:image/jpeg` in namespace 6. Send a User-Agent with a contact URL or full-size downloads keep failing with 429. Pace 3s and back off on 429. Check for 0-byte files.
- **Photos: Unsplash.**
  - Its internal search API `/napi/search/photos?query=...&per_page=30&orientation=landscape` works only from a real browser page on unsplash.com (Claude in Chrome, Playwright, any browser tool), not curl.
  - Keep `width >= 3600`, landscape, and rank by likes. Skip `plus.unsplash.com`.
  - Full-res: `https://images.unsplash.com/<raw path>?w=5120&q=90&fm=jpg&fit=max`. Keep credits.
- **Anime and game art:** `scripts/wallhaven.py cand/wh <TYPE> "query"...` returns native 4K 16:9, SFW only. Most results are character pin-ups or have logos, so keep scenery with small or no characters. Rights are a gray area: private home display only.
- **Studio Ghibli:** official free stills at `https://www.ghibli.jp/gallery/<film>NNN.jpg` (001-050, 1920x1038). Most are close-ups; the scenic films are Marnie, The Red Turtle, The Wind Rises, Poppy Hill and Arrietty. Use kind `anime`.
- For big sourcing jobs, run one sub-agent per source family in parallel.

Cull hard yourself: build sheets with `sheet.py` and look at them. Reject anything with text, watermarks, busy crowds, frames or gallery walls, colour charts, or portrait orientation.

## Step 4: render to `stage/final/<TYPE>/`
```
scripts/render.py photo|print|anime stage/final/<TYPE> cand/<TYPE>/*.jpg
```
- It does an attention-based cover crop to exactly 3840x2160.
- `print` shaves paper margins first (`PRINT_SHAVE`, default `90x88%`; `82x78%` for wide margins; `97x96%` if the scan is already cropped to the image).
- `anime` upscales 2x first; anything below 90% of 4K gets a 4x AI upscale.
- **Run only one render.py at a time.** It already runs 6 CPU jobs, and parallel GPU upscales have frozen a laptop.

Look at one sheet of the results. Any visible paper edge, border or bad crop gets re-rendered or dropped.

## Step 5: review page (optional unless `taste.md` says the human wants to approve)
`scripts/build_review.py` builds `review/index.html`, a phone-friendly page where a tap removes an image. It opens on what the human hasn't reviewed yet; list what they have seen in `reviewed.json` (type codes or `<TYPE>.<basename>` ids).
- **Any agent:** `python3 -m http.server 8765 --directory <project>/review` and give the human `http://<this machine's LAN IP>:8765`. They tap, press "Copy removed list" and paste it to you.
- **Claude with Artifacts:** publish `review/index.html` as an Artifact with `capabilities: {db: {}}`, `root` = the review dir and every `thumbs/*` file. Taps then sync live: read the `removed` collection, where doc id = `<TYPE>.<basename>`. Republish to the same URL later.
- Map ids to files with `review/id_map.json` and move removed files to `stage/rejected/`. Keep them: they tell you what to avoid next time.

## Step 6: put it on the TV
```
scripts/frame.py push stage/final --dry-run   # counts; refuses anything not exactly 3840x2160 JPEG
scripts/frame.py push stage/final             # ~7s/image, matte none, resumable, skips what's already there
scripts/frame.py slideshow 15                 # shuffle My Photos every 15 min
scripts/frame.py status                       # confirm: art mode, slideshow, counts
```
Run push in the background and report progress. Afterwards, tell the human in two lines what is on the TV (counts per type) and that they can ask you to remove anything.

## Hard rules
- **No border.** Only exact 3840x2160 JPEGs with matte `none`. Any other size makes the TV add a mat.
- **Never delete what you didn't upload.** My Photos holds the human's own pictures, and `uploaded.json` is the only list you may delete from. `frame.py delete` refuses other ids unless `--force`, and `--force` is only for ids the human named.
- **Keep the TV light:** at most ~300 images / ~1 GB. To add more, prune first (`frame.py prune stage/final` after removing files locally).
- **Don't change the TV while someone uses it:** if `status` shows art mode `nav`, don't `show` or switch modes.

## Known behaviour (2025 Frame, LS03F; older models mostly the same)
- **Favourites can't be set over the API on 2025 firmware** (`change_favorite` returns error -7). So the shuffle covers all of My Photos, including the human's own photos. Mention it once and record their answer in `taste.md`. On older models, `push --fav` plus `slideshow 15 --fav` isolates the art.
- `set_auto_rotation_status` fails on 2025 firmware; `set_slideshow_status` works. Slideshow category 2 = My Photos, 4 = Favourites.
- Uploads are serial with 2s between them. Killing a push mid-upload can leave one orphan unknown to `uploaded.json`. Find it with `frame.py list` (rows without `*` that aren't the human's photos) and delete it.
- `push` snapshots its file list at start, so files added during a push wait for the next one.
- Storage: `get_device_info` reports flash size (16 GB), not free space. Web claims of a "64 photo max" or "uploads deleting old photos" come from older models: a 2025 Frame held 299 images and deleted nothing.
- The art API is Samsung's local WebSocket (port 8002), reverse-engineered, via NickWaterton/samsung-tv-ws-api. A firmware update can change it; if a call fails in a new way, read the error and adapt.
