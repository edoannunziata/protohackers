import asyncio
import json
import logging
from collections import defaultdict
from itertools import count

HOST = "0.0.0.0"
PORT = 40000
SEED = 22801763489  # One-billionth prime number


class PrimeTest:
    def __init__(self):
        self.__P = {}
        self.__gen = self.__primes()
        self.__top = 0

    @staticmethod
    def __primes():
        ps = defaultdict(list)
        for i in count(2):
            if i not in ps:
                yield i
                ps[i**2].append(i)
            else:
                for n in ps[i]:
                    ps[i + (n if n == 2 else 2 * n)].append(n)
                del ps[i]

    def __next_prime(self) -> int:
        i = next(self.__gen)
        logging.debug(f"Prime found: {i}")
        self.__P[i] = None
        self.__top = max(self.__top, i)
        return i

    def is_prime(self, n: int) -> bool:
        # Is it a known prime?
        if n in self.__P:
            return True

        # Is it a known composite?
        if n <= self.__top and n not in self.__P:
            return False

        # Trial division
        for p in self.__P:
            if p * p > n:
                return True
            if n % p == 0:
                return False

        # Make new primes on the fly until sqrt
        while True:
            p = self.__next_prime()
            if p * p > n:
                return True
            if n % p == 0:
                return False


pt = PrimeTest()


async def handle(r: asyncio.StreamReader, w: asyncio.StreamWriter):
    def write_json(d):
        w.write(json.dumps(d).encode("utf8"))
        w.write(b"\n")

    while not r.at_eof():
        try:
            o = json.loads((await r.readuntil(b"\n")).decode("utf8"))
            logging.debug(f"Request: {o}")
            method = o["method"]
            number = o["number"]
            if method != "isPrime":
                raise ValueError()
            if type(number) == int:
                write_json({"method": method, "prime": pt.is_prime(number)})
            elif type(number) == float:
                write_json({"method": method, "prime": False})
            else:
                raise ValueError()
        except asyncio.LimitOverrunError:
            write_json({"error": "limit_overrun"})
            break
        except asyncio.IncompleteReadError:
            write_json({"error": "invalid_terminator"})
            break
        except (ValueError, KeyError):
            write_json({"error": "invalid_json"})
            break
    await w.drain()
    w.close()


async def main():
    logging.basicConfig(level=logging.DEBUG)
    pt.is_prime(SEED)
    server = await asyncio.start_server(handle, HOST, PORT)
    logging.info("Server Ready.")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
