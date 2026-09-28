---
name: frame-tv
description: Curate and manage art on a Samsung The Frame TV from a Mac - find images by taste, render them borderless at exactly 3840x2160, review them on a tap-to-remove page, then upload, prune and set the shuffle slideshow over the local network. Use for anything about "the Frame", "Frame TV art", "art mode", adding/removing/rotating pictures on the TV, or a new theme for the TV.
---

# The Frame TV art

Works with any agent that reads Agent Skills (Claude Code, Codex, ...). Everything runs from the Mac over the home network; the SmartThings phone app is not needed. Proven on a 2025 Frame (LS03F, 4K) in Sept 2026.

**Read `taste.md` next to this file first** (copy `taste.example.md` if it doesn't exist and fill it with the owner). It holds the owner's rules, approved types and anything they have said about approval. It overrides the defaults below.

## Setup (once)
- `scripts/frame.py discover` finds the Frame on the local /24 and saves its address to `~/.config/frame-tv/host`. The first connection may show an Allow prompt on the TV; the token goes to `~/.config/frame-tv/token.txt`.
- `frame.py` is a `uv` inline script (`#!/usr/bin/env -S uv run --script`), so it needs no venv.
- `scripts/install_esr.sh` fetches the Real-ESRGAN binary (~70 MB) that `render.py` uses to upscale.
- Needs `uv`, ImageMagick (`magick`, `montage`) and libvips (`vips`): `brew install uv imagemagick vips`.
- Project dir: `$FRAME_ART_DIR`, default `~/code/frame-art`. It holds `types.json`, `regions.json`, `reviewed.json`, `cand/`, `stage/final/<TYPE>/`, `review/` and `uploaded.json`, the list of what this tool uploaded.

## Hard rules
- **No border.** Every image must be exactly 3840x2160 JPEG and uploaded with matte `none`. Any other size makes the TV add a mat, the "black bands" people complain about. Full-bleed only, so portrait art is out.
- **Never delete what you didn't upload.** My Photos also holds the owner's own photos. `frame.py delete` refuses ids that aren't in `uploaded.json` unless given `--force`, and `--force` is only for ids the owner named.
- **Taste first, volume second.** Show one example per candidate type on a single sheet and let the owner answer in type codes. Only then source ~7 per type, cull hard yourself, and show the review page with only what they haven't seen.
- **Keep the TV light.** Aim for at most ~300 images / ~1 GB on the TV. Beyond that, rotate by pruning rather than adding.

## Pipeline
1. **Types**: render one example per type (`scripts/render.py`), build a labelled sheet (`scripts/sheet.py out.png 4 files...`), `open` it. Record approved types in `types.json` as `[code, label, source note, kind]`. The first letter of a code is its region, e.g. J = Japan, S = Silk Road; describe regions in `regions.json`.
2. **Source** into `cand/<TYPE>/`:
   - **Photos**: Unsplash's internal search API works keyless from a real browser tab on unsplash.com (use whatever browser automation you have: Claude in Chrome, Playwright, Codex's browser) (`/napi/search/photos?query=...&per_page=30&orientation=landscape`) but not from curl. Filter `width>=3600`, landscape, top ~20 by likes, preview at `images.unsplash.com/<raw>?w=640&h=360&fit=crop&crop=entropy`, cull on a sheet. Full-res: `?w=5120&q=90&fm=jpg&fit=max`. Skip `plus.unsplash.com`. Keep credits.
   - **Woodblock prints**:
     - Art Institute of Chicago API: POST search, IIIF `/full/3000,/0/default.jpg`, send `AIC-User-Agent`. **AIC caps works that are not public domain at 843px** (Hasui, Yoshida, most Koitsu).
     - Minneapolis Institute of Art has 7-14k px public-domain scans: `img.artsmia.org/web_objects_cache/<Cache_Location>/<rendition>_full.jpg`, with values from `search.artsmia.org`.
     - Also Rijksmuseum, the Met and Commons (NDL scans).
   - **Paintings**: Wikimedia Commons, `filew:>2000 filemime:image/jpeg`, 3s pacing, backoff on 429.
     - Full-size downloads keep 429ing until the User-Agent carries a contact URL.
     - A 429 can leave a 0-byte file, so check file sizes.
     - Many 19th-century scans are ~2000px and get the 4x upscale.
   - **Anime and game art**: `scripts/wallhaven.py cand/wh <TYPE> "query"...` returns native 4K 16:9, SFW only, sorted by favourites (Wallhaven's `toplist` only covers the last month). Results are heavy on character pin-ups and logos, so keep scenery with small or no characters and no text. Rights are a gray area: for private display at home.
   - **Ghibli**: Studio Ghibli publishes free stills at `https://www.ghibli.jp/gallery/<film>NNN.jpg` (001-050, 1920x1038) "to use freely within common sense". Most are character close-ups; Marnie, The Red Turtle, The Wind Rises, Poppy Hill and Arrietty are the most scenic. `render.py anime` upscales them 2x.
3. **Render** into `stage/final/<TYPE>/` with `scripts/render.py photo|print|anime OUTDIR files...`. It does an attention-based cover crop to 3840x2160.
   - `print` shaves paper margins first. Use `PRINT_SHAVE` (default `90x88%`, try `82x78%` for wide margins, `97x96%` for scans already cropped to the image).
   - Anything under 90% of 4K gets a 4x upscale.
   - Check every crop on one sheet: no paper edges, no colour charts, no text blocks.
4. **Review**: `scripts/build_review.py` builds `review/index.html` plus thumbnails.
   - **Any agent**: serve it on the LAN so the owner can use a phone (`python3 -m http.server 8765 --directory review`, then share `http://<mac-ip>:8765`) or just `open review/index.html`. The owner taps to remove, then presses "Copy removed list" and pastes it back to you. Each line is `<TYPE>.<basename>`, mapped to its file in `review/id_map.json`.
   - **Claude with Artifacts**: publish the page as an Artifact with `capabilities: {db: {}}` and every `thumbs/*` file (`root` = review dir). Taps then sync live: read the `removed` collection, one doc per removed image, doc id = `<TYPE>.<basename>`.
   - List type codes or item ids the owner has already seen in `reviewed.json`, so the page opens on "To review".
5. **Apply**: move removed files to `stage/rejected/` (keep them, they teach taste), then:
   ```
   scripts/frame.py push stage/final --dry-run   # counts, refuses anything not exactly 3840x2160
   scripts/frame.py push stage/final             # ~7s per image, resumable, skips what is already on the TV
   scripts/frame.py slideshow 15                 # shuffle My Photos every 15 min
   scripts/frame.py prune stage/final            # later: remove TV copies of files deleted locally
   ```

## Gotchas
- **Favourites can't be set over the API on 2025 firmware**: `change_favorite` returns `error_code -7`. So the shuffle can only run on all of My Photos, the owner's own photos included. Ask the owner whether that's fine. Older Frames accept `push --fav` and `slideshow 15 --fav`.
- `set_auto_rotation_status` fails on 2025 firmware; `set_slideshow_status` works. Slideshow category 2 = My Photos, 4 = Favourites.
- Uploads are serial with 2s between them. Killing a push mid-upload can leave one orphan on the TV that `uploaded.json` doesn't know about. Diff `list` (rows without `*`) against the owner's own photo ids and delete only the orphan.
- `push` snapshots its file list at start. Don't add files to `stage/final` during a push unless they are approved.
- `get_artmode` returns `on`, `off` or `nav`; `nav` means someone is using the TV. Don't `show` or switch modes then.
- Storage: `get_device_info` reports `tv_flash_size` (16 GB on the 2025 model), not free space. The web's "64 photos max" and "new uploads delete old ones" claims come from older models; a 2025 Frame held 299 images with nothing deleted.
- **Machine load**: Real-ESRGAN runs on the GPU, and 3 at once froze a MacBook. `render.py` serializes GPU calls behind a lock and runs 6 CPU jobs. Run only one `render.py` process at a time.
- `montage` on macOS needs `-font /System/Library/Fonts/Helvetica.ttc` (`sheet.py` passes it).
