import dungeon_pb2
from utils import fnv32a
import struct
from settings import SERVER_LOG


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


def create_request_header(token, msg_name):
    header = dungeon_pb2.Header()
    header.status.CopyFrom(create_status(0))
    header.msg_hash = fnv32a(msg_name)
    header.token = token if token is not None else 0
    header.is_response = False
    return header


def create_broadcast_header(msg_name):
    return create_request_header(None, msg_name)


def send_message(ws, header, body):
    header_buf = header.SerializeToString()
    body_buf = body.SerializeToString()
    preamble_fmt = '!HI'
    preamble = struct.pack(preamble_fmt, len(header_buf), len(body_buf))
    ws.write_message(preamble + header_buf + body_buf, binary=True)


class MessageBroker(object):
    def __init__(self):
        self.handlers = {}
        self.hash_to_class = {}

    def register_handler(self, msg_name, cls, fn):
        msg_hash = fnv32a(msg_name)
        SERVER_LOG.info(
            'Registering handler for: %r, hash: %r', msg_name, msg_hash)
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
