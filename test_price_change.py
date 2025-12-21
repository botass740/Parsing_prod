import asyncio
from bot.db import create_engine, create_sessionmaker
from bot.db.models import Product
from bot.config import load_settings
from sqlalchemy import select, update

async def simulate_price_drop():
    settings = load_settings()
    engine = create_engine(settings.postgres_dsn)
    session_factory = create_sessionmaker(engine)
    
    async with session_factory() as session:
        # Увеличиваем цену в БД, чтобы при следующем парсинге была "скидка"
        stmt = update(Product).where(
            Product.external_id == "169684889"
        ).values(
            current_price=Product.current_price * 1.2  # +20% к цене
        )
        await session.execute(stmt)
        await session.commit()
        print("✅ Цена в БД увеличена на 20% — следующий парсинг покажет 'снижение'")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(simulate_price_drop())