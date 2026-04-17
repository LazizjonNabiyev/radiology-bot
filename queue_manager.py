import asyncio
from typing import Optional

class AnalysisQueue:
    def __init__(self):
        self._queue = asyncio.Queue()

    async def add_to_queue(self, user_id, message, context, user_data, lang,
                           file_type="photo", is_premium=False) -> int:
        position = self._queue.qsize() + 1
        await self._queue.put({
            "user_id": user_id, "message": message, "context": context,
            "user_data": user_data, "lang": lang,
            "file_type": file_type, "is_premium": is_premium,
        })
        return position

    async def get_next(self) -> Optional[dict]:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def task_done(self):
        try:
            self._queue.task_done()
        except ValueError:
            pass

    @property
    def size(self):
        return self._queue.qsize()
