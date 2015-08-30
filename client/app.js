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
var PlayerActionRequest = Builder.build('dungeon.PlayerActionRequest');

var socket = new WebSocket('ws://127.0.0.1:8888/websocket');
socket.binaryType = 'arraybuffer';

var NEXT_TOKEN = 1;

var flags = { LEFT: 0x1, RIGHT: 0x2, UP: 0x4, DOWN: 0x8 };

var POS = null;

var wallSprites = function() {
    // flags for the oryx tile set. flags indicate which sides are free
    var h = 1;
    var res = {};
    var l = flags.LEFT;
    var r = flags.RIGHT;
    var u = flags.UP;
    var d = flags.DOWN;
    res[0 + 0 + 0 + 0] = [4, h];
    res[0 + 0 + 0 + l] = [24, h];
    res[0 + 0 + r + 0] = [23, h];
    res[0 + 0 + r + l] = [15, h];
    res[0 + u + 0 + 0] = [22, h];
    res[0 + u + 0 + l] = [17, h];
    res[0 + u + r + 0] = [18, h];
    res[0 + u + r + l] = [14, h];

    res[d + 0 + 0 + 0] = [25, h];
    res[d + 0 + 0 + l] = [19, h];
    res[d + 0 + r + 0] = [20, h];
    res[d + 0 + r + l] = [16, h];
    res[d + u + 0 + 0] = [12, h];
    res[d + u + 0 + l] = [11, h];
    res[d + u + r + 0] = [13, h];
    res[d + u + r + l] = [1, h];

    return res;
}();

var floorSprites = [[29, 26], [30, 26]];

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

function handleLobbyResponse(header, body) {
    console.log('lobby response', header, body);
}

function getTile(level, x, y) {

    var h = level.length;
    var w = level[0].length;

    var isInside = function(x, y) {
        return x >= 0 && x < w && y >= 0 && y < h;
    };

    var isFilled = function(x, y) {
        return isInside(x, y) && level[y][x] == 'x';
    };

    var res = 0;
    var filled = isFilled(x, y);
    if (x === 0 || (filled && level[y][x-1] == ' '))
        res += 0x1;
    if (x === w-1 || (filled && level[y][x+1] == ' '))
        res += 0x2;
    if (y === 0 || (filled && level[y-1][x] == ' '))
        res += 0x4;
    if (y === h-1 || (filled && level[y+1][x] == ' '))
        res += 0x8;
    return res;
}

function floatToInt(r) {
    // oh Javascript, you so crazy!
    return 0 | r;
}

function handleNewGameResponse(header, body) {

    var ll = body.level;
    level = [];
    var i, j;
    for (i = 0; i < ll.height; ++i) {
        var row = [];
        for (j = 0; j < ll.width; ++j) {
            row.push(' ');
        }
        level.push(row);
    }

    _.each(ll.wall, function(w) {
        level[w.y][w.x] = 'x';
    });

    for (i=0; i < ll.height; ++i) {
        for (j=0; j < ll.width; ++j) {

            var tile = GAME.add.sprite(j*24, i*24, 'worldSprites');

            var tileSprite;
            if (level[i][j] == ' ') {
                tileSprite = floorSprites[floatToInt(Math.random() * floorSprites.length)];
            } else {
                tileSprite = wallSprites[getTile(level, j, i)];
            }
            tile.frameName = sprintf(
                'sprite%02d_%02d',
                tileSprite[0], tileSprite[1]);
        }
    }

    var charSprite = GAME.add.sprite(1*24, 1*24, 'creatureSprites');
    charSprite.frameName = 'sprite01_01';
    // charSprite.anchor.setTo(0.5, 1);
    // charSprite.scale.x *= -1;

    return level;
}

var MESSAGE_BROKER = new MessageBroker();
MESSAGE_BROKER.registerHandler('dungeon.LobbyStatusResponse',
    LobbyStatusResponse,
    handleLobbyResponse);

MESSAGE_BROKER.registerHandler('dungeon.NewGameResponse',
    NewGameResponse,
    handleNewGameResponse);

var CURSORS;
var GAME = new Phaser.Game(800, 600, Phaser.AUTO, '', {
    preload: preload,
    create: create,
    update: update
});

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
    // GAME.load.image('logo', 'phaser.png');

    GAME.load.atlas(
        'worldSprites',
        'gfx/oryx_16bit_fantasy_world_trans.png',
        'gfx/oryx_16bit_fantasy_world_trans.json');

    GAME.load.atlas(
        'creatureSprites',
        'gfx/oryx_16bit_fantasy_creatures_trans.png',
        'gfx/oryx_16bit_fantasy_creatures_trans.json');
}

function create () {
    var button = GAME.add.button(GAME.world.centerX - 95, 400, 'button', actionOnClick, this, 2, 1, 0);
    CURSORS = GAME.input.keyboard.createCursorKeys();

    // stop keys from propagating to the browser
    GAME.input.keyboard.addKeyCapture([
        Phaser.Keyboard.LEFT, Phaser.Keyboard.RIGHT, Phaser.Keyboard.SPACEBAR]);
}

function isKeyTriggered(key) {
    if (key.justPressed(50)) {
        key.waitForTrigger = true;
        return false;
    } else if (key.isUp && key.waitForTrigger) {
        key.waitForTrigger = false;
        return true;
    } else {
        return false;
    }
}

function update() {

    var req = new PlayerActionRequest();
    if (isKeyTriggered(CURSORS.left)) {
        req.action = PlayerActionRequest.Action.MOVE_LEFT;
    } else if (isKeyTriggered(CURSORS.right)) {
        req.action = PlayerActionRequest.Action.MOVE_RIGHT;
    } else if (isKeyTriggered(CURSORS.up)) {
        req.action = PlayerActionRequest.Action.MOVE_UP;
    } else if (isKeyTriggered(CURSORS.down)) {
        req.action = PlayerActionRequest.Action.MOVE_DOWN;
    }

    if (req.action) {
        sendRequest('dungeon.PlayerActionRequest', req);
    }
}

function actionOnClick () {
    sendRequest('dungeon.NewGameRequest', new NewGameRequest());
}
