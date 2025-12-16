"""
test_with_proxy.py — тест API через прокси
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Берём прокси из .env
WB_PROXY_URL = os.getenv("WB_PROXY_URL", "").strip()

print("=" * 80)
print("ТЕСТ WB API ЧЕРЕЗ ПРОКСИ")
print("=" * 80)

if not WB_PROXY_URL:
    print("❌ WB_PROXY_URL не задан в .env!")
    print("   Добавь строку вида: WB_PROXY_URL=http://login:pass@ip:port")
    exit(1)

# Маскируем пароль для вывода
masked_proxy = WB_PROXY_URL
if "@" in masked_proxy:
    parts = masked_proxy.split("@")
    creds = parts[0].split("//")[1] if "//" in parts[0] else parts[0]
    if ":" in creds:
        user = creds.split(":")[0]
        masked_proxy = masked_proxy.replace(creds, f"{user}:****")

print(f"Прокси: {masked_proxy}")

PROXIES = {
    "http": WB_PROXY_URL,
    "https": WB_PROXY_URL,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
}

NM_ID = 169684889

# 1. Проверяем что прокси работает
print("\n1. ПРОВЕРКА ПРОКСИ...")
try:
    resp = requests.get("https://api.ipify.org?format=json", proxies=PROXIES, timeout=10)
    if resp.status_code == 200:
        ip = resp.json().get("ip")
        print(f"   ✅ Прокси работает! IP: {ip}")
    else:
        print(f"   ❌ Прокси вернул: {resp.status_code}")
except Exception as e:
    print(f"   ❌ Прокси не работает: {e}")
    exit(1)

# 2. Тестируем card.wb.ru через прокси
print("\n2. CARD.WB.RU ЧЕРЕЗ ПРОКСИ...")

card_urls = [
    f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={NM_ID}",
    f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&nm={NM_ID}",
    f"https://card.wb.ru/cards/detail?appType=1&curr=rub&dest=-1257786&nm={NM_ID}",
]

for url in card_urls:
    try:
        resp = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=15)
        short_url = url.replace(f"nm={NM_ID}", "nm=...").split("?")[0].split("/")[-1]
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                products = data.get("data", {}).get("products", [])
                if products:
                    p = products[0]
                    sale_price = p.get("salePriceU", 0) / 100
                    price = p.get("priceU", 0) / 100
                    rating = p.get("rating")
                    
                    print(f"\n   ✅ {short_url}: РАБОТАЕТ!")
                    print(f"      salePriceU: {sale_price} ₽")
                    print(f"      priceU: {price} ₽")
                    print(f"      rating: {rating}")
                    print(f"      Полный URL: {url}")
                else:
                    print(f"   ⚠️ {short_url}: 200, но products пустой")
            except ValueError:
                print(f"   ⚠️ {short_url}: 200, но не JSON")
        else:
            print(f"   ❌ {short_url}: {resp.status_code}")
            
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {e}")

# 3. Тестируем search.wb.ru через прокси
print("\n3. SEARCH.WB.RU ЧЕРЕЗ ПРОКСИ...")

search_url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&curr=rub&dest=-1257786&query={NM_ID}&resultset=catalog"

try:
    resp = requests.get(search_url, headers=HEADERS, proxies=PROXIES, timeout=15)
    
    if resp.status_code == 200:
        data = resp.json()
        products = data.get("data", {}).get("products", [])
        if products:
            p = products[0]
            sale_price = p.get("salePriceU", 0) / 100
            price = p.get("priceU", 0) / 100
            
            print(f"   ✅ РАБОТАЕТ!")
            print(f"      salePriceU: {sale_price} ₽")
            print(f"      priceU: {price} ₽")
        else:
            print(f"   ⚠️ 200, но products пустой")
    elif resp.status_code == 429:
        print(f"   ❌ 429 Too Many Requests (прокси тоже в бане)")
    else:
        print(f"   ❌ {resp.status_code}")
        
except Exception as e:
    print(f"   ❌ {type(e).__name__}: {e}")

# 4. HTML страница через прокси
print("\n4. HTML СТРАНИЦА ЧЕРЕЗ ПРОКСИ...")

page_url = f"https://www.wildberries.ru/catalog/{NM_ID}/detail.aspx"

try:
    page_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    resp = requests.get(page_url, headers=page_headers, proxies=PROXIES, timeout=15)
    
    print(f"   Status: {resp.status_code}")
    print(f"   Content-Length: {len(resp.text)} символов")
    
    if resp.status_code == 200 and len(resp.text) > 5000:
        print(f"   ✅ Страница загружена!")
    else:
        print(f"   ⚠️ Возможно заблокировано")
        
except Exception as e:
    print(f"   ❌ {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("ГОТОВО")
print("=" * 80)