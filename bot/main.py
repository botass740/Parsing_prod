# bot/main.py

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher

from bot.config import load_settings
from bot.db import create_engine, create_sessionmaker, init_db
from bot.db.models import PlatformCode
from bot.filtering.filters import FilterService
from bot.handlers.router import router as root_router
from bot.handlers import admin as admin_handlers  
from bot.parsers.detmir import DetmirParser
from bot.parsers.ozon import OzonParser
from bot.parsers.wb import WildberriesParser
from bot.pipeline.runner import PipelineRunner
from bot.posting.poster import PostingService
from bot.scheduler.scheduler import SchedulerService
from bot.services.product_manager import ProductManager
from bot.services.settings_manager import SettingsManager 
from bot.utils.logger import setup_logger


CLEANUP_TIMESTAMP_FILE = Path(".last_cleanup")
CLEANUP_INTERVAL_HOURS = int(os.getenv("CLEANUP_INTERVAL_HOURS", "24"))


def _needs_cleanup() -> bool:
    if not CLEANUP_TIMESTAMP_FILE.exists():
        return True
    try:
        timestamp = float(CLEANUP_TIMESTAMP_FILE.read_text().strip())
        last_cleanup = datetime.fromtimestamp(timestamp)
        age = datetime.now() - last_cleanup
        return age > timedelta(hours=CLEANUP_INTERVAL_HOURS)
    except Exception:
        return True


def _mark_cleanup_done():
    CLEANUP_TIMESTAMP_FILE.write_text(str(datetime.now().timestamp()))


async def main() -> None:
    settings = load_settings()

    setup_logger(level=logging.INFO)

    log = logging.getLogger("bot")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(root_router)

    engine = create_engine(settings.postgres_dsn)
    session_factory = create_sessionmaker(engine)
    await init_db(engine)

    # Инициализируем менеджеры
    settings_manager = SettingsManager(session_factory)

    # Передаём в хендлеры
    admin_handlers.set_settings_manager(settings_manager)

    # product_manager (с settings_manager)
    product_manager = ProductManager(session_factory, settings_manager=settings_manager)

    # filter_service (с settings_manager)
    filter_service = FilterService(settings.filtering, settings_manager=settings_manager)
    posting_service = PostingService(bot, settings.posting)

    pipeline = PipelineRunner(
        session_factory=session_factory,
        filter_service=filter_service,
        posting_service=posting_service,
        thresholds=settings.filtering,
        product_manager=product_manager,
        settings_manager=settings_manager,
    )

    # Очистка мёртвых товаров
    if _needs_cleanup():
        log.info("Cleaning up dead products (runs every %d hours)...", CLEANUP_INTERVAL_HOURS)
        try:
            removed, dead_ids = await product_manager.cleanup_dead_products(PlatformCode.WB)
            if removed > 0:
                log.info(f"Removed {removed} dead products")
            _mark_cleanup_done()
        except Exception as e:
            log.error(f"Cleanup failed: {e}")
    else:
        log.info("Skipping cleanup (last run < %d hours ago)", CLEANUP_INTERVAL_HOURS)

    # Проверяем количество товаров
    current_count = await product_manager.get_product_count(PlatformCode.WB)
    target_count = 3000
    
    if current_count < target_count:
        log.info(f"Products count {current_count} < {target_count}, refilling...")
        added, total = await product_manager.refill_products(PlatformCode.WB, target_count=target_count)
        log.info(f"Refilled {added} products, total: {total}")

    # Получаем артикулы
    wb_product_ids = await product_manager.get_product_ids(PlatformCode.WB)
    log.info(f"WB products to monitor: {len(wb_product_ids)}")
    
    wb_parser = WildberriesParser(
        product_ids=[int(x) for x in wb_product_ids] if wb_product_ids else None
    )
    
    ozon_parser = OzonParser()
    detmir_parser = DetmirParser()

    log.info("Running WB pipeline once for initial sync")
    await pipeline.run_platform(platform=PlatformCode.WB, parser=wb_parser)
    log.info("WB pipeline initial sync finished")

    scheduler = SchedulerService(
        intervals=settings.parsing,
        wb_task=lambda: pipeline.run_platform(platform=PlatformCode.WB, parser=wb_parser),
        ozon_task=lambda: pipeline.run_platform(platform=PlatformCode.OZON, parser=ozon_parser),
        detmir_task=lambda: pipeline.run_platform(platform=PlatformCode.DM, parser=detmir_parser),
    )

    scheduler.start()
    log.info("Scheduler started")

    try:
        await dp.start_polling(bot)
    finally:
        log.info("Shutting down")
        scheduler.shutdown()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())