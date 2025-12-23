# test_price_check.py

import requests
import time

def check_price():
    nm_id = 494949159
    
    print("Получаем cookies...")
    
    import undetected_chromedriver as uc
    
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = uc.Chrome(options=options)
    driver.get("https://www.wildberries.ru/")
    time.sleep(5)
    
    cookies = {}
    for cookie in driver.get_cookies():
        cookies[cookie['name']] = cookie['value']
    
    driver.quit()
    
    print(f"Cookies получены: {len(cookies)}")
    
    # Запрос
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.wildberries.ru/",
    }
    
    url = f"https://www.wildberries.ru/__internal/u-card/cards/v4/detail?appType=1&curr=rub&dest=12354108&spp=30&lang=ru&nm={nm_id}"
    
    resp = requests.get(url, headers=headers, cookies=cookies, timeout=30)
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        products = data.get("data", {}).get("products", [])
        if not products:
            products = data.get("products", [])
        
        if products:
            p = products[0]
            sizes = p.get("sizes", [])
            
            print(f"\n=== Товар {nm_id} ===")
            print(f"Название: {p.get('name')}")
            print(f"sale (скидка из API): {p.get('sale')}%")
            
            if sizes:
                price_info = sizes[0].get("price", {})
                print(f"\nЦены (в копейках / 100):")
                print(f"  basic (зачёркнутая): {price_info.get('basic', 0) / 100} ₽")
                print(f"  product (по карте): {price_info.get('product', 0) / 100} ₽")
                print(f"  total (кошелёк): {price_info.get('total', 0) / 100} ₽")
                
                # Все размеры
                print(f"\nВсе размеры ({len(sizes)}):")
                for i, size in enumerate(sizes[:5]):  # первые 5
                    sp = size.get("price", {})
                    print(f"  {i+1}. product={sp.get('product', 0)/100}₽, basic={sp.get('basic', 0)/100}₽")
        else:
            print("Товар не найден в ответе")
            print(f"Ответ: {data}")


if __name__ == "__main__":
    check_price()