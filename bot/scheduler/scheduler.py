from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from bot.config import ParsingIntervals


class SchedulerService:
    def __init__(
        self,
        *,
        intervals: ParsingIntervals,
        wb_task: Callable[[], Awaitable[Any]] | None = None,
        ozon_task: Callable[[], Awaitable[Any]] | None = None,
        detmir_task: Callable[[], Awaitable[Any]] | None = None,
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._scheduler = AsyncIOScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 30,
            }
        )

        self._intervals = intervals
        self._wb_task = wb_task or self._wb_placeholder
        self._ozon_task = ozon_task or self._ozon_placeholder
        self._detmir_task = detmir_task or self._detmir_placeholder

        self._jobs_added = False

    def add_jobs(self) -> None:
        if self._jobs_added:
            return

        self._scheduler.add_job(
            self._safe("wb", self._wb_task),
            trigger=IntervalTrigger(seconds=self._intervals.wb_seconds),
            id="parse_wb",
            replace_existing=True,
        )

        self._scheduler.add_job(
            self._safe("ozon", self._ozon_task),
            trigger=IntervalTrigger(seconds=self._intervals.ozon_seconds),
            id="parse_ozon",
            replace_existing=True,
        )

        self._scheduler.add_job(
            self._safe("detmir", self._detmir_task),
            trigger=IntervalTrigger(seconds=self._intervals.detmir_seconds),
            id="parse_detmir",
            replace_existing=True,
        )

        self._jobs_added = True

    def start(self) -> None:
        self.add_jobs()
        self._scheduler.start()

    def reschedule(self, *, intervals: ParsingIntervals) -> None:
        self._intervals = intervals

        for job_id, seconds in (
            ("parse_wb", intervals.wb_seconds),
            ("parse_ozon", intervals.ozon_seconds),
            ("parse_detmir", intervals.detmir_seconds),
        ):
            try:
                self._scheduler.reschedule_job(job_id, trigger=IntervalTrigger(seconds=seconds))
            except JobLookupError:
                continue

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

    def _safe(self, name: str, task: Callable[[], Awaitable[Any]]) -> Callable[[], Awaitable[None]]:
        async def _runner() -> None:
            try:
                await task()
            except Exception:
                self._log.exception("Scheduler task failed: %s", name)

        return _runner

    async def _wb_placeholder(self) -> None:
        # TODO: wire Wildberries parsing pipeline here
        self._log.info("WB parsing task placeholder executed")

    async def _ozon_placeholder(self) -> None:
        # TODO: wire Ozon parsing pipeline here
        self._log.info("Ozon parsing task placeholder executed")

    async def _detmir_placeholder(self) -> None:
        # TODO: wire Detmir parsing pipeline here
        self._log.info("Detmir parsing task placeholder executed")
