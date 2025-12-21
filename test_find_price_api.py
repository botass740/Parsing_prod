import requests
import time

PROXY_URL = "http://23fmwsTtvu:Wx8hCmKzI5@45.132.252.132:38267"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
}

TEST_IDS = [227648352, 443549513, 158173097, 535935438]

print("="*70)
print("ПОИСК API С РЕАЛЬНЫМИ ЦЕНАМИ")
print("="*70)

# Попробуем разные endpoints
ENDPOINTS = [
    # Новые версии API
    ("card.wb.ru v3", "https://card.wb.ru/cards/v3/detail?appType=1&curr=rub&dest=-1257786&nm={nm}"),
    ("card.wb.ru v2 list", "https://card.wb.ru/cards/v2/list?appType=1&curr=rub&dest=-1257786&nm={nm}"),
    ("card.wb.ru baselist", "https://card.wb.ru/cards/baselist?appType=1&curr=rub&dest=-1257786&nm={nm}"),
    
    # Мобильное API
    ("mobile-api", "https://mobile-api.wildberries.ru/api/v1/cards?nm={nm}"),
    
    # Wbx API
    ("wbx-content", "https://wbx-content-v2.wbstatic.net/ru/{nm}.json"),
    
    # Suppliers API  
    ("suppliers-api", "https://suppliers-api.wildberries.ru/public/api/v1/info?quantity=0&nm={nm}"),
    
    # Card API без версии
    ("card.wb.ru simple", "https://card.wb.ru/cards/detail?nm={nm}&dest=-1257786&curr=rub"),
]

for nm_id in TEST_IDS[:2]:  # Проверим на 2 товарах
    print(f"\n{'='*70}")
    print(f"Товар: {nm_id}")
    print("="*70)
    
    for name, url_template in ENDPOINTS:
        url = url_template.format(nm=nm_id)
        
        try:
            r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
            
            if r.status_code == 200:
                try:
                    data = r.json()
                    
                    # Ищем цены в разных структурах
                    prices_found = []
                    
                    # Структура 1: data.products[0].sizes[0].price
                    products = data.get("data", {}).get("products", [])
                    if products:
                        p = products[0]
                        sizes = p.get("sizes", [])
                        if sizes:
                            price = sizes[0].get("price", {})
                            if price:
                                prices_found.append(f"basic={price.get('basic',0)/100}, product={price.get('product',0)/100}, total={price.get('total',0)/100}")
                        
                        # Альтернативные поля
                        if p.get("salePriceU"):
                            prices_found.append(f"salePriceU={p['salePriceU']/100}")
                        if p.get("priceU"):
                            prices_found.append(f"priceU={p['priceU']/100}")
                    
                    # Структура 2: напрямую в корне
                    if data.get("salePriceU"):
                        prices_found.append(f"root.salePriceU={data['salePriceU']/100}")
                    
                    if prices_found:
                        print(f"  ✅ {name}: {', '.join(prices_found)}")
                    else:
                        print(f"  ⚠️  {name}: 200, но цены не найдены")
                        print(f"      Ключи: {list(data.keys())[:5] if isinstance(data, dict) else type(data)}")
                        
                except:
                    print(f"  ⚠️  {name}: 200, не JSON")
            else:
                print(f"  ❌ {name}: HTTP {r.status_code}")
                
        except Exception as e:
            print(f"  ❌ {name}: {str(e)[:50]}")
        
        time.sleep(0.3)

print(f"\n{'='*70}")
print("ГОТОВО")
print("="*70)