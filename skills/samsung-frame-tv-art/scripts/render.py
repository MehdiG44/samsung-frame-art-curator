"""Render any image to exactly 3840x2160 full-bleed for The Frame.
usage: render.py <mode> <out_dir> <files...>   mode: photo | print | anime
print: shaves paper margins first; anime: 2x AI upscale first; small art gets 4x AI upscale."""
import os, sys, subprocess, tempfile, threading, concurrent.futures as cf
ESR = next((p for p in (os.environ.get('FRAME_ESR_DIR', ''), os.path.expanduser('~/.local/share/frame-tv/esr'),
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'esr')) if p and os.path.isdir(p)),
           os.path.expanduser('~/.local/share/frame-tv/esr'))
W, H = 3840, 2160
# The GPU upscaler is the heavy part: two at once on big scans is what froze the Mac. One at a time, always;
# the CPU-side crop/encode can run in parallel around it.
GPU = threading.Lock()

def size(p):
    w, h = subprocess.run(['magick', 'identify', '-format', '%w %h', p + '[0]'], capture_output=True, text=True).stdout.split()
    return int(w), int(h)

def render(mode, src, out, shave=os.environ.get('PRINT_SHAVE', '90x88%')):
    with tempfile.TemporaryDirectory() as t:
        cur = src
        if mode == 'anime':
            with GPU: subprocess.run([f'{ESR}/realesrgan-ncnn-vulkan', '-i', cur, '-o', f'{t}/up.png', '-n', 'realesr-animevideov3', '-s', '2', '-m', f'{ESR}/models'], capture_output=True, check=True)
            cur = f'{t}/up.png'
        if mode == 'print':
            subprocess.run(['magick', cur, '-gravity', 'center', '-crop', shave + '+0+0', '+repage', f'{t}/shave.png'], check=True)
            cur = f'{t}/shave.png'
        w, h = size(cur)
        if mode != 'anime' and min(w / W, h / H) < 0.9:  # too small: AI upscale 4x
            with GPU: subprocess.run([f'{ESR}/realesrgan-ncnn-vulkan', '-i', cur, '-o', f'{t}/up4.png', '-n', 'realesrgan-x4plus', '-s', '4', '-m', f'{ESR}/models'], capture_output=True, check=True)
            cur = f'{t}/up4.png'
        subprocess.run(['vips', 'thumbnail', cur, f'{t}/c.v.png', str(W), '--height', str(H), '--size', 'both', '--crop', 'attention'], check=True, capture_output=True)
        subprocess.run(['magick', f'{t}/c.v.png', '-strip', '-colorspace', 'sRGB', '-quality', '92', out], check=True)
    return out

if __name__ == '__main__':
    mode, outdir, files = sys.argv[1], sys.argv[2], sys.argv[3:]
    os.makedirs(outdir, exist_ok=True)
    jobs = [(f, f'{outdir}/{os.path.splitext(os.path.basename(f))[0]}.jpg') for f in files]
    jobs = [j for j in jobs if not os.path.exists(j[1])]
    with cf.ThreadPoolExecutor(1 if mode == 'anime' else int(os.environ.get('RENDER_JOBS', '6'))) as ex:
        for r in ex.map(lambda j: render(mode, *j), jobs): print('ok', os.path.basename(r), flush=True)
