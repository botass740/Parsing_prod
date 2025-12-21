import requests

PROXY_URL = "http://23fmwsTtvu:Wx8hCmKzI5@45.132.252.132:38267"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
}

TEST_NM = "227648352"

# Разные варианты dest
DESTS = [
    "-3827418",      # Из DevTools (работает в браузере)
    "-1257786",      # Москва (стандартный)
    "-1029256",      # СПб
    "0",
    "-1",
]

print("="*70)
print("ПОИСК РАБОЧЕГО dest")
print("="*70)

for dest in DESTS:
    # Формат как в DevTools
    url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&dest={dest}&spp=30&nm={TEST_NM}"
    
    print(f"\n[dest={dest}]")
    
    # Без прокси
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        status = r.status_code
        
        if status == 200:
            data = r.json()
            products = data.get("data", {}).get("products", [])
            if not products:
                products = data.get("products", [])
            
            if products:
                p = products[0]
                price = p.get("sizes", [{}])[0].get("price", {})
                basic = price.get("basic", 0) / 100
                product = price.get("product", 0) / 100
                print(f"  БЕЗ прокси: ✅ basic={basic}, product={product}")
            else:
                print(f"  БЕЗ прокси: ⚠️ 200, но products пустой")
        else:
            print(f"  БЕЗ прокси: ❌ {status}")
    except Exception as e:
        print(f"  БЕЗ прокси: ❌ {str(e)[:40]}")
    
    # С прокси
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
        status = r.status_code
        
        if status == 200:
            data = r.json()
            products = data.get("data", {}).get("products", [])
            if not products:
                products = data.get("products", [])
            
            if products:
                p = products[0]
                price = p.get("sizes", [{}])[0].get("price", {})
                basic = price.get("basic", 0) / 100
                product = price.get("product", 0) / 100
                print(f"  С прокси:   ✅ basic={basic}, product={product}")
            else:
                print(f"  С прокси:   ⚠️ 200, но products пустой")
        else:
            print(f"  С прокси:   ❌ {status}")
    except Exception as e:
        print(f"  С прокси:   ❌ {str(e)[:40]}")

print("\n" + "="*70)
print("ГОТОВО")
print("="*70)