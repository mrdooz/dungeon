from PIL import Image, ImageDraw
from random import randint, gauss, random
import argparse
import math
import numpy as np
from scipy.spatial import Delaunay
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree
import copy


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

    def __sub__(self, rhs):
        return Vec2(self.x - rhs.x, self.y - rhs.y)

    def __radd__(self, rhs):
        return Vec2(self.x + rhs.x, self.y + rhs.y)

    def __getitem__(self, idx):
        if idx == 0:
            return self.x
        elif idx == 1:
            return self.y
        raise 'Invalid index'


class Room(object):
    def __init__(self, center, width, height, active):
        self.width = width
        self.height = height
        self.update_center(center)
        self.active = active
        self.bonus = False

    def __str__(self):
        return 'center: %r, width: %r, height: %r, tl: %r, br: %r' % (
            self.center, self.width, self.height, self.top_left, self.bottom_right)

    def update_center(self, center):
        self.center = center
        self.top_left = Vec2(center.x - self.width/2, center.y - self.height/2)
        self.bottom_right = Vec2(center.x + self.width/2, center.y + self.height/2)


def rect_overlap(a, b):
    """
    rects are pairs of tuples, (top-left, bottom-right)
    """
    if a[1].x < b[0].x:
        return False
    if a[0].x > b[1].x:
        return False
    if a[1].y < b[0].y:
        return False
    if a[0].y > b[1].y:
        return False
    return True


def room_overlap(lhs, rhs):
    if lhs.bottom_right.x < rhs.top_left.x:
        return False
    if lhs.top_left.x > rhs.bottom_right.x:
        return False
    if lhs.bottom_right.y < rhs.top_left.y:
        return False
    if lhs.top_left.y > rhs.bottom_right.y:
        return False

    return True


def random_point_in_circle(radius):
    t = 2 * math.pi * random()
    u = random() + random()
    r = 2 - u if u > 1 else u
    return Vec2(radius * r * math.cos(t), radius * r * math.sin(t))


def normalize_rooms(rooms):
    min_dim = Vec2(0, 0)
    max_dim = Vec2(0, 0)

    for room in rooms:
        min_dim.x = min(min_dim.x, room.top_left.x)
        min_dim.y = min(min_dim.y, room.top_left.y)

        max_dim.x = max(max_dim.x, room.bottom_right.x)
        max_dim.y = max(max_dim.y, room.bottom_right.y)

    for room in rooms:
        room.update_center(room.center - min_dim)


def fill_array(x0, y0, x1, y1, rows):
    x0, y0, x1, y1 = [int(x) for x in (x0, y0, x1, y1)]
    for i in range(y1-y0):
        for j in range(x1-x0):
            rows[y0+i][x0+j] = 'x'


def prune_array(rows):
    res = copy.deepcopy(rows)
    h = len(rows)
    w = len(rows[0])

    def is_empty(x, y):
        return x < 0 or x == w or y < 0 or y == h or rows[y][x] == ' '

    for i in range(h):
        for j in range(w):
            cnt = (
                is_empty(j-1, i) + is_empty(j+1, i) +
                is_empty(j, i-1) + is_empty(j, i+1))

            if rows[i][j] == 'x':
                if cnt:
                    res[i][j] = 'x'
                else:
                    res[i][j] = ' '
            else:
                res[i][j] = rows[i][j]

    return res


def image_from_rooms(active_rooms, all_rooms, centers, mst_edges, paths):
    min_dim = Vec2(0, 0)
    max_dim = Vec2(0, 0)

    for room in active_rooms:
        min_dim.x = min(min_dim.x, room.top_left.x)
        min_dim.y = min(min_dim.y, room.top_left.y)

        max_dim.x = max(max_dim.x, room.bottom_right.x)
        max_dim.y = max(max_dim.y, room.bottom_right.y)

    w = int(math.ceil(max_dim.x) - math.floor(min_dim.x))
    h = int(math.ceil(max_dim.y) - math.floor(min_dim.y))

    rows = []
    for _ in range(h):
        rows.append([' '] * w)

    im = Image.frombytes('RGBA', (w, h), "\x10\x10\x10\xff" * w * h)
    draw = ImageDraw.Draw(im)
    for room in all_rooms:
        x0 = room.top_left.x - min_dim.x
        y0 = room.top_left.y - min_dim.y
        x1 = x0 + room.width
        y1 = y0 + room.height
        # note, the -1 is used here because rectangle doesn't really seem to
        # keep it its contract..
        c = randint(64, 255)
        if room.active:
            draw.rectangle((x0, y0, x1-1, y1-1), fill=(c, c, c, 255))
            fill_array(x0, y0, x1, y1, rows)
        elif room.bonus:
            draw.rectangle((x0, y0, x1-1, y1-1), fill=(c, c, 0, 255))
            fill_array(x0, y0, x1, y1, rows)
        else:
            draw.rectangle((x0, y0, x1-1, y1-1), fill=(c, 0, 0, 255))

    for path in paths:
        x0 = path[0].x
        y0 = path[0].y
        x1 = path[1].x
        y1 = path[1].y
        c = randint(64, 255)
        draw.rectangle((x0, y0, x1-1, y1-1), fill=(0, 0, c, 255))
        fill_array(x0, y0, x1, y1, rows)

    for c in centers:
        i0, i1, i2 = c[:]
        c0, c1, c2 = active_rooms[i0].center, active_rooms[i1].center, active_rooms[i2].center
        cc = [c0, c1, c2]
        for i in range(3):
            draw.line(
                (cc[i].x, cc[i].y, cc[((i+1) % 3)].x, cc[((i+1) % 3)].y),
                fill=(255, 255, 255))

    for c in mst_edges:
        a, b = c[:]
        c0, c1 = active_rooms[a].center, active_rooms[b].center
        draw.line((c0.x, c0.y, c1.x, c1.y), fill=(0, 255, 0))

    return im, rows


def add_path(a, b):
    """
    create a path between room a and room b
    """
    l_cutoff = 10
    diff_x = abs(a.center.x - b.center.x)
    diff_y = abs(a.center.y - b.center.y)

    def add_horiz_path(a, b):
        if b.x < a.x:
            a, b = b, a

        aa = a + Vec2(-2, -2)
        bb = Vec2(b.x, a.y) + Vec2(+2, +2)
        return (
            Vec2(min(aa.x, bb.x), min(aa.y, bb.y)),
            Vec2(max(aa.x, bb.x), max(aa.y, bb.y)))

    def add_vert_path(a, b):
        if b.y < a.y:
            a, b = b, a

        aa = a + Vec2(-2, -2)
        bb = Vec2(a.x, b.y) + Vec2(+2, +2)
        return (
            Vec2(min(aa.x, bb.x), min(aa.y, bb.y)),
            Vec2(max(aa.x, bb.x), max(aa.y, bb.y)))

    if diff_x >= l_cutoff and diff_y >= l_cutoff:
        # l-shaped
        xa_ofs = randint(-int(a.width/3), int(a.width/3))
        ya_ofs = randint(-int(a.height/3), int(a.height/3))
        src = a.center + Vec2(xa_ofs, ya_ofs)

        xb_ofs = randint(-int(b.width/3), int(b.width/3))
        yb_ofs = randint(-int(b.height/3), int(b.height/3))
        dst = b.center + Vec2(xb_ofs, yb_ofs)

        tmp = Vec2(dst.x, src.y)
        return [add_horiz_path(src, tmp), add_vert_path(tmp, dst)]

    if diff_x < diff_y:
        return [add_vert_path(a.center, b.center)]

    # vertical
    return [add_horiz_path(a.center, b.center)]

parser = argparse.ArgumentParser()
parser.add_argument("--num_rooms", type=int, default=100)
parser.add_argument("--width", type=float, default=32)
parser.add_argument("--width_dev", type=float, default=20)
parser.add_argument("--height", type=float, default=32)
parser.add_argument("--height_dev", type=float, default=20)
parser.add_argument("--radius", type=float, default=100)
parser.add_argument("--ratio", type=float, default=1.25)

args = parser.parse_args()

ROOMS = []
PATHS = []

# generate random room positions
active_size = args.ratio * args.width * args.height
for i in range(args.num_rooms):
    w = gauss(args.width, args.width_dev)
    h = gauss(args.height, args.height_dev)

    size = w * h
    ROOMS.append(
        Room(random_point_in_circle(args.radius), w, h, size >= active_size))

# push rooms away from each other until they no longer overlap
num_rooms = len(ROOMS)
f = 0.5
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

normalize_rooms(ROOMS)

# create delaunay triangulation of the center points. this will create
# non-overlapping edges between all the center points
active_rooms = [r for r in ROOMS if r.active]
centers = [[r.center.x, r.center.y] for r in active_rooms]
centers = np.array(centers)
tris = Delaunay(centers)

# create the adjacency matrix
# todo: we should be able to do this in one step, and not go
# via the set first..
adj = set()
num_pts = 0
for c in tris.simplices:
    i0, i1, i2 = c[:]
    num_pts = max([num_pts, i0, i1, i2])
    adj.add((min(i0, i1), max(i0, i1)))
    adj.add((min(i1, i2), max(i1, i2)))
    adj.add((min(i2, i0), max(i2, i0)))

num_pts += 1
mtx = []
for _ in range(num_pts):
    mtx.append([0] * num_pts)

for i in range(num_pts):
    for j in range(num_pts):
        a, b = min(i, j), max(i, j)
        if (a, b) in adj:
            mtx[a][b] = 1

# find the MST of the triangulation
x = csr_matrix(mtx)
mst = minimum_spanning_tree(x)

paths = []
# extract the edges from the adjacency matrix, and create the paths
# between the connected rooms
d = mst.todense()
mst_edges = []
for i in range(num_pts):
    for j in range(num_pts):
        if d.item(i, j):
            mst_edges.append((i, j))
            paths += add_path(active_rooms[i], active_rooms[j])

# active any rooms that the paths intersect
for path in paths:
    for room in ROOMS:
        if room.active:
            continue
        rr = (room.top_left, room.bottom_right)
        if rect_overlap(path, rr):
            room.bonus = True

im0, rows = image_from_rooms(active_rooms, ROOMS, tris.simplices, mst_edges, paths)
im0.show()

rows = prune_array(rows)

for row in rows:
    print ''.join(row)
