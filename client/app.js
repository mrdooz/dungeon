var ByteBuffer = dcodeIO.ByteBuffer;

var Builder = dcodeIO.ProtoBuf.newBuilder();
dcodeIO.ProtoBuf.loadProtoFile("common/types.proto", Builder);
dcodeIO.ProtoBuf.loadProtoFile("common/level.proto", Builder);
dcodeIO.ProtoBuf.loadProtoFile("common/dungeon.proto", Builder);
var Header = Builder.build('dungeon.Header');
var LobbyStatusRequest = Builder.build('dungeon.LobbyStatusRequest');
var LobbyStatusResponse = Builder.build('dungeon.LobbyStatusResponse');
var NewGameRequest = Builder.build('dungeon.NewGameRequest');
var NewGameResponse = Builder.build('dungeon.NewGameResponse');

var NEXT_TOKEN = 1;

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

function HandleNewGameResponse(header, body) {
    console.log('new game response', body);
}

var MESSAGE_BROKER = new MessageBroker();
MESSAGE_BROKER.registerHandler('dungeon.LobbyStatusResponse',
    LobbyStatusResponse,
    HandleLobbyResponse);

MESSAGE_BROKER.registerHandler('dungeon.NewGameResponse',
    NewGameResponse,
    HandleNewGameResponse);

var game = new Phaser.Game(
    800, 600, Phaser.AUTO, '', { preload: preload, create: create });

function sendRequest(name, req) {
    var header = new Header();
    header.msg_hash = fnv32a(name);
    var headerBuf = header.encode().toArrayBuffer();

    var bodyBuf = req.encode().toArrayBuffer();
    var bb = new ByteBuffer(2 + 2 + headerBuf.byteLength + bodyBuf.byteLength);
    bb.writeInt16(headerBuf.byteLength);
    bb.writeInt16(bodyBuf.byteLength);
    bb.append(headerBuf);
    bb.append(bodyBuf);
    bb.reset();
    socket.send(bb.toArrayBuffer());
}

var socket = new WebSocket('ws://127.0.0.1:8888/websocket');
socket.binaryType = 'arraybuffer';

  // Handle any errors that occur.
  socket.onerror = function(error) {
    console.log('WebSocket Error: ' + error);
  };


  socket.onopen = function(event) {
    sendRequest('dungeon.LobbyStatusRequest', new LobbyStatusRequest());
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

var button;

function create () {
    var logo = game.add.sprite(game.world.centerX, game.world.centerY, 'logo');
    logo.anchor.setTo(0.5, 0.5);

    button = game.add.button(game.world.centerX - 95, 400, 'button', actionOnClick, this, 2, 1, 0);

    button.onInputOver.add(over, this);
    button.onInputOut.add(out, this);
    button.onInputUp.add(up, this);
}

function up() {
    console.log('button up', arguments);
}

function over() {
    console.log('button over');
}

function out() {
    console.log('button out');
}


function actionOnClick () {
    sendRequest('dungeon.NewGameRequest', new NewGameRequest());
}
