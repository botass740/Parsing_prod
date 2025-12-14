from aiogram import Router

from bot.handlers.start import router as start_router

router = Router()
router.include_router(start_router)
