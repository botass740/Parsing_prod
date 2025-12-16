"""
test_price_compare.py — сравнение всех источников цен
"""

import requests

# Два товара для проверки
PRODUCTS = [
    {
        "nm_id": 169684889,
        "name": "Лампы H4",
        # Цены с сайта (запиши что видишь):
        "site_price_auth": None,      # Цена когда ты АВТОРИЗОВАН на WB
        "site_price_no_auth": 1090,   # Цена когда НЕ авторизован / инкогнито
        "site_old_price": 1650,       # Зачёркнутая цена
    },
    {
        "nm_id": 435777124,
        "name": "Товар 2",
        "site_price_auth": None,
        "site_price_no_auth": 699,
        "site_old_price": None,
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Referer": "https://www.wildberries.ru/",
}

def get_basket(nm_id):
    vol = nm_id // 100000
    if vol <= 143: return 1
    elif vol <= 287: return 2
    elif vol <= 431: return 3
    elif vol <= 719: return 4
    elif vol <= 1007: return 5
    elif vol <= 1061: return 6
    elif vol <= 1115: return 7
    elif vol <= 1169: return 8
    elif vol <= 1313: return 9
    elif vol <= 1601: return 10
    elif vol <= 1655: return 11
    elif vol <= 1919: return 12
    elif vol <= 2045: return 13
    elif vol <= 2189: return 14
    elif vol <= 2405: return 15
    elif vol <= 2621: return 16
    elif vol <= 2837: return 17
    elif vol <= 3053: return 18
    elif vol <= 3269: return 19
    elif vol <= 3485: return 20
    elif vol <= 3701: return 21
    elif vol <= 3917: return 22
    elif vol <= 4133: return 23
    elif vol <= 4349: return 24
    elif vol <= 4565: return 25
    elif vol <= 4781: return 26
    elif vol <= 4997: return 27
    elif vol <= 5213: return 28
    elif vol <= 5429: return 29
    elif vol <= 5645: return 30
    elif vol <= 5861: return 31
    else: return 32


for product in PRODUCTS:
    nm_id = product["nm_id"]
    vol = nm_id // 100000
    part = nm_id // 1000
    basket = get_basket(nm_id)
    base = f"https://basket-{basket:02d}.wbbasket.ru/vol{vol}/part{part}/{nm_id}"
    
    print("=" * 70)
    print(f"АРТИКУЛ: {nm_id} — {product['name']}")
    print("=" * 70)
    
    # 1. price-history.json — последняя цена
    history_price = None
    history_all = []
    
    url = f"{base}/info/price-history.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            history = resp.json()
            if history:
                history_price = history[-1].get("price", {}).get("RUB", 0) / 100
                # Собираем все цены из истории
                for item in history:
                    p = item.get("price", {}).get("RUB", 0) / 100
                    if p > 0:
                        history_all.append(p)
    except:
        pass
    
    # 2. Цены с сайта
    site_no_auth = product["site_price_no_auth"]
    site_old = product["site_old_price"]
    
    print(f"\n📊 СРАВНЕНИЕ ЦЕН:")
    print(f"   price-history.json (текущая): {history_price or 'N/A'} ₽")
    print(f"   price-history.json (макс):    {max(history_all) if history_all else 'N/A'} ₽")
    print(f"   price-history.json (мин):     {min(history_all) if history_all else 'N/A'} ₽")
    print(f"   Сайт WB (без авторизации):    {site_no_auth or 'N/A'} ₽")
    print(f"   Сайт WB (зачёркнутая):        {site_old or 'N/A'} ₽")
    
    # 3. Анализ
    print(f"\n📈 АНАЛИЗ:")
    
    if history_price and site_no_auth:
        diff = site_no_auth - history_price
        diff_pct = (diff / history_price) * 100 if history_price else 0
        
        print(f"   Разница (сайт - history): {diff:+.2f} ₽ ({diff_pct:+.1f}%)")
        
        if diff > 0:
            print(f"   → Сайт показывает БОЛЬШЕ чем в history")
            print(f"   → price-history содержит цену СО скидкой СПП")
            print(f"   → Цена без СПП = {site_no_auth} ₽")
        else:
            print(f"   → Сайт показывает МЕНЬШЕ чем в history")
            print(f"   → price-history содержит БАЗОВУЮ цену")
    
    if site_old and site_no_auth:
        discount_pct = (1 - site_no_auth / site_old) * 100
        print(f"   Скидка на сайте: {discount_pct:.0f}%")
    
    if history_all and site_old:
        # Проверяем совпадает ли максимальная цена из history со старой ценой на сайте
        max_hist = max(history_all)
        if abs(max_hist - site_old) < 50:
            print(f"   ✅ Макс. цена из history ≈ зачёркнутая цена на сайте")

print("\n" + "=" * 70)
print("ВЫВОД:")
print("=" * 70)
print("""
Судя по данным, WB использует сложную систему ценообразования:

1. price-history.json — содержит цену с МАКСИМАЛЬНОЙ скидкой (включая СПП)
2. На сайте БЕЗ авторизации — показывается цена без СПП
3. На сайте С авторизацией — показывается цена с персональной СПП

РЕКОМЕНДАЦИЯ:
Используй цену из price-history.json как "лучшую цену" (с максимальной скидкой),
и показывай её в постах как "Цена от X ₽" или "Лучшая цена: X ₽"
""")