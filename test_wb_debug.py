import requests
from urllib.parse import quote

# === ТВОИ ДАННЫЕ (уже вписаны) ===
PROXY_LOGIN = "23fmwsTtvu"
PROXY_PASSWORD = "Wx8hCmKzI5"
PROXY_IP = "45.132.252.132"
PROXY_PORT = "38267"

PROXY_URL = f"http://{PROXY_LOGIN}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
}

NM_ID = 169684889


def get_basket_host(nm_id: int) -> tuple[str, int, int]:
    """Возвращает (host, vol, part)"""
    vol = nm_id // 100000
    part = nm_id // 1000
    
    if vol <= 143: n = 1
    elif vol <= 287: n = 2
    elif vol <= 431: n = 3
    elif vol <= 719: n = 4
    elif vol <= 1007: n = 5
    elif vol <= 1061: n = 6
    elif vol <= 1115: n = 7
    elif vol <= 1169: n = 8
    elif vol <= 1313: n = 9
    elif vol <= 1601: n = 10
    elif vol <= 1655: n = 11
    elif vol <= 1919: n = 12
    elif vol <= 2045: n = 13
    elif vol <= 2189: n = 14
    elif vol <= 2405: n = 15
    elif vol <= 2621: n = 16
    elif vol <= 2837: n = 17
    elif vol <= 3053: n = 18
    elif vol <= 3269: n = 19
    elif vol <= 3485: n = 20
    elif vol <= 3701: n = 21
    elif vol <= 3917: n = 22
    elif vol <= 4133: n = 23
    elif vol <= 4349: n = 24
    elif vol <= 4565: n = 25
    elif vol <= 4781: n = 26
    elif vol <= 4997: n = 27
    elif vol <= 5213: n = 28
    elif vol <= 5429: n = 29
    elif vol <= 5645: n = 30
    elif vol <= 5861: n = 31
    else: n = 32
    
    return f"https://basket-{n:02d}.wbbasket.ru", vol, part


def test_request(name: str, url: str, use_proxy: bool = True):
    """Универсальный тест запроса"""
    print(f"\n{'='*60}")
    print(f"Тест: {name}")
    print(f"Прокси: {'Да' if use_proxy else 'Нет'}")
    
    try:
        proxies = PROXIES if use_proxy else None
        r = requests.get(url, headers=HEADERS, proxies=proxies, timeout=15)
        print(f"Статус: {r.status_code}")
        
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"✅ JSON получен!")
                
                if "data" in data and "products" in data.get("data", {}):
                    products = data["data"]["products"]
                    if products:
                        p = products[0]
                        print(f"   Товар: {p.get('name', 'N/A')}")
                        sizes = p.get("sizes", [])
                        if sizes and sizes[0].get("price"):
                            price = sizes[0]["price"]
                            print(f"   basic (старая): {price.get('basic', 0)/100} ₽")
                            print(f"   product (без СПП): {price.get('product', 0)/100} ₽")
                            print(f"   total (с СПП): {price.get('total', 0)/100} ₽")
                    else:
                        print(f"   Пустой products")
                        
                elif "imt_name" in data:
                    print(f"   Название: {data.get('imt_name')}")
                    
                elif isinstance(data, list) and data:
                    print(f"   Записей: {len(data)}")
                    
            except:
                print(f"   Ответ: {r.text[:200]}")
        else:
            print(f"❌ HTTP {r.status_code}")
            if r.text:
                print(f"   {r.text[:200]}")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    print("="*60)
    print("ТЕСТ WB API ЧЕРЕЗ ПРОКСИ")
    print(f"Артикул: {NM_ID}")
    print("="*60)
    
    # 1. Проверка прокси
    print("\n>>> Проверка прокси...")
    try:
        r = requests.get("https://httpbin.org/ip", proxies=PROXIES, timeout=10)
        print(f"✅ Прокси работает! IP: {r.json().get('origin')}")
    except Exception as e:
        print(f"❌ Прокси ошибка: {e}")
        exit(1)
    
    host, vol, part = get_basket_host(NM_ID)
    print(f"\n>>> Basket: {host}, vol={vol}, part={part}")
    
    # 2. Basket БЕЗ прокси
    test_request(
        "basket card.json (БЕЗ прокси)",
        f"{host}/vol{vol}/part{part}/{NM_ID}/info/ru/card.json",
        use_proxy=False
    )
    
    # 3. Basket С прокси
    test_request(
        "basket card.json (с прокси)",
        f"{host}/vol{vol}/part{part}/{NM_ID}/info/ru/card.json",
        use_proxy=True
    )
    
    # 4. card.wb.ru
    test_request(
        "card.wb.ru",
        f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={NM_ID}",
        use_proxy=True
    )
    
    # 5. feedbacks
    test_request(
        "feedbacks1.wb.ru",
        f"https://feedbacks1.wb.ru/feedbacks/v1/{NM_ID}",
        use_proxy=True
    )
    
    print(f"\n{'='*60}")
    print("ГОТОВО")
    print("="*60)