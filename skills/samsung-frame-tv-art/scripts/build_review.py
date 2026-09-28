"""Build <project>/review/index.html + review/thumbs/*.jpg from <project>/stage/final/<TYPE>/*.jpg.
Project dir: $FRAME_ART_DIR, else ~/.config/frame-tv/project, else ~/frame-tv-art.
<project>/types.json: [[code, label, source note, kind], ...]; the first letter of a code is its region.
<project>/regions.json (optional): {"title": str, "subtitle": str, "regions": {"J": {"title","accent","blurb"}}}."""
import os, re, json, glob, subprocess, concurrent.futures as cf
HERE = os.path.dirname(os.path.realpath(__file__))
def project_dir():
    """$FRAME_ART_DIR, else ~/.config/frame-tv/project, else ~/frame-tv-art."""
    if os.environ.get('FRAME_ART_DIR'): return os.path.expanduser(os.environ['FRAME_ART_DIR'])
    try: return os.path.expanduser(open(os.path.expanduser('~/.config/frame-tv/project')).read().strip())
    except FileNotFoundError: return os.path.expanduser('~/frame-tv-art')
os.chdir(project_dir())
rows = json.load(open('types.json'))
types = {r[0]: r[1] for r in rows}
SRC = {r[0]: r[2] for r in rows if len(r) > 2 and r[2]}
items = []
for t in sorted(os.listdir('stage/final')):
    if t not in types: continue
    for f in sorted(glob.glob(f'stage/final/{t}/*.jpg')):
        base = os.path.splitext(os.path.basename(f))[0]
        iid = t + '.' + re.sub(r'[^A-Za-z0-9_-]', '-', base)[:120]
        items.append({'id': iid, 't': t, 'f': f})
os.makedirs('review/thumbs', exist_ok=True)
def thumb(it):
    out = f"review/thumbs/{it['id']}.jpg"
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(it['f']):
        subprocess.run(['magick', it['f'], '-resize', '960x540', '-strip', '-quality', '74', '-interlace', 'Plane', out], check=True)
with cf.ThreadPoolExecutor(8) as ex: list(ex.map(thumb, items))
keep = {f"{it['id']}.jpg" for it in items}
for f in os.listdir('review/thumbs'):
    if f not in keep: os.remove(f'review/thumbs/{f}')
# type codes or item ids the owner already went through; the page hides them unless he asks (reviewed.json in the project)
try: seen = set(json.load(open('reviewed.json')))
except FileNotFoundError: seen = set()
groups = []
for t in types:
    ids = [it['id'] for it in items if it['t'] == t]
    if ids: groups.append({'seen': [i for i in ids if t in seen or i in seen], 'code': t, 'label': types[t], 'src': SRC.get(t, ''), 'ids': ids})
json.dump({it['id']: it['f'] for it in items}, open('review/id_map.json', 'w'), indent=1)
try: meta = json.load(open('regions.json'))
except FileNotFoundError: meta = {}
regions = {c[0]: {'title': c[0], 'accent': '', 'blurb': ''} for c in types}
regions.update(meta.get('regions', {}))
regions = {k: v for k, v in regions.items() if any(g['code'][0] == k for g in groups)}
title = meta.get('title', 'Frame Art Review')
esc = lambda s: s.replace('&', '&amp;').replace('<', '&lt;')
html = (open(os.path.join(HERE, 'review_template.html')).read()
        .replace('/*__DATA__*/null', json.dumps(groups)).replace('/*__REGIONS__*/null', json.dumps(regions))
        .replace('__TITLE__', esc(title)).replace('__SUBTITLE__', esc(meta.get('subtitle', 'Samsung The Frame · 3840 × 2160, no border'))))
open('review/index.html', 'w').write(html)
print(len(items), 'items', len(groups), 'groups', sum(os.path.getsize('review/thumbs/'+f) for f in os.listdir('review/thumbs'))//1024//1024, 'MB thumbs')
