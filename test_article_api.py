import requests

PROXY_URL = "http://23fmwsTtvu:Wx8hCmKzI5@45.132.252.132:38267"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
}

# Тестовые артикулы
TEST_IDS = [227648352, 443549513, 158173097, 535935438, 68789915]

# Формируем URL как в статье
nm_string = ";".join(str(x) for x in TEST_IDS)
url = f"https://card.wb.ru/cards/detail?appType=0&curr=rub&dest=-1257786&spp=30&nm={nm_string}"

print("="*70)
print("ТЕСТ API ИЗ СТАТЬИ")
print("="*70)
print(f"URL: {url[:80]}...")
print(f"Артикулов: {len(TEST_IDS)}")
print("="*70)

# Пробуем БЕЗ прокси
print("\n[1] Без прокси:")
try:
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"    Статус: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        products = data.get("data", {}).get("products", [])
        print(f"    ✅ Товаров получено: {len(products)}")
        
        for p in products:
            nm = p.get("id")
            name = p.get("name", "")[:40]
            price_old = p.get("priceU", 0) / 100
            price_sale = p.get("salePriceU", 0) / 100
            sale = p.get("sale", 0)
            rating = p.get("reviewRating")
            feedbacks = p.get("feedbacks", 0)
            qty = p.get("totalQuantity", 0)
            
            print(f"\n    📦 {nm}: {name}...")
            print(f"       Цена: {price_sale} ₽ (было {price_old} ₽, -{sale}%)")
            print(f"       Рейтинг: {rating} ({feedbacks} отзывов)")
            print(f"       Остаток: {qty} шт")
    else:
        print(f"    ❌ Ошибка: {r.text[:200]}")
        
except Exception as e:
    print(f"    ❌ {e}")

# Пробуем С прокси
print("\n" + "="*70)
print("[2] С прокси:")
try:
    r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=15)
    print(f"    Статус: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        products = data.get("data", {}).get("products", [])
        print(f"    ✅ Товаров получено: {len(products)}")
        
        for p in products[:3]:  # Первые 3 для краткости
            nm = p.get("id")
            name = p.get("name", "")[:40]
            price_sale = p.get("salePriceU", 0) / 100
            print(f"    📦 {nm}: {price_sale} ₽ — {name}...")
    else:
        print(f"    ❌ Ошибка: {r.text[:200]}")
        
except Exception as e:
    print(f"    ❌ {e}")

print("\n" + "="*70)
print("ГОТОВО")
print("="*70)