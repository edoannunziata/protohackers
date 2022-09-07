import asyncio
import logging

HOST = "0.0.0.0"
PORT = 40000


async def handle(r, w):
    w.write(await r.read())
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
