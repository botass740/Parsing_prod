import requests

PROXY_URL = "http://23fmwsTtvu:Wx8hCmKzI5@45.132.252.132:38267"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

# Заголовки из DevTools
HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "ru,en;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.wildberries.ru/catalog/227648352/detail.aspx",
    "sec-ch-ua": '"Chromium";v="120", "Not=A?Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-requested-with": "XMLHttpRequest",
}

TEST_IDS = [227648352, 443549513, 158173097, 535935438]

# Новый endpoint!
nm_string = ";".join(str(x) for x in TEST_IDS)
url = f"https://www.wildberries.ru/__internal/u-card/cards/v4/detail?appType=1&curr=rub&dest=12354108&spp=30&lang=ru&nm={nm_string}"

print("="*70)
print("ТЕСТ НОВОГО ENDPOINT")
print("="*70)
print(f"URL: .../__internal/u-card/cards/v4/detail?...nm={nm_string[:30]}...")
print("="*70)

# Без прокси
print("\n[1] Без прокси:")
try:
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"    Статус: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        products = data.get("data", {}).get("products", [])
        if not products:
            products = data.get("products", [])
        
        print(f"    ✅ Товаров: {len(products)}")
        
        for p in products[:4]:
            nm = p.get("id")
            name = p.get("name", "")[:35]
            sizes = p.get("sizes", [{}])
            price_info = sizes[0].get("price", {}) if sizes else {}
            basic = price_info.get("basic", 0) / 100
            product = price_info.get("product", 0) / 100
            qty = p.get("totalQuantity", 0)
            rating = p.get("reviewRating", 0)
            
            print(f"\n    📦 {nm}: {name}...")
            print(f"       Цена: {product} ₽ (было {basic} ₽)")
            print(f"       Рейтинг: {rating}, Остаток: {qty}")
    else:
        print(f"    ❌ {r.status_code}: {r.text[:200]}")
        
except Exception as e:
    print(f"    ❌ {e}")

# С прокси
print("\n" + "="*70)
print("[2] С прокси:")
try:
    r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=15)
    print(f"    Статус: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        products = data.get("data", {}).get("products", [])
        if not products:
            products = data.get("products", [])
        
        print(f"    ✅ Товаров: {len(products)}")
        
        for p in products[:2]:
            nm = p.get("id")
            sizes = p.get("sizes", [{}])
            price_info = sizes[0].get("price", {}) if sizes else {}
            product = price_info.get("product", 0) / 100
            print(f"    📦 {nm}: {product} ₽")
    else:
        print(f"    ❌ {r.status_code}: {r.text[:200]}")
        
except Exception as e:
    print(f"    ❌ {e}")

print("\n" + "="*70)
print("ГОТОВО")
print("="*70)