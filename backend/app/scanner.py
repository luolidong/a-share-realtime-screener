from __future__ import annotations

import asyncio
from datetime import datetime, time
from zoneinfo import ZoneInfo

from .config import load_rules
from .providers.akshare_provider import AkShareProvider
from .screener import screen_stocks
from .storage import init_db, record_scan, record_scan_error

SHANGHAI = ZoneInfo("Asia/Shanghai")


def is_market_open(now: datetime | None = None) -> bool:
    now = now or datetime.now(SHANGHAI)
    if now.weekday() >= 5:
        return False
    current = now.time()
    morning = time(9, 30) <= current <= time(11, 30)
    afternoon = time(13, 0) <= current <= time(15, 0)
    return morning or afternoon


class BackgroundScanner:
    def __init__(self, provider: AkShareProvider, interval_seconds: int = 15):
        self.provider = provider
        self.interval_seconds = interval_seconds
        self.task: asyncio.Task | None = None
        self.running = False
        self.last_result: dict | None = None
        self.last_error: str | None = None

    async def start(self) -> None:
        init_db()
        if self.task and not self.task.done():
            return
        self.running = True
        self.task = asyncio.create_task(self._loop(), name="a-share-background-scanner")

    async def stop(self) -> None:
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def scan_once(self) -> dict:
        try:
            result = await asyncio.to_thread(screen_stocks, self.provider, load_rules())
            summary = await asyncio.to_thread(record_scan, result)
            self.last_result = summary
            self.last_error = None
            return summary
        except Exception as exc:
            self.last_error = str(exc)
            await asyncio.to_thread(record_scan_error, self.last_error)
            raise

    async def _loop(self) -> None:
        while self.running:
            if is_market_open():
                try:
                    await self.scan_once()
                except Exception:
                    pass
            await asyncio.sleep(self.interval_seconds)

    def status(self) -> dict:
        now = datetime.now(SHANGHAI)
        return {
            "running": self.running,
            "market_open": is_market_open(now),
            "interval_seconds": self.interval_seconds,
            "china_time": now.isoformat(),
            "last_result": self.last_result,
            "last_error": self.last_error,
        }
