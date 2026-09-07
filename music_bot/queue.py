from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class QueueJob:
    user_id: int
    update: Any
    url: str
    reply_to: int | None
    status: Any


class DownloadQueue:
    def __init__(self, worker: Callable[[QueueJob], Awaitable[None]], workers: int = 2):
        self._worker = worker
        self._queue: asyncio.Queue[QueueJob] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []
        self._workers = workers

    async def start(self) -> None:
        if self._tasks:
            return
        self._tasks = [asyncio.create_task(self._run(), name=f"download-worker-{i}") for i in range(self._workers)]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def enqueue(self, job: QueueJob) -> int:
        await self.start()
        position = self.pending_count(job.user_id) + 1
        await self._queue.put(job)
        return position

    def pending_count(self, user_id: int | None = None) -> int:
        jobs = list(self._queue._queue)
        return sum(1 for job in jobs if user_id is None or job.user_id == user_id)

    def remove_user(self, user_id: int) -> int:
        kept = []
        removed = 0
        while not self._queue.empty():
            job = self._queue.get_nowait()
            if job.user_id == user_id:
                removed += 1
                self._queue.task_done()
            else:
                kept.append(job)
        for job in kept:
            self._queue.put_nowait(job)
        return removed

    async def _run(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                await self._worker(job)
            except asyncio.CancelledError:
                raise
            except Exception:
                # The worker owns user-facing error reporting.
                pass
            finally:
                self._queue.task_done()
