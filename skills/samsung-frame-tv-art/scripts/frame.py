#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["samsungtvws[async,encrypted] @ git+https://github.com/NickWaterton/samsung-tv-ws-api.git"]
# ///
"""frame.py: drive a Samsung The Frame's Art Mode over the LAN.

  frame.py discover                         find Frame TVs on the local /24
  frame.py status                           art mode, current image, slideshow, counts
  frame.py list [--json]                    My Photos; '*' = uploaded by this tool
  frame.py push FILES|DIRS [--fav] [--dry-run]
                                            upload exact-3840x2160 JPEGs, mat none; skips ones already on the TV
  frame.py prune DIRS [--dry-run]           delete TV copies of OUR uploads whose local file is gone from DIRS
  frame.py delete IDS [--force]             delete by content id (only ours unless --force)
  frame.py favs                             re-apply favourite to our uploads that missed it
  frame.py slideshow MIN|off [--fav|--all] [--ordered]
  frame.py show ID                          display one image (switches the TV to Art Mode)
  frame.py thumbs OUTDIR [IDS]              save thumbnails

TV address: $FRAME_TV_HOST, else ~/.config/frame-tv/host (written by `discover` when it finds exactly one Frame).
Project dir (holds uploaded.json): $FRAME_ART_DIR, else ~/.config/frame-tv/project, else ~/frame-tv-art.
Token: ~/.config/frame-tv/token.txt (first connection may show an Allow prompt on the TV).
Safety: the state file (uploaded.json) is the only list of images this tool may delete without --force.
"""
import asyncio, hashlib, json, os, subprocess, sys, time, urllib.request, concurrent.futures as cf
from samsungtvws.async_art import SamsungTVAsyncArt

HOST_FILE = os.path.expanduser('~/.config/frame-tv/host')
def _host():
    if os.environ.get('FRAME_TV_HOST'): return os.environ['FRAME_TV_HOST']
    try: return open(HOST_FILE).read().strip()
    except FileNotFoundError: return None
HOST = _host()
TOKEN = os.path.expanduser('~/.config/frame-tv/token.txt')
def project_dir():
    """$FRAME_ART_DIR, else ~/.config/frame-tv/project, else ~/frame-tv-art."""
    if os.environ.get('FRAME_ART_DIR'): return os.path.expanduser(os.environ['FRAME_ART_DIR'])
    try: return os.path.expanduser(open(os.path.expanduser('~/.config/frame-tv/project')).read().strip())
    except FileNotFoundError: return os.path.expanduser('~/frame-tv-art')
STATE = os.path.join(project_dir(), 'uploaded.json')
MY, FAV = 'MY-C0002', 'MY-C0004'

def load_state():
    try: return json.load(open(STATE))
    except FileNotFoundError: return {}
def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + '.tmp'; json.dump(s, open(tmp, 'w'), indent=1); os.replace(tmp, STATE)
def sha(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def dims(path):
    out = subprocess.run(['magick', 'identify', '-format', '%w %h %m', path + '[0]'], capture_output=True, text=True).stdout.split()
    return int(out[0]), int(out[1]), out[2]
def expand(args):
    files = []
    for a in args:
        if os.path.isdir(a):
            for root, _, fs in os.walk(a):
                files += [os.path.join(root, f) for f in sorted(fs) if f.lower().endswith(('.jpg', '.jpeg')) and not f.startswith('_')]
        else: files.append(a)
    return [os.path.abspath(f) for f in files]

async def connect():
    os.makedirs(os.path.dirname(TOKEN), exist_ok=True)
    tv = SamsungTVAsyncArt(host=HOST, port=8002, token_file=TOKEN, name='MacBook')
    await tv.start_listening()
    return tv

async def cmd_status(tv, _):
    mine = {v['content_id'] for v in load_state().values()}
    items = await tv.available(MY)
    ss = await tv.get_slideshow_status()
    cur = await tv.get_current()
    print(f"host        {HOST}")
    print(f"art mode    {await tv.get_artmode()}")
    print(f"showing     {cur.get('content_id')} (matte {cur.get('matte_id')})")
    print(f"slideshow   every {ss.get('value')} min, {ss.get('type')}, category {ss.get('category_id')}")
    print(f"my photos   {len(items)} total, {sum(i['content_id'] in mine for i in items)} uploaded by this tool")
    fav = await tv.available(FAV)
    print(f"favourites  {len(fav)}")

async def cmd_list(tv, args):
    mine = {v['content_id']: k for k, v in load_state().items()}
    st = load_state()
    items = await tv.available(MY)
    if '--json' in args: print(json.dumps(items, indent=1)); return
    for i in items:
        cid = i['content_id']; f = st[mine[cid]]['file'] if cid in mine else ''
        print(f"{'*' if cid in mine else ' '} {cid:10} {i['width']}x{i['height']:<5} {i['matte_id']:20} {os.path.basename(f)}")

async def cmd_push(tv, args):
    fav = '--fav' in args; dry = '--dry-run' in args
    files = expand([a for a in args if not a.startswith('--')])
    st = load_state(); on_tv = {i['content_id'] for i in await tv.available(MY)}
    todo, bad = [], []
    for f in files:
        w, h, m = dims(f)
        if (w, h) != (3840, 2160) or m != 'JPEG': bad.append(f'{f} ({w}x{h} {m})'); continue
        k = sha(f)
        if k in st and st[k]['content_id'] in on_tv: continue
        todo.append((k, f))
    if bad: print(f"refusing {len(bad)} file(s) not exactly 3840x2160 JPEG (the TV would add a border):\n  " + '\n  '.join(bad))
    print(f"{len(files)} files, {len(todo)} to upload, {len(files) - len(todo) - len(bad)} already on the TV")
    if dry or not todo: return
    for n, (k, f) in enumerate(todo, 1):
        for attempt in range(3):
            try:
                cid = await tv.upload(f, matte='none', portrait_matte='none', file_type='JPEG', timeout=90)
                break
            except Exception as e:
                print(f"  retry {attempt + 1} {os.path.basename(f)}: {e}"); await asyncio.sleep(5 * (attempt + 1))
        else:
            print('  giving up on', f); continue
        if fav:
            try: await tv.set_favourite(cid, 'on')
            except Exception as e:
                # 2025 firmware answers change_favorite on My Photos with error -7: favourites are not settable over
                # the API there. Stop trying after the first refusal instead of paying a timeout per image.
                print('  favourites not supported by this TV, continuing without:', e); fav = False
        st[k] = {'content_id': cid, 'file': f, 'fav': fav, 'at': time.strftime('%Y-%m-%d %H:%M')}
        save_state(st)
        print(f"  [{n}/{len(todo)}] {cid} {os.path.relpath(f)}", flush=True)
        await asyncio.sleep(2)   # the TV needs a breath between uploads past ~25 in a row

async def cmd_favs(tv, args):
    '''make sure every image this tool uploaded is a favourite (set_favourite sometimes times out)'''
    st = load_state(); favs = {i['content_id'] for i in await tv.available(FAV)}
    todo = [v['content_id'] for v in st.values() if v.get('fav') and v['content_id'] not in favs]
    for cid in todo:
        try: await tv.set_favourite(cid, 'on')
        except Exception as e: print('  failed', cid, e)
        await asyncio.sleep(1)
    print(f"{len(todo)} favourite(s) repaired, {len(favs) + len(todo)} favourites")

async def cmd_prune(tv, args):
    dry = '--dry-run' in args
    keep = {sha(f) for f in expand([a for a in args if not a.startswith('--')])}
    st = load_state(); gone = [(k, v) for k, v in st.items() if k not in keep]
    print(f"{len(gone)} uploaded image(s) no longer in the given folders")
    for k, v in gone: print('  ', v['content_id'], os.path.basename(v['file']))
    if dry or not gone: return
    await tv.delete_list([v['content_id'] for _, v in gone])
    for k, _ in gone: st.pop(k)
    save_state(st); print('deleted')

async def cmd_delete(tv, args):
    force = '--force' in args; ids = [a for a in args if not a.startswith('--')]
    st = load_state(); mine = {v['content_id']: k for k, v in st.items()}
    foreign = [i for i in ids if i not in mine]
    if foreign and not force: sys.exit(f"not uploaded by this tool (use --force if you really mean it): {' '.join(foreign)}")
    await tv.delete_list(ids)
    for i in ids:
        if i in mine: st.pop(mine[i])
    save_state(st); print('deleted', len(ids))

async def cmd_slideshow(tv, args):
    v = args[0] if args else sys.exit('usage: slideshow MIN|off [--fav|--all] [--ordered]')
    minutes = 0 if v == 'off' else int(v)
    cat = 4 if '--fav' in args else 2
    r = await tv.set_slideshow_status(duration=minutes, type='--ordered' not in args, category=cat)
    print('slideshow', 'off' if not minutes else f'every {minutes} min', 'favourites' if cat == 4 else 'all my photos', r.get('value', ''))

async def cmd_show(tv, args):
    await tv.select_image(args[0], category=None, show=True); print('showing', args[0])

async def cmd_thumbs(tv, args):
    out = args[0]; os.makedirs(out, exist_ok=True)
    ids = args[1:] or [i['content_id'] for i in await tv.available(MY)]
    for cid in ids:
        data = await tv.get_thumbnail_list(cid)
        for _, b in (data or {}).items(): open(f'{out}/{cid}.jpg', 'wb').write(b)
    print(len(ids), 'thumbnails in', out)

def discover():
    import socket
    sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: sk.connect(('10.255.255.255', 1)); me = sk.getsockname()[0]   # no packet is sent; picks the LAN interface
    finally: sk.close()
    net = me.rsplit('.', 1)[0]
    def probe(i):
        try:
            d = json.load(urllib.request.urlopen(f'http://{net}.{i}:8001/api/v2/', timeout=1.5))['device']
            return f"{d['ip']:15} {d['modelName']:18} frame={d['FrameTVSupport']} power={d['PowerState']} {d['name']}"
        except Exception: return None
    with cf.ThreadPoolExecutor(64) as ex:
        found = [r for r in ex.map(probe, range(1, 255)) if r]
    for r in found: print(r)
    frames = [r for r in found if 'frame=true' in r]
    if len(frames) == 1:
        os.makedirs(os.path.dirname(HOST_FILE), exist_ok=True)
        open(HOST_FILE, 'w').write(frames[0].split()[0])
        print('saved', frames[0].split()[0], 'to', HOST_FILE)
    elif not frames: print('no Frame TV answered on port 8001; is it on and on this network?')

CMDS = {'status': cmd_status, 'list': cmd_list, 'push': cmd_push, 'prune': cmd_prune, 'delete': cmd_delete,
        'slideshow': cmd_slideshow, 'favs': cmd_favs, 'show': cmd_show, 'thumbs': cmd_thumbs}

async def main(cmd, args):
    tv = await connect()
    try: await CMDS[cmd](tv, args)
    finally: await tv.close()

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in [*CMDS, 'discover']: sys.exit(__doc__)
    if sys.argv[1] == 'discover': discover()
    elif not HOST: sys.exit('no TV address: run `frame.py discover` or set FRAME_TV_HOST')
    else: asyncio.run(main(sys.argv[1], sys.argv[2:]))
