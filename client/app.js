var ByteBuffer = dcodeIO.ByteBuffer;
var Builder = dcodeIO.ProtoBuf.loadProtoFile("common/dungeon.proto");
var Header = Builder.build('dungeon.Header');
var LobbyStatusRequest = Builder.build('dungeon.LobbyStatusRequest');
var LobbyStatusResponse = Builder.build('dungeon.LobbyStatusResponse');

fnv32a = function(str) {
    var FNV1_32A_INIT = 0x811c9dc5;
    var hval = FNV1_32A_INIT;
    for (var i = 0; i < str.length; ++i)
    {
        hval ^= str.charCodeAt(i);
        hval += (hval << 1) + (hval << 4) + (hval << 7) + (hval << 8) + (hval << 24);
    }
    return hval >>> 0;
};

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
    var body = LobbyStatusResponse.decode(
        bb.slice(4+headerLength, 4+headerLength+bodyLength));
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
