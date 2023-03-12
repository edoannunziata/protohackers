import asyncio
import logging
import re


UPSTREAM_HOST = "chat.protohackers.com"
UPSTREAM_PORT = 16963
HOST = "0.0.0.0"
PORT = 40000

PATTERN = re.compile(r"(^|\s)(7[a-zA-Z0-9]{25,34})(?=($|\s))")


class ConnectionDropped(Exception):
    ...


def replace(s: bytes):
    def f(m):
        TARGET_ADDR = "7YWHMfk9JZe0LM0g1ZauHuiSxhI"
        return f"{m.group(1)}{TARGET_ADDR}"

    return re.sub(PATTERN, f, s.decode('utf8')).encode('utf8')


async def handle(r: asyncio.StreamReader, w: asyncio.StreamWriter):
    ur, uw = None, None

    async def upstream():
        while not r.at_eof():
            content = await r.readline()
            uw.write(replace(content))
        raise ConnectionDropped()

    async def downstream():
        while not ur.at_eof():
            content = await ur.readline()
            w.write(replace(content))
        raise ConnectionDropped()

    async def cleanup():
        await uw.drain()
        uw.close()
        await uw.wait_closed()
        await w.drain()
        w.close()

    try:
        ur, uw = await asyncio.open_connection(UPSTREAM_HOST, UPSTREAM_PORT)
        upstream_task = asyncio.create_task(upstream())
        downstream_task = asyncio.create_task(downstream())
        await asyncio.gather(upstream_task, downstream_task)
    except ConnectionDropped:
        await cleanup()


async def main():
    logging.basicConfig(level=logging.DEBUG)
    server = await asyncio.start_server(handle, HOST, PORT)
    logging.info("Server Ready.")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
