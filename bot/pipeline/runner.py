from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import PlatformCode
from bot.db.services.change_detection import ChangeResult, detect_and_save_changes
from bot.filtering.filters import FilterService
from bot.parsers.base import BaseParser
from bot.posting.poster import PostingService


class PipelineRunner:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        filter_service: FilterService,
        posting_service: PostingService,
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._session_factory = session_factory
        self._filter = filter_service
        self._poster = posting_service

    async def run_platform(self, *, platform: PlatformCode, parser: BaseParser) -> None:
        self._log.info("Pipeline started: %s", platform.value)

        try:
            raw_items = await parser.fetch_products()
        except NotImplementedError:
            self._log.warning("fetch_products is not implemented for %s", platform.value)
            return
        except Exception:
            self._log.exception("Failed to fetch products for %s", platform.value)
            return

        parsed: list[dict[str, Any]] = []
        for raw in raw_items:
            try:
                item = await parser.parse_product(raw)
            except NotImplementedError:
                self._log.warning("parse_product is not implemented for %s", platform.value)
                return
            except Exception:
                self._log.exception("Failed to parse product for %s", platform.value)
                continue

            if not isinstance(item, dict):
                continue

            parsed.append(item)

        filtered = self._filter.filter_products(parsed)
        self._log.info(
            "Pipeline %s: fetched=%s parsed=%s filtered=%s",
            platform.value,
            _len_safe(raw_items),
            len(parsed),
            len(filtered),
        )

        async with self._session_factory() as session:
            try:
                changes = await detect_and_save_changes(session, platform_code=platform, items=filtered)

                to_publish = self._select_for_publish(changes, filtered)

                posted = 0
                for item in to_publish:
                    try:
                        ok = await self._poster.post_product(item)
                    except Exception:
                        self._log.exception("Posting failed (%s)", platform.value)
                        continue

                    if not ok:
                        self._log.info("Posting rate limit reached")
                        break

                    posted += 1

                await session.commit()

                self._log.info(
                    "Pipeline finished: %s changed=%s posted=%s",
                    platform.value,
                    len(changes),
                    posted,
                )
            except Exception:
                await session.rollback()
                self._log.exception("Pipeline DB step failed: %s", platform.value)

    def _select_for_publish(
        self,
        changes: list[ChangeResult],
        filtered: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_external: dict[str, dict[str, Any]] = {}
        for item in filtered:
            ext = item.get("external_id")
            if ext is None:
                continue
            by_external[str(ext)] = item

        selected: list[dict[str, Any]] = []
        for ch in changes:
            ext = ch.product.external_id
            item = by_external.get(ext)
            if item is None:
                continue
            selected.append(item)

        return selected


def _len_safe(it: Iterable[Any]) -> int | str:
    try:
        return len(it)  # type: ignore[arg-type]
    except Exception:
        return "?"
