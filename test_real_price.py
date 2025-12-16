"""
test_real_price.py — поиск эндпоинта с реальной ценой (со скидками)
"""

import requests
import re

# Твои артикулы с известными ценами
TEST_PRODUCTS = [
    {"nm_id": 169684889, "expected_price": 1090},  # Твоя цена со скидкой
    {"nm_id": 435777124, "expected_price": 699},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
}

def get_basket_host(nm_id: int) -> str:
    vol = nm_id // 100000
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
    elif vol <= 3053: basket = 18
    elif vol <= 3269: basket = 19
    elif vol <= 3485: basket = 20
    elif vol <= 3701: basket = 21
    elif vol <= 3917: basket = 22
    elif vol <= 4133: basket = 23
    elif vol <= 4349: basket = 24
    elif vol <= 4565: basket = 25
    elif vol <= 4781: basket = 26
    elif vol <= 4997: basket = 27
    elif vol <= 5213: basket = 28
    elif vol <= 5429: basket = 29
    elif vol <= 5645: basket = 30
    elif vol <= 5861: basket = 31
    else: basket = 32
    return f"https://basket-{basket:02d}.wbbasket.ru"


for product in TEST_PRODUCTS:
    nm_id = product["nm_id"]
    expected = product["expected_price"]
    vol = nm_id // 100000
    part = nm_id // 1000
    basket_host = get_basket_host(nm_id)
    
    print("=" * 80)
    print(f"АРТИКУЛ: {nm_id}")
    print(f"ОЖИДАЕМАЯ ЦЕНА: {expected} ₽")
    print("=" * 80)
    
    # 1. Проверяем все возможные файлы на basket
    print("\n--- BASKET FILES ---")
    
    basket_files = [
        f"{basket_host}/vol{vol}/part{part}/{nm_id}/info/price-history.json",
        f"{basket_host}/vol{vol}/part{part}/{nm_id}/info/ru/card.json",
        f"{basket_host}/vol{vol}/part{part}/{nm_id}/info/sellers.json",
        # Попробуем другие возможные файлы
        f"{basket_host}/vol{vol}/part{part}/{nm_id}/info/ru/sale.json",
        f"{basket_host}/vol{vol}/part{part}/{nm_id}/info/sale.json",
        f"{basket_host}/vol{vol}/part{part}/{nm_id}/info/ru/sizes.json",
        f"{basket_host}/vol{vol}/part{part}/{nm_id}/info/sizes.json",
    ]
    
    for url in basket_files:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                short_url = url.split("/")[-1]
                
                # Ищем что-то похожее на цену
                def find_prices(obj, path=""):
                    results = []
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if isinstance(v, (int, float)) and 10000 < v < 10000000:
                                # Похоже на цену в копейках
                                results.append((f"{path}.{k}" if path else k, v, v/100))
                            elif isinstance(v, (dict, list)):
                                results.extend(find_prices(v, f"{path}.{k}" if path else k))
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj[:3]):  # только первые 3
                            results.extend(find_prices(item, f"{path}[{i}]"))
                    return results
                
                prices = find_prices(data)
                if prices:
                    print(f"\n✅ {short_url}:")
                    for path, raw, converted in prices[:5]:
                        match = "← MATCH!" if abs(converted - expected) < 50 else ""
                        print(f"   {path}: {raw} ({converted:.2f} ₽) {match}")
                        
        except Exception as e:
            pass
    
    # 2. Пробуем card.wb.ru с прокси
    print("\n--- CARD.WB.RU (разные варианты) ---")
    
    card_urls = [
        # Стандартные варианты
        f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={nm_id}",
        f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&nm={nm_id}",
        f"https://card.wb.ru/cards/detail?appType=1&curr=rub&dest=-1257786&nm={nm_id}",
        # Без spp
        f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&nm={nm_id}",
        # С locale
        f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&locale=ru&nm={nm_id}",
    ]
    
    for url in card_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            status = resp.status_code
            if status == 200:
                print(f"   ✅ {status}: {url[:60]}...")
                try:
                    data = resp.json()
                    products = data.get("data", {}).get("products", [])
                    if products:
                        p = products[0]
                        sale_price = p.get("salePriceU", 0) / 100
                        price_u = p.get("priceU", 0) / 100
                        print(f"      salePriceU: {sale_price}, priceU: {price_u}")
                except:
                    pass
            else:
                print(f"   ❌ {status}")
        except Exception as e:
            print(f"   ❌ {type(e).__name__}")
    
    # 3. Пробуем получить цену со страницы товара
    print("\n--- HTML СТРАНИЦА (парсинг) ---")
    
    page_url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            html = resp.text
            
            # Ищем JSON в script тегах
            # WB часто вставляет данные в window.__INITIAL_STATE__ или подобное
            patterns = [
                r'"price"\s*:\s*(\d+)',
                r'"salePriceU"\s*:\s*(\d+)',
                r'"priceU"\s*:\s*(\d+)',
                r'data-price="(\d+)"',
                r'"currentPrice"\s*:\s*(\d+)',
                r'"finalPrice"\s*:\s*(\d+)',
            ]
            
            found_prices = set()
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for m in matches:
                    val = int(m)
                    if 100 < val < 10000000:
                        found_prices.add(val)
            
            if found_prices:
                print(f"   Найденные значения в HTML:")
                for p in sorted(found_prices):
                    if p > 10000:  # копейки
                        print(f"      {p} → {p/100:.2f} ₽")
                    else:  # рубли
                        print(f"      {p} ₽")
            else:
                print("   Цены в HTML не найдены")
                
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {e}")
    
    # 4. Проверяем API корзины
    print("\n--- КОРЗИНА/CHECKOUT API ---")
    
    cart_urls = [
        f"https://cart-storage.wildberries.ru/v2/product?nmId={nm_id}",
        f"https://www.wildberries.ru/webapi/spa/product/{nm_id}",
        f"https://www.wildberries.ru/api/product/{nm_id}",
    ]
    
    for url in cart_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                print(f"   ✅ {resp.status_code}: {url}")
                try:
                    data = resp.json()
                    print(f"      Keys: {list(data.keys())[:5]}")
                except:
                    print(f"      (не JSON)")
            else:
                print(f"   ❌ {resp.status_code}: {url}")
        except Exception as e:
            print(f"   ❌ {type(e).__name__}: {url}")

print("\n" + "=" * 80)
print("ГОТОВО")
print("=" * 80)