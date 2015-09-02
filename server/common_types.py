import types_pb2


class Pos(object):
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, rhs):
        return Pos(self.x + rhs.x, self.y + rhs.y)

    def __radd__(self, rhs):
        return Pos(self.x + rhs.x, self.y + rhs.y)

    def to_protocol(self):
        pos = types_pb2.Pos()
        pos.x = self.x
        pos.y = self.y
        return pos

    @classmethod
    def from_protocol(cls, proto):
        return cls(proto.x, proto.y)
