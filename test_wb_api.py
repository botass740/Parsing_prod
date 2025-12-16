"""
test_wb_api.py — поиск рабочих эндпоинтов для цен на basket-серверах
"""

import requests

NM_ID = 169684889
VOL = NM_ID // 100000  # 1696
PART = NM_ID // 1000   # 169684

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.wildberries.ru/",
}

BASKET = 12  # Для этого артикула

BASE = f"https://basket-{BASKET:02d}.wbbasket.ru/vol{VOL}/part{PART}/{NM_ID}"

# Возможные файлы с ценами на basket-серверах
ENDPOINTS = [
    # Стандартный card.json (уже работает)
    f"{BASE}/info/ru/card.json",
    
    # Возможные файлы с ценами
    f"{BASE}/info/price-history.json",
    f"{BASE}/info/ru/price.json",
    f"{BASE}/info/price.json",
    f"{BASE}/info/sellers.json",
    f"{BASE}/info/ru/sellers.json",
    f"{BASE}/info/stocks.json",
    f"{BASE}/info/ru/stocks.json",
    f"{BASE}/info/detail.json",
    f"{BASE}/info/ru/detail.json",
    f"{BASE}/info/data.json",
    f"{BASE}/info/ru/data.json",
    
    # Корневой info
    f"{BASE}/info/info.json",
    
    # Альтернативные пути
    f"https://basket-{BASKET:02d}.wbbasket.ru/vol{VOL}/part{PART}/{NM_ID}/data.json",
    f"https://basket-{BASKET:02d}.wbbasket.ru/vol{VOL}/part{PART}/{NM_ID}/price.json",
    
    # Проверим card.wb.ru с прокси-обходом через другие домены
    f"https://wbx-content-v2.wbstatic.net/ru/{NM_ID}.json",
    f"https://wbx-content-v2.wbstatic.net/price/{NM_ID}.json",
    
    # Альтернативный API для цен
    f"https://product-order-qnt.wildberries.ru/v2/by-nm/?nm={NM_ID}",
    f"https://product-order-qnt.wildberries.ru/by-nm/?nm={NM_ID}",
    
    # Feedbacks/rating
    f"https://feedbacks1.wb.ru/feedbacks/v1/{NM_ID}",
    f"https://feedbacks2.wb.ru/feedbacks/v1/{NM_ID}",
]

print("=" * 80)
print("ПОИСК РАБОЧИХ ЭНДПОИНТОВ ДЛЯ ЦЕН WILDBERRIES")
print(f"Тестовы�� артикул: {NM_ID}")
print("=" * 80)

working = []

for url in ENDPOINTS:
    print(f"\n{'─' * 80}")
    # Обрезаем URL для читаемости
    display_url = url if len(url) < 75 else url[:72] + "..."
    print(f"URL: {display_url}")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "")
            
            if "json" in content_type or resp.text.startswith("{") or resp.text.startswith("["):
                try:
                    data = resp.json()
                    print(f"✅ РАБОТАЕТ! Content-Type: {content_type}")
                    
                    # Показываем структуру
                    if isinstance(data, dict):
                        keys = list(data.keys())[:10]
                        print(f"   Keys: {keys}")
                        
                        # Ищем цены
                        for key in ["price", "priceU", "salePriceU", "sale", "rating", "stocks", "qty"]:
                            if key in data:
                                print(f"   {key} = {data[key]}")
                        
                        # Проверяем вложенные структуры
                        if "data" in data:
                            print(f"   data keys: {list(data['data'].keys())[:5] if isinstance(data['data'], dict) else type(data['data'])}")
                            
                    elif isinstance(data, list):
                        print(f"   Array length: {len(data)}")
                        if data and isinstance(data[0], dict):
                            print(f"   First item keys: {list(data[0].keys())[:5]}")
                    
                    working.append(url)
                    
                except ValueError:
                    print(f"⚠️  Status 200, но не валидный JSON")
            else:
                print(f"⚠️  Status 200, но Content-Type: {content_type}")
        else:
            # Не выводим текст ошибки для 404
            if resp.status_code != 404:
                print(f"   Response: {resp.text[:80]}")
                
    except requests.Timeout:
        print("❌ Timeout")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("ИТОГИ:")
print("=" * 80)

if working:
    print(f"\n✅ Рабочие эндпоинты ({len(working)}):")
    for url in working:
        print(f"   {url}")
else:
    print("\n❌ Рабочих эндпоинтов не найдено")

print("\n" + "=" * 80)