import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)

from bot.parsers.wb import WildberriesParser


async def test_parser():
    print("="*70)
    print("ТЕСТ WB ПАРСЕРА (BATCH)")
    print("="*70)
    
    test_ids = [
        169684889,
        227648352,
        443549513,
        158173097,
        535935438,
    ]
    
    parser = WildberriesParser(product_ids=test_ids)
    
    # Используем batch-парсинг — один запрос на все товары!
    print(f"\n📦 Парсим {len(test_ids)} товаров одним запросом...")
    
    results = await parser.parse_products_batch(test_ids)
    
    print(f"✅ Получено: {len(results)} товаров\n")
    
    # Выводим результаты
    for result in results:
        name = result.get('name', 'N/A')
        if len(name) > 55:
            name = name[:55] + "..."
        
        nm = result.get('external_id')
        
        print(f"{'='*70}")
        print(f"📦 {nm}: {name}")
        print(f"   💰 Цена: {result.get('price_min')} - {result.get('price_max')} ₽")
        print(f"   💸 Старая: {result.get('old_price')} ₽ | Скидка: {result.get('discount_percent')}%")
        print(f"   ⭐ Рейтинг: {result.get('rating')} | Отзывов: {result.get('feedbacks')}")
        print(f"   📦 Остаток: {result.get('stock')} шт")
    
    # Итоговая таблица
    print(f"\n{'='*70}")
    print("СВОДНАЯ ТАБЛИЦА")
    print("="*70)
    print(f"{'Артикул':<12} {'Кошелёк':>8} {'Картой':>8} {'Старая':>8} {'Скидка':>7} {'Остаток':>8}")
    print("-"*70)
    
    for r in results:
        nm = r.get('external_id', '?')
        p_min = r.get('price_min') or 0
        p_max = r.get('price_max') or 0
        old = r.get('old_price') or 0
        disc = r.get('discount_percent') or 0
        stock = r.get('stock') or 0
        print(f"{nm:<12} {p_min:>8.0f} {p_max:>8.0f} {old:>8.0f} {disc:>6.0f}% {stock:>8}")
    
    print("="*70)


async def test_single():
    """Тест одиночного парсинга (для сравнения)."""
    print("\n" + "="*70)
    print("ТЕСТ ОДИНОЧНОГО ПАРСИНГА")
    print("="*70)
    
    parser = WildberriesParser()
    
    result = await parser.parse_product(227648352)
    
    print(f"📦 {result.get('name')}")
    print(f"   Цена: {result.get('price_max')} ₽")
    print(f"   Рейтинг: {result.get('rating')}")


if __name__ == "__main__":
    asyncio.run(test_parser())