import requests
import time

PROXY_LOGIN = "23fmwsTtvu"
PROXY_PASSWORD = "Wx8hCmKzI5"
PROXY_IP = "45.132.252.132"
PROXY_PORT = "38267"

PROXY_URL = f"http://{PROXY_LOGIN}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

NM_ID = 169684889

def test_with_session():
    """Создаём сессию и сначала заходим на главную для получения cookies"""
    
    session = requests.Session()
    session.proxies = PROXIES
    
    # Заголовки как у реального браузера
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    })
    
    print("="*70)
    print("ТЕСТ С СЕССИЕЙ И COOKIES")
    print("="*70)
    
    # 1. Заходим на главную WB для получения cookies
    print("\n[1] Заходим на wildberries.ru...")
    try:
        r = session.get("https://www.wildberries.ru/", timeout=15)
        print(f"    Статус: {r.status_code}")
        print(f"    Cookies получено: {len(session.cookies)}")
        for c in session.cookies:
            print(f"      - {c.name}: {c.value[:20]}...")
    except Exception as e:
        print(f"    ❌ Ошибка: {e}")
        return
    
    time.sleep(2)
    
    # 2. Заходим на страницу товара
    print(f"\n[2] Заходим на страницу товара {NM_ID}...")
    try:
        r = session.get(f"https://www.wildberries.ru/catalog/{NM_ID}/detail.aspx", timeout=15)
        print(f"    Статус: {r.status_code}")
        print(f"    Размер: {len(r.content)} байт")
    except Exception as e:
        print(f"    ❌ Ошибка: {e}")
    
    time.sleep(1)
    
    # 3. Теперь пробуем API с cookies
    print("\n[3] Запрос к search.wb.ru (с cookies)...")
    
    # Меняем заголовки для API
    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://www.wildberries.ru/catalog/{NM_ID}/detail.aspx",
        "Origin": "https://www.wildberries.ru",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    })
    
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?appType=1&curr=rub&dest=-1257786&query={NM_ID}&resultset=catalog&spp=30"
    
    try:
        r = session.get(url, timeout=15)
        print(f"    Статус: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            products = data.get("data", {}).get("products", [])
            
            if products:
                p = products[0]
                print(f"    ✅ УСПЕХ!")
                print(f"    Товар: {p.get('name')}")
                
                # Ищем цены
                sizes = p.get("sizes", [])
                if sizes:
                    price = sizes[0].get("price", {})
                    print(f"    basic: {price.get('basic', 0)/100} ₽")
                    print(f"    product: {price.get('product', 0)/100} ₽")
                    print(f"    total: {price.get('total', 0)/100} ₽")
                
                # Альтернативные поля цен
                if p.get("salePriceU"):
                    print(f"    salePriceU: {p.get('salePriceU', 0)/100} ₽")
                if p.get("priceU"):
                    print(f"    priceU: {p.get('priceU', 0)/100} ₽")
            else:
                print(f"    ⚠️ products пустой")
                print(f"    Ответ: {str(data)[:200]}")
        else:
            print(f"    ❌ HTTP {r.status_code}")
            print(f"    {r.text[:200]}")
            
    except Exception as e:
        print(f"    ❌ Ошибка: {e}")
    
    # 4. Пробуем card.wb.ru с cookies
    print("\n[4] Запрос к card.wb.ru (с cookies)...")
    
    url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={NM_ID}"
    
    try:
        r = session.get(url, timeout=15)
        print(f"    Статус: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            products = data.get("data", {}).get("products", [])
            if products:
                print(f"    ✅ УСПЕХ! Товар найден")
            else:
                print(f"    ⚠️ Ответ: {str(data)[:200]}")
        else:
            print(f"    ❌ HTTP {r.status_code}")
            
    except Exception as e:
        print(f"    ❌ Ошибка: {e}")

    print(f"\n{'='*70}")
    print("ГОТОВО")
    print("="*70)


if __name__ == "__main__":
    test_with_session()