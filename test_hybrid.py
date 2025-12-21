import requests
import undetected_chromedriver as uc
import time

def get_wb_cookies():
    """Получает свежие cookies через Selenium"""
    print("Получаем cookies через браузер...")
    
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    driver = uc.Chrome(options=options)
    
    try:
        driver.get("https://www.wildberries.ru/")
        time.sleep(5)  # Ждём загрузки и выполнения JS
        
        # Собираем cookies
        cookies = {}
        for cookie in driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        
        print(f"✅ Получено cookies: {len(cookies)}")
        return cookies
        
    finally:
        try:
            driver.quit()
        except:
            pass


def test_api_with_cookies(cookies: dict):
    """Тестируем API с полученными cookies"""
    
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.wildberries.ru/",
        "x-requested-with": "XMLHttpRequest",
    }
    
    test_ids = [227648352, 443549513, 158173097]
    nm_string = ";".join(str(x) for x in test_ids)
    
    url = f"https://www.wildberries.ru/__internal/u-card/cards/v4/detail?appType=1&curr=rub&dest=12354108&spp=30&lang=ru&nm={nm_string}"
    
    print(f"\nЗапрос к API...")
    
    r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    print(f"Статус: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        products = data.get("data", {}).get("products", []) or data.get("products", [])
        print(f"✅ Товаров: {len(products)}")
        
        for p in products:
            nm = p.get("id")
            name = p.get("name", "")[:40]
            sizes = p.get("sizes", [{}])
            price_info = sizes[0].get("price", {}) if sizes else {}
            basic = price_info.get("basic", 0) / 100
            product_price = price_info.get("product", 0) / 100
            rating = p.get("reviewRating", 0)
            qty = p.get("totalQuantity", 0)
            
            print(f"\n📦 {nm}: {name}...")
            print(f"   Цена: {product_price}₽ (было {basic}₽)")
            print(f"   Рейтинг: {rating}, Остаток: {qty}")
        
        return True
    else:
        print(f"❌ Ошибка: {r.text[:200]}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("ГИБРИДНЫЙ ПОДХОД: Selenium для cookies + requests для API")
    print("="*60)
    
    # 1. Получаем cookies
    cookies = get_wb_cookies()
    
    if cookies:
        # 2. Используем их для API
        test_api_with_cookies(cookies)
    
    print("\n" + "="*60)
    print("ГОТОВО")
    print("="*60)