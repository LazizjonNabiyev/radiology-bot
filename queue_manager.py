"""
queue_manager.py — navbat tizimi
Barcha foydalanuvchilar teng xizmat oladi.
Bir vaqtda ko'p so'rov kelsa ham, birma-bir qayta ishlanadi.
"""

import asyncio
from typing import Optional


class AnalysisQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        self._total_queued = 0

    async def add_to_queue(self, user_id, message, context, user_data, lang) -> int:
        """
        Navbatga qo'shish. Navbat raqamini qaytaradi.
        """
        self._total_queued += 1
        position = self._queue.qsize() + 1

        await self._queue.put({
            "user_id": user_id,
            "message": message,
            "context": context,
            "user_data": user_data,
            "lang": lang,
        })
        return position

    async def get_next(self) -> Optional[dict]:
        """Navbatdagi keyingi vazifani olish"""
        try:
            task = self._queue.get_nowait()
            return task
        except asyncio.QueueEmpty:
            return None

    def task_done(self):
        try:
            self._queue.task_done()
        except ValueError:
            pass

    @property
    def size(self) -> int:
        return self._queue.qsize()
