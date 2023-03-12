import uuid
import struct
import asyncio
import logging
from collections import defaultdict

HOST = "0.0.0.0"
PORT = 40000


class State:
    def __init__(self):
        self.dispatchers = defaultdict(list)
        self.cameras = {}
        self.obs = defaultdict(list)
        self.roads = {}

    def add_camera(self, id):
        ...

    def add_dispatcher(self, id, roads):
        ...

    def register(self, cameraid, plate):
        ...


class Error:
    def __init__(self, content: str):
        self.content = content.encode('utf8')

    def to_bytes(self):
        content_len = len(self.content)
        if not 0 <= content_len <= 255:
            raise ValueError()
        return struct.pack(f"!\x10{content_len + 1}p", self.content)


class Ticket:
    def __init__(self, plate, road, mile1, timestamp1, mile2, timestamp2, speed):
        self.plate = plate.encode('utf8')
        self.road = road
        self.mile1 = mile1
        self.timestamp1 = timestamp1
        self.mile2 = mile2
        self.timestamp2 = timestamp2
        self.speed = speed

    def to_bytes(self):
        plate_len = len(self.plate)
        return struct.pack(f"!\x21{plate_len + 1}pHHIHIH",
                           self.plate, self.road, self.mile1, self.timestamp1,
                           self.mile2, self.timestamp2, self.speed)


class Heartbeat:
    def to_bytes(self):
        return b"\x41"


class ByteBuffer:
    def __init__(self, b: bytes):
        self.b = b

    def consume(self, n):
        if len(self.b) < n:
            raise ValueError()
        sl, self.b = self.b[:n], self.b[n:]
        return sl

    def get_u8(self):
        return int(self.consume(1)[0])

    def get_u16(self):
        u16, = struct.unpack(f"!H", self.consume(2))
        return u16

    def get_u32(self):
        u32, = struct.unpack(f"!I", self.consume(4))
        return u32

    def get_pascal_str(self):
        length = int(self.b[0])
        if not 0 <= length <= 256:
            raise ValueError()
        raw, = struct.unpack(f"!{1 + length}p", self.consume(1 + length))
        return raw.decode('utf8')


class Plate:
    def __init__(self, plate: str, timestamp: int):
        self.plate = plate
        self.timestamp = timestamp

    @classmethod
    def from_bytes(cls, b: bytes):
        buf = ByteBuffer(b)
        if buf.get_u8() != 0x20:
            raise ValueError()
        plate = buf.get_pascal_str()
        timestamp = buf.get_u32()
        return Plate(plate, timestamp)


class WantHeartbeat:
    def __init__(self, interval: int):
        self.interval = interval

    @classmethod
    def from_bytes(cls, b: bytes):
        buf = ByteBuffer(b)
        if buf.get_u8() != 0x40:
            raise ValueError()
        interval = buf.get_u32()
        return WantHeartbeat(interval)


class IAmCamera:
    def __init__(self, road: int, mile: int, limit: int):
        self.road = road
        self.mile = mile
        self.limit = limit

    @classmethod
    def from_bytes(cls, b: bytes):
        buf = ByteBuffer(b)
        if buf.get_u8() != 0x80:
            raise ValueError()
        road = buf.get_u16()
        mile = buf.get_u16()
        limit = buf.get_u16()
        return IAmCamera(road, mile, limit)


class IAmDispatcher:
    def __init__(self, roads):
        self.roads = roads

    @classmethod
    def from_bytes(cls, b: bytes):
        buf = ByteBuffer(b)
        if buf.get_u8() != 0x81:
            raise ValueError()
        numroads = buf.get_u8()
        roads = [buf.get_u16() for _ in range(numroads)]
        return IAmDispatcher(roads)


def msg_from_bytes(b: bytes):
    if b[0] == 0x20:
        ...
    if b[0] == 0x40:
        ...
    if b[0] == 0x80:
        ...
    if b[0] == 0x81:
        ...
        
STATE = State()

async def heartbeat(ds: int, w: asyncio.StreamWriter):
    while True:
        asyncio.sleep(ds * 0.1)
        w.write(Heartbeat().to_bytes())

async def handle(r: asyncio.StreamReader, w: asyncio.StreamWriter):
    clientid = uuid.uuid4()
    while not r.at_eof():
        try:
            pass
        except (ValueError, asyncio.IncompleteReadError):
            pass
    await w.drain()
    w.close()


async def main():
    logging.basicConfig(level=logging.DEBUG)
    server = await asyncio.start_server(handle, HOST, PORT)
    logging.info("Server Ready.")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
