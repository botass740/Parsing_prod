import asyncio
from bot.config import load_settings
from bot.db import create_engine, create_sessionmaker
from bot.db.models import Product, PriceHistory, PlatformCode
from bot.services.product_manager import ProductManager
from sqlalchemy import delete

async def main():
    settings = load_settings()
    engine = create_engine(settings.postgres_dsn)
    session_factory = create_sessionmaker(engine)
    
    async with session_factory() as session:
        # Удаляем историю цен
        await session.execute(delete(PriceHistory))
        # Удаляем товары
        await session.execute(delete(Product))
        await session.commit()
        print("✅ База очищена")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())