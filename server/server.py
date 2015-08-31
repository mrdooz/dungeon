#! /usr/local/bin/python

import tornado.ioloop
import tornado.web
import tornado.websocket
import uuid
import logging
import struct
import dungeon_pb2
from common_types import Pos
from level import Level
from settings import SERVER_LOG
from message_broker import (
    create_request_header,
    create_response_header, send_message,
    MessageBroker)

CONNECTED_CLIENTS = {}
MESSAGE_BROKER = MessageBroker()
MAX_PLAYERS_PER_GAME = 5


class Player(object):
    def __init__(self, player_id, pos):
        self.alive = True
        self.id = player_id
        self.pos = pos


class Game(object):
    def __init__(self):
        self.players = {}
        self.level = Level()
        self.level.load('./room1.txt')
        self.next_player_id = 1

    def get_player_id(self):
        res = self.next_player_id
        self.next_player_id += 1
        return res

    def add_player(self, client, player_id, pos):
        self.players[client] = Player(player_id, pos)

    def get_player_states(self, players):
        """
        Copy the current player states into the supplied object
        """
        for player in self.players.values():
            p = players.add()
            p.id = player.id
            p.pos.CopyFrom(player.pos.to_protocol())

    def player_action(self, client, header, action):
        player = self.players.get(client, None)
        if not player:
                # TODO: log error
            return

        new_pos = None
        if action.action == action.MOVE_LEFT:
            new_pos = player.pos + Pos(-1, 0)
        elif action.action == action.MOVE_RIGHT:
            new_pos = player.pos + Pos(+1, 0)
        elif action.action == action.MOVE_UP:
            new_pos = player.pos + Pos(0, -1)
        elif action.action == action.MOVE_DOWN:
            new_pos = player.pos + Pos(0, +1)

        if new_pos:
            if self.level.is_valid_pos(new_pos):
                player.pos = new_pos

                # send the player response
                response = dungeon_pb2.PlayerActionResponse()
                self.get_player_states(response.players)
                send_message(
                    client,
                    create_response_header(
                        header,
                        'dungeon.PlayerActionResponse'),
                    response)
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
            game = Game()
            self.games.append(game)
        else:
            for game in self.games:
                if len(game.players) <= MAX_PLAYERS_PER_GAME:
                    break
            else:
                game = Game()
                self.games.append(game)

        player_id = game.get_player_id()
        game.add_player(ws, player_id, game.level.get_start_pos())
        ws.game = game
        ws.player_id = player_id

        res_header = create_request_header(header, 'dungeon.NewGameResponse')
        res_body = dungeon_pb2.NewGameResponse()
        res_body.level.CopyFrom(game.level.to_protocol())
        res_body.player_id = player_id
        send_message(ws, res_header, res_body)

    def handle_lobby_status_request(self, ws, header, req):
        header = create_response_header(header, 'dungeon.LobbyStatusResponse')
        body = dungeon_pb2.LobbyStatusResponse()
        body.num_running_games = 3
        send_message(ws, header, body)

    def handle_player_action_request(self, ws, header, req):
        # find game for the player
        game = getattr(ws, 'game', None)
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
