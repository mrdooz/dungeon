import level_pb2
from random import randint
from common_types import Pos


class Level(object):
    def __init__(self, width=None, height=None):
        self.width = width
        self.height = height
        if self.width:
            self.data = [[' '] * width for i in range(height)]
        else:
            self.data = []

    def __iter__(self):
        w, h = self.width, self.height
        for i in range(h):
            for j in range(w):
                yield i, j, self.data[i][j]

    def load(self, filename):
        lines = []
        max_width = 0
        for line in open(filename).readlines():
            line = line.strip()
            max_width = max(max_width, len(line))
            lines.append(line)

        self.width = max_width
        self.height = len(lines)

        self.data = [[' '] * self.width for i in range(self.height)]

        w, h = self.width, self.height
        for i in range(h):
            for j in range(w):
                if j >= len(lines[i]):
                    break
                self.data[i][j] = lines[i][j]

    def get_start_pos(self):
        while True:
            x, y = randint(0, self.width), randint(0, self.height)
            pos = Pos(x, y)
            if self.is_inside(pos) and not self.is_filled(pos):
                return pos

    def generate(self):
        w, h = self.width, self.height
        for i in range(h):
            for j in range(w):
                if i == 0 or i == h - 1 or j == 0 or j == w - 1:
                    self.data[i][j] = 'x'

    def to_protocol(self):
        level = level_pb2.Level()
        level.width = self.width
        level.height = self.height

        for i, j, d in self:
            if d == 'x':
                w = level.wall.add()
                w.x = j
                w.y = i
        return level

    def is_inside(self, pos):
        return (
            pos.x >= 0 and pos.x < self.width and
            pos.y >= 0 and pos.y < self.height
        )

    def is_filled(self, pos):
        return self.data[pos.y][pos.x] == 'x'

    def is_valid_pos(self, pos):
        return self.is_inside(pos) and not self.is_filled(pos)
