import asyncio
import logging
import statistics
import struct
import bisect
from statistics import mean
from itertools import takewhile, islice

HOST = "0.0.0.0"
PORT = 40000

request = struct.Struct('!cii')
response = struct.Struct('!i')


class PriceHistory:
    def __init__(self):
        self.times = []
        self.values = {}

    def insert_value(self, time, value):
        bisect.insort_right(self.times, time)
        self.values[time] = value

    def mean_value_between(self, lo, hi):
        try:
            j = bisect.bisect_left(self.times, lo)
            V = takewhile(lambda u: lo <= u <= hi, islice(self.times, j, None))
            return mean(map(lambda u: self.values[u], V))
        except statistics.StatisticsError:
            return 0


async def handle(r: asyncio.StreamReader, w: asyncio.StreamWriter):
    H = PriceHistory()
    while not r.at_eof():
        try:
            what, a, b = request.unpack(await r.readexactly(9))
            logging.debug(f"Request: {id} - {what} {a} {b}")
            if what == b'I':
                H.insert_value(a, b)
            elif what == b'Q':
                m = int(H.mean_value_between(a, b))
                logging.debug(f"Response: {m}")
                w.write(response.pack(m))
        except (ValueError, asyncio.IncompleteReadError):
            w.write(response.pack(-1))
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