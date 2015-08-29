# based on the oryx sprite sheet
from PIL import Image, ImageDraw, ImageColor
from random import randint


im = Image.open('gfx/oryx_16bit_fantasy_world_trans.png')
draw = ImageDraw.Draw(im)
# print im.size
margin = 0
dim = (24, 24)
y = 0
while y < im.size[1]:
    x = 0
    while x < im.size[0]:
        draw.rectangle((x, y + dim[1], x + dim[0], y + dim[1]), fill=64)
        draw.rectangle((x + dim[0], y, x + dim[0], y + dim[1]), fill=64)
        x += dim[0] + margin
    y += dim[1] + margin

wall_flags = {}
wall_flags['left'] = 0x1
wall_flags['right'] = 0x2
wall_flags['up'] = 0x4
wall_flags['down'] = 0x8

wall_sprites = {}


def f(flags):
    return sum([wall_flags[x] for x in flags])

# bits tell which sides are free
h = 3
wall_sprites[f(['left', 'right', 'up'])] = (14, h)
wall_sprites[f(['left', 'up', 'down'])] = (11, h)
wall_sprites[f(['up', 'down'])] = (12, h)
wall_sprites[f(['right', 'up', 'down'])] = (13, h)
wall_sprites[f(['left', 'up'])] = (17, h)
wall_sprites[f(['right', 'up'])] = (18, h)
wall_sprites[f(['left'])] = (24, h)
wall_sprites[f(['down'])] = (25, h)

wall_sprites[f(['left', 'right', 'down'])] = (16, h)
wall_sprites[f(['left', 'right', 'up', 'down'])] = (1, h)
wall_sprites[f([])] = (10, h)
wall_sprites[f(['left', 'right'])] = (15, h)
wall_sprites[f(['left', 'down'])] = (19, h)
wall_sprites[f(['right', 'down'])] = (20, h)
wall_sprites[f(['right'])] = (23, h)
wall_sprites[f(['up'])] = (22, h)
floor_sprite = (4, h)


def parse_room(f):
    room = []
    for r in open(f).readlines():
        r = r.strip()
        line = [x for x in r]
        room.append(line)

    h = len(room)
    w = len(room[0])

    def is_inside(x, y):
        return x >= 0 and x < w and y >= 0 and y < h

    def is_filled(x, y):
        return is_inside(x, y) and room[y][x] == 'x'

    def is_empty(x, y):
        return is_inside(x, y) and room[y][x] == ' '

    def wall_flags(x, y):
        res = 0
        filled = is_filled(x, y)
        if x == 0 or (filled and room[y][x-1] == ' '):
            res += 0x1
        if x == w-1 or (filled and room[y][x+1] == ' '):
            res += 0x2
        if y == 0 or (filled and room[y-1][x] == ' '):
            res += 0x4
        if y == h-1 or (filled and room[y+1][x] == ' '):
            res += 0x8
        return res

    room_sprites = []

    for y in range(h):
        row_sprites = []
        for x in range(w):
            ff = wall_flags(x, y)
            if ff:
                row_sprites.append(wall_sprites[ff])
            else:
                row_sprites.append(floor_sprite)

        room_sprites.append(row_sprites)

    return room_sprites

room = parse_room('room1.txt')
h = len(room)
w = len(room[0])

room_img = Image.frombytes('RGBA', (w*24, h*24), "\x00\x00\x00\xff" * w * 24 * h * 24)

floor = im.crop(
    (floor_sprite[0]*24, floor_sprite[1]*24, floor_sprite[0]*24+24, floor_sprite[1]*24+24))
for y in range(h):
    rr = room[y]
    for x in range(w):
        room_img.paste(floor, box=(x*24, y*24, (x+1)*24, (y+1)*24), mask=floor)
        r = rr[x]
        im_sprite = im.crop((r[0]*24, r[1]*24, r[0]*24+24, r[1]*24+24))
        room_img.paste(im_sprite, box=(x*24, y*24, (x+1)*24, (y+1)*24), mask=im_sprite)

room_img.show()

