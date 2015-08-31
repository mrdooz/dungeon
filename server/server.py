#! /usr/local/bin/python

import tornado.ioloop
import tornado.web
import tornado.websocket
import uuid
import logging
import struct
import dungeon_pb2
from level import Level
from settings import SERVER_LOG
from message_broker import (
    create_request_header,
    create_response_header, send_message,
    MessageBroker)

CONNECTED_CLIENTS = {}
MESSAGE_BROKER = MessageBroker()


class Player(object):
    def __init__(self, pos):
        self.alive = True
        self.pos = pos


class Pos(object):
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, rhs):
        return Pos(self.x + rhs.x, self.y + rhs.y)

    def __radd__(self, rhs):
        return Pos(self.x + rhs.x, self.y + rhs.y)

    @classmethod
    def from_protocol(cls, proto):
        return cls(proto.x, proto.y)


class Game(object):
    def __init__(self):
        self.players = {}
        self.level = Level()
        self.level.load('./room1.txt')

    def add_player(self, client, pos):
        self.players[client] = Player(pos)

    def player_action(self, client, header, action):
        player = self.players.get(client, None)
        if not player:
                # TODO: log error
            return

        print action

        # import pdb; pdb.set_trace()
        new_pos = None
        if action.action == 1:
            new_pos = player.pos + Pos(-1, 0)
        elif action.action == 2:
            new_pos = player.pos + Pos(+1, 0)
        elif action.action == 3:
            new_pos = player.pos + Pos(0, -1)
        elif action.action == 4:
            new_pos = player.pos + Pos(0, +1)

        if new_pos:
            if self.level.is_valid_pos(new_pos):
                player.pos = new_pos
            else:
                # TODO: log error
                pass


class Client(object):
    def __init__(self, client_id):
        self.client_id = client_id
        self.state = 'game-select'


class ConnectionHandler(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        client_id = uuid.uuid4()
        self.client_id = client_id
        CONNECTED_CLIENTS[client_id] = Client(client_id)
        SERVER_LOG.info('client connected: %r', client_id)

    def on_message(self, message):
        # message: header_size body_size header body
        preamble_fmt = '!HH'
        header_size, body_size = struct.unpack(preamble_fmt, message[0:4])

        SERVER_LOG.info(
            'recv. header_size: %d, body_size: %d',
            header_size, body_size)
        header = dungeon_pb2.Header()
        header.ParseFromString(message[4:4 + header_size])

        s = 4 + header_size
        MESSAGE_BROKER.handle_message(self, header, message[s:s + body_size])

    def on_close(self):
        SERVER_LOG.info('client disconnected: %r', self.client_id)
        del CONNECTED_CLIENTS[self.client_id]


class GameServer(object):

    def __init__(self):
        self.games = []
        self.clients_to_games = {}

    def register_handlers(self):
        MESSAGE_BROKER.register_handler(
            'dungeon.NewGameRequest',
            dungeon_pb2.NewGameRequest,
            self.handle_new_game_request)

        MESSAGE_BROKER.register_handler(
            'dungeon.LobbyStatusRequest',
            dungeon_pb2.LobbyStatusRequest,
            self.handle_lobby_status_request)

        MESSAGE_BROKER.register_handler(
            'dungeon.PlayerActionRequest',
            dungeon_pb2.PlayerActionRequest,
            self.handle_player_action_request)

    def handle_new_game_request(self, ws, header, req):
        # check if any games are in progress, otherwise create one
        if not self.games:
            self.games.append(Game())

        # TODO: pick the best matching
        game = self.games[0]
        game.add_player(ws, Pos(1, 1))
        self.clients_to_games[ws] = game

        res_header = create_request_header(header, 'dungeon.NewGameResponse')
        res_body = dungeon_pb2.NewGameResponse()
        res_body.level.CopyFrom(game.level.to_protocol())
        send_message(ws, res_header, res_body)

    def handle_lobby_status_request(self, ws, header, req):
        header = create_response_header(header, 'dungeon.LobbyStatusResponse')
        body = dungeon_pb2.LobbyStatusResponse()
        body.num_running_games = 3
        send_message(ws, header, body)

    def handle_player_action_request(self, ws, header, req):
        # find game for the player
        game = self.clients_to_games.get(ws, None)
        if not game:
            SERVER_LOG.warning('Unable to find game for client: %r', ws)
            # TODO: send error
            return

        game.player_action(ws, header, req)


SERVER = GameServer()


application = tornado.web.Application([
    (r"/websocket", ConnectionHandler)],
    debug=True
)

if __name__ == "__main__":
    print 'server started'
    logging.basicConfig(filename='server.log', level=logging.DEBUG)
    SERVER.register_handlers()

    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()
