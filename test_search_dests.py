import requests
import time

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
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}

NM_ID = 169684889

# Популярные dest (регионы РФ)
DESTS = [
    ("-1257786", "Москва"),
    ("-1029256", "Санкт-Петербург"),
    ("-2133462", "Краснодар"),
    ("-1059500", "Казань"),
    ("-1113276", "Новосибирск"),
    ("-140294", "Екатеринбург"),
    ("12358296", "Москва alt"),
    ("123585548", "Электросталь"),
    ("-5818883", "Владивосток"),
    ("0", "По умолчанию"),
    ("1", "Вариант 1"),
]

print("="*70)
print("ПОИСК РАБОЧЕГО dest ДЛЯ search.wb.ru")
print(f"Артикул: {NM_ID}")
print("="*70)

for dest_id, dest_name in DESTS:
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?appType=1&curr=rub&dest={dest_id}&query={NM_ID}&resultset=catalog&spp=30"
    
    print(f"\n[{dest_name}] dest={dest_id}")
    
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
        
        if r.status_code == 200:
            try:
                data = r.json()
                products = data.get("data", {}).get("products", [])
                
                if products:
                    p = products[0]
                    
                    # Цены могут быть в разных местах
                    # Вариант 1: в sizes
                    sizes = p.get("sizes", [])
                    if sizes:
                        price_info = sizes[0].get("price", {})
                        if price_info:
                            basic = price_info.get("basic", 0) / 100
                            product = price_info.get("product", 0) / 100
                            total = price_info.get("total", 0) / 100
                            print(f"   ✅ РАБОТАЕТ! (через sizes)")
                            print(f"   Товар: {p.get('name', 'N/A')[:50]}")
                            print(f"   basic={basic}₽, product={product}₽, total={total}₽")
                            continue
                    
                    # Вариант 2: напрямую в product
                    sale_price = p.get("salePriceU", 0) / 100
                    price_u = p.get("priceU", 0) / 100
                    
                    if sale_price or price_u:
                        print(f"   ✅ РАБОТАЕТ! (через priceU)")
                        print(f"   Товар: {p.get('name', 'N/A')[:50]}")
                        print(f"   salePriceU={sale_price}₽, priceU={price_u}₽")
                    else:
                        # Покажем что есть в product
                        print(f"   ⚠️ Товар найден, но цены непонятные")
                        print(f"   Ключи: {list(p.keys())[:10]}")
                else:
                    print(f"   ⚠️ 200, но products пустой")
                    
            except Exception as e:
                print(f"   ⚠️ Ошибка парсинга: {e}")
                
        elif r.status_code == 429:
            print(f"   ❌ 429 Rate Limit — пауза 2 сек...")
            time.sleep(2)
        else:
            print(f"   ❌ HTTP {r.status_code}")
            
    except Exception as e:
        print(f"   ❌ Ошибка: {str(e)[:50]}")
    
    # Небольшая пауза между запросами
    time.sleep(0.5)

# Дополнительно: попробуем basket price-info
print(f"\n{'='*70}")
print("АЛЬТЕРНАТИВА: basket price-info endpoints")
print("="*70)

vol = NM_ID // 100000
part = NM_ID // 1000

BASKET_URLS = [
    f"https://basket-12.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/price-history.json",
    f"https://basket-12.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/ru/card.json",
    f"https://basket-12.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/sellers.json",
]

for url in BASKET_URLS:
    name = url.split("/")[-1]
    print(f"\n[{name}]")
    
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
        print(f"   Статус: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            
            if isinstance(data, list) and data:
                # price-history
                last = data[-1]
                if "price" in last:
                    price = last["price"].get("RUB", 0) / 100
                    print(f"   ✅ Последняя цена: {price} ₽")
                    print(f"   Всего записей: {len(data)}")
            elif isinstance(data, dict):
                if "imt_name" in data:
                    print(f"   ✅ Название: {data.get('imt_name')}")
                else:
                    print(f"   ✅ Ключи: {list(data.keys())[:8]}")
                    
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

print(f"\n{'='*70}")
print("ГОТОВО")
print("="*70)