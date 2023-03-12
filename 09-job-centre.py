import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List
from heapq import heappush, heappop

HOST = "0.0.0.0"
PORT = 40000

@dataclass(order=True)
class Job:
    pri: int
    jid: int = field(compare=False)
    queue: str = field(compare=False)
    task: dict = field(compare=False)


class Context:
    def __init__(self):
        self.queues = defaultdict(list)
        self.cond = asyncio.Condition()
        self.jid = 1
        self.clientid = 1
        self.working = defaultdict(dict)
        self.deleted = set()
        self.posted = set()

    def is_live(self, jid):
        return jid in self.posted and jid not in self.deleted
    
    async def get_client_id(self) -> int:
        async with self.cond:
            self.clientid += 1
            return self.clientid

    async def put(self, queue: str, task: dict, pri: int) -> int:
        async with self.cond:
            self.jid += 1
            heappush(self.queues[queue], Job(-pri, self.jid, queue, task))
            self.posted.add(self.jid)
            self.cond.notify()
            return self.jid
        
    async def get(self, client: int, queues: List[str], wait: bool) -> Job | None:
        def jobs_available() -> bool:
            return any(self.queues[q] for q in queues)
        
        def pop_job() -> Job:
            def min_pri(queue: str) -> int:
                if self.queues[queue]:
                    return self.queues[queue][0].pri
                else:
                    return 1

            to_pop = min((q for q in queues), key=min_pri)
            return heappop(self.queues[to_pop])
        
        async with self.cond:
            while True:
                if not jobs_available() and not wait:
                    return None
                if wait:
                    await self.cond.wait_for(jobs_available)

                job = pop_job()
                self.working[client][job.jid] = job
                if self.is_live(job.jid):
                    return job
        
    async def delete(self, jid: int) -> bool:
        async with self.cond:
            if self.is_live(jid):
                self.deleted.add(jid)
                return True
            else:
                return False
        
    async def abort(self, jid: int, client: int) -> bool:
        async with self.cond:
            job = self.working[client].get(jid)
            if job is None or not self.is_live(jid):
                return False
            heappush(self.queues[job.queue], job)
            del self.working[client][jid]
            self.cond.notify()
            return True

    async def disconnect(self, client: int):
        for jid in set(self.working[client].keys()):
            await self.abort(jid, client)

        async with self.cond:
            del self.working[client]
            

context = Context()

async def handle(r: asyncio.StreamReader, w: asyncio.StreamWriter):
    def write_json(d):
        w.write(json.dumps(d).encode("utf8"))
        w.write(b"\n")

    clientid = await context.get_client_id()

    while not r.at_eof():
        try:
            o = json.loads((await r.readline()).decode("utf8"))
            match o['request']:
                case "get":
                    wait = o.get('wait', False)
                    job = await context.get(clientid, o['queues'], wait)
                    if job:
                        write_json({
                            "status": "ok", 
                            "id": job.jid, 
                            "job": job.task, 
                            "pri": -job.pri, 
                            "queue": job.queue})
                    else:
                        write_json({"status": "no-job"})
                case "put":
                    jid = await context.put(o['queue'], o['job'], o['pri'])
                    write_json({"status": "ok", "id": jid})
                case "delete":
                    success = await context.delete(o['id'])
                    if success:
                        write_json({"status": "ok"})
                    else:
                        write_json({"status": "no-job"})
                case "abort":
                    success = await context.abort(o['id'], clientid)
                    if success:
                        write_json({"status": "ok"})
                    else:
                        write_json({"status": "no-job"})
        except (ValueError, KeyError):
            write_json({"status": "error", "error": "invalid-json"})
        except ConnectionError:
            break
    await context.disconnect(clientid)
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
