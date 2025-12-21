import requests
import re
import json

PROXY_URL = "http://23fmwsTtvu:Wx8hCmKzI5@45.132.252.132:38267"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

TEST_IDS = [227648352, 443549513]

print("="*70)
print("ПАРСИНГ ЦЕН ИЗ HTML СТРАНИЦЫ")
print("="*70)

for nm_id in TEST_IDS:
    url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
    print(f"\n{'='*70}")
    print(f"Товар: {nm_id}")
    print(f"URL: {url}")
    print("="*70)
    
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=20)
        print(f"Статус: {r.status_code}")
        print(f"Размер: {len(r.content)} байт")
        
        if r.status_code == 200:
            html = r.text
            
            # Способ 1: ищем JSON в <script> теге с данными товара
            # WB часто вставляет данные в window.__INITIAL_STATE__ или подобное
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});',
                r'"priceU"\s*:\s*(\d+)',
                r'"salePriceU"\s*:\s*(\d+)',
                r'"price"\s*:\s*(\d+)',
                r'data-price="(\d+)"',
                r'"currentPrice"\s*:\s*(\d+)',
                r'"finalPrice"\s*:\s*(\d+)',
            ]
            
            print("\nПоиск цен в HTML:")
            
            for pattern in patterns:
                matches = re.findall(pattern, html[:50000])  # Первые 50KB
                if matches:
                    print(f"  ✅ {pattern[:30]}...: {matches[:3]}")
            
            # Способ 2: ищем мета-теги с ценой
            meta_price = re.findall(r'<meta[^>]*property="product:price:amount"[^>]*content="(\d+)"', html)
            if meta_price:
                print(f"  ✅ meta product:price: {meta_price}")
            
            # Способ 3: ищем микроразметку Schema.org
            schema_price = re.findall(r'"price"\s*:\s*"?(\d+)"?', html)
            if schema_price:
                print(f"  ✅ schema price: {schema_price[:5]}")
            
            # Способ 4: ищем элементы с классами цен
            price_classes = re.findall(r'class="[^"]*price[^"]*"[^>]*>([^<]+)', html, re.IGNORECASE)
            if price_classes:
                # Фильтруем только числа
                prices = [p.strip() for p in price_classes if re.search(r'\d', p)]
                print(f"  ✅ class*=price: {prices[:5]}")
            
            # Покажем кусок HTML для анализа
            print(f"\n--- Первые 2000 символов HTML ---")
            print(html[:2000])
            
        elif r.status_code == 498:
            print("❌ 498 — антибот защита")
            print(f"Ответ: {r.text[:500]}")
            
        else:
            print(f"❌ Ошибка {r.status_code}")
            
    except Exception as e:
        print(f"❌ Исключение: {e}")

print(f"\n{'='*70}")
print("ГОТОВО")
print("="*70)