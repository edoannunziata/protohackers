import asyncio
import json
import logging
from collections import defaultdict

HOST = "0.0.0.0"
PORT = 40000

VERSION = 'udp keystore 1.0'

class Store:
    def __init__(self):
        self.d = defaultdict(str)

    def get(self, key):
        if key == 'version':
            return VERSION
        else:
            return self.d[key]

    def set(self, key, value):
        if key == 'version':
            pass
        else:
            self.d[key] = value

s = Store()


class EchoServerProtocol(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode('utf8')
        parts = message.split('=')
        if len(parts) == 1:
            key = parts[0]
            value = s.get(parts[0])
            response = f'{key}={value}'.encode('utf8')
            self.transport.sendto(response, addr)
        else:
            key = parts[0]
            value = '='.join(parts[1:])
            s.set(key, value)


async def main():
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: EchoServerProtocol(),
        local_addr=(HOST, PORT))
    logging.info("Server Ready.")
    try:
        await asyncio.sleep(1000)
    finally:
        transport.close()


if __name__ == "__main__":
    asyncio.run(main())

