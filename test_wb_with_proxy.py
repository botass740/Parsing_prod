import os
import requests
from urllib.parse import quote

# === ВПИШИ СВОИ ДАННЫЕ ===
PROXY_LOGIN = "23fmwsTtvu"
PROXY_PASSWORD = "Wx8hCmKzI5"  # <-- впиши реальный пароль
PROXY_IP = "45.132.252.132"
PROXY_PORT = "38267"

# URL-кодируем пароль (на случай спецсимволов)
PROXY_PASSWORD_ENCODED = quote(PROXY_PASSWORD, safe="")

PROXY_URL = f"http://{PROXY_LOGIN}:{PROXY_PASSWORD_ENCODED}@{PROXY_IP}:{PROXY_PORT}"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

print(f"Прокси (без пароля): http://{PROXY_LOGIN}:****@{PROXY_IP}:{PROXY_PORT}")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

NM_ID = 169684889


def test_proxy():
    """Проверка что прокси работает"""
    print(f"\n{'='*60}")
    print("Проверка прокси...")
    
    try:
        r = requests.get("https://api.ipify.org?format=json", proxies=PROXIES, timeout=10)
        ip = r.json().get("ip")
        print(f"✅ Прокси работает! IP: {ip}")
        return True
    except Exception as e:
        print(f"❌ Прокси не работает: {e}")
        return False


def test_card_wb():
    """Тест card.wb.ru — точные цены"""
    url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={NM_ID}"
    print(f"\n{'='*60}")
    print(f"Тест: card.wb.ru")
    
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=15)
        print(f"Статус: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            products = data.get("data", {}).get("products", [])
            if products:
                p = products[0]
                print(f"✅ Успех!")
                print(f"   Название: {p.get('name')}")
                print(f"   Бренд: {p.get('brand')}")
                
                sizes = p.get("sizes", [])
                if sizes:
                    price_info = sizes[0].get("price", {})
                    basic = price_info.get("basic", 0) / 100
                    product_price = price_info.get("product", 0) / 100
                    total = price_info.get("total", 0) / 100
                    print(f"   Цена basic (старая): {basic} ₽")
                    print(f"   Цена product (без СПП): {product_price} ₽")
                    print(f"   Цена total (с СПП): {total} ₽")
                
                print(f"   Рейтинг: {p.get('reviewRating')}")
                print(f"   Отзывов: {p.get('feedbacks')}")
                return True
            else:
                print(f"⚠️ Пустой ответ")
        else:
            print(f"❌ HTTP {r.status_code}: {r.text[:300]}")
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
    
    return False


def test_basket():
    """Тест basket — текущий метод"""
    vol = NM_ID // 100000
    part = NM_ID // 1000
    basket = 2  # для vol=1696
    
    url = f"https://basket-{basket:02d}.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/ru/card.json"
    print(f"\n{'='*60}")
    print(f"Тест: basket (текущий)")
    
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=15)
        print(f"Статус: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print(f"✅ Успех!")
            print(f"   Название: {data.get('imt_name')}")
            return True
        else:
            print(f"❌ HTTP {r.status_code}")
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
    
    return False


if __name__ == "__main__":
    print("="*60)
    print("ТЕСТ WB API ЧЕРЕЗ ПРОКСИ")
    print("="*60)
    
    if not test_proxy():
        print("\n⛔ Прокси не работает, дальнейшие тесты невозможны")
        exit(1)
    
    test_card_wb()
    test_basket()
    
    print(f"\n{'='*60}")
    print("ГОТОВО")
    print("="*60)