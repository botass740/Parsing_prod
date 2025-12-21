# bot/main.py

import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import load_settings
from bot.db import create_engine, create_sessionmaker, init_db
from bot.db.models import PlatformCode
from bot.filtering.filters import FilterService
from bot.handlers.router import router as root_router
from bot.parsers.detmir import DetmirParser
from bot.parsers.ozon import OzonParser
from bot.parsers.wb import WildberriesParser
from bot.pipeline.runner import PipelineRunner
from bot.posting.poster import PostingService
from bot.scheduler.scheduler import SchedulerService
from bot.services.product_manager import ProductManager
from bot.utils.logger import setup_logger


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

    filter_service = FilterService(settings.filtering)
    posting_service = PostingService(bot, settings.posting)

    pipeline = PipelineRunner(
    session_factory=session_factory,
    filter_service=filter_service,
    posting_service=posting_service,
    thresholds=settings.filtering,
)

    # Получаем артикулы из БД
    product_manager = ProductManager(session_factory)
    
    wb_product_ids = await product_manager.get_product_ids(PlatformCode.WB)
    log.info(f"WB products to monitor: {len(wb_product_ids)}")
    
    wb_parser = WildberriesParser(
        product_ids=[int(x) for x in wb_product_ids] if wb_product_ids else None
    )
    
    ozon_parser = OzonParser()
    detmir_parser = DetmirParser()

    # Первый запуск — сохраняет в БД, не постит (всё новое)
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