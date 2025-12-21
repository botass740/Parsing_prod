import requests

PROXY_LOGIN = "23fmwsTtvu"
PROXY_PASSWORD = "Wx8hCmKzI5"
PROXY_IP = "45.132.252.132"
PROXY_PORT = "38267"

PROXY_URL = f"http://{PROXY_LOGIN}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
}

NM_ID = 169684889

# Разные варианты URL для card.wb.ru
URLS = [
    # v2 с разными dest
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={NM_ID}",
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1029256&spp=30&nm={NM_ID}",
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=123585548&spp=30&nm={NM_ID}",
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=0&spp=30&nm={NM_ID}",
    
    # v1 (старый)
    f"https://card.wb.ru/cards/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={NM_ID}",
    f"https://card.wb.ru/cards/detail?appType=1&curr=rub&dest=-1029256&nm={NM_ID}",
    
    # Без spp
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&nm={NM_ID}",
    
    # С locale
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&locale=ru&nm={NM_ID}",
    
    # Множественные nm
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&nm={NM_ID};{NM_ID}",
    
    # search.wb.ru как альтернатива
    f"https://search.wb.ru/exactmatch/ru/common/v9/search?ab_testing=false&appType=1&curr=rub&dest=-1257786&query={NM_ID}&resultset=catalog&spp=30&suppressSpellcheck=false",
    f"https://search.wb.ru/exactmatch/ru/common/v7/search?appType=1&curr=rub&dest=-1257786&query={NM_ID}&resultset=catalog",
    f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&curr=rub&dest=-1257786&query={NM_ID}&resultset=catalog",
]

print("="*70)
print("ПОИСК РАБОЧЕГО API ДЛЯ ЦЕН WB")
print("="*70)

for i, url in enumerate(URLS, 1):
    # Короткое имя для вывода
    if "cards/v2" in url:
        name = "card.wb.ru/v2"
    elif "cards/detail" in url:
        name = "card.wb.ru/v1"
    elif "search.wb.ru" in url:
        name = "search.wb.ru"
    else:
        name = "other"
    
    # Извлекаем dest
    if "dest=" in url:
        dest = url.split("dest=")[1].split("&")[0]
    else:
        dest = "N/A"
    
    print(f"\n[{i:02d}] {name} (dest={dest})")
    
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
        
        if r.status_code == 200:
            try:
                data = r.json()
                products = data.get("data", {}).get("products", [])
                
                if products:
                    p = products[0]
                    sizes = p.get("sizes", [])
                    
                    if sizes and sizes[0].get("price"):
                        price = sizes[0]["price"]
                        basic = price.get("basic", 0) / 100
                        product = price.get("product", 0) / 100
                        total = price.get("total", 0) / 100
                        
                        print(f"     ✅ РАБОТАЕТ!")
                        print(f"     Товар: {p.get('name', 'N/A')[:40]}")
                        print(f"     Цены: basic={basic}₽, product={product}₽, total={total}₽")
                    else:
                        print(f"     ⚠️ 200, но нет цен в sizes")
                else:
                    print(f"     ⚠️ 200, но products пустой")
                    
            except Exception as e:
                print(f"     ⚠️ 200, но не JSON: {str(e)[:50]}")
        else:
            print(f"     ❌ HTTP {r.status_code}")
            
    except Exception as e:
        print(f"     ❌ Ошибка: {str(e)[:50]}")

print(f"\n{'='*70}")
print("ГОТОВО")
print("="*70)