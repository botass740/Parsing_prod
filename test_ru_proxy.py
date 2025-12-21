"""
test_ru_proxy.py — проверка российского прокси
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

WB_PROXY_URL = os.getenv("WB_PROXY_URL", "").strip()

print("=" * 60)
print("ТЕСТ РОССИЙСКОГО ПРОКСИ")
print("=" * 60)

if not WB_PROXY_URL:
    print("❌ WB_PROXY_URL не задан в .env!")
    exit(1)

# Маскируем пароль
masked = WB_PROXY_URL
if "@" in masked:
    parts = masked.split("@")
    creds = parts[0].split("//")[1] if "//" in parts[0] else parts[0]
    if ":" in creds:
        user = creds.split(":")[0]
        masked = masked.replace(creds, f"{user}:****")

print(f"Прокси: {masked}")

PROXIES = {"http": WB_PROXY_URL, "https": WB_PROXY_URL}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
}

NM_ID = 169684889

# 1. Проверяем IP
print("\n1. ПРОВЕРКА IP...")
try:
    resp = requests.get("https://api.ipify.org?format=json", proxies=PROXIES, timeout=10)
    if resp.status_code == 200:
        ip = resp.json().get("ip")
        print(f"   ✅ IP через прокси: {ip}")
    else:
        print(f"   ❌ Ошибка: {resp.status_code}")
except Exception as e:
    print(f"   ❌ Прокси не работает: {e}")
    exit(1)

# 2. Проверяем геолокацию
print("\n2. ГЕОЛОКАЦИЯ IP...")
try:
    resp = requests.get(f"http://ip-api.com/json/{ip}?lang=ru", timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        country = data.get("country", "?")
        city = data.get("city", "?")
        print(f"   Страна: {country}")
        print(f"   Город: {city}")
        
        if data.get("countryCode") == "RU":
            print("   ✅ Это российский IP!")
        else:
            print("   ⚠️ Это НЕ российский IP! WB может блокировать.")
except Exception as e:
    print(f"   ⚠️ Не удалось проверить геолокацию: {e}")

# 3. Тестируем card.wb.ru
print("\n3. ТЕСТ CARD.WB.RU...")

card_url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={NM_ID}"

try:
    resp = requests.get(card_url, headers=HEADERS, proxies=PROXIES, timeout=15)
    print(f"   Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        products = data.get("data", {}).get("products", [])
        
        if products:
            p = products[0]
            sale_price = p.get("salePriceU", 0) / 100
            price = p.get("priceU", 0) / 100
            name = p.get("name", "")[:50]
            rating = p.get("rating")
            
            print(f"\n   ✅ РАБОТАЕТ!")
            print(f"   Товар: {name}")
            print(f"   Цена: {sale_price} ₽ (было {price} ₽)")
            print(f"   Рейтинг: {rating}")
        else:
            print("   ⚠️ Пустой список products")
            print(f"   Response: {resp.text[:200]}")
    else:
        print(f"   ❌ Ошибка: {resp.text[:200]}")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 4. Тестируем HTML страницу
print("\n4. ТЕСТ HTML СТРАНИЦЫ WB...")

page_url = f"https://www.wildberries.ru/catalog/{NM_ID}/detail.aspx"

try:
    resp = requests.get(page_url, headers=HEADERS, proxies=PROXIES, timeout=15)
    print(f"   Status: {resp.status_code}")
    print(f"   Content-Length: {len(resp.text)} символов")
    
    if resp.status_code == 200 and len(resp.text) > 5000:
        print("   ✅ Страница загружается!")
    else:
        print("   ⚠️ Возможно блокировка")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

print("\n" + "=" * 60)
print("ГОТОВО")
print("=" * 60)