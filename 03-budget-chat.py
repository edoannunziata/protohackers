import asyncio
import logging
from dataclasses import dataclass
from typing import Dict


HOST = "0.0.0.0"
PORT = 40000

USERS: Dict[str, asyncio.Queue] = {}

WELCOME_MESSAGE = "Welcome to budgetchat! What shall I call you?\n"

@dataclass
class Message:
    sender: str
    content: str

    def __str__(self):
        return f'[{self.sender}] {self.content}\n'


@dataclass
class ServerMessage:
    content: str
    
    def __str__(self):
        return f'* {self.content}\n'


def connect_user(username: str):
    if username in USERS:
        raise ValueError()
    if len(username) < 1:
        raise ValueError()
    if not username.isalnum():
        raise ValueError()
    USERS[username] = asyncio.Queue()
    for name, queue in USERS.items():
        if name != username:
            queue.put_nowait(ServerMessage(f'{username} has entered the room'))
    logging.info(f'User connected: {username}')


def disconnect_user(username: str):
    if username in USERS:
        del USERS[username]
        for name, queue in USERS.items():
            queue.put_nowait(ServerMessage(f'{username} has left the room'))
        logging.info(f'User disconnected: {username}')


def send_message(m: Message):
    for name, queue in USERS.items():
        if name != m.sender:
            queue.put_nowait(m)
    logging.info(f'Message sent: {str(m)}')


def room_membership(username: str):
    U = ', '.join(u for u in USERS if u != username)
    return str(ServerMessage(f"The room contains: {U}"))


async def handle(r: asyncio.StreamReader, w: asyncio.StreamWriter):
    username = None
    worker_task = None

    async def worker_message():
        while True:
            m = await USERS[username].get()
            w.write(str(m).encode('utf8'))
            USERS[username].task_done()

    async def disconnect():
        if username is not None:
            disconnect_user(username)
        if worker_task is not None:
            worker_task.cancel()
            await asyncio.gather(worker_task)
        await w.drain()
        w.close()

    try:
        w.write(WELCOME_MESSAGE.encode('utf8'))
        username = (await r.readline()).decode('utf8').strip()
        connect_user(username)
        worker_task = asyncio.create_task(worker_message())
        w.write(room_membership(username).encode('utf8'))
        while not r.at_eof():
            content = (await r.readline()).decode('utf8').strip()
            if content:
                send_message(Message(username, content))
    except ValueError:
        pass
    finally:
        await disconnect()


async def main():
    logging.basicConfig(level=logging.DEBUG)
    server = await asyncio.start_server(handle, HOST, PORT)
    logging.info("Server Ready.")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
