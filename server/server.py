#! /usr/local/bin/python

import tornado.ioloop
import tornado.web
import tornado.websocket
import uuid
import logging
import struct
import dungeon_pb2
import level_pb2
import types_pb2


CONNECTED_CLIENTS = {}
SERVER_LOG = logging.getLogger('server')


def fnv32a(msg):
    hval = 0x811c9dc5
    fnv_32_prime = 0x01000193
    uint32_max = 2 ** 32
    for s in msg:
        hval = hval ^ ord(s)
        hval = (hval * fnv_32_prime) % uint32_max
    return hval


class Game(object):
    pass


class Player(object):
    def __init__(self, pos):
        self.alive = True
        self.pos = pos


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

level = Level()
level.load('./room1.txt')


class Client(object):
    def __init__(self, client_id):
        self.client_id = client_id
        self.state = 'game-select'


def create_status(code, msg=None):
    status = dungeon_pb2.Status()
    status.code = code
    if msg:
        status.msg = msg
    return status


def create_response_header(req_header, msg_name):
    header = dungeon_pb2.Header()
    header.status.CopyFrom(create_status(0))
    header.msg_hash = fnv32a(msg_name)
    header.token = req_header.token
    header.is_response = True
    return header


def create_request_header(req_header, msg_name):
    header = dungeon_pb2.Header()
    header.status.CopyFrom(create_status(0))
    header.msg_hash = fnv32a(msg_name)
    header.token = req_header.token
    header.is_response = True
    return header


class MessageBroker(object):
    def __init__(self):
        self.handlers = {}
        self.hash_to_class = {}

    def register_handler(self, msg_name, cls, fn):
        msg_hash = fnv32a(msg_name)
        if msg_hash in self.handlers:
            SERVER_LOG.warning('Handler already registered for: %r' % msg_hash)
            return
        self.handlers[msg_hash] = fn
        self.hash_to_class[msg_hash] = cls

    def handle_message(self, ws, header, body):
        msg_hash = header.msg_hash
        handler = self.handlers.get(msg_hash, None)
        if not handler:
            SERVER_LOG.warning('No handler for message: %r', header)
            return False

        cls = self.hash_to_class[msg_hash]
        msg = cls()
        msg.ParseFromString(body)

        handler(ws, header, msg)

        return True

MESSAGE_BROKER = MessageBroker()


def send_message(ws, header, body):
    header_buf = header.SerializeToString()
    body_buf = body.SerializeToString()
    preamble_fmt = '!HH'
    preamble = struct.pack(preamble_fmt, len(header_buf), len(body_buf))
    ws.write_message(preamble + header_buf + body_buf, binary=True)


def handle_new_game_request(ws, header, req):
    res_header = create_request_header(header, 'dungeon.NewGameResponse')
    res_body = dungeon_pb2.NewGameResponse()
    res_body.level.CopyFrom(level.to_protocol())
    send_message(ws, res_header, res_body)


def handle_lobby_status_request(ws, header, req):
    header = create_response_header(header, 'dungeon.LobbyStatusResponse')
    body = dungeon_pb2.LobbyStatusResponse()
    body.num_running_games = 3
    send_message(ws, header, body)


def handle_player_action_request(ws, header, req):
    print req


def register_handlers():
    MESSAGE_BROKER.register_handler(
        'dungeon.NewGameRequest',
        dungeon_pb2.NewGameRequest,
        handle_new_game_request)

    MESSAGE_BROKER.register_handler(
        'dungeon.LobbyStatusRequest',
        dungeon_pb2.LobbyStatusRequest,
        handle_lobby_status_request)

    MESSAGE_BROKER.register_handler(
        'dungeon.PlayerActionRequest',
        dungeon_pb2.PlayerActionRequest,
        handle_player_action_request)


class EchoWebSocket(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        print 'connected'
        client_id = uuid.uuid4()
        self.client_id = client_id
        CONNECTED_CLIENTS[client_id] = Client(client_id)
        SERVER_LOG.info('client connected: %r', client_id)

    def on_message(self, message):
        # message: header_size body_size header body
        preamble_fmt = '!HH'
        header_size, body_size = struct.unpack(preamble_fmt, message[0:4])

        print 'recv. header_size: %d, body_size: %d' % (header_size, body_size)
        header = dungeon_pb2.Header()
        header.ParseFromString(message[4:4 + header_size])

        s = 4 + header_size
        MESSAGE_BROKER.handle_message(self, header, message[s:s + body_size])

    def on_close(self):
        SERVER_LOG.info('client disconnected: %r', self.client_id)
        del CONNECTED_CLIENTS[self.client_id]


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

application = tornado.web.Application([
    (r"/websocket", EchoWebSocket)],
    debug=True
)

if __name__ == "__main__":
    print 'server started'
    logging.basicConfig(filename='server.log', level=logging.DEBUG)
    register_handlers()

    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()
