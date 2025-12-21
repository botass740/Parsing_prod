import requests
import json

PROXY_LOGIN = "23fmwsTtvu"
PROXY_PASSWORD = "Wx8hCmKzI5"
PROXY_IP = "45.132.252.132"
PROXY_PORT = "38267"

PROXY_URL = f"http://{PROXY_LOGIN}:{PROXY_PASSWORD}@{PROXY_IP}:{PROXY_PORT}"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

NM_ID = 169684889
vol = NM_ID // 100000  # 1696
part = NM_ID // 1000   # 169684
BASKET = "basket-12"

print("="*70)
print(f"ПОЛНЫЙ АНАЛИЗ ДАННЫХ BASKET ДЛЯ {NM_ID}")
print("="*70)

# Все возможные endpoints в basket
ENDPOINTS = [
    f"https://{BASKET}.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/ru/card.json",
    f"https://{BASKET}.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/price-history.json",
    f"https://{BASKET}.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/sellers.json",
    f"https://{BASKET}.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/ru/extras.json",
    f"https://{BASKET}.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/options.json",
    f"https://{BASKET}.wbbasket.ru/vol{vol}/part{part}/{NM_ID}/info/compositions.json",
]

for url in ENDPOINTS:
    filename = url.split("/")[-1]
    print(f"\n{'='*70}")
    print(f"[{filename}]")
    print(f"URL: {url}")
    
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
        print(f"Статус: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            
            # Красивый вывод JSON
            print(f"\n{json.dumps(data, ensure_ascii=False, indent=2)[:2000]}")
            
            if len(json.dumps(data)) > 2000:
                print("\n... (обрезано)")
                
        else:
            print(f"❌ Не найден")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# Отдельно feedbacks
print(f"\n{'='*70}")
print("[feedbacks]")
url = f"https://feedbacks1.wb.ru/feedbacks/v1/{NM_ID}"
print(f"URL: {url}")

try:
    r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=10)
    print(f"Статус: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        # Показываем только ключевые поля (без списка отзывов)
        summary = {
            "valuation": data.get("valuation"),
            "valuationSum": data.get("valuationSum"),
            "feedbackCount": data.get("feedbackCount"),
            "feedbackCountWithPhoto": data.get("feedbackCountWithPhoto"),
            "feedbackCountWithText": data.get("feedbackCountWithText"),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        
except Exception as e:
    print(f"❌ Ошибка: {e}")

print(f"\n{'='*70}")
print("ГОТОВО")
print("="*70)