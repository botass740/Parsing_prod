from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Iterable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import PlatformCode
from bot.db.models.settings import BotSettings
from bot.db.services.change_detection import ChangeResult, detect_and_save_changes
from bot.filtering.filters import FilterService
from bot.parsers.base import BaseParser
from bot.posting.poster import PostingService, ProductUnavailableError
from bot.config import FilteringThresholds
from bot.services.settings_manager import SettingsManager


# Автоматическое удаление мёртвых товаров и добор
AUTO_CLEANUP_ENABLED = os.getenv("AUTO_CLEANUP_ENABLED", "true").lower() in ("true", "1", "yes")
TARGET_PRODUCT_COUNT = int(os.getenv("TARGET_PRODUCT_COUNT", "3000"))

# Размер батча для парсинга
BATCH_SIZE = int(os.getenv("PARSE_BATCH_SIZE", "50"))


class PipelineRunner:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        filter_service: FilterService,
        posting_service: PostingService,
        thresholds: FilteringThresholds | None = None,
        product_manager=None,
        settings_manager: SettingsManager | None = None,
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._session_factory = session_factory
        self._filter = filter_service
        self._poster = posting_service
        self._product_manager = product_manager
        self._settings_manager = settings_manager
        
        # Пороги для публикации (начальные значения из конфига)
        self._min_price_drop = thresholds.min_price_drop_percent if thresholds else 1.0
        self._min_discount_increase = thresholds.min_discount_increase if thresholds else 5.0
        
        self._log.info(
            "Publishing thresholds: price_drop>=%.1f%%, discount_increase>=%.1f%%",
            self._min_price_drop,
            self._min_discount_increase,
        )

    async def run_platform(self, *, platform: PlatformCode, parser: BaseParser) -> None:
        self._log.info("Pipeline started: %s", platform.value)
        
        # Загружаем актуальные пороги из БД
        if self._settings_manager:
            self._min_price_drop = await self._settings_manager.get_float(BotSettings.KEY_MIN_PRICE_DROP)
            self._min_discount_increase = await self._settings_manager.get_float(BotSettings.KEY_MIN_DISCOUNT_INCREASE)
            self._log.debug(
                "Loaded thresholds from DB: price_drop=%.1f%%, discount_increase=%.1f%%",
                self._min_price_drop,
                self._min_discount_increase,
            )

        try:
            raw_items = await parser.fetch_products()
        except NotImplementedError:
            self._log.warning("fetch_products is not implemented for %s", platform.value)
            return
        except Exception:
            self._log.exception("Failed to fetch products for %s", platform.value)
            return

        raw_list = list(raw_items)
        
        # Парсинг: batch или по одному
        parsed = await self._parse_products(parser, raw_list, platform)

        filtered = await self._filter.filter_products_async(parsed)
        self._log.info(
            "Pipeline %s: fetched=%s parsed=%s filtered=%s",
            platform.value,
            len(raw_list),
            len(parsed),
            len(filtered),
        )

        dead_products: list[str] = []

        async with self._session_factory() as session:
            try:
                changes = await detect_and_save_changes(session, platform_code=platform, items=filtered)

                to_publish = self._select_for_publish(changes, filtered)

                posted = 0
                skipped = 0
                
                for item in to_publish:
                    try:
                        ok = await self._poster.post_product(item)
                    except ProductUnavailableError as e:
                        self._log.warning("Skipped unavailable: %s", e)
                        skipped += 1
                        if e.external_id:
                            dead_products.append(e.external_id)
                        continue
                    except Exception:
                        self._log.exception("Posting failed (%s)", platform.value)
                        continue

                    if not ok:
                        self._log.info("Posting rate limit reached")
                        break

                    posted += 1

                await session.commit()

                self._log.info(
                    "Pipeline finished: %s new=%s changed=%s posted=%s skipped=%s dead=%s",
                    platform.value,
                    sum(1 for ch in changes if ch.is_new),
                    sum(1 for ch in changes if not ch.is_new),
                    posted,
                    skipped,
                    len(dead_products),
                )
                
            except Exception:
                await session.rollback()
                self._log.exception("Pipeline DB step failed: %s", platform.value)
                return

        # После основного pipeline — удаляем мёртвых и добираем новых
        if dead_products and AUTO_CLEANUP_ENABLED and self._product_manager:
            await self._cleanup_and_refill(platform, dead_products)

    async def _parse_products(
        self,
        parser: BaseParser,
        raw_list: list[Any],
        platform: PlatformCode,
    ) -> list[dict[str, Any]]:
        """
        Парсит товары. Использует batch если доступен, иначе по одному.
        """
        parsed: list[dict[str, Any]] = []
        
        # Проверяем поддержку batch-парсинга
        if hasattr(parser, 'parse_products_batch') and callable(getattr(parser, 'parse_products_batch')):
            self._log.info(
                "Using BATCH parsing: %d products, batch_size=%d",
                len(raw_list),
                BATCH_SIZE,
            )
            
            total_batches = (len(raw_list) + BATCH_SIZE - 1) // BATCH_SIZE
            
            for batch_num, i in enumerate(range(0, len(raw_list), BATCH_SIZE), start=1):
                batch = raw_list[i:i + BATCH_SIZE]
                
                # Конвертируем в int (для WB это nm_id)
                try:
                    batch_ids = [int(x) for x in batch]
                except (TypeError, ValueError) as e:
                    self._log.warning("Failed to convert batch to int: %s", e)
                    continue
                
                try:
                    batch_results = await parser.parse_products_batch(batch_ids)
                    parsed.extend(batch_results)
                    
                    self._log.debug(
                        "Batch %d/%d: requested=%d, got=%d",
                        batch_num,
                        total_batches,
                        len(batch_ids),
                        len(batch_results),
                    )
                    
                except Exception:
                    self._log.exception(
                        "Batch %d/%d parsing failed",
                        batch_num,
                        total_batches,
                    )
                
                # Пауза между батчами (избегаем rate limit)
                if i + BATCH_SIZE < len(raw_list):
                    await asyncio.sleep(0.3)
            
            self._log.info(
                "Batch parsing complete: %d/%d products parsed",
                len(parsed),
                len(raw_list),
            )
        
        else:
            # Fallback: парсим по одному
            self._log.info(
                "Using SINGLE parsing: %d products (no batch support)",
                len(raw_list),
            )
            
            for idx, raw in enumerate(raw_list):
                try:
                    item = await parser.parse_product(raw)
                except NotImplementedError:
                    self._log.warning("parse_product is not implemented for %s", platform.value)
                    return parsed
                except Exception:
                    self._log.exception("Failed to parse product #%d", idx)
                    continue

                if isinstance(item, dict):
                    parsed.append(item)
                
                # Логируем прогресс каждые 100 товаров
                if (idx + 1) % 100 == 0:
                    self._log.debug("Parsed %d/%d products", idx + 1, len(raw_list))
        
        return parsed

    async def _cleanup_and_refill(
        self, 
        platform: PlatformCode, 
        dead_products: list[str]
    ) -> None:
        """Удаляет мёртвые товары и добирает новые."""
        try:
            removed = await self._product_manager.remove_products(platform, dead_products)
            self._log.info(f"Removed {removed} dead products: {dead_products}")
            
            added, total = await self._product_manager.refill_products(
                platform, 
                target_count=TARGET_PRODUCT_COUNT
            )
            
            if added > 0:
                self._log.info(f"Refilled {added} new products, total now: {total}")
                
        except Exception:
            self._log.exception("Cleanup/refill failed")

    def _select_for_publish(
        self,
        changes: list[ChangeResult],
        filtered: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Выбирает товары для публикации."""
        by_external: dict[str, dict[str, Any]] = {}
        for item in filtered:
            ext = item.get("external_id")
            if ext is None:
                continue
            by_external[str(ext)] = item

        selected: list[dict[str, Any]] = []
        
        for ch in changes:
            if ch.is_new:
                self._log.debug("Skipping new product: %s", ch.product.external_id)
                continue
            
            # Проверяем и получаем причину публикации
            publish_reason = self._get_publish_reason(ch)
            if not publish_reason:
                continue
            
            ext = ch.product.external_id
            item = by_external.get(ext)
            if item is None:
                continue
            
            # Добавляем причину публикации в товар
            item = item.copy()
            item["publish_reason"] = publish_reason
            
            self._log.info(
                "Selected for publish %s: %s",
                ext,
                ", ".join(f"{c.field}: {c.old} → {c.new}" for c in ch.changes)
            )
            selected.append(item)

        return selected

    def _get_publish_reason(self, ch: ChangeResult) -> str | None:
        """
        Проверяет изменения и возвращает причину публикации.
        """
        reasons = []
        
        for change in ch.changes:
            if change.old is None:
                continue
            
            # Цена упала
            if change.field == "price":
                try:
                    old_price = float(change.old)
                    new_price = float(change.new) if change.new else 0
                except (TypeError, ValueError):
                    continue
                
                if new_price == 0 or old_price == 0:
                    continue
                
                if new_price < old_price:
                    drop_percent = (old_price - new_price) / old_price * 100
                    if drop_percent >= self._min_price_drop:
                        reasons.append(
                            f"📉 Цена снижена: {int(old_price)} → {int(new_price)} ₽ (-{drop_percent:.1f}%)"
                        )
            
            # Скидка увеличилась
            if change.field == "discount":
                try:
                    old_discount = float(change.old) if change.old else 0
                    new_discount = float(change.new) if change.new else 0
                except (TypeError, ValueError):
                    continue
                
                if new_discount > old_discount:
                    increase = new_discount - old_discount
                    if increase >= self._min_discount_increase:
                        reasons.append(
                            f"🔥 Скидка выросла: {int(old_discount)}% → {int(new_discount)}% (+{increase:.0f}%)"
                        )
        
        if reasons:
            return "\n".join(reasons)
        return None

    def _has_favorable_changes(self, ch: ChangeResult) -> bool:
        """Проверяет, есть ли выгодные изменения для публикации."""
        return self._get_publish_reason(ch) is not None


def _len_safe(it: Iterable[Any]) -> int | str:
    try:
        return len(it)
    except Exception:
        return "?"