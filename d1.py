from PIL import Image, ImageDraw, ImageColor
from random import randint


class Room(object):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h


class Level(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.rooms = []

    def add_room(self, room):
        self.rooms.append(room)


im = Image.open('gfx/roguelikeDungeon_transparent.png')
draw = ImageDraw.Draw(im)
# print im.size
margin = 1
dim = (16, 16)
y = 0
while y < im.size[1]:
    x = 0
    while x < im.size[0]:
        draw.rectangle((x, y + dim[1], x + dim[0], y + dim[1]), fill=64)
        draw.rectangle((x + dim[0], y, x + dim[0], y + dim[1]), fill=64)
        x += dim[0] + margin
    y += dim[1] + margin

# im.show()

wall_flags = {}
wall_flags['left'] = 0x1
wall_flags['right'] = 0x2
wall_flags['up'] = 0x4
wall_flags['down'] = 0x8

wall_sprites = {}


def f(flags):
    return sum([wall_flags[x] for x in flags])


wall_sprites[f(['left', 'right', 'up'])] = (8, 0)
wall_sprites[f(['left', 'up', 'down'])] = (9, 0)
wall_sprites[f(['up', 'down'])] = (10, 0)
wall_sprites[f(['right', 'up', 'down'])] = (11, 0)
wall_sprites[f(['left', 'up'])] = (12, 0)
wall_sprites[f(['right', 'up'])] = (13, 0)
wall_sprites[f(['left'])] = (14, 0)
wall_sprites[f(['down'])] = (15, 0)

wall_sprites[f(['left', 'right', 'down'])] = (8, 1)
wall_sprites[f(['left', 'right', 'up', 'down'])] = (9, 1)
wall_sprites[f([])] = (10, 1)
wall_sprites[f(['left', 'right'])] = (11, 1)
wall_sprites[f(['left', 'down'])] = (12, 1)
wall_sprites[f(['right', 'down'])] = (13, 1)
wall_sprites[f(['right'])] = (14, 1)
wall_sprites[f(['up'])] = (15, 1)

inner_wall_sprites = {}
inner_wall_sprites[0x8+0x1] = (8, 2)
inner_wall_sprites[0x8] = (9, 2)
inner_wall_sprites[0x8+0x2] = (10, 2)
inner_wall_sprites[0x8+0x1+0x2] = (11, 2)

inner_wall_sprites[0x4+0x1] = (8, 4)
inner_wall_sprites[0x4] = (9, 4)
inner_wall_sprites[0x4+0x2] = (10, 4)
inner_wall_sprites[0x4+0x1+0x2] = (11, 4)

floor_sprite = (16, 12)


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

    def extra_flags(x, y):
        empty = is_empty(x, y)
        # check for inner wall flags
        res = 0
        fill1 = is_filled(x, y-1)
        fill2 = is_filled(x, y-2)
        is_inner_wall = fill1 or fill2
        if empty and is_inner_wall:
            if is_filled(x-1, y):
                res += 0x1
            if is_filled(x+1, y):
                res += 0x2
            if fill1:
                res += 0x8
            elif fill2:
                res += 0x4
        return res

    room_sprites = []

    for y in range(h):
        row_sprites = []
        for x in range(w):
            ff = wall_flags(x, y)
            ee = extra_flags(x, y)
            if ff:
                row_sprites.append(wall_sprites[ff])
            elif ee:
                row_sprites.append(inner_wall_sprites[ee])
            else:
                row_sprites.append(floor_sprite)

        room_sprites.append(row_sprites)

    return room_sprites

room = parse_room('room1.txt')
h = len(room)
w = len(room[0])

# print h, w, room

room_img = Image.frombytes('RGBA', (w*16, h*16), "\x00\x00\x00\xff" * w * 16 * h * 16)

floor = im.crop((floor_sprite[0]*17, floor_sprite[1]*17, floor_sprite[0]*17+16, floor_sprite[1]*17+16))
for y in range(h):
    rr = room[y]
    for x in range(w):
        room_img.paste(floor, box=(x*16, y*16, (x+1)*16, (y+1)*16), mask=floor)
        r = rr[x]
        im_sprite = im.crop((r[0]*17, r[1]*17, r[0]*17+16, r[1]*17+16))
        room_img.paste(im_sprite, box=(x*16, y*16, (x+1)*16, (y+1)*16), mask=im_sprite)

room_img.show()

