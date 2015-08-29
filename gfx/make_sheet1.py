import json
from PIL import Image
im = Image.open('roguelikeDungeon_transparent.png')

res = {}
frames = []
y = 0
while y < im.size[1]:
    x = 0
    while x < im.size[0]:
        frame = {}
        frame['filename'] = 'sprite%.2d_%.2d' % (x / 17, y / 17)
        frame['frame'] = {'x': x, 'y': y, 'w': 16, 'h': 16}
        frame['rotated'] = False
        frame['trimmed'] = False
        frame['spriteSourceSize'] = {'x': 0, 'y': 0, 'w': 16, 'h': 16}
        frame['sourceSize'] = {'w': 16, 'h': 16}
        frames.append(frame)
        x += 17
    y += 17

meta = {
    'app': 'magnus funky script',
    'image': 'roguelikeDungeon_transparent.png',
    'format': 'RGBA8888',
    'size': {'w': im.size[0], 'h': im.size[1]},
}

res['frames'] = frames
res['meta'] = meta

print json.dumps(res, indent=4)
