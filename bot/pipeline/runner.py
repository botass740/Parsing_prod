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
from bot.config import FilteringThresholds


class PipelineRunner:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        filter_service: FilterService,
        posting_service: PostingService,
        thresholds: FilteringThresholds | None = None,
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._session_factory = session_factory
        self._filter = filter_service
        self._poster = posting_service
        
        # Пороги для публикации
        self._min_price_drop = thresholds.min_price_drop_percent if thresholds else 1.0
        self._min_discount_increase = thresholds.min_discount_increase if thresholds else 5.0
        
        self._log.info(
            "Publishing thresholds: price_drop>=%.1f%%, discount_increase>=%.1f%%",
            self._min_price_drop,
            self._min_discount_increase,
        )

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
                    "Pipeline finished: %s new=%s changed=%s posted=%s",
                    platform.value,
                    sum(1 for ch in changes if ch.is_new),
                    sum(1 for ch in changes if not ch.is_new),
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
        """
        Выбирает товары для публикации.
        
        Правила:
        - Новые товары (is_new=True) → НЕ постим, только сохраняем в БД
        - Цена упала → постим
        - Скидка увеличилась → постим
        """
        by_external: dict[str, dict[str, Any]] = {}
        for item in filtered:
            ext = item.get("external_id")
            if ext is None:
                continue
            by_external[str(ext)] = item

        selected: list[dict[str, Any]] = []
        
        for ch in changes:
            # Новые товары — только в БД, не постим
            if ch.is_new:
                self._log.debug("Skipping new product: %s", ch.product.external_id)
                continue
            
            # Проверяем, есть ли выгодные изменения
            if not self._has_favorable_changes(ch):
                self._log.debug("No favorable changes for: %s", ch.product.external_id)
                continue
            
            ext = ch.product.external_id
            item = by_external.get(ext)
            if item is None:
                continue
            
            self._log.info(
                "Publishing %s: %s",
                ext,
                ", ".join(f"{c.field}: {c.old} → {c.new}" for c in ch.changes)
            )
            selected.append(item)

        return selected

    def _has_favorable_changes(self, ch: ChangeResult) -> bool:
        """
        Проверяет, есть ли выгодные изменения для публикации.
        
        Пороги берутся из конфига:
        - min_price_drop_percent — минимальное снижение цены в %
        - min_discount_increase — минимальное увеличение скидки в п.п.
        """
        for change in ch.changes:
            # Пропускаем изменения где старое значение было None
            if change.old is None:
                continue
            
            # Цена упала
            if change.field == "price":
                try:
                    old_price = float(change.old)
                    new_price = float(change.new) if change.new else 0
                except (TypeError, ValueError):
                    continue
                
                # Пропускаем если цена 0
                if new_price == 0 or old_price == 0:
                    continue
                
                # Цена упала на min_price_drop_percent%
                if new_price < old_price:
                    drop_percent = (old_price - new_price) / old_price * 100
                    if drop_percent >= self._min_price_drop:
                        self._log.debug(
                            "Price drop: %.0f -> %.0f (%.1f%% >= %.1f%%)",
                            old_price, new_price, drop_percent, self._min_price_drop
                        )
                        return True
            
            # Скидка увеличилась
            if change.field == "discount":
                try:
                    old_discount = float(change.old) if change.old else 0
                    new_discount = float(change.new) if change.new else 0
                except (TypeError, ValueError):
                    continue
                
                # Скидка увеличилась на min_discount_increase п.п.
                if new_discount > old_discount:
                    increase = new_discount - old_discount
                    if increase >= self._min_discount_increase:
                        self._log.debug(
                            "Discount increase: %.0f -> %.0f (+%.0f%% >= %.0f%%)",
                            old_discount, new_discount, increase, self._min_discount_increase
                        )
                        return True
        
        return False


def _len_safe(it: Iterable[Any]) -> int | str:
    try:
        return len(it)  # type: ignore[arg-type]
    except Exception:
        return "?"