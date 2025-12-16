"""
test_stock_debug.py — проверка остатков
"""

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Referer": "https://www.wildberries.ru/",
}

# Твои артикулы
NM_IDS = [169684889, 435777124, 570821597]

print("=" * 60)
print("ПРОВЕРКА ОСТАТКОВ")
print("=" * 60)

for nm_id in NM_IDS:
    print(f"\n📦 Артикул: {nm_id}")
    
    # Метод 1: product-order-qnt
    url1 = f"https://product-order-qnt.wildberries.ru/v2/by-nm/?nm={nm_id}"
    try:
        resp = requests.get(url1, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   product-order-qnt: {data}")
        else:
            print(f"   product-order-qnt: status {resp.status_code}")
    except Exception as e:
        print(f"   product-order-qnt: error {e}")
    
    # Метод 2: через card.wb.ru (если бы работал)
    # Пропускаем, т.к. 404
    
    # Метод 3: проверим soldout
    vol = nm_id // 100000
    part = nm_id // 1000
    
    # Определяем basket
    if vol <= 143: basket = 1
    elif vol <= 287: basket = 2
    elif vol <= 431: basket = 3
    elif vol <= 719: basket = 4
    elif vol <= 1007: basket = 5
    elif vol <= 1061: basket = 6
    elif vol <= 1115: basket = 7
    elif vol <= 1169: basket = 8
    elif vol <= 1313: basket = 9
    elif vol <= 1601: basket = 10
    elif vol <= 1655: basket = 11
    elif vol <= 1919: basket = 12
    elif vol <= 2045: basket = 13
    elif vol <= 2189: basket = 14
    elif vol <= 2405: basket = 15
    elif vol <= 2621: basket = 16
    elif vol <= 2837: basket = 17
    else: basket = 18
    
    base = f"https://basket-{basket:02d}.wbbasket.ru/vol{vol}/part{part}/{nm_id}"
    
    # Пробуем разные файлы
    stock_files = [
        f"{base}/info/soldout.json",
        f"{base}/info/quantity.json",
        f"{base}/info/availability.json",
    ]
    
    for url in stock_files:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=5)
            if resp.status_code == 200:
                print(f"   {url.split('/')[-1]}: {resp.json()}")
        except:
            pass

print("\n" + "=" * 60)
print("""
ВАЖНО: product-order-qnt.wildberries.ru показывает ОГРАНИЧЕННЫЕ данные.
Поле 'qnt' часто возвращает 0, даже если товар есть в наличии.

Это НЕ полные остатки на всех складах, а что-то другое 
(возможно, остаток для быстрой доставки или кэшированные данные).
""")