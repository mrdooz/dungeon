from PIL import Image, ImageDraw, ImageColor
from random import randint, gauss, random
import argparse
import math


class Vec2(object):
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return 'x: %r, y: %r' % (self.x, self.y)

    __str__ = __repr__

    def __add__(self, rhs):
        return Vec2(self.x + rhs.x, self.y + rhs.y)

    def __radd__(self, rhs):
        return Vec2(self.x + rhs.x, self.y + rhs.y)

    def __getitem__(self, idx):
        if idx == 0:
            return self.x
        elif idx == 1:
            return self.y
        raise 'Invalid index'


class Room(object):
    def __init__(self, center, width, height):
        self.width = width
        self.height = height
        self.update_center(center)

    def __str__(self):
        return 'center: %r, width: %r, height: %r, tl: %r, br: %r' % (
            self.center, self.width, self.height, self.top_left, self.bottom_right)

    def update_center(self, center):
        self.center = center
        self.top_left = Vec2(center.x - self.width/2, center.y - self.height/2)
        self.bottom_right = Vec2(center.x + self.width/2, center.y + self.height/2)


def room_overlap(lhs, rhs):

    for i in range(2):
        if rhs.top_left[i] < lhs.top_left[i]:
            lhs, rhs = rhs, lhs

        a0, a1 = lhs.top_left[i], lhs.bottom_right[i]
        b0, b1 = rhs.top_left[i], rhs.bottom_right[i]

        if not (a0 <= b1 and a1 > b0):
            return False
    return True


def random_point_in_circle(radius):
    t = 2 * math.pi * random()
    u = random() + random()
    r = 2 - u if u > 1 else u
    return Vec2(radius * r * math.cos(t), radius * r * math.sin(t))


def image_from_rooms(rooms):
    min_dim = Vec2(0, 0)
    max_dim = Vec2(0, 0)

    for room in rooms:
        min_dim.x = min(min_dim.x, room.top_left.x)
        min_dim.y = min(min_dim.y, room.top_left.y)

        max_dim.x = max(max_dim.x, room.bottom_right.x)
        max_dim.y = max(max_dim.y, room.bottom_right.y)

    w = int(math.ceil(max_dim.x) - math.floor(min_dim.x))
    h = int(math.ceil(max_dim.y) - math.floor(min_dim.y))

    im = Image.frombytes('RGBA', (w, h), "\x00\x00\x00\xff" * w * h)
    draw = ImageDraw.Draw(im)
    for room in rooms:
        x0 = room.top_left.x - min_dim.x
        y0 = room.top_left.y - min_dim.y
        x1 = x0 + room.width
        y1 = y0 + room.height
        draw.rectangle((x0, y0, x1, y1), fill=randint(64, 255))
    return im


parser = argparse.ArgumentParser()
parser.add_argument("--num_rooms", type=int, default=100)
parser.add_argument("--width", type=float, default=32)
parser.add_argument("--width_dev", type=float, default=10)
parser.add_argument("--height", type=float, default=32)
parser.add_argument("--height_dev", type=float, default=10)
parser.add_argument("--radius", type=float, default=50)
args = parser.parse_args()


ROOMS = []

# generate random room positions
for i in range(args.num_rooms):
    w = gauss(args.width, args.width_dev)
    h = gauss(args.height, args.height_dev)

    ROOMS.append(Room(random_point_in_circle(args.radius), w, h))

# push rooms away from each other

num_rooms = len(ROOMS)
f = 2
cnt = 0
while True:
    forces = [Vec2(0, 0) for _ in range(len(ROOMS))]
    overlap = False
    for i in range(num_rooms):
        for j in range(num_rooms):
            if i == j:
                continue
            lhs = ROOMS[i]
            rhs = ROOMS[j]
            if room_overlap(lhs, rhs):
                overlap = True
                v = Vec2(lhs.center.x - rhs.center.x, lhs.center.y - rhs.center.y)
                ll = math.sqrt(v.x * v.x + v.y * v.y)
                if ll:
                    v.x /= ll
                    v.y /= ll
                forces[i].x += f * v.x
                forces[i].y += f * v.y
                forces[j].x -= f * v.x
                forces[j].y -= f * v.y

    if not overlap:
        break

    for i in range(num_rooms):
        ROOMS[i].update_center(ROOMS[i].center + forces[i])


im0 = image_from_rooms(ROOMS)
im0.show()
