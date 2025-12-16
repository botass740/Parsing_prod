"""
test_price_deep.py — глубокий поиск цен WB
"""

import requests
import re
import json

NM_ID = 169684889
EXPECTED_PRICE = 1090

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

print("=" * 80)
print(f"ГЛУБОКИЙ ПОИСК ЦЕНЫ ДЛЯ {NM_ID}")
print(f"Ожидаемая цена: {EXPECTED_PRICE} ₽")
print("=" * 80)

# 1. Загружаем HTML страницы
print("\n1. ЗАГРУЗКА HTML СТРАНИЦЫ...")
url = f"https://www.wildberries.ru/catalog/{NM_ID}/detail.aspx"

try:
    resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    print(f"   Status: {resp.status_code}")
    print(f"   URL после редиректов: {resp.url}")
    print(f"   Content-Length: {len(resp.text)} символов")
    
    html = resp.text
    
    # Сохраняем для анализа
    with open("wb_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("   Сохранено в wb_page.html")
    
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    html = ""

if html:
    # 2. Ищем JSON в script тегах
    print("\n2. ПОИСК JSON В SCRIPT ТЕГАХ...")
    
    # Паттерны для поиска встроенных данных
    script_patterns = [
        (r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});', "INITIAL_STATE"),
        (r'window\.__CONFIG__\s*=\s*(\{.+?\});', "CONFIG"),
        (r'window\.ssrModel\s*=\s*(\{.+?\});', "ssrModel"),
        (r'"priceForProduct"\s*:\s*(\{[^}]+\})', "priceForProduct"),
        (r'<script[^>]*type="application/json"[^>]*>(\{.+?\})</script>', "JSON script"),
        (r'data-nm="' + str(NM_ID) + r'"[^>]*data-price="(\d+)"', "data-price attr"),
    ]
    
    for pattern, name in script_patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        if matches:
            print(f"\n   ✅ Найден {name}: {len(matches)} совпадений")
            for i, match in enumerate(matches[:2]):  # первые 2
                try:
                    if match.startswith("{"):
                        data = json.loads(match)
                        print(f"      [{i}] Keys: {list(data.keys())[:10]}")
                    else:
                        print(f"      [{i}] Value: {match[:100]}")
                except:
                    print(f"      [{i}] Raw: {match[:200]}...")
    
    # 3. Ищем все числа похожие на цену
    print("\n3. ПОИСК ЧИСЕЛ ПОХОЖИХ НА ЦЕНУ...")
    
    # Цена в рублях (1090) или копейках (109000)
    target_prices = [EXPECTED_PRICE, EXPECTED_PRICE * 100]
    
    for target in target_prices:
        # Ищем точное совпадение
        pattern = rf'["\s:=]({target})["\s,}}\]]'
        matches = re.findall(pattern, html)
        if matches:
            print(f"   ✅ Найдено {target}: {len(matches)} раз")
            
            # Показываем контекст
            for m in re.finditer(pattern, html):
                start = max(0, m.start() - 50)
                end = min(len(html), m.end() + 50)
                context = html[start:end].replace("\n", " ").strip()
                print(f"      ...{context}...")
                break
    
    # 4. Ищем API вызовы в HTML
    print("\n4. ПОИСК API URL В HTML...")
    
    api_patterns = [
        r'(https?://[a-z0-9.-]+\.wildberries\.ru/[^"\'<>\s]+)',
        r'(https?://[a-z0-9.-]+\.wb\.ru/[^"\'<>\s]+)',
        r'(/api/[^"\'<>\s]+)',
        r'(/webapi/[^"\'<>\s]+)',
    ]
    
    found_apis = set()
    for pattern in api_patterns:
        matches = re.findall(pattern, html)
        for m in matches:
            if "price" in m.lower() or "card" in m.lower() or "product" in m.lower():
                found_apis.add(m)
    
    if found_apis:
        print(f"   Найдено {len(found_apis)} API URL:")
        for api in list(found_apis)[:10]:
            print(f"      {api[:80]}")

# 5. Пробуем мобильную версию
print("\n5. МОБИЛЬНАЯ ВЕРСИЯ САЙТА...")

mobile_headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml",
}

try:
    resp = requests.get(url, headers=mobile_headers, timeout=15)
    print(f"   Status: {resp.status_code}")
    
    mobile_html = resp.text
    
    # Ищем цену
    price_matches = re.findall(r'"price"\s*:\s*(\d+)', mobile_html)
    if price_matches:
        print(f"   Найдены цены: {price_matches[:5]}")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 6. Пробуем разные dest (регионы)
print("\n6. CARD.WB.RU С РАЗНЫМИ РЕГИОНАМИ...")

# Разные коды регионов
dests = [
    -1257786,   # Москва
    -1029256,   # Питер  
    -2133464,   # Новосибирск
    123585707,  # Другой формат
    0,
]

for dest in dests:
    url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest={dest}&nm={NM_ID}"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("data", {}).get("products", [])
            if products:
                p = products[0]
                print(f"   ✅ dest={dest}: salePriceU={p.get('salePriceU')}, priceU={p.get('priceU')}")
            else:
                print(f"   ⚠️ dest={dest}: пустой products")
        else:
            print(f"   ❌ dest={dest}: {resp.status_code}")
    except Exception as e:
        print(f"   ❌ dest={dest}: {type(e).__name__}")

# 7. Ищем через поиск (не exactmatch)
print("\n7. ПОИСК ЧЕРЕЗ РАЗНЫЕ SEARCH API...")

search_urls = [
    f"https://search.wb.ru/exactmatch/ru/common/v5/search?appType=1&curr=rub&dest=-1257786&query={NM_ID}&resultset=catalog",
    f"https://search.wb.ru/exactmatch/ru/common/v7/search?appType=1&curr=rub&dest=-1257786&query={NM_ID}&resultset=catalog",
    f"https://search.wb.ru/exactmatch/sng/common/v4/search?appType=1&curr=rub&dest=-1257786&query={NM_ID}&resultset=catalog",
    f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&curr=rub&dest=-1257786&query={NM_ID}",
]

for url in search_urls:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("data", {}).get("products", [])
            if products:
                p = products[0]
                sale = p.get("salePriceU", 0) / 100
                price = p.get("priceU", 0) / 100
                print(f"   ✅ {url.split('/')[-1][:30]}: sale={sale}, price={price}")
            else:
                print(f"   ⚠️ Пустой ответ")
        else:
            print(f"   ❌ {resp.status_code}")
    except Exception as e:
        print(f"   ❌ {type(e).__name__}")

print("\n" + "=" * 80)
print("ГОТОВО. Проверь файл wb_page.html для ручного анализа")
print("=" * 80)