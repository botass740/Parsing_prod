# bot/pipeline/runner.py

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Iterable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.config import FilteringThresholds
from bot.db.models import PlatformCode
from bot.db.models.settings import BotSettings
from bot.db.services.change_detection import ChangeResult, detect_and_save_changes
from bot.filtering.filters import FilterService
from bot.parsers.base import BaseParser
from bot.posting.poster import PostingService, ProductUnavailableError
from bot.services.settings_manager import SettingsManager

YIELD_EVERY_N_ITEMS = int(os.getenv("YIELD_EVERY_N_ITEMS", "20"))

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

                # Логируем статистику стабильности
                stable_count = sum(1 for ch in changes if ch.is_stable)
                unstable_count = sum(1 for ch in changes if not ch.is_stable and not ch.is_new)
                just_stabilized_count = sum(1 for ch in changes if ch.just_stabilized)
                self._log.info(
                    "Stability stats: stable=%d, unstable=%d, just_stabilized=%d",
                    stable_count,
                    unstable_count,
                    just_stabilized_count,
                )

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
                    except ProductUnavailableError as e:
                        self._log.warning("Skipped unavailable: %s", e)
                        skipped += 1

                        # Для OZON НЕ удаляем товар из БД только из-за отсутствия картинки:
                        # это может быть временная проблема CDN/403.
                        if platform != PlatformCode.OZON:
                            if e.external_id:
                                dead_products.append(e.external_id)

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
                    sum(1 for ch in changes if ch.has_changes),
                    posted,
                    skipped,
                    len(dead_products),
                )

            except Exception:
                await session.rollback()
                self._log.exception("Pipeline DB step failed: %s", platform.value)
                return

        # После основного pipeline — удаляем мёртвых и добираем новых
        # Для OZON refill делаем внутри _parse_products (auto-refill), поэтому тут не вызываем _cleanup_and_refill
        if dead_products and AUTO_CLEANUP_ENABLED and self._product_manager and platform != PlatformCode.OZON:
            await self._cleanup_and_refill(platform, dead_products)

        # OZON: удаляем мёртвые (no-image), refill будет сделан auto-refill на следующем цикле
        elif dead_products and AUTO_CLEANUP_ENABLED and self._product_manager and platform == PlatformCode.OZON:
            try:
                removed = await self._product_manager.remove_products(platform, dead_products)
                self._log.info("OZON: removed %d dead products (no-image): %s", removed, dead_products)

                # === OZON: добираем сразу до TARGET_PRODUCT_COUNT ===
                try:
                    current = await self._product_manager.get_product_count(PlatformCode.OZON)
                except Exception:
                    self._log.exception("OZON: failed to get count after delete")
                    current = TARGET_PRODUCT_COUNT

                need = max(0, TARGET_PRODUCT_COUNT - current)
                if need > 0:
                    self._log.warning("OZON: immediate refill needed: %d (current=%d target=%d)", need, current, TARGET_PRODUCT_COUNT)

                    # Собираем кандидатов через COLLECT и добавляем только недостающее
                    try:
                        # parser у нас уже есть, используем тот же
                        # Берём общий список категорий/тем (из БД/ENV)
                        queries: list[str] = []
                        if self._product_manager and hasattr(self._product_manager, "get_refill_categories"):
                            queries = await self._product_manager.get_refill_categories()

                        # Собираем кандидатов равномерно по запросам (быстро, без прокрутки до 3000)
                        if queries and hasattr(parser, "collect_skus_by_queries"):
                            target_for_collect = min(300, max(need * 10, need + 30))
                            collected_ids = await parser.collect_skus_by_queries(queries, target=target_for_collect)
                        else:
                            # fallback: старый COLLECT если queries пустые или метода ещё нет
                            collected = await getattr(parser, "parse_products_batch")([])  # COLLECT
                            collected_ids = [str(x.get("external_id")) for x in collected if isinstance(x, dict)]
                            collected_ids = [x for x in collected_ids if x and x.isdigit()]

                        existing_ids = set(await self._product_manager.get_product_ids(PlatformCode.OZON))
                        new_ids: list[str] = []
                        for eid in collected_ids:
                            if eid in existing_ids:
                                continue
                            if eid in new_ids:
                                continue
                            new_ids.append(eid)
                            if len(new_ids) >= need:
                                break

                        if new_ids:
                            added, skipped = await self._product_manager.add_products(PlatformCode.OZON, new_ids)
                            self._log.info("OZON immediate refill: added=%d skipped=%d", added, skipped)

                        removed_extra = await self._product_manager.trim_to_target(PlatformCode.OZON, TARGET_PRODUCT_COUNT)
                        if removed_extra:
                            self._log.info("OZON immediate refill: trimmed extra removed=%d", removed_extra)

                    except Exception:
                        self._log.exception("OZON immediate refill failed")

            except Exception:
                self._log.exception("OZON: failed to remove dead products")


    async def _parse_products(
        self,
        parser: BaseParser,
        raw_list: list[Any],
        platform: PlatformCode,
    ) -> list[dict[str, Any]]:
        """Парсит товары."""
        
        # === OZON ===
        if platform == PlatformCode.OZON and hasattr(parser, "parse_products_batch"):

            # 1) Если raw_list не пустой — обычный MONITOR
            if raw_list:
                self._log.info("OZON: MONITOR mode (%d products from DB)", len(raw_list))
                try:
                    results = await parser.parse_products_batch(raw_list)
                    self._log.info("OZON monitor returned %d items", len(results) if results else 0)
                    # === OZON AUTO-REFILL до TARGET_PRODUCT_COUNT ===
                    # Если после удаления "мёртвых" стало меньше 3000 — добираем недостающее через COLLECT.
                    if self._product_manager:
                        try:
                            db_count = await self._product_manager.get_product_count(PlatformCode.OZON)
                        except Exception:
                            self._log.exception("OZON: failed to get count for auto-refill")
                            db_count = TARGET_PRODUCT_COUNT

                        if db_count < TARGET_PRODUCT_COUNT:
                            need = TARGET_PRODUCT_COUNT - db_count
                            self._log.warning("OZON: auto-refill needed: %d (current=%d target=%d)", need, db_count, TARGET_PRODUCT_COUNT)

                            try:
                                # Берём общий список категорий/тем (из БД/ENV)
                                queries: list[str] = []
                                if self._product_manager and hasattr(self._product_manager, "get_refill_categories"):
                                    queries = await self._product_manager.get_refill_categories()

                                # Собираем кандидатов равномерно по запросам
                                if queries and hasattr(parser, "collect_skus_by_queries"):
                                    # небольшой запас, но без лишней нагрузки при need=1..3
                                    target_for_collect = min(300, max(need * 10, need + 30))
                                    collected_ids = await parser.collect_skus_by_queries(queries, target=target_for_collect)
                                else:
                                    # fallback: старый COLLECT если queries пустые или метод ещё не добавлен
                                    collected = await parser.parse_products_batch([])  # COLLECT
                                    collected_ids = [str(x.get("external_id")) for x in collected if isinstance(x, dict)]
                                    collected_ids = [x for x in collected_ids if x and x.isdigit()]

                                existing_ids = set(await self._product_manager.get_product_ids(PlatformCode.OZON))
                                new_ids: list[str] = []
                                for eid in collected_ids:
                                    if eid in existing_ids:
                                        continue
                                    if eid in new_ids:
                                        continue
                                    new_ids.append(eid)
                                    if len(new_ids) >= need:
                                        break

                                if new_ids:
                                    added, skipped = await self._product_manager.add_products(PlatformCode.OZON, new_ids)
                                    self._log.info("OZON auto-refill: added=%d skipped=%d", added, skipped)

                                removed = await self._product_manager.trim_to_target(PlatformCode.OZON, TARGET_PRODUCT_COUNT)
                                if removed:
                                    self._log.info("OZON auto-refill: trimmed extra removed=%d", removed)

                            except Exception:
                                self._log.exception("OZON auto-refill failed")
                    return results if isinstance(results, list) else []
                except Exception:
                    self._log.exception("OZON monitor failed")
                    return []

            # 2) raw_list пустой — но это может быть из-за "пустого парсера".
            #    Проверяем БД и если там есть товары — форсим MONITOR.
            db_count = 0
            if self._product_manager:
                try:
                    db_count = await self._product_manager.get_product_count(PlatformCode.OZON)
                except Exception:
                    self._log.exception("OZON: failed to get product count from DB")
                    db_count = 0

            if db_count > 0 and self._product_manager:
                self._log.warning(
                    "OZON: raw_list empty, but DB has %d products -> forcing MONITOR from DB",
                    db_count,
                )
                try:
                    ids = await self._product_manager.get_product_ids(PlatformCode.OZON)
                    results = await parser.parse_products_batch(ids)
                    self._log.info("OZON monitor returned %d items", len(results) if results else 0)
                    return results if isinstance(results, list) else []
                except Exception:
                    self._log.exception("OZON forced MONITOR from DB failed")
                    return []

            # 3) БД реально пустая — делаем COLLECT
            self._log.info("OZON: COLLECT mode (DB empty)")

            try:
                results = await parser.parse_products_batch([])

                ids: list[str] = []
                if results:
                    ids = [str(x.get("external_id")) for x in results if isinstance(x, dict)]
                    ids = [x for x in ids if x and x.isdigit()]
                    ids = ids[:TARGET_PRODUCT_COUNT]  # ровно 3000

                if self._product_manager and ids:
                    added, skipped = await self._product_manager.add_products(PlatformCode.OZON, ids)
                    self._log.info("OZON COLLECT: saved to DB added=%d skipped=%d", added, skipped)

                    # Приводим базу к ровно TARGET_PRODUCT_COUNT (твой Шаг 2 уже сделал метод trim_to_target)
                    removed = await self._product_manager.trim_to_target(PlatformCode.OZON, TARGET_PRODUCT_COUNT)
                    if removed:
                        self._log.info("OZON: trimmed extra products removed=%d", removed)

                self._log.info("OZON collect returned %d items", len(results) if results else 0)

                # Сразу запускаем MONITOR в этом же запуске (по ровно 3000 ids)
                if ids:
                    self._log.info("OZON: switching to MONITOR right after COLLECT (%d products)", len(ids))
                    monitor_results = await parser.parse_products_batch(ids)
                    self._log.info(
                        "OZON monitor after collect returned %d items",
                        len(monitor_results) if monitor_results else 0,
                    )
                    return monitor_results if isinstance(monitor_results, list) else []

                return []
            except Exception:
                self._log.exception("OZON collect failed")
                return []

        parsed: list[dict[str, Any]] = []

        # === WB и другие: batch парсинг ===
        if hasattr(parser, "parse_products_batch") and callable(getattr(parser, "parse_products_batch")):
            self._log.info(
                "Using BATCH parsing: %d products, batch_size=%d",
                len(raw_list),
                BATCH_SIZE,
            )

            total_batches = (len(raw_list) + BATCH_SIZE - 1) // BATCH_SIZE

            for batch_num, i in enumerate(range(0, len(raw_list), BATCH_SIZE), start=1):
                batch = raw_list[i:i + BATCH_SIZE]

                try:
                    batch_ids = [int(x) for x in batch]
                except (TypeError, ValueError):
                    batch_ids = [str(x) for x in batch]

                try:
                    batch_results = await parser.parse_products_batch(batch_ids)
                    if isinstance(batch_results, list):
                        parsed.extend(batch_results)

                    self._log.debug(
                        "Batch %d/%d: requested=%d, got=%d",
                        batch_num,
                        total_batches,
                        len(batch_ids),
                        len(batch_results) if isinstance(batch_results, list) else 0,
                    )
                except Exception:
                    self._log.exception("Batch %d/%d parsing failed", batch_num, total_batches)

                if i + BATCH_SIZE < len(raw_list):
                    await asyncio.sleep(0.3)

            self._log.info("Batch parsing complete: %d/%d products parsed", len(parsed), len(raw_list))
            return parsed

        # === Fallback: по одному ===
        self._log.info("Using SINGLE parsing: %d products", len(raw_list))
        for idx, raw in enumerate(raw_list):
            try:
                item = await parser.parse_product(raw)
            except Exception:
                self._log.exception("Failed to parse product #%d", idx)
                continue
            if isinstance(item, dict):
                parsed.append(item)

        return parsed

        # === fallback single ===
        self._log.info("Using SINGLE parsing: %d products", len(raw_list))
        for idx, raw in enumerate(raw_list):
            try:
                item = await parser.parse_product(raw)
            except Exception:
                self._log.exception("Failed to parse product #%d", idx)
                continue
            if isinstance(item, dict):
                parsed.append(item)

        return parsed

    async def _cleanup_and_refill(
        self,
        platform: PlatformCode,
        dead_products: list[str],
    ) -> None:
        """Удаляет мёртвые товары и добирает новые."""
        try:
            removed = await self._product_manager.remove_products(platform, dead_products)
            self._log.info("Removed %d dead products: %s", removed, dead_products)

            added, total = await self._product_manager.refill_products(
                platform,
                target_count=TARGET_PRODUCT_COUNT,
            )

            if added > 0:
                self._log.info("Refilled %d new products, total now: %d", added, total)

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
            # Пропускаем новые товары
            if ch.is_new:
                self._log.debug("Skipping new product: %s", ch.product.external_id)
                continue

            # Пропускаем нестабильные товары
            if not ch.is_stable:
                self._log.debug(
                    "Skipping unstable product: %s (parse_count=%d)",
                    ch.product.external_id,
                    ch.product.stable_parse_count,
                )
                continue

            # Пропускаем только что стабилизировавшиеся
            if ch.just_stabilized:
                self._log.debug(
                    "Skipping just-stabilized product: %s (baseline set)",
                    ch.product.external_id,
                )
                continue

            # Нет изменений — пропускаем
            if not ch.has_changes:
                continue

            publish_reason = self._get_publish_reason(ch)
            if not publish_reason:
                continue

            ext = ch.product.external_id
            item = by_external.get(ext)
            if item is None:
                continue

            item = item.copy()
            item["publish_reason"] = publish_reason

            self._log.info(
                "Selected for publish %s: %s",
                ext,
                ", ".join(f"{c.field}: {c.old} → {c.new}" for c in ch.changes),
            )
            selected.append(item)

        return selected

    def _get_publish_reason(self, ch: ChangeResult) -> str | None:
        """Проверяет изменения и возвращает причину публикации."""
        reasons: list[str] = []

        for change in ch.changes:
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
                    old_discount = float(change.old)
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
        return self._get_publish_reason(ch) is not None


def _len_safe(it: Iterable[Any]) -> int | str:
    try:
        return len(it)
    except Exception:
        return "?"