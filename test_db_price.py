# test_db_price.py

import asyncio
from bot.db import create_engine, create_sessionmaker
from bot.config import load_settings
from sqlalchemy import text

async def check_db():
    settings = load_settings()
    engine = create_engine(settings.postgres_dsn)
    session_factory = create_sessionmaker(engine)
    
    nm_id = "494949159"
    
    async with session_factory() as session:
        # Смотрим текущие данные товара
        result = await session.execute(
            text("SELECT * FROM products WHERE external_id = :nm_id"),
            {"nm_id": nm_id}
        )
        product = result.fetchone()
        
        if product:
            print(f"=== Товар в БД ===")
            print(f"Колонки: {result.keys()}")
            print(f"Данные: {product}")
        else:
            print(f"Товар {nm_id} не найден в БД")
        
        # Смотрим историю цен
        result2 = await session.execute(
            text("""
                SELECT ph.* FROM price_history ph
                JOIN products p ON ph.product_id = p.id
                WHERE p.external_id = :nm_id
                ORDER BY ph.created_at DESC
                LIMIT 10
            """),
            {"nm_id": nm_id}
        )
        history = result2.fetchall()
        
        if history:
            print(f"\n=== История цен (последние 10) ===")
            for row in history:
                print(row)
        else:
            print(f"\nИстории цен нет")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_db())