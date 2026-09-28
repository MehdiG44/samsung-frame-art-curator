"""sheet.py out.png cols files...  -> labeled contact sheet (label = index:name)"""
import sys, subprocess, os
out, cols, files = sys.argv[1], sys.argv[2], sys.argv[3:]
args = []
for i, f in enumerate(files): args += ['-label', f'{i}: {os.path.splitext(os.path.basename(f))[0][:28]}', f]
subprocess.run(['montage', *args, '-font', '/System/Library/Fonts/Helvetica.ttc', '-tile', f'{cols}x', '-geometry', '400x225+4+4', '-pointsize', '15', '-background', '#111', '-fill', '#ddd', out], check=True)
