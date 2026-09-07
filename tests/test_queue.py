import asyncio

from music_bot.queue import DownloadQueue, QueueJob


def test_queue_counts_and_removes_user_jobs() -> None:
    async def run() -> None:
        async def worker(job: QueueJob) -> None:
            await asyncio.sleep(0.01)

        queue = DownloadQueue(worker, workers=1)
        await queue.start()
        await queue.enqueue(QueueJob(1, None, "one", None, None))
        await queue.enqueue(QueueJob(1, None, "two", None, None))
        await queue.enqueue(QueueJob(2, None, "three", None, None))
        assert queue.remove_user(1) == 2
        await queue.stop()

    asyncio.run(run())
