"""
test_basket_full.py — полный анализ данных с basket-серверов
"""

import requests

NM_ID = 169684889
EXPECTED_PRICE = 1090

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.wildberries.ru/",
}

def get_basket(nm_id):
    vol = nm_id // 100000
    if vol <= 143: return 1
    elif vol <= 287: return 2
    elif vol <= 431: return 3
    elif vol <= 719: return 4
    elif vol <= 1007: return 5
    elif vol <= 1061: return 6
    elif vol <= 1115: return 7
    elif vol <= 1169: return 8
    elif vol <= 1313: return 9
    elif vol <= 1601: return 10
    elif vol <= 1655: return 11
    elif vol <= 1919: return 12
    elif vol <= 2045: return 13
    elif vol <= 2189: return 14
    elif vol <= 2405: return 15
    elif vol <= 2621: return 16
    elif vol <= 2837: return 17
    else: return 18

vol = NM_ID // 100000
part = NM_ID // 1000
basket = get_basket(NM_ID)
base = f"https://basket-{basket:02d}.wbbasket.ru/vol{vol}/part{part}/{NM_ID}"

print("=" * 80)
print(f"ПОЛНЫЙ АНАЛИЗ BASKET-СЕРВЕРОВ ДЛЯ {NM_ID}")
print(f"Ожидаемая цена на сайте: {EXPECTED_PRICE} ₽")
print("=" * 80)

# 1. card.json
print("\n1. CARD.JSON (описание товара)")
print("-" * 40)

url = f"{base}/info/ru/card.json"
resp = requests.get(url, headers=HEADERS, timeout=15)
if resp.status_code == 200:
    card = resp.json()
    print(f"   nm_id: {card.get('nm_id')}")
    print(f"   imt_name: {card.get('imt_name')}")
    
    selling = card.get("selling", {})
    print(f"   brand_name: {selling.get('brand_name')}")
    
    # Может тут есть цена?
    for key in ["price", "priceU", "salePriceU", "sale", "discount"]:
        if key in card:
            print(f"   {key}: {card[key]}")
    
    # Проверяем все ключи
    print(f"\n   Все ключи: {list(card.keys())}")
else:
    print(f"   ❌ {resp.status_code}")

# 2. price-history.json
print("\n2. PRICE-HISTORY.JSON (история цен)")
print("-" * 40)

url = f"{base}/info/price-history.json"
resp = requests.get(url, headers=HEADERS, timeout=15)
if resp.status_code == 200:
    history = resp.json()
    print(f"   Записей: {len(history)}")
    
    if history:
        # Последние 3 записи
        print("\n   Последние записи:")
        for item in history[-3:]:
            dt = item.get("dt")
            price_rub = item.get("price", {}).get("RUB", 0)
            print(f"      dt={dt}, RUB={price_rub} ({price_rub/100:.2f} ₽)")
        
        # Текущая (последняя)
        current = history[-1].get("price", {}).get("RUB", 0)
        print(f"\n   Текущая по history: {current/100:.2f} ₽")
        print(f"   Ожидаемая: {EXPECTED_PRICE} ₽")
        print(f"   Разница: {EXPECTED_PRICE - current/100:.2f} ₽")
else:
    print(f"   ❌ {resp.status_code}")

# 3. sellers.json
print("\n3. SELLERS.JSON (информация о продавце)")
print("-" * 40)

url = f"{base}/info/sellers.json"
resp = requests.get(url, headers=HEADERS, timeout=15)
if resp.status_code == 200:
    sellers = resp.json()
    print(f"   supplierId: {sellers.get('supplierId')}")
    print(f"   supplierName: {sellers.get('supplierName')}")
    
    # Все ключи
    print(f"   Все ключи: {list(sellers.keys())}")
else:
    print(f"   ❌ {resp.status_code}")

# 4. Ищем другие файлы
print("\n4. ПОИСК ДРУГИХ ФАЙЛОВ")
print("-" * 40)

other_files = [
    "info/soldout.json",
    "info/ru/short.json",  
    "info/short.json",
    "info/ru/promotions.json",
    "info/promotions.json",
    "info/ru/sizes.json",
    "info/sizes.json",
    "info/ru/options.json",
    "info/options.json",
    "info/ru/compositions.json",
    "info/compositions.json",
    "info/ru/props.json",
    "info/props.json",
    "info/ru/related.json",
    "info/related.json",
    "info/ru/sets.json",
    "info/sets.json",
]

for file in other_files:
    url = f"{base}/{file}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            short_file = file.split("/")[-1]
            
            if isinstance(data, dict):
                keys = list(data.keys())[:5]
                print(f"   ✅ {short_file}: {keys}")
                
                # Ищем цену
                for k, v in data.items():
                    if isinstance(v, (int, float)) and 10000 < v < 10000000:
                        print(f"      {k}: {v} ({v/100:.2f} ₽)")
                        
            elif isinstance(data, list) and data:
                print(f"   ✅ {short_file}: list[{len(data)}]")
    except:
        pass

# 5. API остатков (работал)
print("\n5. PRODUCT-ORDER-QNT (остатки)")
print("-" * 40)

url = f"https://product-order-qnt.wildberries.ru/v2/by-nm/?nm={NM_ID}"
resp = requests.get(url, headers=HEADERS, timeout=15)
if resp.status_code == 200:
    data = resp.json()
    print(f"   Данные: {data}")
else:
    print(f"   ❌ {resp.status_code}")

# 6. Feedbacks
print("\n6. FEEDBACKS (рейтинг)")  
print("-" * 40)

url = f"https://feedbacks1.wb.ru/feedbacks/v1/{NM_ID}"
resp = requests.get(url, headers=HEADERS, timeout=15)
if resp.status_code == 200:
    data = resp.json()
    print(f"   valuation: {data.get('valuation')}")
    print(f"   feedbackCount: {data.get('feedbackCount')}")
else:
    print(f"   ❌ {resp.status_code}")

# 7. Вычисляем скидку
print("\n7. АНАЛИЗ ЦЕН")
print("-" * 40)

# Цена из history
url = f"{base}/info/price-history.json"
resp = requests.get(url, headers=HEADERS, timeout=15)
if resp.status_code == 200:
    history = resp.json()
    if history:
        base_price = history[-1].get("price", {}).get("RUB", 0) / 100
        
        print(f"   Базовая цена (из history): {base_price:.2f} ₽")
        print(f"   Цена на сайте (ожид.): {EXPECTED_PRICE} ₽")
        
        if base_price > 0:
            # СПП обычно 15-30%
            for spp in [15, 20, 25, 27, 30]:
                calculated = base_price * (1 - spp/100)
                diff = abs(calculated - EXPECTED_PRICE)
                match = "✅ MATCH!" if diff < 20 else ""
                print(f"   При СПП {spp}%: {calculated:.2f} ₽ {match}")

print("\n" + "=" * 80)
print("ВЫВОД:")
print("=" * 80)
print("""
WB хранит БАЗОВУЮ цену без скидок в price-history.json.
Финальная цена для покупателя = базовая цена × (1 - СПП/100)

СПП (Скидка Постоянного Покупателя) зависит от:
- Истории покупок пользователя  
- Региона
- Других персональных факторов

БЕЗ АВТОРИЗАЦИИ мы не можем узнать точную СПП!

ВАРИАНТЫ РЕШЕНИЯ:
1. Использовать российский прокси
2. Показывать базовую цену с пометкой "без учёта СПП"
3. Применять усреднённую СПП (например, 25%)
""")