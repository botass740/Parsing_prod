"""
test_wb_price.py — детальная проверка эндпоинтов с ценами
"""

import requests
from datetime import datetime

NM_ID = 169684889
VOL = NM_ID // 100000
PART = NM_ID // 1000
BASKET = 12

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
}

print("=" * 80)
print(f"ДЕТАЛЬНАЯ ПРОВЕРКА ЦЕН ДЛЯ АРТИКУЛА {NM_ID}")
print("=" * 80)

# 1. price-history.json
print("\n" + "─" * 80)
print("1. PRICE-HISTORY.JSON (история цен)")
print("─" * 80)

url = f"https://basket-{BASKET:02d}.wbbasket.ru/vol{VOL}/part{PART}/{NM_ID}/info/price-history.json"
resp = requests.get(url, headers=HEADERS, timeout=10)
if resp.status_code == 200:
    data = resp.json()
    print(f"   Записей в истории: {len(data)}")
    if data:
        # Последняя запись = текущая цена?
        latest = data[-1] if isinstance(data, list) else data
        print(f"   Последняя запись: {latest}")
        
        # Все записи
        print("\n   Вся история:")
        for item in data[-5:]:  # последние 5
            dt = item.get("dt")
            price_data = item.get("price", {})
            if isinstance(dt, int):
                dt_str = datetime.fromtimestamp(dt).strftime("%Y-%m-%d")
            else:
                dt_str = str(dt)
            print(f"      {dt_str}: {price_data}")
else:
    print(f"   ❌ Status: {resp.status_code}")


# 2. product-order-qnt (остатки)
print("\n" + "─" * 80)
print("2. PRODUCT-ORDER-QNT (остатки)")
print("─" * 80)

url = f"https://product-order-qnt.wildberries.ru/v2/by-nm/?nm={NM_ID}"
resp = requests.get(url, headers=HEADERS, timeout=10)
if resp.status_code == 200:
    data = resp.json()
    print(f"   Данные: {data}")
else:
    print(f"   ❌ Status: {resp.status_code}")


# 3. feedbacks (рейтинг)
print("\n" + "─" * 80)
print("3. FEEDBACKS (рейтинг и отзывы)")
print("─" * 80)

url = f"https://feedbacks1.wb.ru/feedbacks/v1/{NM_ID}"
resp = requests.get(url, headers=HEADERS, timeout=10)
if resp.status_code == 200:
    data = resp.json()
    print(f"   valuation (рейтинг): {data.get('valuation')}")
    print(f"   feedbackCount: {data.get('feedbackCount')}")
    print(f"   valuationSum: {data.get('valuationSum')}")
else:
    print(f"   ❌ Status: {resp.status_code}")


# 4. Пробуем найти текущую цену через другие эндпоинты
print("\n" + "─" * 80)
print("4. ПОИСК ЭНДПОИНТА С ТЕКУЩЕЙ ЦЕНОЙ")
print("─" * 80)

price_endpoints = [
    # Возможные API для цен
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&nm={NM_ID}",
    f"https://card.wb.ru/cards/detail?appType=1&curr=rub&dest=-1257786&nm={NM_ID}",
    f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&nm={NM_ID}",
    
    # С добавлением locale
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&nm={NM_ID}&locale=ru",
    
    # Mobile API?
    f"https://mobile-api.wildberries.ru/card/{NM_ID}",
    f"https://wbx-content-v2.wbstatic.net/price/{NM_ID}.json",
    
    # Через cors proxy домен
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={NM_ID}",
    
    # Seller API
    f"https://seller-content.wildberries.ru/card/{NM_ID}",
    
    # Catalog API
    f"https://catalog.wb.ru/catalog/electronic16/v2/catalog?appType=1&curr=rub&dest=-1257786&nm={NM_ID}",
    
    # Возможно через wbxsearch
    f"https://wbxsearch.wildberries.ru/exactmatch/v2/search?appType=1&curr=rub&dest=-1257786&query={NM_ID}",
    
    # Napi
    f"https://napi.wildberries.ru/api/catalog/{NM_ID}/detail.aspx",
]

for url in price_endpoints:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        status = resp.status_code
        
        short_url = url[:70] + "..." if len(url) > 70 else url
        
        if status == 200:
            try:
                data = resp.json()
                # Ищем цену
                price_found = False
                
                def find_price(obj, path=""):
                    """Рекурсивно ищем поля с ценой"""
                    if isinstance(obj, dict):
                        for key in ["salePriceU", "priceU", "price", "salePrice", "basicPrice"]:
                            if key in obj:
                                val = obj[key]
                                if isinstance(val, (int, float)) and val > 0:
                                    return f"{path}.{key}" if path else key, val
                        for k, v in obj.items():
                            result = find_price(v, f"{path}.{k}" if path else k)
                            if result:
                                return result
                    elif isinstance(obj, list) and obj:
                        result = find_price(obj[0], f"{path}[0]")
                        if result:
                            return result
                    return None
                
                result = find_price(data)
                if result:
                    print(f"   ✅ {short_url}")
                    print(f"      Найдена цена: {result[0]} = {result[1]}")
                else:
                    print(f"   ⚠️  {short_url} (200, но цена не найдена)")
                    
            except ValueError:
                print(f"   ⚠️  {short_url} (200, но не JSON)")
        else:
            print(f"   ❌ {short_url} ({status})")
            
    except Exception as e:
        short_url = url[:70] + "..." if len(url) > 70 else url
        print(f"   ❌ {short_url} ({type(e).__name__})")


# 5. Проверяем card.wb.ru с разными заголовками
print("\n" + "─" * 80)
print("5. CARD.WB.RU С РАЗНЫМИ ЗАГОЛОВКАМИ")
print("─" * 80)

url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&nm={NM_ID}"

header_variants = [
    # Вариант 1: Минимальные заголовки
    {"User-Agent": "Mozilla/5.0"},
    
    # Вариант 2: Как мобильное приложение
    {
        "User-Agent": "Wildberries/6.5.8000 (Android; SDK 33)",
        "Accept": "application/json",
    },
    
    # Вариант 3: Полные заголовки
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.wildberries.ru",
        "Referer": "https://www.wildberries.ru/catalog/169684889/detail.aspx",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    },
    
    # Вариант 4: С x-requested-with
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.wildberries.ru/",
    },
]

for i, headers in enumerate(header_variants, 1):
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            print(f"   ✅ Вариант {i}: Status 200!")
            try:
                data = resp.json()
                products = data.get("data", {}).get("products", [])
                if products:
                    p = products[0]
                    print(f"      salePriceU: {p.get('salePriceU')}")
                    print(f"      priceU: {p.get('priceU')}")
            except:
                pass
        else:
            print(f"   ❌ Вариант {i}: Status {resp.status_code}")
    except Exception as e:
        print(f"   ❌ Вариант {i}: {type(e).__name__}")

print("\n" + "=" * 80)
print("ГОТОВО")
print("=" * 80)