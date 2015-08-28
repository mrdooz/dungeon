var ByteBuffer = dcodeIO.ByteBuffer;
var Builder = dcodeIO.ProtoBuf.loadProtoFile("common/dungeon.proto");
var Header = Builder.build('dungeon.Header');
var LobbyStatusRequest = Builder.build('dungeon.LobbyStatusRequest');
var LobbyStatusResponse = Builder.build('dungeon.LobbyStatusResponse');

function fnv32a(str) {
    var FNV1_32A_INIT = 0x811c9dc5;
    var hval = FNV1_32A_INIT;
    for (var i = 0; i < str.length; ++i)
    {
        hval ^= str.charCodeAt(i);
        hval += (hval << 1) + (hval << 4) + (hval << 7) + (hval << 8) + (hval << 24);
    }
    return hval >>> 0;
}

var MessageBroker = function() {
    this.handlers = {};
    this.hashToClass = {};
};

MessageBroker.prototype.registerHandler = function(msgName, cls, fn) {

    var msgHash = fnv32a(msgName);
    if (_.has(this.hashToClass, msgHash)) {
        console.log('Handler already registered for: ', msgHash);
        return;
    }
    this.hashToClass[msgHash] = cls;
    this.handlers[msgHash] = fn;
};

MessageBroker.prototype.handleMessage = function(header, body) {

    var hash = header.msg_hash;
    if (!_.has(this.hashToClass, hash)) {
        console.log('Unknown msg: ', hash);
        return;
    }

    var bodyMsg = this.hashToClass[hash].decode(body);
    this.handlers[hash](header, bodyMsg);
};

function HandleLobbyResponse(header, body) {
    console.log('lobby response', header, body);
}

var MESSAGE_BROKER = new MessageBroker();
MESSAGE_BROKER.registerHandler('LobbyStatusResponse',
    LobbyStatusResponse,
    HandleLobbyResponse);

var game = new Phaser.Game(
    800, 600, Phaser.AUTO, '', { preload: preload, create: create });

var socket = new WebSocket('ws://127.0.0.1:8888/websocket');
socket.binaryType = 'arraybuffer';

  // Handle any errors that occur.
  socket.onerror = function(error) {
    console.log('WebSocket Error: ' + error);
  };


  socket.onopen = function(event) {

    var header = new Header();
    header.msg_hash = fnv32a('LobbyStatusRequest');
    var headerBuf = header.encode().toArrayBuffer();

    var req = new LobbyStatusRequest();
    var bodyBuf = req.encode().toArrayBuffer();

    var bb = new ByteBuffer(2 + 2 + headerBuf.byteLength + bodyBuf.byteLength);
    bb.writeInt16(headerBuf.byteLength);
    bb.writeInt16(bodyBuf.byteLength);
    bb.append(headerBuf);
    bb.append(bodyBuf);
    bb.reset();
    socket.send(bb.toArrayBuffer());
  };

  socket.onmessage = function(msg) {
    var bb = new ByteBuffer.wrap(msg.data);
    var headerLength = bb.readInt16();
    var bodyLength = bb.readInt16();

    var header = Header.decode(bb.slice(4, 4+headerLength));
    var body = bb.slice(4+headerLength, 4+headerLength+bodyLength);

    MESSAGE_BROKER.handleMessage(header, body);
  };


  socket.onclose = function(event) {
  };

function preload () {
    game.load.image('logo', 'phaser.png');
}

function create () {
    var logo = game.add.sprite(game.world.centerX, game.world.centerY, 'logo');
    logo.anchor.setTo(0.5, 0.5);
}
