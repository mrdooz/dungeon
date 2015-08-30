import json
import sys
import glob
import os
from PIL import Image

ofs = 0
margin = 0
size = 24

for filename in glob.glob('*.png'):
    head, _ = os.path.splitext(filename)
    outname = head + '.json'

    im = Image.open(filename)

    res = {}
    frames = []
    y = 0

    xx = margin + size
    yy = margin + size

    while y + yy <= im.size[1]:
        x = 0
        while x + xx <= im.size[0]:
            frame = {}
            frame['filename'] = 'sprite%.2d_%.2d' % (x / xx, y / yy)
            frame['frame'] = {'x': x, 'y': y, 'w': size, 'h': size}
            frame['rotated'] = False
            frame['trimmed'] = False
            frame['spriteSourceSize'] = {'x': 0, 'y': 0, 'w': size, 'h': size}
            frame['sourceSize'] = {'w': size, 'h': size}
            frames.append(frame)
            x += xx
        y += yy

    meta = {
        'app': 'magnus funky script',
        'image': filename,
        'format': 'RGBA8888',
        'size': {'w': im.size[0], 'h': im.size[1]},
    }

    res['frames'] = frames
    res['meta'] = meta

    s = json.dumps(res, indent=4)
    open(outname, 'wt').write(s)
